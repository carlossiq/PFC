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
    signer_error,
)
from app.core.services.report_lifecycle import (
    build_lifecycle,
    complete_years_only,
    lifecycle_stage,
    summary_text,
    yearly_summary,
)
from app.core.services.report_text_quality import find_text_issues, fix_number_formatting
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
    assert "total de 3.900 documentos entre 2020 e 2022" in text
    assert "pico em 2021 com 1.800" in text


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


def test_pipeline_leaks_are_detected():
    for leak in ("[Informação não disponível]", "(Fonte: N/A)", "Relevância: 18%", "no contexto fornecido", "com a , , e"):
        assert find_text_issues(leak), leak
    assert find_text_issues("A Figura [[REF:article_yearly_volume]] mostra 1.800 patentes (SILVA, 2020).") == []


# ---------------------------------------------------------------- formulário e seções fixas


def test_form_validation_rejects_placeholders():
    assert admin_reference_error("diex 2322-1")
    assert admin_reference_error("DIEx Nº 115-A3/DCT de 6 de janeiro de 2023;") is None
    assert bibliography_error("sasassas")
    assert signer_error("Elaborado por", "sdasdsad", "dsdsd")
    assert signer_error("Elaborado por", "RICARDO WAGNER AMORIM GUIMARÃES – TC", "Adj da Seção") is None


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
