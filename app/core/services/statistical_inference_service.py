"""
Enriquece iterativamente a amostra de uma busca final (OPS ou Scopus) até
ela saturar (Chao1, ver app/core/services/sample_statistics.py) ou o tempo
configurado acabar, agrega os resultados, mede a estabilidade dos rankings
top-10 (bootstrap) e a relevância semântica (SBERT) com o tema da pesquisa.

Não tem porta/adapter própria: reusa ChatService.run_final_search (já
encapsula toda a lógica de range/ano/iteração pra OPS e Scopus - refazer
isso aqui duplicaria lógica já testada) e a porta de embedding já existente
(EmbeddingAdapter, injetada via container["embedding"]) - hexagonal só onde
há I/O de verdade (busca externa, modelo SBERT); o resto (Chao1, bootstrap,
esse laço de orquestração) é lógica pura, sem necessidade de abstração
adicional.
"""

from __future__ import annotations

import random
import time
from typing import Any

import numpy as np

from app.core.services.sample_statistics import bootstrap_topk_stability, is_sample_insufficient
from core.config import Settings
from core.logging import get_logger
from services.nlp.fuzzy_grouping import fuzzy_group_names
from services.nlp.language_filter import is_non_english_abstract

logger = get_logger(__name__)

# api -> (campo de categoria exata, campo de entidade fuzzy, campo de ano).
# CPC/área de estudo são contagens exatas (chave já normalizada por
# ChatService); depositantes/instituições precisam de fuzzy matching porque
# cada iteração só foi fuzzy-agrupada dentro de si mesma (ver _merge_entity_counts).
_API_FIELDS: dict[str, tuple[str, str, str]] = {
    "ops": ("cpc", "depositants", "patents_by_year"),
    "scopus": ("area_of_study", "institutions", "articles_by_year"),
}


