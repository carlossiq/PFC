from app.core.services.report_review import (
    Suggestion,
    ai_review_scope,
    clean_replacements,
    filter_languagetool_matches,
    lint_latex,
    overlaps,
    review_scope,
    to_annotated_text,
    validate_ai_suggestion,
)

PREAMBLE = r"""\documentclass{article}
\newcommand{\figura}[3][O autor.]{\includegraphics{#3}}
\begin{document}
"""


def _doc(body: str) -> str:
    return PREAMBLE + body + "\n\\end{document}\n"


IMAGES = {"article_yearly_volume.png", "madeo.png"}


# ---------------------------------------------------------------- verificador de LaTeX


def _messages(tex: str, **kwargs) -> list[str]:
    return [issue.message for issue in lint_latex(tex, IMAGES, **kwargs)]


def test_valid_document_has_no_issues():
    tex = _doc(
        "\\section{RESULTADOS}\nCrescimento de 17,3\\% em P\\&D (SILVA et al., 2020).\n"
        "A Figura \\ref{fig:a} mostra.\n\\figura{Título.\\label{fig:a}}{article_yearly_volume.png}\n"
        "% comentário com _ e & liberados\n"
    )
    assert _messages(tex) == []


def test_preamble_macro_definitions_are_not_checked_as_calls():
    assert _messages(_doc("Texto.")) == []


def test_unescaped_special_chars_have_one_click_fix():
    issues = lint_latex(_doc("P&D em x_y e item #1."), IMAGES)
    fixes = {issue.replacement for issue in issues}
    assert fixes == {"\\&", "\\_", "\\#"}


def test_percent_after_number_is_flagged_because_it_silently_comments_out_the_line():
    issues = lint_latex(_doc("Crescimento de 17,3% no período."), IMAGES)
    assert len(issues) == 1 and issues[0].replacement == "\\%"


def test_braces_environments_images_refs_and_markers():
    tex = _doc(
        "Texto com {chave aberta.\n"
        "\\begin{itemize}\n\\item x\n"
        "Ver \\ref{quadro:inexistente} e [[FIG:article_x]].\n"
        "\\figura{Sem arquivo}{grafico_sumido.png}\n"
    )
    messages = " | ".join(_messages(tex))
    assert 'Chave "{" aberta' in messages
    assert "\\begin{itemize} nunca fechado" in messages
    assert 'Imagem "grafico_sumido.png" não existe' in messages
    assert "\\ref{quadro:inexistente} sem \\label" in messages
    assert 'Marcador interno "[[FIG:article_x]]"' in messages
    assert "sem escape" not in messages  # o "_" do marcador não conta


def test_content_after_end_document_and_compile_log():
    tex = _doc("Texto.") + "sobrou\n"
    messages = _messages(tex, compile_log="! Undefined control sequence.\nl.12 \\figuraa")
    assert any("depois de \\end{document}" in m for m in messages)
    assert any("Undefined control sequence" in m for m in messages)


# ---------------------------------------------------------------- escopo


def _report(conclusao: str = "Texto da conclusão gerado pela IA.") -> str:
    return _doc(
        "\\section{FINALIDADE}\nFrase fixa.\n"
        "\\section{METODOLOGIA}\nTexto fixo.\n\\subsection{Informações Científicas}\nTexto fixo 5.1.\n"
        "\\section{RESULTADOS}\n\\noindent\\begin{minipage}{\\textwidth}Quadro com queries\\end{minipage}\n"
        "\\subsection{Informações Científicas}\nTexto 6.1 gerado.\n"
        "\\figura{Legenda.}{article_yearly_volume.png}\n"
        f"\\section{{CONCLUSÃO}}\n{conclusao}\n"
        "\\section{REFERÊNCIAS BIBLIOGRÁFICAS}\nSILVA, J. Obra. 2020.\n"
    )


def _ai_scoped_text(tex: str, reason=None, baseline=None) -> str:
    return " ".join(
        tex[r.start:r.end] for r in ai_review_scope(tex, baseline) if reason is None or r.reason == reason
    )


def test_languagetool_scope_is_the_whole_body_except_the_search_box():
    tex = _report().replace(
        "Quadro com queries", "\\captionof{quadro}{Estratégias.\\label{quadro:busca}}Quadro com queries"
    )
    scoped = " ".join(tex[r.start:r.end] for r in review_scope(tex))
    for text in ("Frase fixa.", "Texto fixo 5.1.", "Texto 6.1 gerado.", "Legenda.", "Texto da conclusão", "SILVA, J."):
        assert text in scoped
    assert "Quadro com queries" not in scoped
    assert "\\documentclass" not in scoped  # preâmbulo fora
    assert {r.reason for r in review_scope(tex)} == {"languagetool"}


