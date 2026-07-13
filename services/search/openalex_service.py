"""
Complementary abstract lookup via OpenAlex (public API, no key required).
"""

import asyncio
from typing import Optional

import httpx

from core.logging import get_logger

logger = get_logger(__name__)


class OpenAlexService:
    """
    Busca abstracts complementares via OpenAlex, usando o DOI que a Scopus
    Search API já retorna mas cujo abstract (dc:description) a API key do
    projeto não tem entitlement pra receber (ver notes/pendencias.md). O
    OpenAlex não garante cobertura total - alguns DOIs não estão indexados
    ou têm o abstract retido pela editora - então o retorno é best-effort:
    None quando não encontrado, nunca uma exceção pro chamador.
    """

    _BASE_URL = "https://api.openalex.org/works/doi:{doi}"
    _TIMEOUT_SECONDS = 10
    _MAX_CONCURRENCY = 8

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

    async def fetch_abstract(self, doi: str) -> Optional[str]:
        async with self._semaphore:
            try:
                response = await self._client.get(self._BASE_URL.format(doi=doi))
                if response.status_code != 200:
                    return None
                data = response.json()
                return self._reconstruct_abstract(data.get("abstract_inverted_index"))
            except Exception as exc:
                logger.warning("openalex_fetch_abstract_failed", doi=doi, error=str(exc))
                return None

    async def fetch_abstracts(self, dois: list[str]) -> dict[str, Optional[str]]:
        if not dois:
            return {}
        results = await asyncio.gather(*(self.fetch_abstract(doi) for doi in dois))
        return dict(zip(dois, results))

    async def close(self) -> None:
        await self._client.aclose()
