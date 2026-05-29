from __future__ import annotations

import logging
import math
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from app.core.domain.types import Embedding, LLMRequest, LLMResponse, SearchResult
from app.core.ports.outbound.embedding_port import EmbeddingPort
from app.core.ports.outbound.llm_port import LLMPort
from app.core.ports.outbound.query_builder_port import (
    PatentQueryBuilderPort,
    ScholarlyQueryBuilderPort,
)
from app.core.ports.outbound.repository_port import (
    DedupRegistryPort,
    PatentRepositoryPort,
    ScholarlyRepositoryPort,
)
from app.core.ports.outbound.search_port import PatentSearchPort, ScholarlySearchPort

logger = logging.getLogger(__name__)


@dataclass
class PipelineRunResult:
    run_id: str
    success: bool
    total_found: int = 0
    after_filter: int = 0
    unique: int = 0
    persisted: int = 0
    api_failures: dict[str, str] = field(default_factory=dict)
    duration_seconds: float = 0.0


class ResearchService:
    """
    Core domain service para o pipeline de prospecção tecnológica.

    Recebe todos os colaboradores via injeção de dependência e não importa
    nenhuma biblioteca externa nem módulos de adapters/services/db.
    """

    def __init__(
        self,
        llm: LLMPort,
        embedding: EmbeddingPort,
        patent_pairs: list[tuple[PatentSearchPort, PatentQueryBuilderPort]],
        scholarly_pairs: list[tuple[ScholarlySearchPort, ScholarlyQueryBuilderPort]],
        patent_repo: PatentRepositoryPort,
        scholarly_repo: ScholarlyRepositoryPort,
        dedup_registry: DedupRegistryPort,
        year_from: int = 2015,
        year_to: int = 2024,
        relevance_threshold: float = 0.3,
    ) -> None:
        self._llm = llm
        self._embedding = embedding
        self._patent_pairs = patent_pairs
        self._scholarly_pairs = scholarly_pairs
        self._patent_repo = patent_repo
        self._scholarly_repo = scholarly_repo
        self._dedup_registry = dedup_registry
        self._year_from = year_from
        self._year_to = year_to
        self._relevance_threshold = relevance_threshold

    # ------------------------------------------------------------------
    # Step 1 – Geração de estratégia via LLM
    # ------------------------------------------------------------------

    async def generate_strategy(
        self,
        request: LLMRequest,
        system_prompt: str,
    ) -> LLMResponse:
        response = await self._llm.process_intake(request=request, system_prompt=system_prompt)
        logger.info("strategy_generated theme=%s", request.theme)
        return response

    # ------------------------------------------------------------------
    # Step 2 – Probe search (um único par port+builder)
    # ------------------------------------------------------------------

    async def probe_search(
        self,
        strategy: LLMResponse,
        pair: tuple[PatentSearchPort, PatentQueryBuilderPort],
        run_id: str,
    ) -> SearchResult:
        search_port, builder_port = pair
        query = builder_port.build_query(
            strategy,
            year_from=self._year_from,
            year_to=self._year_to,
            search_mode="probe",
        )
        result = await search_port.search(query=query, run_id=run_id)
        logger.info(
            "probe_search_done api=%s success=%s docs=%d",
            search_port.api_name,
            result.success,
            result.results_returned,
        )
        return result

    # ------------------------------------------------------------------
    # Step 3 – Extração de palavras-chave (sem bibliotecas externas)
    # ------------------------------------------------------------------

    def extract_keywords_from_docs(
        self,
        documents: list[dict[str, Any]],
        top_k: int = 20,
        stopwords: Optional[set[str]] = None,
    ) -> list[str]:
        """
        Extração de palavras-chave por frequência de tokens.

        Implementação stdlib pura. Para extração semântica (KeyBERT),
        o chamador pode complementar usando o KeywordService legado.
        """
        if stopwords is None:
            stopwords = _DEFAULT_STOPWORDS

        freq: dict[str, int] = {}
        for doc in documents:
            text = " ".join(
                str(doc.get(f) or "")
                for f in ("title", "abstract", "keywords")
            )
            tokens = _tokenize(text)
            for token in tokens:
                if token and token not in stopwords and len(token) > 2:
                    freq[token] = freq.get(token, 0) + 1

        ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in ranked[:top_k]]

    # ------------------------------------------------------------------
    # Step 4 – Production search (todos os pares)
    # ------------------------------------------------------------------

    async def production_search(
        self,
        patent_strategy: LLMResponse,
        scholarly_strategy: LLMResponse,
        run_id: str,
    ) -> list[SearchResult]:
        results: list[SearchResult] = []

        for search_port, builder_port in self._patent_pairs:
            try:
                query = builder_port.build_query(
                    patent_strategy,
                    year_from=self._year_from,
                    year_to=self._year_to,
                )
                result = await search_port.search(query=query, run_id=run_id)
                results.append(result)
                logger.info(
                    "patent_search_done api=%s success=%s docs=%d",
                    search_port.api_name,
                    result.success,
                    result.results_returned,
                )
            except Exception as exc:
                logger.error("patent_search_error api=%s error=%s", search_port.api_name, exc)

        for search_port, builder_port in self._scholarly_pairs:
            try:
                query = builder_port.build_query(
                    scholarly_strategy,
                    year_from=self._year_from,
                    year_to=self._year_to,
                )
                result = await search_port.search(query=query, run_id=run_id)
                results.append(result)
                logger.info(
                    "scholarly_search_done api=%s success=%s docs=%d",
                    search_port.api_name,
                    result.success,
                    result.results_returned,
                )
            except Exception as exc:
                logger.error("scholarly_search_error api=%s error=%s", search_port.api_name, exc)

        return results

    # ------------------------------------------------------------------
    # Step 5 – Filtro de relevância semântica
    # ------------------------------------------------------------------

    def filter_by_relevance(
        self,
        theme: str,
        documents: list[dict[str, Any]],
        threshold: Optional[float] = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        threshold = threshold if threshold is not None else self._relevance_threshold
        theme_emb = self._embedding.embed_text(theme)

        if theme_emb is None:
            logger.warning("theme_embedding_failed — returning all docs as approved")
            return documents, []

        approved: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []

        for doc in documents:
            doc_emb = self._embedding.embed_document(
                title=doc.get("title"),
                abstract=doc.get("abstract"),
            )
            if doc_emb is None:
                approved.append(doc)
                continue

            score = _cosine_similarity(theme_emb, doc_emb)
            if score >= threshold:
                approved.append({**doc, "relevance_score": round(score, 4)})
            else:
                rejected.append(doc)

        logger.info(
            "relevance_filter done approved=%d rejected=%d threshold=%.2f",
            len(approved),
            len(rejected),
            threshold,
        )
        return approved, rejected

    # ------------------------------------------------------------------
    # Step 6 – Deduplicação (puro)
    # ------------------------------------------------------------------

    def deduplicate(
        self,
        patents: list[dict[str, Any]],
        scholarly: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        unique_patents, dup_patents = _deduplicate_patents(patents)
        unique_scholarly, dup_scholarly = _deduplicate_scholarly(scholarly)
        logger.info(
            "dedup_done patents=%d->%d scholarly=%d->%d",
            len(patents),
            len(unique_patents),
            len(scholarly),
            len(unique_scholarly),
        )
        return {
            "unique_patents": unique_patents,
            "unique_scholarly": unique_scholarly,
            "duplicate_patents": dup_patents,
            "duplicate_scholarly": dup_scholarly,
        }

    # ------------------------------------------------------------------
    # Step 7 – Persistência via repository ports
    # ------------------------------------------------------------------

    async def persist_batch(
        self,
        patents: list[dict[str, Any]],
        scholarly: list[dict[str, Any]],
        run_id: str,
    ) -> dict[str, int]:
        from schemas.normalized_metadata import (  # noqa: PLC0415
            StandardizedPatentMetadata,
            StandardizedScholarlyMetadata,
        )

        created_patents = 0
        skipped_patents = 0
        created_scholarly = 0
        skipped_scholarly = 0

        for p in patents:
            dedup_key = p.get("dedup_key", "")
            if dedup_key and await self._dedup_registry.exists_patent(dedup_key):
                skipped_patents += 1
                continue
            meta = StandardizedPatentMetadata(**p)
            doc_id = await self._patent_repo.create(meta)
            if dedup_key:
                await self._dedup_registry.register_patent(
                    dedup_key=dedup_key,
                    document_id=int(doc_id),
                    source=p.get("source", ""),
                    source_record_id=p.get("source_record_id", ""),
                )
            created_patents += 1

        for a in scholarly:
            dedup_key = a.get("dedup_key", "")
            if dedup_key and await self._dedup_registry.exists_scholarly(dedup_key):
                skipped_scholarly += 1
                continue
            meta = StandardizedScholarlyMetadata(**a)
            doc_id = await self._scholarly_repo.create(meta)
            if dedup_key:
                await self._dedup_registry.register_scholarly(
                    dedup_key=dedup_key,
                    document_id=int(doc_id),
                    source=a.get("source", ""),
                    source_record_id=a.get("source_record_id", ""),
                )
            created_scholarly += 1

        logger.info(
            "persist_batch_done patents_created=%d patents_skipped=%d "
            "scholarly_created=%d scholarly_skipped=%d run_id=%s",
            created_patents,
            skipped_patents,
            created_scholarly,
            skipped_scholarly,
            run_id,
        )
        return {
            "patents_created": created_patents,
            "patents_skipped": skipped_patents,
            "scholarly_created": created_scholarly,
            "scholarly_skipped": skipped_scholarly,
        }


# ------------------------------------------------------------------
# Helpers privados (sem bibliotecas externas)
# ------------------------------------------------------------------

def _cosine_similarity(a: Embedding, b: Embedding) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x ** 2 for x in a))
    norm_b = math.sqrt(sum(x ** 2 for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = "".join(
        c
        for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return re.findall(r"[a-z0-9]+", text)


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = "".join(
        c
        for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return " ".join(text.split())


def _patent_key(doc: dict[str, Any]) -> str:
    pub = doc.get("publication_number")
    if pub:
        return f"patent:{pub}"
    title = _normalize_text(doc.get("title", ""))
    year = doc.get("year", "unknown")
    if title:
        return f"patent:{title}:{year}"
    return f"patent:{doc.get('source_record_id', 'unknown')}"


def _scholarly_key(doc: dict[str, Any]) -> str:
    doi = doc.get("doi")
    if doi:
        return f"scholarly:{doi.lower()}"
    title = _normalize_text(doc.get("title", ""))
    year = doc.get("year", "unknown")
    if title:
        return f"scholarly:{title}:{year}"
    return f"scholarly:{doc.get('source_record_id', 'unknown')}"


def _deduplicate_patents(
    docs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen: set[str] = set()
    unique, dupes = [], []
    for doc in docs:
        key = _patent_key(doc)
        if key not in seen:
            seen.add(key)
            unique.append(doc)
        else:
            dupes.append(doc)
    return unique, dupes


def _deduplicate_scholarly(
    docs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen: set[str] = set()
    unique, dupes = [], []
    for doc in docs:
        key = _scholarly_key(doc)
        if key not in seen:
            seen.add(key)
            unique.append(doc)
        else:
            dupes.append(doc)
    return unique, dupes


_DEFAULT_STOPWORDS: set[str] = {
    "the", "of", "and", "in", "a", "to", "for", "with", "on", "at",
    "an", "by", "is", "are", "was", "be", "as", "or", "from", "that",
    "this", "it", "its", "we", "our", "has", "have", "been", "which",
    "also", "into", "not", "can", "but", "de", "da", "do", "em", "e",
    "o", "a", "os", "as", "um", "uma", "para", "com", "por", "se",
}
