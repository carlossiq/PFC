"""
Pós-processamento/validação do texto gerado pelo LLM pras seções do
relatório - texto PURO (antes de escape_latex).

- `fix_number_formatting`: corrige automaticamente o que é mecânico
  (ponto decimal -> vírgula; separador de milhar), sem regenerar.
- `find_text_issues`: detecta termos internos do pipeline e marcas de texto
  "genérico" que vazaram pro relatório - quem chama regenera a seção.
- `find_fact_issues`: detecta incoerência com os fatos calculados (número
  que não existe nos dados, ano usado como quantidade, "lidera" atribuído
  a quem não é o 1º do ranking, estágio do ciclo de vida contraditório,
  saturação > 100%, patentes chamadas de "publicações científicas").
"""

from __future__ import annotations

import re
from typing import Any, Optional

# "17.3%" / "0.311" -> "17,3%" / "0,311". Não mexe em "1.800" (3 dígitos
# depois do ponto e parte inteira curta = separador de milhar pt-BR já
# correto), em códigos ("H04W4/10", "5.0.1") nem em números colados a
# letras/barras.
_DECIMAL_RE = re.compile(r"(?<![\w./,])(\d+)\.(\d+)(?![\w/]|\.\d)")
# Inteiro de 4+ dígitos sem separador -> "1800" vira "1.800". Anos
# (1900-2099) ficam como estão.
_BIG_INT_RE = re.compile(r"(?<![\w./,\-])(\d{4,})(?![\w./,]|,\d)")


def _format_thousands(match: re.Match[str]) -> str:
    raw = match.group(1)
    value = int(raw)
    if len(raw) == 4 and 1900 <= value <= 2099:
        return raw
    return f"{value:,}".replace(",", ".")


def _fix_decimal(match: re.Match[str]) -> str:
    integer, fraction = match.group(1), match.group(2)
    if len(fraction) == 3 and len(integer) <= 3 and integer != "0":
        return match.group(0)  # já é milhar pt-BR ("1.800")
    return f"{integer},{fraction}"


def fix_number_formatting(text: str) -> str:
    text = _DECIMAL_RE.sub(_fix_decimal, text)
    return _BIG_INT_RE.sub(_format_thousands, text)


# (padrão, descrição do problema - vai pro prompt de regeneração)
_ISSUE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"informa[çc][ãa]o n[ãa]o dispon[íi]vel", re.IGNORECASE), 'marcador "[Informação não disponível]"'),
    (re.compile(r"\bN/A\b"), 'marcador "N/A"'),
    (re.compile(r"relev[âa]ncia\s*(?::|de)?\s*\d", re.IGNORECASE), "percentual de relevância/similaridade da busca"),
    (re.compile(r"\bFontes?\s*:", re.IGNORECASE), 'citação no formato "(Fonte: ...)"'),
    (re.compile(r"(contexto|dados|informa[çc][õo]es|documentos)\s+(fornecid|apresentad|recuperad)", re.IGNORECASE),
     'referência ao material de apoio ("contexto fornecido", "dados apresentados"...)'),
    (re.compile(r"n[ãa]o revel[ea]m? achados", re.IGNORECASE), "frase sobre ausência de achados"),
    (re.compile(r",\s*,|\(\s*[,;]?\s*\)|\(\s*,"), "lista ou parênteses vazios"),
    (re.compile(r"\brecomendamos\b|\bobservamos\b|\bconclu[íi]mos\b", re.IGNORECASE),
     'primeira pessoa do plural (use a forma impessoal: "recomenda-se")'),
]


def find_text_issues(text: str) -> list[str]:
    return [label for pattern, label in _ISSUE_PATTERNS if pattern.search(text)]


# ---------------------------------------------------------------------------
# Coerência com os fatos calculados (números, ranking, estágio, vocabulário)
# ---------------------------------------------------------------------------
# `facts` (montado em report_document_router._fact_check):
#   counts: list[int]  - toda quantidade que existe nos dados da seção
#   leaders: list[str] - 1º colocado de cada ranking da seção
#   stages: {"article"?, "patent"?, "overall"?} - estágio calculado de cada curva
#   document_type: "patent" | "article" | None - de que a seção trata

