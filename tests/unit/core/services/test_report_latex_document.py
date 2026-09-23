import pytest
from fastapi import HTTPException

from app.adapters.driving.http.report_document_router import (
    _attachment_filename,
    _ATTACHMENT_FILENAME_RE,
    _CHART_CAPTIONS,
    _quadro_busca_cell,
)
from config.prompts.report_latex_template import render_report_latex
from config.prompts.report_static_sections import (
    DEFAULT_BIBLIOGRAPHY,
    legacy_metodologia_to_paragraph,
    merge_bibliography,
    render_metodologia,
)


# ---------------------------------------------------------------- metodologia


def test_metodologia_omits_keywords_period_and_databases_when_missing():
    text = render_metodologia([], None, None, [])

    assert "palavras-chave" not in text
    assert "não especificad" not in text
    assert text.startswith("O conjunto de dados entabulado se constitui")


def test_metodologia_with_all_data():
    text = render_metodologia(["solar panel", "photovoltaic"], 2000, 2026, ["Espacenet (EPO/OPS)", "Scopus"])

    assert "palavras-chave solar panel e photovoltaic." in text
    assert "acumulado até 2026 (a partir de 2000) para patentes e artigos" in text
    assert "das bases de dados Espacenet (EPO/OPS) e Scopus" in text


def test_legacy_metodologia_keeps_only_last_paragraph_without_placeholders():
    old = (
        "Os estudos de prospecção tecnológica, também chamados...\n\n"
        "A análise de tendências...\n\n"
        "Para o presente estudo, foram empregadas as palavras-chave [não especificadas], com dados "
        "acumulados até 2026 (a partir de 2000 quando disponível), utilizando as bases de dados Scopus. "
        "O conjunto de dados entabulado..."
    )

    paragraph = legacy_metodologia_to_paragraph(old)

    assert paragraph.startswith("Para o presente estudo, foram utilizados dados acumulados até 2026")
    assert "não especificad" not in paragraph


def test_legacy_metodologia_leaves_new_format_untouched():
    assert legacy_metodologia_to_paragraph("Neste relatório, ...") == "Neste relatório, ..."


def test_merge_bibliography_adds_defaults_dedupes_and_sorts():
    stored = [DEFAULT_BIBLIOGRAPHY[1], "ZULU, A. Obra adicionada pelo usuário."]

    merged = merge_bibliography(DEFAULT_BIBLIOGRAPHY, stored)

    assert len(merged) == len(DEFAULT_BIBLIOGRAPHY) + 1
    assert merged == sorted(merged, key=str.casefold)
    assert merged[-1].startswith("ZULU")


def test_bibliography_covers_every_work_cited_by_the_fixed_text():
    template = render_report_latex({})
    for author in ("ANDRADE", "BORSCHIVER", "DAIM", "ERNST", "FRANÇA", "KUCHARAVY", "LEZAMA-NICOLÁS",
                   "LINDEN", "MADEO", "NIETO", "PORTER"):
        assert author in template
        assert any(ref.startswith(author) for ref in DEFAULT_BIBLIOGRAPHY), author


# ---------------------------------------------------------------- template


def _render(**overrides):
    return render_report_latex({"numero": "001", "ano": "2026", "tema": "placas solares", **overrides})


def test_template_header_footer_and_uppercase_sections():
    tex = _render()

    assert r"\fancyhead[C]{\small REPTEC 001/2026 -- \MakeUppercase{placas solares}}" in tex
    assert r"Página \thepage\ de \pageref*{LastPage}" in tex
    for title in ("FINALIDADE", "METODOLOGIA", "RESULTADOS", "CONCLUSÃO", "REFERÊNCIAS BIBLIOGRÁFICAS"):
        assert rf"\section{{{title}}}" in tex
    for title in ("INFORMAÇÕES CIENTÍFICAS", "INFORMAÇÕES TECNOLÓGICAS"):
        assert tex.count(rf"\subsection{{{title}}}") == 2  # 5.x e 6.x


def test_template_fixed_metodologia_figures():
    tex = _render()

    assert r"{madeo.png}" in tex
    assert r"{kucharavy.png}" in tex
    assert "Fonte: #1" in tex  # macro \figura: "Fonte" abaixo de toda figura


def test_template_charts_use_figura_macro_with_caption():
    tex = _render(charts_cientificas=[{"filename": "article_yearly_volume.png", "caption": "Artigos por Ano"}])

    assert r"\figura{Artigos por Ano}{article_yearly_volume.png}" in tex


def test_template_quadro_table():
    tex = _render(quadro_busca={"patente": "Patentes (1.800) = q1", "artigo": "Artigos (444) = q2"})

    assert r"\captionof{quadro}" in tex
    assert r"Patentes (1.800) = q1 & Artigos (444) = q2 \\" in tex


def test_template_signatures_are_centered_and_bold():
    tex = _render(
        assinaturas={
            "elaborado_por": [{"nome": "FULANO", "posto_funcao": "TC"}],
            "revisado_por": [],
            "revisado_por_comment": "%",
            "aprovado_por": [],
            "aprovado_por_comment": "%",
        }
    )

    assert "\\begin{center}\n\\vspace{1cm}\n\\rule{8cm}{0.4pt}\\\\\n\\textbf{FULANO}\\\\\n\\textbf{TC}\n\\end{center}" in tex


# ---------------------------------------------------------------- router helpers


def test_quadro_cell_formats_count_pt_br_and_escapes_query():
    assert _quadro_busca_cell("Patentes", 'ti = "a_b"', 1800) == 'Patentes (1.800) = ti = "a\\_b"'
    assert _quadro_busca_cell("Artigos", None, 10) == "—"
    assert _quadro_busca_cell("Artigos", "q", None) == "—"


def test_chart_whitelist_excludes_legacy_charts():
    allowed = {chart_type for _, chart_type in _CHART_CAPTIONS}

    assert allowed == {"s_curve", "top_depositants", "top_institutions", "yearly_volume", "top10_heatmap"}
    assert _CHART_CAPTIONS[("article", "yearly_volume")] == "Artigos por Ano"
    assert "CPC" in _CHART_CAPTIONS[("patent", "top10_heatmap")]


def test_attachment_filename_is_latex_safe_and_unique():
    assert _attachment_filename("Minha Figura_1 (ã).PNG", set()) == "anexo-minha-figura-1-a.png"
    assert _attachment_filename("foto.jpeg", {"anexo-foto.jpeg"}) == "anexo-foto-2.jpeg"
    assert _ATTACHMENT_FILENAME_RE.match("anexo-foto-2.jpeg")
    assert not _ATTACHMENT_FILENAME_RE.match("patent_top10_heatmap.png")
    with pytest.raises(HTTPException):
        _attachment_filename("documento.pdf", set())
