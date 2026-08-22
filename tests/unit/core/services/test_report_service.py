from pathlib import Path

import pytest

from app.core.services.report_service import ReportService


class FakeStoragePort:
    """StoragePort fake em memória - substitui o MinIO real nos testes."""

    def __init__(self) -> None:
        self.uploaded: dict[str, tuple[bytes, str]] = {}
        self.fail_upload = False

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        if self.fail_upload:
            raise RuntimeError("upload falhou (simulado)")
        self.uploaded[key] = (data, content_type)

    async def download(self, key: str) -> bytes:
        return self.uploaded[key][0]

    async def delete(self, key: str) -> None:
        self.uploaded.pop(key, None)

    async def ensure_bucket(self) -> None:
        pass


@pytest.fixture
def storage():
    return FakeStoragePort()


@pytest.fixture
def svc(tmp_path, storage):
    return ReportService(output_dir=tmp_path, storage=storage)


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


def _patents_by_year_from(patents):
    counts: dict[int, int] = {}
    for patent in patents:
        counts[patent["year"]] = counts.get(patent["year"], 0) + 1
    return counts


def test_generate_session_report_creates_expected_charts(svc, tmp_path):
    result = svc.generate_session_report(1, _patents(), _articles())

    assert result["patents_used"] == 12
    assert result["articles_used"] == 12
    assert result["skipped"] == []

    # A curva S de patentes NÃO é mais gerada por generate_session_report -
    # ela vem de generate_patent_s_curve, a partir de patents_by_year
    # fornecido pelo chamador (ver test_generate_patent_s_curve_* abaixo).
    chart_keys = {(c["document_type"], c["chart"]) for c in result["charts"]}
    assert chart_keys == {
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
    assert len(result["skipped"]) == 10


def test_generate_session_report_partial_data_skips_only_missing_side(svc):
    result = svc.generate_session_report(3, patents=_patents(), articles=[])

    document_types = {c["document_type"] for c in result["charts"]}
    assert document_types == {"patent"}
    assert all(s.startswith("article:") for s in result["skipped"])


def test_article_s_curve_requires_at_least_two_distinct_years(svc):
    single_year_articles = [{"year": 2020, "authors": ["Doe, J."]} for _ in range(5)]
    result = svc.generate_session_report(4, patents=[], articles=single_year_articles)

    assert "article:s_curve" in result["skipped"]


@pytest.mark.asyncio
async def test_generate_patent_s_curve_requires_at_least_two_distinct_years(svc):
    result = await svc.generate_patent_s_curve(session_id=5, probe_query_id=50, patents_by_year={"2020": 5})

    assert result["chart"] is None
    assert result["fit"] is None
    assert "2 anos distintos" in result["skipped_reason"]


@pytest.mark.asyncio
async def test_generate_patent_s_curve_from_yearly_counts(svc, storage):
    patents_by_year = _patents_by_year_from(_patents())

    result = await svc.generate_patent_s_curve(
        session_id=6, probe_query_id=60, patents_by_year=patents_by_year, projection_end_year=2035
    )

    assert result["skipped_reason"] is None
    assert result["chart"]["document_type"] == "patent"
    assert result["chart"]["chart"] == "s_curve"
    assert result["chart"]["image_base64"]

    # object_key vem preenchido (upload deu certo) e a chave é determinística
    # (session_id + probe_query_id) - regenerar sobrescreveria o mesmo objeto.
    object_key = result["chart"]["object_key"]
    assert object_key == "sessions/6/probe_query_60/patent_s_curve.png"
    uploaded_bytes, content_type = storage.uploaded[object_key]
    assert content_type == "image/png"
    assert len(uploaded_bytes) > 0

    fit = result["fit"]
    assert set(fit) == {
        "K", "r", "t0", "gp_year", "mp_year", "sp_year",
        "current_saturation", "years_observed", "cumulative_observed", "fit_quality",
    }
    assert fit["mp_year"] == fit["t0"]
    assert set(fit["fit_quality"]) == {"r_squared", "reliable", "warning"}


@pytest.mark.asyncio
async def test_generate_patent_s_curve_survives_storage_failure(tmp_path):
    storage = FakeStoragePort()
    storage.fail_upload = True
    svc = ReportService(output_dir=tmp_path, storage=storage)
    patents_by_year = _patents_by_year_from(_patents())

    result = await svc.generate_patent_s_curve(session_id=7, probe_query_id=70, patents_by_year=patents_by_year)

    assert result["skipped_reason"] is None
    assert result["chart"]["image_base64"]
    assert "object_key" not in result["chart"]


def test_generate_patent_yearly_volume_requires_data(svc):
    result = svc.generate_patent_yearly_volume(session_id=7, patents_by_year={})

    assert result["chart"] is None
    assert "nenhum dado" in result["skipped_reason"]


def test_generate_patent_yearly_volume_from_yearly_counts(svc, tmp_path):
    patents_by_year = _patents_by_year_from(_patents())

    result = svc.generate_patent_yearly_volume(session_id=8, patents_by_year=patents_by_year)

    assert result["skipped_reason"] is None
    assert result["chart"]["document_type"] == "patent"
    assert result["chart"]["chart"] == "yearly_volume"

    path = Path(result["chart"]["path"])
    assert path.exists()
    assert path.stat().st_size > 0
    assert path.parent == tmp_path / "session_8"


def test_generate_top10_heatmap_requires_data(svc):
    result = svc.generate_top10_heatmap(session_id=9, top10={})

    assert result["chart"] is None
    assert "nenhum dado" in result["skipped_reason"]


def test_generate_top10_heatmap_from_cpc_distribution(svc, tmp_path):
    cpc = {
        "Y02E": 1447,
        "B32B": 60,
        "C09J": 32,
        "H10F": 1100,
        "Y02P": 191,
        "H01G": 56,
        "H10P": 68,
        "E06B": 12,
        "F24S": 641,
        "H02S": 376,
    }

    result = svc.generate_top10_heatmap(
        session_id=10, top10=cpc, title="Distribuição por CPC", document_type="patent"
    )

    assert result["skipped_reason"] is None
    assert result["chart"]["document_type"] == "patent"
    assert result["chart"]["chart"] == "top10_heatmap"

    path = Path(result["chart"]["path"])
    assert path.exists()
    assert path.stat().st_size > 0
    assert path.parent == tmp_path / "session_10"


def test_generate_top10_heatmap_reused_for_articles_with_fewer_than_ten(svc, tmp_path):
    field_of_study = {"AI": 40, "Robotics": 12, "Optics": 5}

    result = svc.generate_top10_heatmap(
        session_id=11, top10=field_of_study, title="Distribuição por Área de Estudo", document_type="article"
    )

    assert result["skipped_reason"] is None
    assert result["chart"]["document_type"] == "article"

    path = Path(result["chart"]["path"])
    assert path.exists()
    assert path.stat().st_size > 0
