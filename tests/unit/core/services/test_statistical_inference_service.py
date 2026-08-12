from typing import Any, Optional

import pytest

from app.core.services.statistical_inference_service import StatisticalInferenceService
from core.config import Settings


class FakeChatService:
    """Fila de respostas de run_final_search, uma por chamada (iteration 1, 2, ...)."""

    def __init__(self, responses: Optional[list[dict[str, Any]]] = None) -> None:
        self._responses = responses or []
        self.calls: list[tuple[str, int, int, int]] = []

    async def run_final_search(self, query, api, year_from, year_to, iteration=0):
        self.calls.append((api, year_from, year_to, iteration))
        idx = len(self.calls) - 1
        if idx < len(self._responses):
            return self._responses[idx]
        return {"success": True, "api": api, "title": []}


class FakeEmbeddingAdapter:
    """Vetores constantes - qualquer texto vira o mesmo vetor, cosseno sempre 1.0."""

    def embed_text(self, text):
        return [1.0, 0.0, 0.0]

    def embed_batch(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


def _settings(**overrides) -> Settings:
    return Settings(**overrides)


def _svc(chat_service=None, embedding=None, **settings_overrides) -> StatisticalInferenceService:
    return StatisticalInferenceService(
        chat_service=chat_service or FakeChatService(),
        embedding=embedding or FakeEmbeddingAdapter(),
        settings=_settings(**settings_overrides),
    )


def _ops_result(cpc=None, depositants=None, title=None, patents_by_year=None) -> dict[str, Any]:
    return {
        "success": True,
        "api": "ops",
        "cpc": cpc or {},
        "depositants": depositants or {},
        "title": title or [],
        "patents_by_year": patents_by_year or {},
        "strategy": "year",
    }


def _scopus_result(area_of_study=None, institutions=None, title=None, articles_by_year=None) -> dict[str, Any]:
    return {
        "success": True,
        "api": "scopus",
        "area_of_study": area_of_study or {},
        "institutions": institutions or {},
        "title": title or [],
        "articles_by_year": articles_by_year or {},
        "strategy": "year",
    }


@pytest.mark.asyncio
async def test_run_unsupported_api_returns_error():
    svc = _svc()
    result = await svc.run("lens_patent", {}, {}, "theme")
    assert result["success"] is False
    assert "não suportada" in result["error"]


@pytest.mark.asyncio
async def test_run_no_year_data_skips_enrichment_loop():
    chat = FakeChatService()
    svc = _svc(chat_service=chat)

    result = await svc.run(
        "ops", {}, _ops_result(cpc={"A61B": 1}, depositants={"Acme": 1}), "theme"
    )

    assert result["stopped_reason"] == "no_year_data"
    assert result["iterations_used"] == 0
    assert chat.calls == []


@pytest.mark.asyncio
async def test_run_saturates_immediately_with_lenient_thresholds():
    chat = FakeChatService()
    svc = _svc(
        chat_service=chat,
        statistical_inference_saturation_threshold=0.0,
        statistical_inference_f1_ratio_threshold=1.0,
        statistical_inference_f2_min=0,
    )

    result = await svc.run(
        "ops",
        {},
        _ops_result(cpc={"A61B": 3}, depositants={"Acme": 2}, title=["t1"], patents_by_year={2020: 10}),
        "theme",
    )

    assert result["stopped_reason"] == "saturated"
    assert result["iterations_used"] == 0
    assert chat.calls == []
    assert result["cpc"]["top10"] == {"A61B": 1.0}
    assert result["depositants"]["top10"] == {"Acme": 1.0}
    assert result["area_of_study"] is None
    assert result["institutions"] is None
    assert result["patents_by_year"] == {2020: 10}
    assert result["articles_by_year"] is None


@pytest.mark.asyncio
async def test_run_enriches_with_one_iteration_then_saturates():
    # thresholds estritos o bastante pra iteração 0 sozinha ser insuficiente,
    # mas satisfeitos depois de somar a iteração 1.
    chat = FakeChatService(
        responses=[
            _ops_result(
                cpc={"A61B": 5, "A61C": 5, "A61D": 5, "A61E": 5, "A61F": 5, "A61G": 5},
                depositants={"Acme": 5, "Globex": 5},
                title=["t2"],
            )
        ]
    )
    # threshold de saturação alto o bastante pra iteração 0 sozinha (2
    # categorias/1 depositante - riqueza estimada bem acima do observado)
    # não bater; f1_ratio/f2 relaxados pra isolar só esse sinal.
    svc = _svc(
        chat_service=chat,
        statistical_inference_saturation_threshold=0.9,
        statistical_inference_f1_ratio_threshold=1.0,
        statistical_inference_f2_min=0,
    )

    initial = _ops_result(
        cpc={"A61B": 1, "A61C": 1},
        depositants={"Acme": 1},
        title=["t1"],
        patents_by_year={2020: 10, 2021: 20},
    )

    result = await svc.run("ops", {"query": "x"}, initial, "theme")

    assert result["stopped_reason"] == "saturated"
    assert result["iterations_used"] == 1
    assert len(chat.calls) == 1
    assert chat.calls[0] == ("ops", 2020, 2021, 1)
    # contagens somadas (1+5=6 pra A61B, novo Globex incorporado).
    assert result["cpc"]["top10"]["A61B"] == pytest.approx(1.0)
    assert set(result["depositants"]["top10"]) == {"Acme", "Globex"}


@pytest.mark.asyncio
async def test_run_stops_at_time_limit_before_any_fetch():
    chat = FakeChatService()
    svc = _svc(chat_service=chat, statistical_inference_max_duration_seconds=0)

    result = await svc.run(
        "ops",
        {},
        _ops_result(cpc={"A61B": 1}, depositants={"Acme": 1}, patents_by_year={2020: 1}),
        "theme",
    )

    assert result["stopped_reason"] == "time_limit"
    assert result["iterations_used"] == 0
    assert chat.calls == []


@pytest.mark.asyncio
async def test_run_stops_on_fetch_error():
    chat = FakeChatService(responses=[{"success": False, "api": "ops", "error": "boom"}])
    svc = _svc(
        chat_service=chat,
        statistical_inference_saturation_threshold=1.0,
        statistical_inference_f1_ratio_threshold=0.0,
        statistical_inference_f2_min=999,
    )

    result = await svc.run(
        "ops", {}, _ops_result(cpc={"A61B": 1}, depositants={"Acme": 1}, patents_by_year={2020: 1}), "theme"
    )

    assert result["stopped_reason"] == "fetch_error"
    assert result["iterations_used"] == 0
    assert len(chat.calls) == 1


@pytest.mark.asyncio
async def test_run_stops_on_no_more_data():
    chat = FakeChatService(responses=[_ops_result()])  # tudo vazio
    svc = _svc(
        chat_service=chat,
        statistical_inference_saturation_threshold=1.0,
        statistical_inference_f1_ratio_threshold=0.0,
        statistical_inference_f2_min=999,
    )

    result = await svc.run(
        "ops", {}, _ops_result(cpc={"A61B": 1}, depositants={"Acme": 1}, patents_by_year={2020: 1}), "theme"
    )

    assert result["stopped_reason"] == "no_more_data"
    assert result["iterations_used"] == 0


@pytest.mark.asyncio
async def test_run_scopus_returns_only_article_fields():
    svc = _svc(
        statistical_inference_saturation_threshold=0.0,
        statistical_inference_f1_ratio_threshold=1.0,
        statistical_inference_f2_min=0,
    )

    result = await svc.run(
        "scopus",
        {},
        _scopus_result(
            area_of_study={"Medicine": 3},
            institutions={"MIT": 2},
            title=["t1"],
            articles_by_year={2020: 5},
        ),
        "theme",
    )

    assert result["cpc"] is None
    assert result["depositants"] is None
    assert result["patents_by_year"] is None
    assert result["area_of_study"]["top10"] == {"Medicine": 1.0}
    assert result["institutions"]["top10"] == {"MIT": 1.0}
    assert result["articles_by_year"] == {2020: 5}


@pytest.mark.asyncio
async def test_score_is_one_when_titles_available_with_constant_embeddings():
    svc = _svc(
        statistical_inference_saturation_threshold=0.0,
        statistical_inference_f1_ratio_threshold=1.0,
        statistical_inference_f2_min=0,
    )

    result = await svc.run(
        "ops",
        {},
        _ops_result(cpc={"A61B": 1}, depositants={"Acme": 1}, title=["t1", "t2"], patents_by_year={2020: 1}),
        "theme",
    )

    assert result["score"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_score_is_zero_when_no_titles_available():
    svc = _svc(
        statistical_inference_saturation_threshold=0.0,
        statistical_inference_f1_ratio_threshold=1.0,
        statistical_inference_f2_min=0,
    )

    result = await svc.run(
        "ops",
        {},
        _ops_result(cpc={"A61B": 1}, depositants={"Acme": 1}, title=[], patents_by_year={2020: 1}),
        "theme",
    )

    assert result["score"] == 0.0
