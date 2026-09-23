"""
Extração dos campos estruturados (title/abstract/ipc/field_of_study) de
volta a partir do TEXTO de uma query - inverso dos query builders
(services/query_builders/ops_query_builder.py e scopus_query_builder.py).

Usado quando o usuário edita a query inteira como texto livre (caixa única
de edição do Step3/FinalExploration): sem isso, o card perdia o breakdown
por campo ao salvar, e a query deixava de ser "identificável" pelos termos
de título/resumo. Mesma simplificação de
ChatService._flatten_llm_response_fields: cada campo vira uma lista plana
de termos, sem a estrutura de grupos AND/OR.

Regras:
- Campos combinados (OPS `ta`/`txt`, Scopus `TITLE-ABS`/`TITLE-ABS-KEY`)
  contam como title E abstract, já que a busca olha os dois.
- Termos negados (qualquer operando de NOT) são ignorados - um termo
  excluído não identifica o que a query busca.
- Campos fora da UI (claims, pa, KEY, AUTH...) e a cláusula de data são
  ignorados (ano já vem de _extract_year_range_from_query).
"""

from __future__ import annotations

import re

# Sigla CQL (minúscula) -> campos da UI. Espelha _get_default_field_map de
# OPSQueryBuilder; "ic" é o alias oficial de "ipc" na CQL da OPS.
_OPS_FIELD_TARGETS: dict[str, tuple[str, ...]] = {
    "ti": ("title",),
    "ab": ("abstract",),
    "ta": ("title", "abstract"),
    "txt": ("title", "abstract"),
    "ipc": ("ipc",),
    "ic": ("ipc",),
}
_OPS_EMPTY: dict[str, list[str]] = {"title": [], "abstract": [], "ipc": []}

# Função Scopus (maiúscula) -> campos da UI. Espelha _get_default_field_map
# de ScopusQueryBuilder.
_SCOPUS_FIELD_TARGETS: dict[str, tuple[str, ...]] = {
    "TITLE": ("title",),
    "ABS": ("abstract",),
    "TITLE-ABS": ("title", "abstract"),
    "TITLE-ABS-KEY": ("title", "abstract"),
    "SUBJAREA": ("field_of_study",),
}
_SCOPUS_EMPTY: dict[str, list[str]] = {"title": [], "abstract": [], "field_of_study": []}

_QUOTED = r'"(?:[^"\\]|\\.)*"'
_BRACED = r"\{[^}]*\}"
_QUOTED_RE = re.compile(_QUOTED)

# Alternância com strings entre aspas/chaves de propósito: finditer as
# consome inteiras, então um "ti = x" DENTRO de um termo entre aspas nunca
# é confundido com um predicado.
_OPS_PREDICATE_RE = re.compile(
    rf'(?P<skip>{_QUOTED})'
    rf'|\b(?P<field>[A-Za-z]+)\s*(?:=|\b(?:all|any|exact)\b)\s*(?P<value>{_QUOTED}|[^\s()]+)',
    re.IGNORECASE,
)
_SCOPUS_FUNCTION_RE = re.compile(
    rf'(?P<skip>{_QUOTED}|{_BRACED})|(?<![\w-])(?P<field>[A-Za-z]+(?:-[A-Za-z]+)*)\s*\(',
)
_SCOPUS_TERM_RE = re.compile(rf'(?P<quoted>{_QUOTED})|(?P<braced>{_BRACED})')
_SCOPUS_OPERATOR_RE = re.compile(r'\b(?:AND|OR|W/\d+|PRE/\d+)\b', re.IGNORECASE)
_NOT_RE = re.compile(rf'(?P<skip>{_QUOTED}|{_BRACED})|\bNOT\b', re.IGNORECASE)
_NOT_OPERAND_RE = re.compile(
    rf'[A-Za-z\-]+\s*\('  # chamada de função Scopus: resolvida via parênteses
    rf'|[\w.\-]+\s*(?:=|\b(?:all|any|exact|within)\b)\s*(?:{_QUOTED}|[^\s()]+)'  # predicado OPS
    rf'|{_QUOTED}|{_BRACED}|[^\s()]+',
    re.IGNORECASE,
)