def test_ai_scope_is_ai_sections_only():
    tex = _report()
    scoped = _ai_scoped_text(tex)
    assert "Texto 6.1 gerado." in scoped and "Texto da conclusão" in scoped
    for fixed in ("Frase fixa.", "Texto fixo 5.1.", "Quadro com queries", "Legenda.", "SILVA, J."):
        assert fixed not in scoped


def test_edited_fixed_text_enters_ai_scope_but_references_never_do():
    baseline = _report()
    edited = baseline.replace("Texto fixo.", "Texto fixo alterado pelo analista.").replace(
        "SILVA, J. Obra. 2020.", "SILVA, J. Obra revisada. 2020."
    )
    scoped = _ai_scoped_text(edited, reason="editado", baseline=baseline)
    assert "Texto fixo alterado pelo analista." in scoped
    assert "Obra revisada" not in scoped


# ---------------------------------------------------------------- LanguageTool


def test_annotated_text_concatenates_back_to_the_original():
    fragment = "Cresceu 17,3\\% em P\\&D -- ver Figura \\ref{fig:x} e \\textit{probe}.\n\nNovo parágrafo."
    segments = to_annotated_text(fragment)
    assert "".join(s.text if s.text is not None else s.markup for s in segments) == fragment
    as_dicts = [s.to_dict() for s in segments]
    assert {"markup": "\\%", "interpretAs": "%"} in as_dicts
    assert {"markup": "\\ref{fig:x}", "interpretAs": "1"} in as_dicts


def test_annotated_text_hides_technical_latex_from_languagetool():
    fragment = (
        "\\begin{list}{}{\\setlength{\\leftmargin}{0pt}}\n\\item SILVA, J. Obra.\n\\end{list}\n"
        "\\figura[MADEO, 2019.]{Estágios da tecnologia.\\label{fig:madeo}}{madeo.png}\n"
        "\\rule{8cm}{0.4pt}\\\\\n\\textbf{Nome -- Posto}\\setcounter{page}{2}"
    )
    segments = to_annotated_text(fragment)
    assert "".join(s.text if s.text is not None else s.markup for s in segments) == fragment
    plain = "".join(s.text for s in segments if s.text is not None)
    for technical in ("list", "leftmargin", "0pt", "madeo.png", "fig:madeo", "8cm", "page", "MADEO"):
        assert technical not in plain
    for prose in ("SILVA, J. Obra.", "Estágios da tecnologia.", "Nome", "Posto"):
        assert prose in plain


def test_split_word_suggestion_becomes_the_real_word():
    assert clean_replacements("comumentemente", ["comumente mente"]) == ["comumente"]
    # divisão legítima continua valendo
    assert clean_replacements("derepente", ["de repente"]) == ["de repente"]
    assert clean_replacements("modulos", ["módulos", "módulos"]) == ["módulos"]


def _match(fragment: str, word: str, category: str = "TYPOS", rule: str = "MORFOLOGIK_RULE_PT_BR") -> dict:
    return {"offset": fragment.index(word), "length": len(word), "rule": {"id": rule, "category": {"id": category}}}


def test_false_positives_are_filtered_but_real_errors_kept():
    fragment = "As classificações H02S e CPC do PEI (SILVA et al., 2020) em \\textit{probe}. Os modulos cresceram."
    matches = [
        _match(fragment, "H02S"),
        _match(fragment, "CPC"),
        _match(fragment, "PEI"),
        _match(fragment, "SILVA"),
        _match(fragment, "probe"),
        _match(fragment, "modulos"),
    ]
    kept = [fragment[m["offset"]: m["offset"] + m["length"]] for m in filter_languagetool_matches(fragment, matches)]
    assert kept == ["modulos"]


def test_english_titles_are_not_spellchecked_but_nearby_portuguese_is():
    fragment = (
        "\\item LEZAMA, R. A bibliometric method for assessing the maturity. Scientometrics, 2018.\n"
        "Sistemas de rádio trunkados. A classificação H04L – TRANSMISSION OF DIGITAL INFORMATION FOR DATA ocupa a posição."
    )
    matches = [_match(fragment, "bibliometric"), _match(fragment, "method"), _match(fragment, "trunkados")]
    kept = [fragment[m["offset"]: m["offset"] + m["length"]] for m in filter_languagetool_matches(fragment, matches)]
    assert kept == ["trunkados"]


