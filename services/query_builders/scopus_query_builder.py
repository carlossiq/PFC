"""
Query builder for Scopus API.
"""

import json
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

from core.logging import get_logger
from schemas.llm import LLMOutput, SimpleFieldQuery, TextualFieldQuery
from services.query_builders.base import BaseQueryBuilder

logger = get_logger(__name__)


class ScopusQueryBuilder(BaseQueryBuilder):
    """
    Construtor de consultas para Scopus API.

    Transforma saída normalizada do LLM em parâmetros de requisição
    específicos da Scopus API para publicações acadêmicas e citações.
    """

    # Configurações da API
    _MAX_QUERY_LENGTH = 10000
    _FIELD_MAP_FILE = Path(__file__).parent.parent.parent / "schemas_config" / "scopus_fields.json"

    def __init__(self, api_name: str = "scopus", search_mode: str = "general") -> None:
        """
        Inicializa o construtor Scopus.

        Args:
            api_name: Nome da API.
            search_mode: Modo de busca (probe ou general).
        """
        super().__init__(api_name, search_mode)
        self.field_map = self._load_field_map()

    @property
    def api_identifier(self) -> str:
        """
        Identificador da Scopus API.
        """
        return "api.elsevier.com/content/search/scopus"

    @property
    def max_query_length(self) -> int:
        """
        Comprimento máximo de consulta Scopus.
        """
        return self._MAX_QUERY_LENGTH

    def build_query(
        self,
        llm_output: LLMOutput,
        year_from: int,
        year_to: int,
    ) -> dict[str, Any]:
        """
        Constrói parâmetros de requisição para Scopus API.

        Args:
            llm_output: Saída normalizada do LLM.
            year_from: Ano inicial (SEARCH_YEAR_FROM).
            year_to: Ano final (SEARCH_YEAR_TO).

        Returns:
            Dicionário com parâmetros para Scopus API.
        """
        # Construir partes da query
        query_parts = []

        # Campos textuais
        for field_name in ["title", "abstract", "description", "full_text"]:
            field_value = getattr(llm_output, field_name)

            if not field_value.is_empty():
                scopus_field = self.field_map.get("textual", {}).get(field_name)

                if scopus_field:
                    query_part = self._build_textual_query(field_value, scopus_field)
                    if query_part:
                        query_parts.append(query_part)

        # Campos simples
        for field_name in [
            "authors",
            "affiliation",
            "field_of_study",
            "keywords",
            "source_title",
            "year",
        ]:
            field_value = getattr(llm_output, field_name)

            if not field_value.is_empty():
                scopus_field = self.field_map.get("simple", {}).get(field_name)

                if scopus_field:
                    query_part = self._build_simple_query(field_value, scopus_field)
                    if query_part:
                        query_parts.append(query_part)

        # Adicionar intervalo de anos
        date_query = self._build_date_query(year_from, year_to)
        if date_query:
            query_parts.append(date_query)

        # Combinar partes com AND
        scopus_query = " AND ".join(query_parts)

        # Validar comprimento
        if len(scopus_query) > self.max_query_length:
            logger.warning(
                "query_exceeds_max_length",
                api=self.api_name,
                length=len(scopus_query),
                max=self.max_query_length,
            )

        # Construir parâmetros da requisição
        params = {
            "query": scopus_query,
            "sort": "citedby-count,pubdate",  # TODO: Fazer configurável
            "count": 25,  # TODO: Fazer configurável
            "start": 0,
            "view": "COMPLETE",  # TODO: Fazer configurável
        }

        logger.info(
            "scopus_query_built",
            search_mode=self.search_mode,
            query_length=len(scopus_query),
        )

        return params

    def _build_textual_query(
        self,
        field: TextualFieldQuery,
        scopus_field: str,
    ) -> Optional[str]:
        """
        Constrói parte textual de query Scopus.

        Args:
            field: Campo textual estruturado.
            scopus_field: Nome do campo na Scopus API.

        Returns:
            String de query ou None se vazio.
        """
        if not field.groups:
            return None

        group_queries = []

        for group in field.groups:
            if not group.terms:
                continue

            # Scopus sintaxe: TITLE() ou ABSTRACT() etc
            escaped_terms = [self._escape_scopus_term(term) for term in group.terms]

            # Combinar com operador
            if group.operator.value == "OR":
                term_query = f" OR ".join(escaped_terms)
            else:  # AND
                term_query = f" AND ".join(escaped_terms)

            group_queries.append(f"{scopus_field}(({term_query}))")

        if not group_queries:
            return None

        # Combinar grupos
        if len(group_queries) == 1:
            return group_queries[0]
        elif field.group_operator.value == "AND":
            return " AND ".join(group_queries)
        else:  # OR
            return " OR ".join(group_queries)

    def _build_simple_query(
        self,
        field: SimpleFieldQuery,
        scopus_field: str,
    ) -> Optional[str]:
        """
        Constrói parte simples de query Scopus.

        Args:
            field: Campo simples com lista de valores.
            scopus_field: Nome do campo na Scopus API.

        Returns:
            String de query ou None se vazio.
        """
        if not field.values:
            return None

        escaped_values = [self._escape_scopus_term(val) for val in field.values]

        if len(escaped_values) == 1:
            return f'{scopus_field}("{escaped_values[0]}")'
        else:
            # TODO: Definir estratégia final para múltiplos valores
            values_query = f'" OR "{scopus_field}("'.join(escaped_values)
            return f'{scopus_field}("{values_query}")'

    def _build_date_query(self, year_from: int, year_to: int) -> Optional[str]:
        """
        Constrói cláusula de intervalo de anos Scopus.

        Args:
            year_from: Ano inicial.
            year_to: Ano final.

        Returns:
            String de query ou None se inválido.
        """
        if year_from <= 0 or year_to <= 0 or year_from > year_to:
            return None

        # Scopus PUBYEAR range
        return f"PUBYEAR > {year_from - 1} AND PUBYEAR < {year_to + 1}"

    @staticmethod
    def _escape_scopus_term(term: str) -> str:
        """
        Escapa termo para query Scopus.

        Remove caracteres especiais e aspas.

        Args:
            term: Termo a escapar.

        Returns:
            Termo escapado para Scopus.
        """
        # Remover aspas
        term = term.replace('"', "")
        # Remover caracteres especiais para Scopus
        # Manter hífens e underscores
        term = "".join(c for c in term if c.isalnum() or c in ["-", "_", " "])
        return term.strip()

    def _load_field_map(self) -> dict[str, dict[str, str]]:
        """
        Carrega mapa de campos da Scopus API.

        Returns:
            Dicionário com mapeamento de campos.
        """
        if not self._FIELD_MAP_FILE.exists():
            logger.warning(f"Field map file not found: {self._FIELD_MAP_FILE}")
            return self._get_default_field_map()

        try:
            with open(self._FIELD_MAP_FILE, "r") as f:
                return json.load(f)
        except Exception as exc:
            logger.error(f"Failed to load field map: {exc}")
            return self._get_default_field_map()

    @staticmethod
    def _get_default_field_map() -> dict[str, dict[str, str]]:
        """
        Retorna mapa de campos padrão Scopus.

        Returns:
            Mapa padrão com campos conhecidos.
        """
        return {
            "textual": {
                "title": "TITLE",
                "abstract": "ABS",
                "claims": None,  # Não disponível
                "description": "ABS",
                "full_text": None,  # Requer acesso especial
            },
            "simple": {
                "authors": "AUTH",
                "affiliation": "AFFILORG",
                "field_of_study": "SUBJAREA",
                "keywords": "KEY",
                "source_title": "SRCTITLE",
                "year": "PUBYEAR",
            },
        }
