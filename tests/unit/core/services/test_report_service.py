from pathlib import Path

import pytest

from app.core.services.report_service import ReportService


@pytest.fixture
def svc(tmp_path):
    return ReportService(output_dir=tmp_path)


def _patents(n_years=6):
    return [
        {
            "year": 2018 + (i % n_years),
            "applicants": ["Acme"] if i % 2 == 0 else ["Globex", "Acme"],
            "inventors": ["Silva"],
            "cpc_codes": ["G06F16/00"],
            "ipc_codes": ["G06F"],
            "country": "US" if i % 2 == 0 else "BR",
        }
        for i in range(12)
    ]


def _articles(n_years=6):
    return [
        {
            "year": 2018 + (i % n_years),
            "authors": ["Doe, J."],
            "journal_or_source": "Nature",
            "field_of_study": ["AI"],
            "affiliation_countries": ["US", "DE"],
        }
        for i in range(12)
    ]


def test_generate_session_report_creates_expected_charts(svc, tmp_path):
    result = svc.generate_session_report(1, _patents(), _articles())

    assert result["patents_used"] == 12
    assert result["articles_used"] == 12
    assert result["skipped"] == []

    chart_keys = {(c["document_type"], c["chart"]) for c in result["charts"]}
    assert chart_keys == {
        ("patent", "s_curve"),
        ("article", "s_curve"),
        ("patent", "top_applicants"),
        ("patent", "top_inventors"),
        ("article", "top_authors"),
        ("article", "top_journals"),
        ("patent", "cpc_distribution"),
        ("patent", "ipc_distribution"),
        ("article", "field_of_study_distribution"),
        ("patent", "geographic_distribution"),
        ("article", "geographic_distribution"),
    }

    for chart in result["charts"]:
        path = Path(chart["path"])
        assert path.exists()
        assert path.stat().st_size > 0
        assert path.parent == tmp_path / "session_1"


def test_generate_session_report_skips_charts_without_data(svc):
    result = svc.generate_session_report(2, patents=[], articles=[])

    assert result["patents_used"] == 0
    assert result["articles_used"] == 0
    assert result["charts"] == []
    assert len(result["skipped"]) == 11


def test_generate_session_report_partial_data_skips_only_missing_side(svc):
    result = svc.generate_session_report(3, patents=_patents(), articles=[])

    document_types = {c["document_type"] for c in result["charts"]}
    assert document_types == {"patent"}
    assert all(s.startswith("article:") for s in result["skipped"])


def test_s_curve_requires_at_least_two_distinct_years(svc):
    single_year_patents = [{"year": 2020, "applicants": ["Acme"]} for _ in range(5)]
    result = svc.generate_session_report(4, patents=single_year_patents, articles=[])

    assert "patent:s_curve" in result["skipped"]
    assert any(c["chart"] == "top_applicants" for c in result["charts"])
