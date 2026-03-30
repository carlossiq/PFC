"""
Query builder for Lens Patent API.
"""

import json
from pathlib import Path
from typing import Any, Optional

from core.logging import get_logger
from schemas.llm import LLMOutput, SimpleFieldQuery, TermGroup, TextualFieldQuery
from services.query_builders.base import BaseQueryBuilder

logger = get_logger(__name__)


class LensPatentQueryBuilder(BaseQueryBuilder):
    """
    Construtor de consultas para Lens Patent API.

    Transforma saída normalizada do LLM em JSON payload específico
    da Lens Patent API, aplicando sintaxe e regras de busca booleana.
    """

    # Configurações da API
    _MAX_QUERY_LENGTH = 50000
    _FIELD_MAP_FILE = Path(__file__).parent.parent.parent / "schemas_config" / "lens_patent_fields.json"

    def __init__(self, api_name: str = "lens_patent", search_mode: str = "general") -> None:
        """
        Inicializa o construtor Lens Patent.

        Args:
            api_name: Nome da API.
            search_mode: Modo de busca (probe ou general).
        """
        super().__init__(api_name, search_mode)
        self.field_map = self._load_field_map()

    @property
    def api_identifier(self) -> str:
        """
        Identificador da Lens Patent API.
        """
        return "lens.org/patent"

    @property
    def max_query_length(self) -> int:
        """
        Comprimento máximo de consulta Lens Patent.
        """
        return self._MAX_QUERY_LENGTH

    def build_query(
        self,
        llm_output: LLMOutput,
        year_from: int,
        year_to: int,
    ) -> dict[str, Any]:
        """
        Constrói payload JSON para Lens Patent API.

        Args:
            llm_output: Saída normalizada do LLM.
            year_from: Ano inicial (SEARCH_YEAR_FROM).
            year_to: Ano final (SEARCH_YEAR_TO).

        Returns:
            Dicionário com payload para Lens API.
        """
        # Iniciar payload
        payload = {
            "query": {
                "bool": {
                    "must": [],
                }
            }
        }

        # Construir consultas booleanas para campos textuais
        for field_name in ["title", "abstract", "claims", "description", "full_text"]:
            field_value = getattr(llm_output, field_name)

            if not field_value.is_empty():
                lens_field = self.field_map.get("textual", {}).get(field_name)

                if lens_field:
                    query_clause = self._build_textual_query(field_value, lens_field)
                    payload["query"]["bool"]["must"].append(query_clause)

        # Construir consultas para campos simples
        for field_name in [
            "ipc",
            "cpc",
            "authors",
            "affiliation",
            "applicant",
            "inventor",
            "field_of_study",
            "keywords",
            "source_title",
            "year",
        ]:
            field_value = getattr(llm_output, field_name)

            if not field_value.is_empty():
                lens_field = self.field_map.get("simple", {}).get(field_name)

                if lens_field:
                    query_clause = self._build_simple_query(field_value, lens_field)
                    payload["query"]["bool"]["must"].append(query_clause)

        # Injetar intervalo de anos
        date_query = self._build_date_query(year_from, year_to)
        if date_query:
            payload["query"]["bool"]["must"].append(date_query)

        # Validar comprimento
        query_str = json.dumps(payload)
        if len(query_str) > self.max_query_length:
            logger.warning(
                "query_exceeds_max_length",
                api=self.api_name,
                length=len(query_str),
                max=self.max_query_length,
            )

        logger.info(
            "lens_patent_query_built",
            search_mode=self.search_mode,
            query_length=len(query_str),
        )

        return payload

    def _build_textual_query(
        self,
        field: TextualFieldQuery,
        lens_field: str,
    ) -> dict[str, Any]:
        """
        Constrói cláusula booleana para campo textual.

        Args:
            field: Campo textual estruturado.
            lens_field: Nome do campo na Lens API.

        Returns:
            Cláusula de consulta booleana.
        """
        # Construir grupos de termos
        group_queries = []

        for group in field.groups:
            if not group.terms:
                continue

            # Combinar termos do grupo com operador
            if group.operator.value == "OR":
                term_query = {
                    "multi_match": {
                        "query": " OR ".join(group.terms),
                        "fields": [lens_field],
                    }
                }
            else:  # AND
                term_query = {
                    "multi_match": {
                        "query": " AND ".join(group.terms),
                        "fields": [lens_field],
                    }
                }

            group_queries.append(term_query)

        # Combinar grupos com group_operator
        if len(group_queries) == 1:
            return group_queries[0]
        elif field.group_operator.value == "AND":
            return {"bool": {"must": group_queries}}
        else:  # OR
            return {"bool": {"should": group_queries, "minimum_should_match": 1}}

    def _build_simple_query(
        self,
        field: SimpleFieldQuery,
        lens_field: str,
    ) -> dict[str, Any]:
        """
        Constrói cláusula booleana para campo simples.

        Args:
            field: Campo simples com lista de valores.
            lens_field: Nome do campo na Lens API.

        Returns:
            Cláusula de consulta.
        """
        # TODO: Definir estratégia final para campos simples (term vs match)
        # Opções: 'terms' para busca exata, 'match' para busca fuzzy

        if len(field.values) == 1:
            return {"term": {lens_field: field.values[0]}}
        else:
            return {"terms": {lens_field: field.values}}

    def _build_date_query(self, year_from: int, year_to: int) -> Optional[dict[str, Any]]:
        """
        Constrói cláusula de intervalo de anos.

        Args:
            year_from: Ano inicial.
            year_to: Ano final.

        Returns:
            Cláusula de range ou None se inválido.
        """
        if year_from <= 0 or year_to <= 0 or year_from > year_to:
            return None

        # TODO: Confirmar nome do campo de data na Lens API (publication_date, filing_date)
        return {
            "range": {
                "publication_date": {
                    "gte": f"{year_from}-01-01",
                    "lte": f"{year_to}-12-31",
                }
            }
        }

    def _load_field_map(self) -> dict[str, dict[str, str]]:
        """
        Carrega mapa de campos da Lens Patent API.

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
        Retorna mapa de campos padrão.

        Returns:
            Mapa padrão com campos conhecidos.
        """
        return {
            "textual": {
                "title": "publication.title",
                "abstract": "publication.abstract",
                "claims": "claims.text",
                "description": "description",
                "full_text": "full_text",
            },
            "simple": {
                "ipc": "classifications.ipc_code",
                "cpc": "classifications.cpc_code",
                "authors": "publication.authors",
                "affiliation": "publication.author_affiliations",
                "applicant": "applicant",
                "inventor": "inventor",
                "field_of_study": "technology_field",
                "keywords": "keywords",
                "source_title": "publication.source",
                "year": "publication_year",
            },
        }
