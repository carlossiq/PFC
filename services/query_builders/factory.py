"""
Factory for creating query builder instances.
"""

from typing import Optional

from core.logging import get_logger
from services.query_builders.base import BaseQueryBuilder
from services.query_builders.lens_patent_query_builder import LensPatentQueryBuilder
from services.query_builders.lens_scholarly_query_builder import LensScholarlyQueryBuilder
from services.query_builders.ops_query_builder import OPSQueryBuilder
from services.query_builders.scopus_query_builder import ScopusQueryBuilder

logger = get_logger(__name__)


class QueryBuilderFactory:
    """
    Factory para criação de construtores de consulta API.

    Gerencia a instanciação de diferentes builders baseado na API especificada.
    """

    _builders = {
        "lens_patent": LensPatentQueryBuilder,
        "lens_scholarly": LensScholarlyQueryBuilder,
        "ops": OPSQueryBuilder,
        "scopus": ScopusQueryBuilder,
    }

    @staticmethod
    def create(
        api_name: str,
        search_mode: str = "general",
    ) -> BaseQueryBuilder:
        """
        Cria instância de construtor de consulta.

        Args:
            api_name: Nome da API (lens_patent, lens_scholarly, ops, scopus).
            search_mode: Modo de busca (probe ou general).

        Returns:
            Instância de BaseQueryBuilder.

        Raises:
            ValueError: Se API não for suportada.
        """
        builder_class = QueryBuilderFactory._builders.get(api_name.lower())

        if not builder_class:
            raise ValueError(
                f"Unsupported API: {api_name}. "
                f"Supported: {', '.join(QueryBuilderFactory._builders.keys())}"
            )

        builder = builder_class(api_name, search_mode)

        logger.info(
            "query_builder_created",
            api=api_name,
            search_mode=search_mode,
        )

        return builder

    @staticmethod
    def get_supported_apis() -> list[str]:
        """
        Retorna lista de APIs suportadas.

        Returns:
            Lista de nomes de APIs.
        """
        return list(QueryBuilderFactory._builders.keys())

    @staticmethod
    def register_builder(api_name: str, builder_class: type) -> None:
        """
        Registra um novo construtor de consulta customizado.

        Args:
            api_name: Nome da API.
            builder_class: Classe do construtor (deve herdar BaseQueryBuilder).
        """
        if not issubclass(builder_class, BaseQueryBuilder):
            raise TypeError(f"{builder_class} must inherit from BaseQueryBuilder")

        QueryBuilderFactory._builders[api_name.lower()] = builder_class

        logger.info("query_builder_registered", api=api_name)