_COUNT_NOUN = (
    r"(?:publica[çc](?:[ãa]o|[õo]es)(?:\s+cient[íi]ficas?)?|artigos?|patentes?|registros?|dep[óo]sitos?|"
    r"documentos?|depositantes?|institui[çc](?:[ãa]o|[õo]es)|empresas?)"
)
_COUNT_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+|\d+)\s+(" + _COUNT_NOUN + r")\b", re.IGNORECASE)
_LEAD_RE = re.compile(r"\blider(?:a|am|ando|ou|an[çc]a)\b|\bem primeiro lugar\b|\bprimeira posi[çc][ãa]o\b", re.IGNORECASE)
_LEADER_GENERIC = {
    "university", "universidade", "universite", "inc", "ltd", "corp", "corporation", "company", "institute",
    "instituto", "limited", "llc", "gmbh", "the", "and", "technology", "technologies", "co",
}
_STAGE_RE = re.compile(
    r"(?:est[áa]gio|fase)\s+(?:de\s+|da\s+)?(emergente|crescimento|maturidade|satura[çc][ãa]o)"
    r"|atingi\w*\s+(?:o\s+|seu\s+|a\s+|sua\s+)?(?:est[áa]gio\s+de\s+|fase\s+de\s+)?(maturidade|satura[çc][ãa]o)",
    re.IGNORECASE,
)
_SATURATION_PCT_RE = re.compile(r"satura[çc][ãa]o[^.%]{0,60}?(\d{3,}(?:,\d+)?)\s*%", re.IGNORECASE)
_WRONG_VOCABULARY = {
    "patent": (re.compile(r"publica[çc][õo]es\s+cient[íi]ficas|\bartigos?\b", re.IGNORECASE),
               'esta subseção trata de PATENTES - não as chame de "publicações científicas"/"artigos"'),
    "article": (re.compile(r"\bpatentes?\b|\bdep[óo]sitos?\b", re.IGNORECASE),
                "esta subseção trata de PUBLICAÇÕES CIENTÍFICAS - não fale de patentes/depósitos"),
}
_LEAD_WINDOW = 60


def _to_int(raw: str) -> int:
    return int(raw.replace(".", ""))


def _stage_key(stage: str) -> str:
    return stage.lower().replace("ç", "c").replace("ã", "a")


def _leader_tokens(name: str) -> set[str]:
    words = re.findall(r"[^\W\d_]{4,}", name.lower())
    return {w for w in words if w not in _LEADER_GENERIC}


def _count_issues(text: str, counts: set[int]) -> list[str]:
    issues = []
    for match in _COUNT_RE.finditer(text):
        value, phrase = _to_int(match.group(1)), match.group(0)
        if 1900 <= value <= 2100 and value not in counts:
            issues.append(f'ano usado como quantidade: "{phrase}" (anos não são contagens de documentos)')
        elif counts and value not in counts and value > 10:
            issues.append(f'quantidade que não existe nos dados: "{phrase}" - use só os números dos "Dados"')
    return issues


def _leader_issues(text: str, leaders: list[str]) -> list[str]:
    token_sets = [(name, _leader_tokens(name)) for name in leaders]
    token_sets = [(name, tokens) for name, tokens in token_sets if tokens]
    if not token_sets:
        return []
    issues = []
    for match in _LEAD_RE.finditer(text):
        before = text[max(0, match.start() - _LEAD_WINDOW): match.start()].lower()
        after = text[match.end(): match.end() + 25].lower()
        if not any(any(t in before or t in after for t in tokens) for _, tokens in token_sets):
            names = " / ".join(name for name, _ in token_sets)
            issues.append(f'"{match.group(0)}" atribuído à entidade errada - quem lidera (1º do ranking) é {names}')
    return issues


def _doc_types_in(passage: str) -> set[str]:
    lower = passage.lower()
    found = set()
    if re.search(r"patente|dep[óo]sit", lower):
        found.add("patent")
    if re.search(r"artigo|cient[íi]fic|publica[çc]", lower):
        found.add("article")
    return found


def _stage_issues(text: str, stages: dict[str, str]) -> list[str]:
    if not stages:
        return []
    issues = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph_types = _doc_types_in(paragraph)
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            for match in _STAGE_RE.finditer(sentence):
                mentioned = _stage_key(match.group(1) or match.group(2))
                types = _doc_types_in(sentence) or paragraph_types
                expected = {stages[t] for t in types if stages.get(t)} or (
                    {stages["overall"]} if stages.get("overall") else set()
                )
                if expected and mentioned not in {_stage_key(s) for s in expected}:
                    issues.append(
                        f'estágio "{match.group(0)}" contradiz o estágio calculado ({" / ".join(sorted(expected))})'
                    )
    return issues


def find_fact_issues(text: str, facts: Optional[dict[str, Any]]) -> list[str]:
    """Incoerências do texto com os fatos calculados em Python - quem chama
    regenera UMA vez e, se persistirem, devolve como aviso (não bloqueia:
    um falso positivo não pode impedir o relatório)."""
    if not facts:
        return []
    issues = _count_issues(text, set(facts.get("counts") or []))
    issues += _leader_issues(text, list(facts.get("leaders") or []))
    issues += _stage_issues(text, dict(facts.get("stages") or {}))
    for match in _SATURATION_PCT_RE.finditer(text):
        if float(match.group(1).replace(",", ".")) > 100:
            issues.append(
                f'saturação acima de 100% ("{match.group(1)}%") - diga que o total observado já supera o platô estimado'
            )
    vocabulary = _WRONG_VOCABULARY.get(facts.get("document_type") or "")
    if vocabulary and vocabulary[0].search(text):
        issues.append(vocabulary[1])
    return list(dict.fromkeys(issues))
