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
def svc(storage):
    return ReportService(storage=storage)


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


@pytest.mark.asyncio
async def test_generate_session_report_creates_expected_charts(svc, storage):
    result = await svc.generate_session_report(
        1, _patents(), _articles(), probe_query_ids={"patent": 10, "article": 20}
    )

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
        assert chart["image_base64"]
        probe_query_id = 10 if chart["document_type"] == "patent" else 20
        object_key = chart["object_key"]
        assert object_key == f"sessions/1/probe_query_{probe_query_id}/{chart['document_type']}_{chart['chart']}.png"
        uploaded_bytes, content_type = storage.uploaded[object_key]
        assert content_type == "image/png"
        assert len(uploaded_bytes) > 0


@pytest.mark.asyncio
async def test_generate_session_report_skips_charts_without_data(svc):
    result = await svc.generate_session_report(2, patents=[], articles=[], probe_query_ids={})

    assert result["patents_used"] == 0
    assert result["articles_used"] == 0
    assert result["charts"] == []
    assert len(result["skipped"]) == 10


@pytest.mark.asyncio
async def test_generate_session_report_partial_data_skips_only_missing_side(svc):
    result = await svc.generate_session_report(3, patents=_patents(), articles=[], probe_query_ids={"patent": 30})

    document_types = {c["document_type"] for c in result["charts"]}
    assert document_types == {"patent"}
    assert all(s.startswith("article:") for s in result["skipped"])


@pytest.mark.asyncio
async def test_generate_session_report_missing_probe_query_id_still_returns_image(svc, storage):
    """Fonte ausente de `probe_query_ids` (ex.: sessão sem query final de
    artigo) não impede o gráfico de ser gerado/devolvido - só fica sem
    subir pro storage dessa vez (mesma filosofia best-effort do resto do
    arquivo)."""
    result = await svc.generate_session_report(4, patents=_patents(), articles=[], probe_query_ids={})

    chart = next(c for c in result["charts"] if c["document_type"] == "patent")
    assert chart["image_base64"]
    assert "object_key" not in chart
    assert storage.uploaded == {}


@pytest.mark.asyncio
async def test_article_s_curve_requires_at_least_two_distinct_years(svc):
    single_year_articles = [{"year": 2020, "authors": ["Doe, J."]} for _ in range(5)]
    result = await svc.generate_session_report(
        5, patents=[], articles=single_year_articles, probe_query_ids={"article": 50}
    )

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
        session_id=6, probe_query_id=60, patents_by_year=patents_by_year, projection_years=10
    )

    assert result["skipped_reason"] is None
    assert result["chart"]["document_type"] == "patent"
    assert result["chart"]["chart"] == "s_curve"
    assert result["chart"]["image_base64"]
    assert result["chart"]["projection_years"] == 10

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
async def test_generate_patent_s_curve_survives_storage_failure():
    storage = FakeStoragePort()
    storage.fail_upload = True
    svc = ReportService(storage=storage)
    patents_by_year = _patents_by_year_from(_patents())

    result = await svc.generate_patent_s_curve(session_id=7, probe_query_id=70, patents_by_year=patents_by_year)

    assert result["skipped_reason"] is None
    assert result["chart"]["image_base64"]
    assert "object_key" not in result["chart"]


@pytest.mark.asyncio
async def test_generate_patent_yearly_volume_requires_data(svc):
    result = await svc.generate_patent_yearly_volume(session_id=7, probe_query_id=70, patents_by_year={})

    assert result["chart"] is None
    assert "nenhum dado" in result["skipped_reason"]


@pytest.mark.asyncio
async def test_generate_patent_yearly_volume_from_yearly_counts(svc, storage):
    patents_by_year = _patents_by_year_from(_patents())

    result = await svc.generate_patent_yearly_volume(session_id=8, probe_query_id=80, patents_by_year=patents_by_year)

    assert result["skipped_reason"] is None
    assert result["chart"]["document_type"] == "patent"
    assert result["chart"]["chart"] == "yearly_volume"
    assert result["chart"]["image_base64"]

    object_key = result["chart"]["object_key"]
    assert object_key == "sessions/8/probe_query_80/patent_yearly_volume.png"
    assert storage.uploaded[object_key][0]


