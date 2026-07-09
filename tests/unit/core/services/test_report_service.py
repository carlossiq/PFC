from app.core.services.report_service import ReportService

import pytest


@pytest.fixture
def svc():
    return ReportService()


@pytest.fixture
def minimal_research():
    return {
        "research_id": "r1",
        "theme": "Quantum Computing",
        "description": "Test research",
        "status": "done",
        "created_at": "2024-01-01",
        "updated_at": "2024-01-02",
        "patent_results_count": 0,
        "scholarly_results_count": 0,
        "total_results_count": 0,
    }


# ---- map_research_data ----

def test_map_research_data_returns_expected_keys(svc, minimal_research):
    result = svc.map_research_data(minimal_research, [], [])
    for key in ("theme", "patent_data", "scientific_data", "metrics", "s_curve_data"):
        assert key in result


def test_map_research_data_patent_count(svc, minimal_research):
    patents = [
        {"publication_number": "EP1", "year": 2022},
        {"publication_number": "EP2", "year": 2023},
    ]
    result = svc.map_research_data(minimal_research, patents, [])
    assert result["patent_data"]["patent_count"] == 2


# ---- generate_latex ----

def test_generate_latex_contains_documentclass(svc, minimal_research):
    latex = svc.generate_latex(minimal_research)
    assert r"\documentclass" in latex


def test_generate_latex_contains_end_document(svc, minimal_research):
    latex = svc.generate_latex(minimal_research)
    assert r"\end{document}" in latex


def test_generate_latex_contains_theme(svc, minimal_research):
    latex = svc.generate_latex(minimal_research)
    assert "Quantum Computing" in latex


# ---- convert_to_rag_documents ----

def test_convert_to_rag_documents_respects_max_patents(svc):
    patents = [{"title": f"P{i}", "publication_number": f"EP{i}"} for i in range(5)]
    docs = svc.convert_to_rag_documents(patents, [], max_patents=2)
    patent_docs = [d for d in docs if d["type"] == "patent"]
    assert len(patent_docs) == 2


def test_convert_to_rag_documents_respects_max_articles(svc):
    articles = [{"title": f"A{i}", "doi": f"10.1/{i}"} for i in range(5)]
    docs = svc.convert_to_rag_documents([], articles, max_articles=3)
    article_docs = [d for d in docs if d["type"] == "article"]
    assert len(article_docs) == 3


def test_convert_to_rag_documents_text_contains_title(svc):
    patents = [{"title": "NanoTech Patent", "publication_number": "EP42"}]
    docs = svc.convert_to_rag_documents(patents, [])
    assert "NanoTech Patent" in docs[0]["text"]
