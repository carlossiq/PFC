from datetime import date

from app.core.services.cpc_titles import describe_code
from app.core.services.report_citations import (
    build_citation,
    build_reference,
    disambiguate,
    filter_citations,
    references_for_text,
)
from app.core.services.report_form_validation import (
    admin_reference_error,
    bibliography_error,
    destinatario_error,
    signer_error,
)
from app.core.services.report_lifecycle import (
    build_lifecycle,
    complete_years_only,
    lifecycle_stage,
    summary_text,
    yearly_summary,
)
from app.core.services.report_text_quality import find_fact_issues, find_text_issues, fix_number_formatting
from config.prompts.report_static_sections import render_finalidade, render_local_data

# ---------------------------------------------------------------- ciclo de vida


def test_current_year_is_dropped_from_curves():
    assert complete_years_only({2024: 5, 2025: 9, 2026: 2}, today=date(2026, 9, 23)) == {2024: 5, 2025: 9}


def test_stage_from_gp_mp_sp():
    curve = {"gp": 2000, "mp": 2011, "sp": 2021}
    assert lifecycle_stage(curve, 1995) == "Emergente"
    assert lifecycle_stage(curve, 2005) == "Crescimento"
    assert lifecycle_stage(curve, 2015) == "Maturidade"
    assert lifecycle_stage(curve, 2025) == "Saturação"


def test_overall_stage_follows_patent_curve():
    lifecycle = build_lifecycle(
        {"article": {"gp": 2000, "mp": 2011, "sp": 2021}, "patent": {"gp": 2006, "mp": 2020, "sp": 2033}},
        reference_year=2025,
    )
    assert lifecycle["article"]["stage"] == "Saturação"
    assert lifecycle["patent"]["stage"] == "Maturidade"
    assert lifecycle["overall_stage"] == "Maturidade"


def test_yearly_summary_text_is_pt_br():
    text = summary_text("yearly_volume", yearly_summary({2020: 900, 2021: 1800, 2022: 1200}))
    assert "total de 3.900 documentos entre os anos de 2020 e 2022" in text
    assert "pico) no ano de 2021, com 1.800 documentos" in text


def test_summary_text_names_the_unit_of_every_number():
    patents = summary_text("yearly_volume", yearly_summary({2011: 7, 2024: 1}), "patent")
    assert "7 patentes depositadas" in patents and "1 patente depositada" in patents
    assert "publicações" not in patents

    ranking = summary_text("top_institutions", {"top": [["The MathWorks, Inc.", 4], ["JSC Concern", 2]]}, "article")
    assert ranking.startswith("o 1º colocado (o que lidera) é The MathWorks, Inc.")
    assert "1º The MathWorks, Inc. (4 publicações científicas); 2º JSC Concern (2" in ranking

    curve = {"gp": 2007, "mp": 2013, "sp": 2019, "saturation_level": "27", "current_saturation_pct": 103.7,
             "first_year": 2010, "last_year": 2024, "cumulative": 28}
    text = summary_text("s_curve", curve, "patent")
    assert "ACUMULADO" in text and "ponto de crescimento (GP) no ano de 2007" in text
    assert "103,7" not in text and "SUPERA o platô estimado pela curva (27 patentes depositadas)" in text


# ---------------------------------------------------------------- citações


def test_citation_and_reference_from_metadata():
    article = {"title": "Perovskite cells.", "authors": ["Pei G.", "Liu L."], "year": 2008, "journal_or_source": "Energy"}
    assert build_citation(article["authors"], 2008) == "PEI et al., 2008"
    assert build_reference(article, "article") == "PEI, G. et al. Perovskite cells. Energy, 2008."

    patent = {"title": "Solar module", "inventors": ["Shen, Hai Jun"], "applicants": ["ACME CO"], "year": 2020}
    assert build_reference(patent, "patent") == "SHEN, H. J. Solar module. Depositante: ACME CO. Patente, 2020."


def test_non_latin_author_is_not_citable():
    assert build_citation(["华能"], 2020) is None


def test_same_citation_for_different_works_gets_letters():
    sources = disambiguate(
        [
            {"citation": "SILVA, 2020", "reference": "SILVA, J. A. Periódico, 2020."},
            {"citation": "SILVA, 2020", "reference": "SILVA, J. B. Periódico, 2020."},
        ]
    )
    assert [s["citation"] for s in sources] == ["SILVA, 2020a", "SILVA, 2020b"]
    assert sources[1]["reference"].endswith("2020b.")


