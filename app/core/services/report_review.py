"""
Revisão do .tex do relatório no editor (botão "Revisão") - funções puras:

1. `lint_latex`: problemas de LaTeX que quebram ou atrapalham a compilação
   (chaves/ambientes desbalanceados, caractere especial sem escape, imagem
   inexistente, \\ref sem \\label, marcadores [[FIG]] que sobraram...) e os
   erros do log da última compilação, com a linha no .tex.
2. Escopo da revisão de LÍNGUA:
   - `review_scope` (LanguageTool): o corpo INTEIRO do documento, por
     seção - o .tex todo é editável. Só o Quadro de busca fica de fora (as
     queries são sintaxe de busca, não texto; "corrigir" alteraria a
     estratégia relatada).
   - `ai_review_scope` (IA, mais cara): só as seções redigidas por IA
     (Objetivo, Introdução, 6.1-6.3, Conclusão) e as linhas que o usuário
     editou em relação à versão montada (`baseline`).
3. `to_annotated_text`: converte um trecho de LaTeX no formato "annotated
   text" da API do LanguageTool - comandos/argumentos técnicos viram markup
   (não são analisados) e as posições devolvidas batem com o .tex original.
4. `filter_languagetool_matches`: descarta falsos positivos do nosso texto
   (códigos CPC, siglas/nomes em maiúsculas, citações, termos em itálico).
5. `validate_ai_suggestion`: só aceita correção da IA que é flexão
   (concordância) ou acentuação - comandos, números, citações e siglas
   intactos, plural após numeral preservado, nada de estilo/pontuação/tempo
   verbal.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------


@dataclass
class LatexIssue:
    line: int
    message: str
    severity: str = "error"  # "error" (quebra a compilação) | "warning"
    offset: Optional[int] = None
    length: int = 0
    # Correção de um clique, quando existe (substitui [offset, offset+length)).
    replacement: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Suggestion:
    offset: int
    length: int
    original: str
    replacements: list[str]
    message: str
    category: str
    source: str  # "languagetool" | "ia"
    rule_id: str = ""
    section: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScopeRange:
    start: int
    end: int
    section: str
    reason: str  # "languagetool" (documento inteiro) | "ia" | "editado" (escopo da IA)


@dataclass
class AnnotatedSegment:
    text: Optional[str] = None
    markup: Optional[str] = None
    interpret_as: Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        if self.text is not None:
            return {"text": self.text}
        item = {"markup": self.markup or ""}
        if self.interpret_as is not None:
            item["interpretAs"] = self.interpret_as
        return item


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _body_start(text: str) -> int:
    idx = text.find(r"\begin{document}")
    return idx + len(r"\begin{document}") if idx != -1 else 0


def _mask_comments(text: str) -> str:
    """Troca comentários (% até o fim da linha, sem ser \\%) por espaços -
    mantém as posições."""
    return re.sub(r"(?<!\\)%[^\n]*", lambda m: " " * len(m.group(0)), text)


# Argumentos técnicos (rótulos, arquivos, URLs) - podem ter "_" etc.
# legitimamente; mascarados antes das checagens de escape.
_TECHNICAL_ARG_RE = re.compile(
    r"\\(?:label|ref|pageref\*?|eqref|cite|url|href|includegraphics(?:\[[^\]]*\])?|input|include)\{[^{}]*\}"
)
_FIGURE_MACRO_RE = re.compile(r"\\(figura|quadroimg)(\[[^\]]*\])?")


def _brace_group_end(text: str, start: int) -> int:
    """Índice logo após o grupo {...} que começa em `start` (text[start]
    deve ser "{"), respeitando aninhamento e \\{ \\}. -1 se não fechar."""
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _figure_calls(text: str) -> list[tuple[int, int, str, list[str]]]:
    """(início, fim, macro, argumentos obrigatórios) de cada \\figura/\\quadroimg."""
    calls = []
    for match in _FIGURE_MACRO_RE.finditer(text):
        pos = match.end()
        args: list[str] = []
        while len(args) < 2:
            while pos < len(text) and text[pos] in " \t":
                pos += 1
            if pos >= len(text) or text[pos] != "{":
                break
            end = _brace_group_end(text, pos)
            if end == -1:
                break
            args.append(text[pos + 1 : end - 1])
            pos = end
        calls.append((match.start(), pos, match.group(1), args))
    return calls


# ---------------------------------------------------------------------------
# 1. Verificador de LaTeX
# ---------------------------------------------------------------------------

_ENV_RE = re.compile(r"\\(begin|end)\{([^{}]+)\}")
_INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}")
_LABEL_RE = re.compile(r"\\label\{([^{}]+)\}")
_REF_RE = re.compile(r"\\(?:ref|pageref\*?)\{([^{}]+)\}")
_MARKER_RE = re.compile(r"\[\[(?:FIG|REF):[^\]]*\]\]")
_LOG_ERROR_RE = re.compile(r"^! (.+?)$(?:.*?^l\.(\d+))?", re.MULTILINE | re.DOTALL)


def _check_braces(text: str, masked: str) -> list[LatexIssue]:
    issues: list[LatexIssue] = []
    stack: list[int] = []
    i = 0
    while i < len(masked):
        ch = masked[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            stack.append(i)
        elif ch == "}":
            if stack:
                stack.pop()
            else:
                issues.append(LatexIssue(_line_of(text, i), 'Chave "}" sem a "{" correspondente.', offset=i, length=1))
        i += 1
    for pos in stack[:5]:
        issues.append(LatexIssue(_line_of(text, pos), 'Chave "{" aberta e nunca fechada.', offset=pos, length=1))
    return issues


def _check_environments(text: str, masked: str) -> list[LatexIssue]:
    issues: list[LatexIssue] = []
    stack: list[tuple[str, int]] = []
    for match in _ENV_RE.finditer(masked):
        kind, name = match.group(1), match.group(2)
        if kind == "begin":
            stack.append((name, match.start()))
        elif stack and stack[-1][0] == name:
            stack.pop()
        else:
            expected = f" (esperado \\end{{{stack[-1][0]}}})" if stack else ""
            issues.append(
                LatexIssue(_line_of(text, match.start()), f"\\end{{{name}}} sem \\begin correspondente{expected}.",
                           offset=match.start(), length=len(match.group(0)))
            )
    for name, pos in stack:
        issues.append(LatexIssue(_line_of(text, pos), f"\\begin{{{name}}} nunca fechado com \\end{{{name}}}.",
                                 offset=pos, length=len(name) + 8))
    return issues


def _check_special_chars(text: str, masked: str) -> list[LatexIssue]:
    """Caracteres especiais sem escape no CORPO do texto (não no preâmbulo,
    onde "#1" dos \\newcommand é legítimo)."""
    issues: list[LatexIssue] = []
    body = _body_start(text)
    in_table = False
    for line_start, line in _iter_lines(masked):
        if line_start < body:
            continue
        if re.search(r"\\begin\{(tabularx?|tabular\*?)\}", line):
            in_table = True
        if re.search(r"\\end\{(tabularx?|tabular\*?)\}", line):
            in_table = False
            continue
        for match in re.finditer(r"(?<!\\)([_&#])", line):
            char = match.group(1)
            if char == "&" and in_table:
                continue
            pos = line_start + match.start()
            issues.append(
                LatexIssue(_line_of(text, pos), f'"{char}" sem escape no texto - use "\\{char}".',
                           offset=pos, length=1, replacement=f"\\{char}")
            )
    # "17,3%" sem escape vira comentário e apaga o resto da linha em silêncio.
    for match in re.finditer(r"(?<=\d)(?<!\\)%", text[body:]):
        pos = body + match.start()
        issues.append(
            LatexIssue(_line_of(text, pos), '"%" depois de número sem escape: o resto da linha vira comentário '
                       'e some do PDF - use "\\%".', offset=pos, length=1, replacement="\\%")
        )
    body_masked = masked[body:]
    dollars = [m.start() + body for m in re.finditer(r"(?<!\\)\$", body_masked)]
    if len(dollars) % 2:
        pos = dollars[-1]
        issues.append(LatexIssue(_line_of(text, pos), '"$" sem par (modo matemático aberto) - use "\\$" para o símbolo.',
                                 offset=pos, length=1, replacement="\\$"))
    return issues


def _iter_lines(text: str):
    start = 0
    for line in text.split("\n"):
        yield start, line
        start += len(line) + 1


def lint_latex(text: str, available_images: set[str], compile_log: Optional[str] = None) -> list[LatexIssue]:
    masked = _mask_comments(text)
    technical_masked = _TECHNICAL_ARG_RE.sub(lambda m: " " * len(m.group(0)), masked)
    # Marcadores [[FIG:...]] já têm aviso próprio - o "_" do id não conta.
    technical_masked = _MARKER_RE.sub(lambda m: " " * len(m.group(0)), technical_masked)
    # O 2º argumento de \figura/\quadroimg é nome de arquivo (pode ter "_").
    for start, end, _, args in _figure_calls(technical_masked):
        if len(args) == 2:
            file_arg = args[1]
            file_pos = technical_masked.rfind("{" + file_arg + "}", start, end)
            if file_pos != -1:
                technical_masked = (
                    technical_masked[:file_pos] + " " * (len(file_arg) + 2) + technical_masked[file_pos + len(file_arg) + 2:]
                )

    issues: list[LatexIssue] = []
    issues += _check_braces(text, masked)
    issues += _check_environments(text, masked)
    issues += _check_special_chars(text, technical_masked)

    # Imagens referenciadas que não existem entre gráficos/anexos/figuras fixas.
    # Só no corpo: o preâmbulo DEFINE \\figura/\\quadroimg (\\newcommand, com
    # "#3" no lugar do arquivo) - não são chamadas.
    body = _body_start(text)
    referenced: list[tuple[int, str]] = [
        (m.start(), m.group(1).strip()) for m in _INCLUDEGRAPHICS_RE.finditer(masked) if m.start() >= body
    ]
    for start, _, macro, args in _figure_calls(masked):
        if start < body:
            continue
        if len(args) < 2:
            issues.append(LatexIssue(_line_of(text, start), f"\\{macro} precisa de dois argumentos: {{título}}{{arquivo}}.",
                                     offset=start, length=len(macro) + 1))
        else:
            referenced.append((start, args[1].strip()))
    for pos, filename in referenced:
        if filename and filename not in available_images:
            issues.append(LatexIssue(_line_of(text, pos), f'Imagem "{filename}" não existe entre os gráficos e anexos '
                                     "desta sessão - a compilação vai falhar.", offset=pos))

    labels: dict[str, int] = {}
    for match in _LABEL_RE.finditer(masked):
        name = match.group(1)
        if name in labels:
            issues.append(LatexIssue(_line_of(text, match.start()), f'\\label{{{name}}} duplicado.', severity="warning",
                                     offset=match.start(), length=len(match.group(0))))
        labels[name] = match.start()
    for match in _REF_RE.finditer(masked):
        name = match.group(1)
        if name != "LastPage" and name not in labels:
            issues.append(LatexIssue(_line_of(text, match.start()), f'\\ref{{{name}}} sem \\label correspondente - '
                                     'vai aparecer "??" no PDF.', severity="warning", offset=match.start(),
                                     length=len(match.group(0))))

    for match in _MARKER_RE.finditer(masked):
        issues.append(LatexIssue(_line_of(text, match.start()), f'Marcador interno "{match.group(0)}" sobrou no texto.',
                                 offset=match.start(), length=len(match.group(0)), replacement=""))

    end_doc = masked.rfind(r"\end{document}")
    if end_doc != -1 and masked[end_doc + len(r"\end{document}"):].strip():
        pos = end_doc + len(r"\end{document}")
        issues.append(LatexIssue(_line_of(text, pos), "Há conteúdo depois de \\end{document} - ele é ignorado e não "
                                 "aparece no PDF.", severity="warning", offset=pos))

    if compile_log:
        issues += parse_compile_log(compile_log)

    return sorted(issues, key=lambda issue: (issue.line, issue.message))


def referenced_image_files(text: str) -> set[str]:
    """Arquivos de imagem que o .tex usa de fato (\\includegraphics e
    \\figura/\\quadroimg no corpo, fora de comentários) - o que entra no
    .zip de download do relatório."""
    masked = _mask_comments(text)
    body = _body_start(text)
    files = {m.group(1).strip() for m in _INCLUDEGRAPHICS_RE.finditer(masked) if m.start() >= body}
    files |= {args[1].strip() for start, _, _, args in _figure_calls(masked) if start >= body and len(args) == 2}
    return {f for f in files if f}


def parse_compile_log(log: str) -> list[LatexIssue]:
    """Erros do pdflatex ("! Undefined control sequence." ... "l.123 ...")."""
    issues = []
    for match in re.finditer(r"^! (.+)$", log, re.MULTILINE):
        tail = log[match.end(): match.end() + 1500]
        line_match = re.search(r"^l\.(\d+)", tail, re.MULTILINE)
        line = int(line_match.group(1)) if line_match else 0
        issues.append(LatexIssue(line, f"Erro da última compilação: {match.group(1).strip()}"))
    return issues[:10]


# ---------------------------------------------------------------------------
# 2. Escopo da revisão de língua
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"^\\(section|subsection)\*?\{([^{}]*)\}\s*$", re.MULTILINE)

# Seções redigidas por IA (títulos do template, em qualquer caixa - relatórios
# antigos tinham subseções em MAIÚSCULAS). Subseções de Resultados só contam
# DENTRO de "RESULTADOS" (5.1/5.2 têm os mesmos nomes e são texto fixo).
_AI_SECTIONS = {"objetivo", "introdução", "conclusão"}
_AI_RESULT_SUBSECTIONS = {
    "informações científicas",
    "informações tecnológicas",
    "tendências e ciclo de vida da tecnologia",
}

# Blocos nunca revisados, mesmo editados: quadro de busca (queries), figuras,
# lista de referências e assinaturas.
_NEVER_REVIEW_RE = re.compile(
    r"\\noindent\\begin\{minipage\}.*?\\end\{minipage\}"
    r"|^\\(?:figura|quadroimg)\b[^\n]*$"
    r"|\\begin\{(?:list|itemize|enumerate|tabularx|figure)\}.*?\\end\{(?:list|itemize|enumerate|tabularx|figure)\}",
    re.MULTILINE | re.DOTALL,
)


def _sections(text: str) -> list[tuple[int, int, str, Optional[str]]]:
    """(início do conteúdo, fim, título, seção-pai) de cada \\section/\\subsection."""
    headers = list(_SECTION_RE.finditer(text))
    result = []
    parent: Optional[str] = None
    for idx, header in enumerate(headers):
        kind, title = header.group(1), header.group(2).strip()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(text)
        if kind == "section":
            parent = title
            result.append((header.end(), end, title, None))
        else:
            result.append((header.end(), end, title, parent))
    return result


def _edited_ranges(text: str, baseline: str) -> list[tuple[int, int]]:
    """Faixas (offsets no texto ATUAL) das linhas inseridas/alteradas."""
    current_lines = text.split("\n")
    matcher = difflib.SequenceMatcher(a=baseline.split("\n"), b=current_lines, autojunk=False)
    line_starts = [0]
    for line in current_lines:
        line_starts.append(line_starts[-1] + len(line) + 1)
    ranges = []
    for tag, _, _, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert") and j2 > j1:
            ranges.append((line_starts[j1], line_starts[j2] - 1))
    return ranges


def _subtract(ranges: list[tuple[int, int]], holes: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result = []
    for start, end in ranges:
        pieces = [(start, end)]
        for hole_start, hole_end in holes:
            next_pieces = []
            for a, b in pieces:
                if hole_end <= a or hole_start >= b:
                    next_pieces.append((a, b))
                    continue
                if a < hole_start:
                    next_pieces.append((a, hole_start))
                if hole_end < b:
                    next_pieces.append((hole_end, b))
            pieces = next_pieces
        result.extend(pieces)
    return result


# Quadro de busca (queries): a minipage do Quadro "Estratégias de busca" -
# sintaxe de busca em inglês, nunca texto corrido.
_SEARCH_BOX_RE = re.compile(
    r"\\noindent\\begin\{minipage\}(?:(?!\\end\{minipage\}).)*?quadro:busca.*?\\end\{minipage\}",
    re.DOTALL,
)


def _body_end(text: str) -> int:
    idx = text.find(r"\end{document}")
    return idx if idx != -1 else len(text)


def review_scope(text: str) -> list[ScopeRange]:
    """Escopo do LanguageTool: o corpo inteiro (capa, sumário, todas as
    seções, legendas, referências e assinaturas), fatiado por seção - só o
    Quadro de busca fica de fora. Comandos LaTeX não são "retirados" aqui:
    `to_annotated_text` os manda como markup."""
    body, end = _body_start(text), _body_end(text)
    holes = [(m.start(), m.end()) for m in _SEARCH_BOX_RE.finditer(text)]
    cuts = [body] + [start for start, _, _, _ in _sections(text) if body < start < end] + [end]
    # Cada fatia começa no fim do cabeçalho \section{...}; o próprio título
    # entra na fatia anterior (é texto revisável também).
    ranges: list[ScopeRange] = []
    sections = _sections(text)

    def section_of(offset: int) -> str:
        for start, stop, title, parent in sections:
            if start <= offset < stop:
                return f"{parent} › {title}" if parent else title
        return "Capa e Sumário"

    for a, b in zip(cuts, cuts[1:]):
        for start, stop in _subtract([(a, b)], holes):
            ranges.append(ScopeRange(start, stop, section_of(start), "languagetool"))
    return [r for r in ranges if re.search(r"[^\W\d_]{2,}", _mask_commands(text[r.start:r.end]))]


def ai_review_scope(text: str, baseline: Optional[str] = None) -> list[ScopeRange]:
    """Escopo da revisão por IA (uma chamada de LLM por parágrafo): seções
    redigidas por IA + linhas editadas pelo usuário."""
    body = _body_start(text)
    sections = _sections(text)
    never = [(m.start(), m.end()) for m in _NEVER_REVIEW_RE.finditer(text)]
    # Referências bibliográficas e assinaturas: do título até o fim.
    refs = re.search(r"^\\section\{REFER[ÊE]NCIAS BIBLIOGR[ÁA]FICAS\}", text, re.MULTILINE | re.IGNORECASE)
    if refs:
        never.append((refs.start(), len(text)))

    def section_of(offset: int) -> str:
        for start, end, title, parent in sections:
            if start <= offset < end:
                return f"{parent} › {title}" if parent else title
        return "Documento"

    ranges: list[ScopeRange] = []
    for start, end, title, parent in sections:
        lower = title.lower()
        is_ai = (parent is None and lower in _AI_SECTIONS) or (
            parent is not None and parent.lower() == "resultados" and lower in _AI_RESULT_SUBSECTIONS
        )
        if is_ai:
            for a, b in _subtract([(start, end)], never):
                ranges.append(ScopeRange(a, b, section_of(a), "ia"))

    if baseline:
        covered = [(r.start, r.end) for r in ranges]
        edited = [(a, b) for a, b in _edited_ranges(text, baseline) if a >= body]
        for a, b in _subtract(_subtract(edited, covered), never):
            ranges.append(ScopeRange(a, b, section_of(a), "editado"))

    # Descarta trechos sem texto de verdade (só quebras de linha/comandos
    # soltos entre dois blocos excluídos).
    ranges = [r for r in ranges if re.search(r"[^\W\d_]{2,}", _mask_commands(text[r.start:r.end]))]
    return sorted(ranges, key=lambda r: r.start)


def _mask_commands(fragment: str) -> str:
    return re.sub(r"\\[A-Za-z]+\*?|[{}]", " ", fragment)


# ---------------------------------------------------------------------------
# 3. LaTeX -> "annotated text" do LanguageTool
# ---------------------------------------------------------------------------

_ESCAPES = {r"\%": "%", r"\&": "&", r"\_": "_", r"\#": "#", r"\$": "$", "--": "–", "~": " "}
# Ordem importa: alternativas mais específicas primeiro.
_TOKEN_RE = re.compile(
    r"(?P<comment>(?<!\\)%[^\n]*)"
    # Argumento de ambiente + especificação de colunas de tabela
    # ("\begin{tabularx}{\textwidth}{|>{\raggedright}X|}") e opções de lista.
    r"|(?P<env>\\(?:begin|end)\{[^{}]*\}(?:\{(?:[^{}]|\{[^{}]*\})*\}){0,2}(?:\[[^\]]*\])?)"
    r"|(?P<silent>\\(?:label|setcounter|addtocounter|setlength|thispagestyle|pagestyle|captionsetup)"
    r"(?:\{[^{}]*\})+)"
    # \texttt: nomes de modelo na 5.4 ("gemma3:4b") - não são palavras.
    r"|(?P<techcmd>\\(?:ref|pageref\*?|cite|url|texttt|includegraphics(?:\[[^\]]*\])?)\{[^{}]*\})"
    # Nome de arquivo (último argumento de \figura/\quadroimg) e dimensões
    # soltas ("{0.4pt}", "{8cm}").
    r"|(?P<file>\{[\w\-.]+\.(?:png|jpe?g|pdf|eps)\})"
    r"|(?P<dimen>\{-?\d+(?:\.\d+)?(?:pt|cm|mm|em|ex|in)\})"
    r"|(?P<marker>\[\[(?:FIG|REF):[^\]]*\]\])"
    r"|(?P<linebreak>\\\\(?:\[[^\]]*\])?)"
    r"|(?P<space>\\[,;:! ])"
    r"|(?P<escape>\\[%&_#$]|--|~)"
    r"|(?P<cmd>\\[A-Za-z]+\*?(?:\[[^\]]*\])?)"
    r"|(?P<brace>[{}])"
    r"|(?P<parbreak>\n\s*\n)"
)


def to_annotated_text(fragment: str) -> list[AnnotatedSegment]:
    """Segmentos texto/markup cuja concatenação é EXATAMENTE `fragment` -
    assim os offsets do LanguageTool valem direto no .tex."""
    segments: list[AnnotatedSegment] = []
    pos = 0
    for match in _TOKEN_RE.finditer(fragment):
        if match.start() > pos:
            segments.append(AnnotatedSegment(text=fragment[pos: match.start()]))
        token = match.group(0)
        kind = match.lastgroup
        if kind == "escape":
            segments.append(AnnotatedSegment(markup=token, interpret_as=_ESCAPES[token]))
        elif kind == "parbreak":
            segments.append(AnnotatedSegment(markup=token, interpret_as="\n\n"))
        elif kind == "marker":
            segments.append(AnnotatedSegment(markup=token, interpret_as="Figura 1"))
        elif kind == "techcmd":
            segments.append(AnnotatedSegment(markup=token, interpret_as="1"))
        elif kind == "linebreak":
            segments.append(AnnotatedSegment(markup=token, interpret_as="\n"))
        elif kind == "space":
            segments.append(AnnotatedSegment(markup=token, interpret_as=" "))
        else:
            segments.append(AnnotatedSegment(markup=token))
        pos = match.end()
    if pos < len(fragment):
        segments.append(AnnotatedSegment(text=fragment[pos:]))
    return segments


# ---------------------------------------------------------------------------
# 4. Filtro de falsos positivos do LanguageTool
# ---------------------------------------------------------------------------

# Regras que só geram ruído em texto técnico gerado/escapado pra LaTeX.
DISABLED_LANGUAGETOOL_RULES = [
    "WHITESPACE_RULE",
    "UPPERCASE_SENTENCE_START",
    "COMMA_PARENTHESIS_WHITESPACE",
    "DOUBLE_PUNCTUATION",
    "UNPAIRED_BRACKETS",
    "PT_MULTI_SPACE",
    "HUNSPELL_RULE",
]

_CPC_RE = re.compile(r"^[A-HY]\d{2}[A-Z]?(\d{1,4}/\d{2,6})?$")
_CITATION_RE = re.compile(r"\([^()]*\b(?:1[5-9]|20)\d{2}[a-z]?\)")
_TEXTIT_RE = re.compile(r"\\textit\{[^{}]*\}")

# Siglas e termos do domínio que o dicionário pt-BR não conhece.
KNOWN_TERMS = {
    "cpc", "ipc", "ops", "epo", "scopus", "espacenet", "agitec", "reptec", "eb", "om", "ict", "ebt", "p&d",
    "llm", "pln", "ia", "gp", "mp", "sp", "cvt", "bm25f", "keybert", "rag", "probe", "et", "al", "loglet",
    "sigmaplot", "imbel", "diex", "dct", "patentária", "patentárias", "patentário", "patentários", "interciência",
}

# Palavras funcionais do inglês: 2+ delas (em minúsculas) perto da palavra
# marcam um título/trecho em inglês (típico das Referências) - o dicionário
# pt-BR só geraria ruído ali. Janela na mesma linha, e maiúsculas não
# contam: um parágrafo em português que cita um título CPC ("TRANSMISSION
# OF DIGITAL INFORMATION") continua revisado.
_ENGLISH_FUNCTION_WORDS = {"the", "of", "and", "for", "in", "on", "with", "using", "an", "to", "from", "by", "its"}
_ENGLISH_WINDOW = 80


def _in_english_context(fragment: str, offset: int) -> bool:
    line_start = fragment.rfind("\n", 0, offset) + 1
    line_end = fragment.find("\n", offset)
    line_end = line_end if line_end != -1 else len(fragment)
    window = fragment[max(line_start, offset - _ENGLISH_WINDOW): min(line_end, offset + _ENGLISH_WINDOW)]
    words = re.findall(r"[A-Za-z]+", window)
    return sum(word in _ENGLISH_FUNCTION_WORDS for word in words) >= 2


def _protected_spans(fragment: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _CITATION_RE.finditer(fragment)] + [
        (m.start(), m.end()) for m in _TEXTIT_RE.finditer(fragment)
    ]


# Só o que foi pedido: ortografia, acentuação, gramática/concordância e
# palavras trocadas - estilo, repetição, tipografia etc. ficam de fora (em
# texto técnico geram mais ruído que ajuda).
_ALLOWED_CATEGORIES = {"TYPOS", "MISSPELLING", "GRAMMAR", "CONFUSED_WORDS", "MISC"}


def filter_languagetool_matches(fragment: str, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    protected = _protected_spans(fragment)
    kept = []
    for match in matches:
        start, length = match["offset"], match["length"]
        word = fragment[start: start + length]
        rule_id = match.get("rule", {}).get("id", "")
        if match.get("rule", {}).get("category", {}).get("id", "") not in _ALLOWED_CATEGORIES and not (
            "CONCORD" in rule_id or "AGREEMENT" in rule_id
        ):
            continue
        if any(a <= start < b for a, b in protected):
            continue
        if _CPC_RE.match(word) or word.lower() in KNOWN_TERMS:
            continue
        if word.isascii() and _in_english_context(fragment, start):
            continue
        category = match.get("rule", {}).get("category", {}).get("id", "")
        # Sigla/nome próprio em maiúsculas ("PEI", "HUANENG") só é descartado
        # nas regras de ortografia - erro de concordância continua valendo.
        if category == "TYPOS" and len(word) >= 2 and word.isupper():
            continue
        if category == "TYPOS" and word[:1].isupper() and not word.isupper() and start > 0 and fragment[start - 2: start] != ". ":
            # Nome próprio no meio da frase (ex.: "Kucharavy", "Nanjing").
            continue
        kept.append(match)
    return kept


def clean_replacements(original: str, replacements: list[str]) -> list[str]:
    """O corretor do LanguageTool (Morfologik) propõe DIVIDIR uma palavra
    com sufixo duplicado: "comumentemente" -> "comumente mente" (aplicar
    criaria um erro novo). Quando a primeira parte já termina com a segunda,
    a correção real é só a primeira ("comumente"). Divisões legítimas
    ("derepente" -> "de repente") ficam como estão."""
    cleaned: list[str] = []
    for value in replacements:
        parts = value.split()
        if (
            len(parts) == 2
            and " " not in original.strip()
            and parts[0].lower().endswith(parts[1].lower())
            and (parts[0] + parts[1]).lower() == original.lower()
        ):
            value = parts[0]
        if value and value != original and value not in cleaned:
            cleaned.append(value)
    return cleaned


def languagetool_suggestions(fragment: str, base_offset: int, section: str,
                             matches: list[dict[str, Any]]) -> list[Suggestion]:
    suggestions = []
    for match in filter_languagetool_matches(fragment, matches):
        start, length = match["offset"], match["length"]
        rule = match.get("rule", {})
        original = fragment[start: start + length]
        suggestions.append(
            Suggestion(
                offset=base_offset + start,
                length=length,
                original=original,
                replacements=clean_replacements(original, [r["value"] for r in match.get("replacements", [])])[:5],
                message=match.get("message", ""),
                category=_category_label(rule.get("category", {}).get("id", ""), rule.get("id", "")),
                source="languagetool",
                rule_id=rule.get("id", ""),
                section=section,
            )
        )
    return suggestions


def _category_label(category_id: str, rule_id: str) -> str:
    if "CONCORD" in rule_id or "AGREEMENT" in rule_id or rule_id == "HAVER":
        return "concordância"
    return {
        "TYPOS": "ortografia",
        "MISSPELLING": "acentuação",
        "GRAMMAR": "gramática",
        "PUNCTUATION": "pontuação",
        "CONFUSED_WORDS": "palavra trocada",
        "MISC": "gramática",
        "STYLE": "estilo",
        "REDUNDANCY": "redundância",
    }.get(category_id, category_id.lower() or "outro")


# ---------------------------------------------------------------------------
# 5. Segunda opinião por IA - validação das sugestões
# ---------------------------------------------------------------------------

_PROTECTED_TOKEN_RE = re.compile(
    r"\\[A-Za-z]+\*?|[{}$&%#_]|\d+(?:[.,]\d+)*|\([^()]*\b(?:1[5-9]|20)\d{2}[a-z]?\)|\b[A-Z]{2,}[A-Z0-9]*\b"
)


def _protected_tokens(text: str) -> list[str]:
    return _PROTECTED_TOKEN_RE.findall(text)


_WORD_TOKEN_RE = re.compile(r"\w+|[^\w\s]")

# Flexões irregulares de concordância verbal que as regras de sufixo abaixo
# não cobrem (minúsculas, COM acento - "e" conjunção não vira "são").
_IRREGULAR_AGREEMENT = {frozenset(pair) for pair in (("foi", "foram"), ("é", "são"), ("há", "hão"))}


def _fold(word: str) -> str:
    """Minúsculas e sem acentos - "Publicações" -> "publicacoes"."""
    decomposed = unicodedata.normalize("NFD", word.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _inflection_kind(a: str, b: str) -> Optional[str]:
    """Que tipo de mudança é `a` -> `b`: "accent" (só acento), "verb"
    (pessoa/número do verbo), "number" (número nominal), "gender" - ou None
    se não for flexão (troca de palavra, de tempo verbal como "observa" ->
    "observou", grafia de Portugal como "respectivamente" -> "respetivamente").
    Só flexão e acento a revisão por IA pode propor."""
    fa, fb = _fold(a), _fold(b)
    if fa == fb:
        return "accent" if a.lower() != b.lower() else None  # caixa sozinha não conta
    if frozenset((a.lower(), b.lower())) in _IRREGULAR_AGREEMENT:
        return "verb"
    for x, y in ((fa, fb), (fb, fa)):
        if y == x + "m":  # mostra/mostram
            return "verb"
        if x.endswith("a") and y == x[:-1] + "ao":  # está/estão, será/serão
            return "verb"
        if x.endswith("ou") and y == x[:-2] + "aram":  # observou/observaram
            return "verb"
        if x.endswith(("eu", "iu")) and y == x[:-1] + "ram":  # cresceu/cresceram, contribuiu/contribuíram
            return "verb"
        if y in (x + "s", x + "es"):  # registro/registros
            return "number"
        if x.endswith("ao") and y in (x[:-2] + "oes", x[:-2] + "aes"):  # publicação/publicações
            return "number"
        if x.endswith("l") and y == x[:-1] + "is":  # ambiental/ambientais
            return "number"
    # Gênero, com ou sem plural: relacionado/relacionada(s).
    sa, sb = fa.rstrip("s"), fb.rstrip("s")
    if len(sa) == len(sb) > 2 and sa[:-1] == sb[:-1] and {sa[-1], sb[-1]} == {"a", "o"}:
        return "gender"
    return None


_PLURAL_DETERMINERS = {
    "os", "as", "dos", "das", "nos", "nas", "aos", "pelos", "pelas", "esses", "essas", "estes", "estas",
    "aqueles", "aquelas", "seus", "suas", "muitos", "muitas", "varios", "varias", "alguns", "algumas",
    "outros", "outras", "diversos", "diversas", "todos", "todas", "tais",
}
_SINGULAR_DETERMINERS = {
    "o", "a", "do", "da", "no", "na", "ao", "pelo", "pela", "esse", "essa", "este", "esta", "aquele",
    "aquela", "seu", "sua", "um", "uma", "cada", "outro", "outra",
}


def _word_number(word: str) -> Optional[bool]:
    """True = plural, False = singular, None = não dá pra dizer (preposição, verbo...)."""
    folded = _fold(word)
    if folded in _PLURAL_DETERMINERS:
        return True
    if folded in _SINGULAR_DETERMINERS:
        return False
    return None


def _has_number_evidence(tokens: list[str], index: int, corrected: str) -> bool:
    """Troca de número nominal só vale com um vizinho que concorde com a
    forma corrigida: determinante antes ("as empresa" -> "as empresas") ou
    palavra seguinte flexionada no mesmo número ("empresa relacionadas").
    Sem isso ("número de patentes" -> "número de patente") é palpite da IA."""
    want_plural = _is_plural(corrected)
    if index > 0 and _word_number(tokens[index - 1]) == want_plural:
        return True
    if index + 1 < len(tokens) and tokens[index + 1][:1].isalpha() and len(tokens[index + 1]) > 3:
        neighbor = tokens[index + 1]
        return _word_number(neighbor) == want_plural or (want_plural and _fold(neighbor).endswith("s"))
    return False


def _is_plural(word: str) -> bool:
    return _fold(word).endswith("s")


def _numeral_before(tokens: list[str], index: int) -> Optional[float]:
    """Valor do numeral imediatamente antes de tokens[index] ("com 2 publicações",
    "(4 registros)"); None se não houver. "17,3" conta como decimal (plural)."""
    if index == 0 or not tokens[index - 1].isdigit():
        return None
    value = float(tokens[index - 1])
    if index >= 3 and tokens[index - 2] in ",." and tokens[index - 3].isdigit():
        return value + 0.5  # parte decimal: nunca é exatamente 1
    return value


def validate_ai_suggestion(fragment: str, original: str, corrected: str) -> Optional[int]:
    """Posição de `original` em `fragment` se a correção for aceitável; None
    se não for. O trecho precisa existir literalmente (uma única vez); a
    correção não pode alterar comandos LaTeX, números, citações, siglas nem
    códigos, nem ser uma reescrita; e cada palavra trocada precisa ser só
    acentuação ou flexão de concordância. Mudança só de caixa, pontuação ou
    espaços é estilo (recusada), palavras não podem entrar/sair, e depois
    de um numeral o substantivo segue o número (plural se != 1)."""
    if not original or original == corrected or fragment.count(original) != 1:
        return None
    if _protected_tokens(original) != _protected_tokens(corrected):
        return None
    if difflib.SequenceMatcher(a=original, b=corrected).ratio() < 0.6:
        return None

    tokens_a = _WORD_TOKEN_RE.findall(original)
    tokens_b = _WORD_TOKEN_RE.findall(corrected)
    changed = False
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=tokens_a, b=tokens_b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag != "replace" or i2 - i1 != j2 - j1:
            return None  # palavra/pontuação inserida ou removida
        for offset in range(i2 - i1):
            a, b = tokens_a[i1 + offset], tokens_b[j1 + offset]
            kind = _inflection_kind(a, b) if a[:1].isalnum() and b[:1].isalnum() else None
            if kind is None:
                return None
            number = _numeral_before(tokens_a, i1 + offset)
            if number is not None and _is_plural(b) != (number != 1):
                return None
            if kind == "number" and number is None and not _has_number_evidence(tokens_b, j1 + offset, b):
                return None
            changed = True
    return fragment.index(original) if changed else None


def overlaps(a: Suggestion, b: Suggestion) -> bool:
    return a.offset < b.offset + max(b.length, 1) and b.offset < a.offset + max(a.length, 1)


@dataclass
class ReviewResult:
    latex_issues: list[LatexIssue] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)
    scope: list[ScopeRange] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