def _matching_paren(text: str, open_idx: int) -> int:
    """Índice do ")" que fecha o "(" em open_idx, ignorando aspas/chaves.
    Parênteses desbalanceados (usuário ainda editando) -> fim do texto."""
    depth = 0
    i = open_idx
    while i < len(text):
        ch = text[i]
        if ch == '"':
            m = _QUOTED_RE.match(text, i)
            i = m.end() if m else len(text)
            continue
        if ch == "{":
            end = text.find("}", i)
            i = end + 1 if end != -1 else len(text)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(text) - 1


def _strip_negations(query: str) -> str:
    """Remove cada NOT junto com seu operando (grupo entre parênteses,
    função Scopus, predicado OPS ou termo solto)."""
    while True:
        match = next((m for m in _NOT_RE.finditer(query) if not m.group("skip")), None)
        if match is None:
            return query
        start = match.start()
        pos = match.end()
        while pos < len(query) and query[pos].isspace():
            pos += 1
        if pos >= len(query):
            end = len(query)
        elif query[pos] == "(":
            end = _matching_paren(query, pos) + 1
        else:
            operand = _NOT_OPERAND_RE.match(query, pos)
            if operand is None:
                end = pos + 1
            elif operand.group(0).endswith("("):
                end = _matching_paren(query, operand.end() - 1) + 1
            else:
                end = operand.end()
        query = query[:start] + " " + query[end:]


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1].replace('\\"', '"')
    elif len(value) >= 2 and value[0] == "{" and value[-1] == "}":
        value = value[1:-1]
    return value.strip()


def _append(fields: dict[str, list[str]], targets: tuple[str, ...], term: str) -> None:
    if not term:
        return
    for target in targets:
        if term not in fields[target]:
            fields[target].append(term)


def _extract_ops(query: str) -> dict[str, list[str]]:
    fields = {k: [] for k in _OPS_EMPTY}
    for m in _OPS_PREDICATE_RE.finditer(query):
        if m.group("skip"):
            continue
        targets = _OPS_FIELD_TARGETS.get(m.group("field").lower())
        if targets:
            _append(fields, targets, _unquote(m.group("value")))
    return fields


def _scopus_terms(content: str) -> list[str]:
    """Termos dentro de TITLE(...)/ABS(...): entre aspas/chaves, ou trechos
    soltos separados por operadores/parênteses."""
    terms: list[str] = []

    def add_loose(chunk: str) -> None:
        for piece in re.split(r"[()|]", _SCOPUS_OPERATOR_RE.sub("|", chunk)):
            piece = " ".join(piece.split())
            if piece:
                terms.append(piece)

    pos = 0
    for m in _SCOPUS_TERM_RE.finditer(content):
        add_loose(content[pos : m.start()])
        terms.append(_unquote(m.group(0)))
        pos = m.end()
    add_loose(content[pos:])
    return terms


def _extract_scopus(query: str) -> dict[str, list[str]]:
    fields = {k: [] for k in _SCOPUS_EMPTY}
    pos = 0
    while True:
        m = _SCOPUS_FUNCTION_RE.search(query, pos)
        if m is None:
            return fields
        if m.group("skip"):
            pos = m.end()
            continue
        open_idx = m.end() - 1
        close_idx = _matching_paren(query, open_idx)
        targets = _SCOPUS_FIELD_TARGETS.get(m.group("field").upper())
        if targets:
            for term in _scopus_terms(query[open_idx + 1 : close_idx]):
                _append(fields, targets, term)
            pos = close_idx + 1
        else:
            # Função fora da UI (KEY, AUTH, PUBYEAR...) - pula só o nome,
            # pra ainda achar campos aninhados dentro dela, se houver.
            pos = m.end()


def extract_fields_from_query(query: str, api: str) -> dict[str, list[str]]:
    """{campo: [termos]} pros campos da UI da api (sem "year"). API não
    suportada -> {}."""
    query = _strip_negations(query or "")
    if api == "ops":
        return _extract_ops(query)
    if api == "scopus":
        return _extract_scopus(query)
    return {}
