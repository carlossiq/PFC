"""
Base abstract class for query builders.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from schemas.llm import LLMOutput


class BaseQueryBuilder(ABC):
    """
    Interface abstrata para construtores de consultas API.

    Define contrato que todos os construtores devem implementar
    para transformar saída normalizada do LLM em queries específicas
    de cada API (Lens, OPS, Scopus, etc).
    """

    def __init__(self, api_name: str, search_mode: str = "general", variant: Optional[str] = None) -> None:
        """
        Inicializa o construtor de consultas.

        Args:
            api_name: Nome da API (lens_patent, lens_scholarly, ops, scopus).
            search_mode: Modo de busca (probe ou final).
            variant: Variante da busca final (specific/balanced/generic) -
                None pra probe, onde o conceito não existe (ver
                ChatService.build_probe_queries_multi). Usada só por
                `_title_abstract_operator` hoje.
        """
        self.api_name = api_name
        self.search_mode = search_mode
        self.variant = variant

    def _title_abstract_operator(self) -> str:
        """TITLE e ABSTRACT são combinados com OR em todo modo/variante,
        MENOS na variante "specific" da busca final, onde viram AND.

        Motivo: o próprio ABSTRACT já pode ter 1-2 conceitos secundários
        mais soltos (ver probe_system_prompt.txt/final_system_prompt.md,
        seção ABSTRACT CONSTRAINT) - com OR, um documento que só bate nesse
        ABSTRACT mais largo entra no resultado mesmo sem bater no TITLE
        apertado, e a variante "specific" deixa de ser específica na
        prática, não importa quão bem a IA monte os grupos internos. Nos
        demais casos (probe, balanced, generic) o OR é intencional -
        recall-first, ver FIELD COMBINATION LOGIC nos prompts."""
        if self.search_mode == "final" and self.variant == "specific":
            return "AND"
        return "OR"

    @abstractmethod
    def build_query(
        self,
        llm_output: LLMOutput,
        year_from: int,
        year_to: int,
    ) -> Any:
        """
        Constrói consulta específica da API a partir de saída LLM.

        Args:
            llm_output: Saída normalizada do LLM com campos estruturados.
            year_from: Ano inicial da busca (SEARCH_YEAR_FROM).
            year_to: Ano final da busca (SEARCH_YEAR_TO).

        Returns:
            Consulta estruturada específica da API.

        Raises:
            Exception: Se construção da consulta falhar.
        """
        pass

    @property
    @abstractmethod
    def api_identifier(self) -> str:
        """
        Identificador único da API.

        Returns:
            String com identificação da API.
        """
        pass

    @property
    @abstractmethod
    def max_query_length(self) -> int:
        """
        Comprimento máximo de uma consulta para esta API.

        Returns:
            Número máximo de caracteres.
        """
        pass