class StatisticalInferenceService:
    """Orquestra o loop de enriquecimento + estatísticas de uma busca final."""

    def __init__(self, chat_service: Any, embedding: Any, settings: Settings) -> None:
        self.chat_service = chat_service
        self.embedding = embedding
        self.settings = settings

    async def run(
        self,
        api: str,
        query: dict[str, Any],
        final_search_result: dict[str, Any],
        theme: str,
    ) -> dict[str, Any]:
        """
        Returns:
            Dict pronto pra virar StatisticalInferenceResponse (ver
            schemas/inference.py), ou {"success": False, "error": ...} se
            `api` não for suportada.
        """
        if api not in _API_FIELDS:
            return {"success": False, "api": api, "error": f"API '{api}' não suportada pra inferência estatística"}

        category_field, entity_field, year_field = _API_FIELDS[api]

        category_counts: dict[str, int] = dict(final_search_result.get(category_field) or {})
        entity_counts: dict[str, int] = dict(final_search_result.get(entity_field) or {})
        titles: list[str] = list(final_search_result.get("title") or [])
        year_counts: dict[Any, int] = dict(final_search_result.get(year_field) or {})

        start = time.monotonic()
        iteration = 0

        years = [int(y) for y in year_counts]
        if not years:
            # Sem dados de ano na amostra inicial - não dá pra saber qual
            # intervalo pedir em novas iterações (ver run_final_search,
            # year_from/year_to obrigatórios). Degrada graciosamente:
            # calcula as estatísticas em cima só do que já veio.
            stopped_reason = "no_year_data"
        else:
            year_from, year_to = min(years), max(years)
            stopped_reason, iteration, category_counts, entity_counts, titles = await self._enrich_loop(
                api, query, year_from, year_to, category_counts, entity_counts, titles, start
            )

        elapsed_seconds = time.monotonic() - start

        resamples = getattr(self.settings, "statistical_inference_bootstrap_resamples", 1000)
        bootstrap_category = bootstrap_topk_stability(category_counts, top_k=10, resamples=resamples)
        bootstrap_entity = bootstrap_topk_stability(entity_counts, top_k=10, resamples=resamples)

        max_titles = getattr(self.settings, "statistical_inference_max_titles_for_relevance", 20)
        score = self._compute_theme_relevance(theme, titles, max_titles)

        response: dict[str, Any] = {
            "success": True,
            "api": api,
            "score": score,
            "iterations_used": iteration,
            "elapsed_seconds": elapsed_seconds,
            "stopped_reason": stopped_reason,
            "cpc": None,
            "depositants": None,
            "area_of_study": None,
            "institutions": None,
            "patents_by_year": None,
            "articles_by_year": None,
        }
        response[category_field] = {"top10": bootstrap_category}
        response[entity_field] = {"top10": bootstrap_entity}
        response[year_field] = year_counts
        return response

    async def _enrich_loop(
        self,
        api: str,
        query: dict[str, Any],
        year_from: int,
        year_to: int,
        category_counts: dict[str, int],
        entity_counts: dict[str, int],
        titles: list[str],
        start: float,
    ) -> tuple[str, int, dict[str, int], dict[str, int], list[str]]:
        """
        Loop principal: pede iterações extras de run_final_search (iteration
        1, 2, 3...) enquanto a amostra estiver insuficiente (Chao1, ver
        sample_statistics.is_sample_insufficient) em CPC/área de estudo OU
        em depositantes/instituições, e o tempo configurado não tiver
        acabado. Para em saturação, tempo, falha de busca, ou quando uma
        iteração não trouxe nada de novo (amostra daquele intervalo de anos
        já esgotada).
        """
        max_duration = getattr(self.settings, "statistical_inference_max_duration_seconds", 60)
        saturation_threshold = getattr(self.settings, "statistical_inference_saturation_threshold", 0.5)
        f1_ratio_threshold = getattr(self.settings, "statistical_inference_f1_ratio_threshold", 0.7)
        f2_min = getattr(self.settings, "statistical_inference_f2_min", 5)
        fuzzy_threshold = getattr(self.settings, "depositant_fuzzy_match_threshold", 90.0)
        category_field, entity_field, _ = _API_FIELDS[api]

        iteration = 0
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= max_duration:
                return "time_limit", iteration, category_counts, entity_counts, titles

            insufficient = is_sample_insufficient(
                category_counts, saturation_threshold, f1_ratio_threshold, f2_min
            ) or is_sample_insufficient(entity_counts, saturation_threshold, f1_ratio_threshold, f2_min)
            if not insufficient:
                return "saturated", iteration, category_counts, entity_counts, titles

            iteration += 1
            compiled = await self.chat_service.run_final_search(query, api, year_from, year_to, iteration=iteration)

            if not compiled.get("success"):
                logger.warning(
                    "statistical_inference_fetch_failed", api=api, iteration=iteration, error=compiled.get("error")
                )
                return "fetch_error", iteration - 1, category_counts, entity_counts, titles

            new_category = compiled.get(category_field) or {}
            new_entity = compiled.get(entity_field) or {}
            new_titles = compiled.get("title") or []
            if not new_category and not new_entity and not new_titles:
                return "no_more_data", iteration - 1, category_counts, entity_counts, titles

            category_counts = _merge_counts(category_counts, new_category)
            entity_counts = fuzzy_group_names(_merge_counts(entity_counts, new_entity), fuzzy_threshold)
            titles = titles + new_titles

    def _compute_theme_relevance(self, theme: str, titles: list[str], max_titles: int) -> float:
        """
        Média da similaridade de cosseno (embeddings SBERT via
        self.embedding, mesma porta usada em outros pontos do app) entre o
        tema da pesquisa e até `max_titles` títulos em inglês, sorteados
        aleatoriamente da amostra acumulada. 0.0 se não houver nenhum
        título utilizável (amostra vazia, ou tema/títulos sem embedding
        disponível).
        """
        english_titles = [t for t in titles if t and not is_non_english_abstract(t)]
        if not english_titles:
            return 0.0

        sample = random.sample(english_titles, min(max_titles, len(english_titles)))

        theme_vec = self.embedding.embed_text(theme)
        if theme_vec is None:
            return 0.0
        theme_arr = np.array(theme_vec)
        theme_norm = float(np.linalg.norm(theme_arr))
        if theme_norm == 0:
            return 0.0

        title_vecs = self.embedding.embed_batch(sample)
        scores: list[float] = []
        for vec in title_vecs:
            if vec is None:
                continue
            arr = np.array(vec)
            denom = theme_norm * float(np.linalg.norm(arr))
            if denom == 0:
                continue
            scores.append(float(np.dot(theme_arr, arr) / denom))

        return float(np.mean(scores)) if scores else 0.0


def _merge_counts(base: dict[str, int], extra: dict[str, int]) -> dict[str, int]:
    """Soma duas contagens por chave exata (Counter-style), sem depender de collections.Counter pra manter o tipo dict[str,int] simples no retorno."""
    merged = dict(base)
    for key, value in extra.items():
        merged[key] = merged.get(key, 0) + value
    return merged