def test_filter_keeps_non_citation_parentheses():
    text, removed = filter_citations("Pico (MP = 2011) e artigos (2015 e 2016).", [])
    assert text == "Pico (MP = 2011) e artigos (2015 e 2016)." and removed == []


def test_references_only_for_citations_present_in_text():
    sources = [{"citation": "SILVA et al., 2020", "reference": "A"}, {"citation": "PEI, 2008", "reference": "B"}]
    assert references_for_text("Como mostrado (SILVA et al., 2020).", sources) == ["A"]


# ---------------------------------------------------------------- qualidade do texto


def test_number_formatting():
    assert fix_number_formatting("17.3% de 1800 patentes em 2015; 1.800 já ok") == "17,3% de 1.800 patentes em 2015; 1.800 já ok"


# Frases reais de um REPTEC gerado pelo gemma3:4b (Trunked Radio).
TRUNKED_FACTS = {
    "counts": [2, 4, 7, 12, 29, 92, 16],
    "leaders": ["The MathWorks, Inc."],
    "stages": {"article": "Maturidade", "patent": "Saturação", "overall": "Saturação"},
    "document_type": None,
}


def test_fact_issues_catch_the_real_errors():
    def issues(text, **overrides):
        return " | ".join(find_fact_issues(text, {**TRUNKED_FACTS, **overrides}))

    assert "ano usado como quantidade" in issues("Observa-se um pico de 2007 publicações em 2017.")
    assert "não existe nos dados" in issues("Observa-se um volume de 11 documentos entre 2011 e 2021.")
    assert "entidade errada" in issues(
        "A análise revela que a JSC Concern Sozvezdie lidera com 2 publicações, seguida pela The MathWorks, Inc. com 4."
    )
    assert "contradiz" in issues(
        "A linha de desenvolvimento das patentes indica que a tecnologia atingiu seu estágio de maturidade."
    )
    assert "acima de 100%" in issues("A saturação atual de 103,7% indica um estágio de saturação elevado.")
    assert "PATENTES" in issues(
        "A Figura [[REF:patent_yearly_volume]] mostra a distribuição das publicações científicas.",
        document_type="patent",
    )


def test_fact_issues_accept_coherent_text():
    text = (
        "A The MathWorks, Inc. lidera com 4 publicações, seguida pela JSC com 2 publicações.\n\n"
        "A curva dos artigos está no estágio de maturidade, enquanto a das patentes atingiu o estágio de saturação. "
        "Foram identificadas 29 patentes e 12 artigos entre 2010 e 2024, com pico de 7 depósitos em 2011; "
        "a Figura [[REF:article_top10_heatmap]] mostra as 10 maiores áreas."
    )
    assert find_fact_issues(text, TRUNKED_FACTS) == []
    assert find_fact_issues("A tecnologia encontra-se no estágio de SATURAÇÃO.", TRUNKED_FACTS) == []


def test_pipeline_leaks_are_detected():
    for leak in ("[Informação não disponível]", "(Fonte: N/A)", "Relevância: 18%", "no contexto fornecido", "com a , , e"):
        assert find_text_issues(leak), leak
    assert find_text_issues("A Figura [[REF:article_yearly_volume]] mostra 1.800 patentes (SILVA, 2020).") == []


# ---------------------------------------------------------------- formulário e seções fixas


def test_form_validation_rejects_placeholders():
    assert admin_reference_error("diex 2322-1")
    assert admin_reference_error("DIEx Nº 115-A3/DCT de 6 de janeiro de 2023;") is None
    assert bibliography_error("sasassas")
    assert signer_error("Elaborado por", "sdasdsad", "dsdsd", "dsdsd")
    assert signer_error("Elaborado por", "RICARDO WAGNER AMORIM GUIMARÃES", "TC", "Adj da Seção") is None
    assert "função" in signer_error("Elaborado por", "RICARDO WAGNER AMORIM GUIMARÃES", "TC", "")
    # "campo vazio" digitado por extenso também é placeholder
    assert signer_error("Elaborado por", "Não especificado", "Sem posto", "Sem função")


