"""
Pós-processamento/validação do texto gerado pelo LLM pras seções do
relatório - texto PURO (antes de escape_latex).

- `fix_number_formatting`: corrige automaticamente o que é mecânico
  (ponto decimal -> vírgula; separador de milhar), sem regenerar.
- `find_text_issues`: detecta termos internos do pipeline e marcas de texto
  "genérico" que vazaram pro relatório - quem chama regenera a seção.
"""

from __future__ import annotations

import re

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