def test_uppercase_word_still_flagged_for_agreement_rules():
    fragment = "AS EMPRESA lideram."
    match = _match(fragment, "AS EMPRESA", category="GRAMMAR", rule="GENERAL_NUMBER_AGREEMENT_ERRORS")
    assert filter_languagetool_matches(fragment, [match]) == [match]


# ---------------------------------------------------------------- sugestões da IA


def test_ai_suggestion_must_only_change_words():
    fragment = "A concentração de depositantes (SILVA et al., 2020) indicam 17,3\\% de CPC H02S."
    assert validate_ai_suggestion(fragment, "depositantes (SILVA et al., 2020) indicam",
                                  "depositantes (SILVA et al., 2020) indica") is not None
    # muda número / citação / sigla / comando -> recusada
    assert validate_ai_suggestion(fragment, "17,3\\% de", "18,0\\% de") is None
    assert validate_ai_suggestion(fragment, "(SILVA et al., 2020) indicam", "(SOUZA et al., 2020) indica") is None
    assert validate_ai_suggestion(fragment, "CPC H02S", "IPC H02S") is None
    # trecho inexistente ou reescrita grande -> recusada
    assert validate_ai_suggestion(fragment, "não existe", "nada") is None
    assert validate_ai_suggestion(fragment, "A concentração de", "Observa-se que o conjunto formado por") is None


# Casos reais do gemma3:4b num REPTEC (todos aceitos pela validação antiga).
PARAGRAPH = (
    "Entre 2011 e 2019, observa-se um crescimento, com um pico de 2 publicações em 2019. "
    "A JSC lidera com 2 publicações, e a Hitachi LTD (4 registros) aparece com 1 registro. "
    "A tecnologia encontra-se no estágio de SATURAÇÃO, totalizando 12 e 29 documentos, respectivamente, "
    "atingindo um pico em 2019 com 28 patentes depositadas. Os dados mostra que as empresa relacionados crescem."
)


def test_ai_cannot_break_plural_after_numerals():
    assert validate_ai_suggestion(PARAGRAPH, "lidera com 2 publicações", "lidera com 2 publicação") is None
    assert validate_ai_suggestion(PARAGRAPH, "(4 registros)", "(4 registro)") is None
    assert validate_ai_suggestion(PARAGRAPH, "com 1 registro", "com 1 registros") is None


def test_ai_number_change_needs_an_agreeing_neighbor():
    fragment = "Observa-se um aumento no número de patentes e as empresa crescem com 3 depositante."
    assert validate_ai_suggestion(fragment, "número de patentes", "número de patente") is None
    assert validate_ai_suggestion(fragment, "as empresa", "as empresas") is not None
    assert validate_ai_suggestion(fragment, "3 depositante", "3 depositantes") is not None


def test_ai_cannot_change_style_tense_or_use_european_spelling():
    assert validate_ai_suggestion(PARAGRAPH, "estágio de SATURAÇÃO", "estágio de saturação") is None
    assert validate_ai_suggestion(PARAGRAPH, "em 2019 com 28", "em 2019, com 28") is None
    assert validate_ai_suggestion(PARAGRAPH, "Entre 2011 e 2019, observa-se", "Entre 2011 e 2019, observou-se") is None
    assert validate_ai_suggestion(PARAGRAPH, "documentos, respectivamente", "documentos, respetivamente") is None


def test_ai_agreement_and_accent_fixes_still_pass():
    assert validate_ai_suggestion(PARAGRAPH, "Os dados mostra", "Os dados mostram") is not None
    assert validate_ai_suggestion(PARAGRAPH, "as empresa relacionados", "as empresas relacionadas") is not None
    fragment = "Os modulos foi instalados e a analise esta pronta."
    assert validate_ai_suggestion(fragment, "modulos foi instalados", "módulos foram instalados") is not None
    assert validate_ai_suggestion(fragment, "analise esta", "análise está") is not None


def test_overlap_detection_for_dedup():
    a = Suggestion(10, 5, "x", [], "", "", "languagetool")
    assert overlaps(a, Suggestion(12, 2, "y", [], "", "", "ia"))
    assert not overlaps(a, Suggestion(20, 2, "y", [], "", "", "ia"))