@pytest.mark.asyncio
async def test_generate_top10_heatmap_requires_data(svc):
    result = await svc.generate_top10_heatmap(session_id=9, probe_query_id=90, top10={})

    assert result["chart"] is None
    assert "nenhum dado" in result["skipped_reason"]


@pytest.mark.asyncio
async def test_generate_top10_heatmap_from_cpc_distribution(svc, storage):
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

    result = await svc.generate_top10_heatmap(
        session_id=10, probe_query_id=100, top10=cpc, title="Distribuição por CPC", document_type="patent"
    )

    assert result["skipped_reason"] is None
    assert result["chart"]["document_type"] == "patent"
    assert result["chart"]["chart"] == "top10_heatmap"
    assert result["chart"]["image_base64"]

    object_key = result["chart"]["object_key"]
    assert object_key == "sessions/10/probe_query_100/patent_top10_heatmap.png"
    assert storage.uploaded[object_key][0]


@pytest.mark.asyncio
async def test_generate_top_entities_chart_requires_data(svc):
    result = await svc.generate_top_entities_chart(
        session_id=12, probe_query_id=120, entity_counts={}, chart_type="top_depositants", document_type="patent",
        title="Top Depositantes",
    )

    assert result["chart"] is None
    assert "nenhum dado" in result["skipped_reason"]


@pytest.mark.asyncio
async def test_generate_top_entities_chart_from_enriched_counts(svc, storage):
    entity_counts = {"Acme": 42, "Globex": 30, "Initech": 12}

    result = await svc.generate_top_entities_chart(
        session_id=13,
        probe_query_id=130,
        entity_counts=entity_counts,
        chart_type="top_depositants",
        document_type="patent",
        title="Top Depositantes",
    )

    assert result["skipped_reason"] is None
    assert result["chart"]["document_type"] == "patent"
    assert result["chart"]["chart"] == "top_depositants"
    assert result["chart"]["image_base64"]

    object_key = result["chart"]["object_key"]
    assert object_key == "sessions/13/probe_query_130/patent_top_depositants.png"
    assert storage.uploaded[object_key][0]


@pytest.mark.asyncio
async def test_generate_top_entities_chart_for_article_uses_own_chart_type(svc, storage):
    # institutions (artigo) usa um chart_type diferente do de patente, mesmo
    # reusando o mesmo método - evita colisão de chave se ambos os lados
    # forem gerados na mesma sessão.
    result = await svc.generate_top_entities_chart(
        session_id=14,
        probe_query_id=140,
        entity_counts={"MIT": 20, "Stanford": 15},
        chart_type="top_institutions",
        document_type="article",
        title="Top Instituições",
    )

    object_key = result["chart"]["object_key"]
    assert object_key == "sessions/14/probe_query_140/article_top_institutions.png"


@pytest.mark.asyncio
async def test_generate_yearly_volume_for_article(svc, storage):
    articles_by_year = {2019: 5, 2020: 8, 2021: 3}

    result = await svc.generate_yearly_volume(
        document_type="article", session_id=15, probe_query_id=150, yearly_counts=articles_by_year
    )

    assert result["skipped_reason"] is None
    assert result["chart"]["document_type"] == "article"
    assert result["chart"]["chart"] == "yearly_volume"

    object_key = result["chart"]["object_key"]
    assert object_key == "sessions/15/probe_query_150/article_yearly_volume.png"
    assert storage.uploaded[object_key][0]


@pytest.mark.asyncio
async def test_generate_top10_heatmap_reused_for_articles_with_fewer_than_ten(svc):
    field_of_study = {"AI": 40, "Robotics": 12, "Optics": 5}

    result = await svc.generate_top10_heatmap(
        session_id=11,
        probe_query_id=110,
        top10=field_of_study,
        title="Distribuição por Área de Estudo",
        document_type="article",
    )

    assert result["skipped_reason"] is None
    assert result["chart"]["document_type"] == "article"
    assert result["chart"]["image_base64"]


@pytest.mark.asyncio
async def test_download_chart_returns_uploaded_bytes(svc, storage):
    patents_by_year = _patents_by_year_from(_patents())
    generated = await svc.generate_patent_s_curve(session_id=12, probe_query_id=120, patents_by_year=patents_by_year)

    downloaded = await svc.download_chart(generated["chart"]["object_key"])

    assert len(downloaded) > 0
