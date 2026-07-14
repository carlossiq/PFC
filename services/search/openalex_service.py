"""
Complementary abstract lookup via OpenAlex (public API, no key required).
"""

import asyncio
from typing import Any, Optional

import httpx

from core.logging import get_logger

logger = get_logger(__name__)


class OpenAlexService:
    """
    Busca metadados complementares via OpenAlex, usando o DOI que a Scopus
    Search API já retorna mas cujo abstract (dc:description) e área de
    assunto por artigo a API key do projeto não tem entitlement pra receber
    (ver notes/pendencias.md). O OpenAlex não garante cobertura total -
    alguns DOIs não estão indexados ou têm o abstract retido pela editora -
    então o retorno é best-effort: campos None/vazios quando não encontrado,
    nunca uma exceção pro chamador.
    """

    _BASE_URL = "https://api.openalex.org/works/doi:{doi}"
    _TIMEOUT_SECONDS = 10
    _MAX_CONCURRENCY = 8
    _MAX_CONCEPTS = 3

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=self._TIMEOUT_SECONDS)
        self._semaphore = asyncio.Semaphore(self._MAX_CONCURRENCY)

    @staticmethod
    def _reconstruct_abstract(inverted_index: Optional[dict[str, list[int]]]) -> Optional[str]:
        """OpenAlex devolve o abstract como índice invertido (palavra -> posições), não como texto - precisa remontar a ordem original."""
        if not inverted_index:
            return None
        max_pos = max(pos for positions in inverted_index.values() for pos in positions)
        words: list[Optional[str]] = [None] * (max_pos + 1)
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        abstract = " ".join(w for w in words if w)
        return abstract or None

    @classmethod
    def _extract_field_of_study(cls, concepts: Optional[list[dict]]) -> list[str]:
        """OpenAlex classifica cada trabalho com uma lista de "concepts" (área/assunto,
        com um score de confiança) - pega os mais relevantes como aproximação de
        field_of_study, já que a Scopus não libera isso pra essa API key."""
        if not concepts:
            return []
        sorted_concepts = sorted(concepts, key=lambda c: c.get("score", 0), reverse=True)
        return [
            c["display_name"]
            for c in sorted_concepts[: cls._MAX_CONCEPTS]
            if c.get("display_name")
        ]

    async def fetch_metadata(self, doi: str) -> dict[str, Any]:
        async with self._semaphore:
            try:
                response = await self._client.get(self._BASE_URL.format(doi=doi))
                if response.status_code != 200:
                    return {"abstract": None, "field_of_study": []}
                data = response.json()
                return {
                    "abstract": self._reconstruct_abstract(data.get("abstract_inverted_index")),
                    "field_of_study": self._extract_field_of_study(data.get("concepts")),
                }
            except Exception as exc:
                logger.warning("openalex_fetch_metadata_failed", doi=doi, error=str(exc))
                return {"abstract": None, "field_of_study": []}

    async def fetch_metadata_batch(self, dois: list[str]) -> dict[str, dict[str, Any]]:
        if not dois:
            return {}
        results = await asyncio.gather(*(self.fetch_metadata(doi) for doi in dois))
        return dict(zip(dois, results))

    async def close(self) -> None:
        await self._client.aclose()
