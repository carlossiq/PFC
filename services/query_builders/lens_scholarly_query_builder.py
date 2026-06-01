"""
Query builder for Lens Scholarly API.

Gera queries Elasticsearch com:
- Title e Abstract combinados com OR (buscar em um ou outro)
- Outros campos com AND (obrigatório)
"""

import json
from pathlib import Path
from typing import Any, Optional

from core.config import settings
from core.logging import get_logger
from schemas.llm import LLMOutput, SimpleFieldQuery, TermGroup, TextualFieldQuery
from services.query_builders.base import BaseQueryBuilder

logger = get_logger(__name__)


class LensScholarlyQueryBuilder(BaseQueryBuilder):
    """
    Construtor de consultas para Lens Scholarly API.

    Transforma saída normalizada do LLM em JSON payload específico
    da Lens Scholarly API para publicações acadêmicas.
    """

    # Configurações da API
    _MAX_QUERY_LENGTH = 50000
    _FIELD_MAP_FILE = Path(__file__).parent.parent.parent / "config" / "dict" / "lens_scholarly_fields.json"

    def __init__(self, api_name: str = "lens_scholarly", search_mode: str = "general") -> None:
        """
        Inicializa o construtor Lens Scholarly.

        Args:
            api_name: Nome da API.
            search_mode: Modo de busca (probe ou general).
        """
        super().__init__(api_name, search_mode)
        self.field_map = self._load_field_map()

    @property
    def api_identifier(self) -> str:
        """
        Identificador da Lens Scholarly API.
        """
        return "lens.org/scholarly"

    @property
    def max_query_length(self) -> int:
        """
        Comprimento máximo de consulta Lens Scholarly.
        """
        return self._MAX_QUERY_LENGTH

    def build_query(
        self,
        llm_output: LLMOutput,
        year_from: int,
        year_to: int,
    ) -> dict[str, Any]:
        """
        Constrói payload JSON para Lens Scholarly API.

        Estratégia:
        - Title e Abstract: combinados com OR (buscar em um ou outro)
        - Outros campos: combinados com AND

        Args:
            llm_output: Saída normalizada do LLM.
            year_from: Ano inicial.
            year_to: Ano final.

        Returns:
            Dicionário com payload para Lens Scholarly.
        """
        # Iniciar payload
        payload = {
            "query": {
                "bool": {
                    "must": [],
                    "should": [],  # Para title/abstract com OR
                }
            }
        }

        # Estratégia especial: title e abstract combinados com OR (should clause)
        title_query = None
        abstract_query = None

        title_value = getattr(llm_output, "title")
        if not title_value.is_empty():
            lens_field = self.field_map.get("textual", {}).get("title")
            if lens_field:
                title_query = self._build_textual_query(title_value, lens_field)

        abstract_value = getattr(llm_output, "abstract")
        if not abstract_value.is_empty():
            lens_field = self.field_map.get("textual", {}).get("abstract")
            if lens_field:
                abstract_query = self._build_textual_query(abstract_value, lens_field)

        # Adicionar title e abstract ao should (OR)
        if title_query:
            payload["query"]["bool"]["should"].append(title_query)
        if abstract_query:
            payload["query"]["bool"]["should"].append(abstract_query)

        # Se há should clauses, definir minimum_should_match = 1 (pelo menos um deve bater)
        if payload["query"]["bool"]["should"]:
            payload["query"]["bool"]["minimum_should_match"] = 1

        # Construir consultas para outros campos textuais com AND
        for field_name in ["claims", "description", "full_text"]:
            field_value = getattr(llm_output, field_name)

            if not field_value.is_empty():
                lens_field = self.field_map.get("textual", {}).get(field_name)

                if lens_field:
                    query_clause = self._build_textual_query(field_value, lens_field)
                    payload["query"]["bool"]["must"].append(query_clause)

        # Construir consultas para campos simples com AND
        for field_name in [
            "authors",
            "affiliation",
            "field_of_study",
            "keywords",
            "source_title",
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

        # Adicionar size baseado em search_mode
        if self.search_mode == "probe":
            payload["size"] = getattr(settings, "probe_top_k", 10)
        else:
            payload["size"] = getattr(settings, "final_top_k", 100)

        payload["from"] = 0

        # Validar comprimento
        query_str = json.dumps(payload)
        if len(query_str) > self.max_query_length:
            logger.warning(
                "lens_scholarly_query_exceeds_max_length",
                length=len(query_str),
                max=self.max_query_length,
                search_mode=self.search_mode,
            )

        logger.info(
            "lens_scholarly_query_built",
            search_mode=self.search_mode,
            query_length=len(query_str),
            size=payload.get("size"),
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

        if len(field.values) == 1:
            return {"term": {lens_field: field.values[0]}}
        else:
            return {"terms": {lens_field: field.values}}

    def _build_date_query(self, year_from: int, year_to: int) -> Optional[dict[str, Any]]:
        """
        Constrói cláusula de intervalo de anos para publicações.

        Args:
            year_from: Ano inicial.
            year_to: Ano final.

        Returns:
            Cláusula de range ou None se inválido.
        """
        if year_from <= 0 or year_to <= 0 or year_from > year_to:
            return None

        return {
            "range": {
                "year_published": {
                    "gte": year_from,
                    "lte": year_to,
                }
            }
        }

    def _load_field_map(self) -> dict[str, dict[str, str]]:
        """
        Carrega mapa de campos da Lens Scholarly API.

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
                "title": "title",
                "abstract": "abstract",
                "claims": None,  # Não disponível para publicações
                "description": "abstract",
                "full_text": "full_text",
            },
            "simple": {
                "authors": "authors.name",
                "affiliation": "authors.affiliations",
                "field_of_study": "fields_of_study",
                "keywords": "keywords",
                "source_title": "source.title",
                "year": "year_published",
            },
        }