def test_destinatario_is_only_the_recipient():
    assert destinatario_error("AGITEC") is None
    assert destinatario_error("Indústria de Material Bélico do Brasil (IMBEL)") is None
    # a frase fixa inteira colada no campo duplicava a Finalidade
    assert "só o destinatário" in destinatario_error(
        "Apresentar o relatório de Prospecção Tecnológica sobre o tema a fim de fornecer informações de "
        "tendências e ciclo de vida da tecnologia para AGITEC, utilizando o modelo de LLM local QWEN 3:2B."
    )
    assert destinatario_error("Não informado")


def test_finalidade_and_local_data():
    assert render_finalidade("placas solares", "Indústria de Material Bélico do Brasil (IMBEL).") == (
        "Apresentar o relatório de Prospecção Tecnológica sobre placas solares a fim de fornecer informações "
        "de tendências e ciclo de vida da tecnologia para Indústria de Material Bélico do Brasil (IMBEL)."
    )
    assert render_local_data("Rio de Janeiro", date(2023, 8, 10)) == "Rio de Janeiro, 10 de agosto de 2023."


def test_cpc_official_titles():
    assert describe_code("B09B").startswith("DISPOSAL OF SOLID WASTE")
    assert "PHOTOVOLTAIC" in describe_code("H02S")
    # H01L foi extinta (reorganizada em H10): cai no título da classe, sem inventar.
    assert "classe H01" in describe_code("H01L")


def test_ordinal_indicators_survive_latex_escaping():
    from app.core.services.report_writer_service import escape_latex

    # "DIEx Nº 256" saía "DIEx N 256" e "1º Ten" saía "1 Ten".
    assert escape_latex("DIEx Nº 256/IME") == "DIEx Nº 256/IME"
    assert escape_latex("1º Ten e 3ª Seção") == "1º Ten e 3ª Seção"
    assert escape_latex("华能 HUANENG") == " HUANENG"  # CJK continua removido


# ---------------------------------------------------------------- 5.4 Apoio Computacional


def test_models_by_stage_uses_latest_writer_per_section():
    from config.prompts.report_static_sections import models_by_stage

    stages = dict(
        models_by_stage(
            [
                ("refine_topic", "qwen2.5:3b-instruct"),
                ("probe_queries_multi", "gemma3:4b"),
                ("final_query", "gemma3:4b"),
                ("extract_terms", "distiluse-base-multilingual-cased-v2"),
                ("report_writing:introducao", "qwen2.5:3b-instruct"),  # descartada: gerada de novo abaixo
                ("report_writing:introducao", "gemma4:12b"),
                ("report_writing:conclusao", "gemma4:12b"),
            ]
        )
    )
    assert stages["refinamento do tema"] == ["qwen2.5:3b-instruct"]
    assert stages["redação das seções analíticas"] == ["gemma4:12b"]
    assert stages["representação vetorial de textos (KeyBERT e recuperação semântica)"] == [
        "distiluse-base-multilingual-cased-v2"
    ]
    # sessão antiga sem registro da extração: completa com o modelo configurado
    assert models_by_stage([], embedding_model="all-mpnet-base-v2")[0][1] == ["all-mpnet-base-v2"]


def test_apoio_computacional_cites_only_works_in_the_bibliography():
    import re

    from config.prompts.report_static_sections import DEFAULT_BIBLIOGRAPHY, render_apoio_computacional

    text = render_apoio_computacional([("redação das seções analíticas", ["gemma3:4b"])])
    assert r"\texttt{gemma3:4b}" in text
    for technique in ("persona", "few-shot", "chain-of-thought", "RAG", "BM25F", "KeyBERT", "Chao1"):
        assert technique in text
    # "(ROBERTSON; ZARAGOZA; TAYLOR, 2004)", "(BROWN et al., 2020; ZHAO et al., 2023)":
    # cada citação termina no ano; a obra é identificada pelo 1º sobrenome.
    cited_surnames = set()
    for group in re.findall(r"\(([A-ZÀ-Ý][^()]*?\d{4})\)", text):
        for citation in re.split(r"(?<=\d{4});\s*", group):
            cited_surnames.add(re.split(r";|,| et al\.", citation)[0].strip())
    assert {"VASWANI", "WHITE", "WEI", "ROBERTSON", "CHAO", "LEWIS", "GAO"} <= cited_surnames
    for surname in cited_surnames:
        assert any(ref.startswith(surname) for ref in DEFAULT_BIBLIOGRAPHY), surname
    assert "modelos utilizados" not in render_apoio_computacional([])
