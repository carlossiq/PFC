"""
Query builder for European Patent Office (OPS) API.
"""

import json
from pathlib import Path
from typing import Any, Optional

from core.logging import get_logger
from schemas.llm import LLMOutput, SimpleFieldQuery, TextualFieldQuery
from services.query_builders.base import BaseQueryBuilder

logger = get_logger(__name__)


class OPSQueryBuilder(BaseQueryBuilder):
    """
    Construtor de consultas para OPS (European Patent Office) API.

    Transforma saída normalizada do LLM em CQL (Common Query Language)
    e estrutura de requisição específica da OPS API.
    """

    # Configurações da API
    _MAX_QUERY_LENGTH = 10000  # CQL tem limite menor
    _FIELD_MAP_FILE = Path(__file__).parent.parent.parent / "schemas_config" / "ops_fields.json"

    def __init__(self, api_name: str = "ops", search_mode: str = "general") -> None:
        """
        Inicializa o construtor OPS.

        Args:
            api_name: Nome da API.
            search_mode: Modo de busca (probe ou general).
        """
        super().__init__(api_name, search_mode)
        self.field_map = self._load_field_map()

    @property
    def api_identifier(self) -> str:
        """
        Identificador da OPS API.
        """
        return "espacenet.com/ops"

    @property
    def max_query_length(self) -> int:
        """
        Comprimento máximo de consulta CQL OPS.
        """
        return self._MAX_QUERY_LENGTH

    def build_query(
        self,
        llm_output: LLMOutput,
        year_from: int,
        year_to: int,
    ) -> dict[str, Any]:
        """
        Constrói estrutura de requisição para OPS API.

        Returns CQL query e parâmetros de requisição.

        Args:
            llm_output: Saída normalizada do LLM.
            year_from: Ano inicial (SEARCH_YEAR_FROM).
            year_to: Ano final (SEARCH_YEAR_TO).

        Returns:
            Dicionário com CQL query e parâmetros OPS.
        """
        # Construir cláusulas CQL
        cql_clauses = []

        # Campos textuais
        for field_name in ["title", "abstract", "claims", "description", "full_text"]:
            field_value = getattr(llm_output, field_name)

            if not field_value.is_empty():
                ops_field = self.field_map.get("textual", {}).get(field_name)

                if ops_field:
                    cql_clause = self._build_textual_cql(field_value, ops_field)
                    if cql_clause:
                        cql_clauses.append(cql_clause)

        # Campos simples
        for field_name in [
            "ipc",
            "cpc",
            "authors",
            "applicant",
            "inventor",
            "year",
        ]:
            field_value = getattr(llm_output, field_name)

            if not field_value.is_empty():
                ops_field = self.field_map.get("simple", {}).get(field_name)

                if ops_field:
                    cql_clause = self._build_simple_cql(field_value, ops_field)
                    if cql_clause:
                        cql_clauses.append(cql_clause)

        # Adicionar intervalo de anos
        date_cql = self._build_date_cql(year_from, year_to)
        if date_cql:
            cql_clauses.append(date_cql)

        # Combinar cláusulas com AND (diferentes campos por padrão)
        cql_query = " AND ".join([f"({clause})" for clause in cql_clauses])

        # Validar comprimento
        if len(cql_query) > self.max_query_length:
            logger.warning(
                "query_exceeds_max_length",
                api=self.api_name,
                length=len(cql_query),
                max=self.max_query_length,
            )

        # Construir requisição OPS
        ops_request = {
            "query": cql_query,
            "range": "1-100",  # TODO: Fazer configurável
            "format": "json",
            "inputs": "DOCDB",  # TODO: Fazer configurável
        }

        logger.info(
            "ops_query_built",
            search_mode=self.search_mode,
            query_length=len(cql_query),
        )

        return ops_request

    def _build_textual_cql(
        self,
        field: TextualFieldQuery,
        ops_field: str,
    ) -> Optional[str]:
        """
        Constrói cláusula CQL para campo textual.

        Args:
            field: Campo textual estruturado.
            ops_field: Nome do campo na OPS API.

        Returns:
            String CQL ou None se vazio.
        """
        if not field.groups:
            return None

        group_clauses = []

        for group in field.groups:
            if not group.terms:
                continue

            # Escapar termos para CQL
            escaped_terms = [self._escape_cql_term(term) for term in group.terms]

            # Combinar com operador
            if group.operator.value == "OR":
                term_clause = f" OR ".join(escaped_terms)
            else:  # AND
                term_clause = f" AND ".join(escaped_terms)

            group_clauses.append(f"({term_clause})")

        if not group_clauses:
            return None

        # Combinar grupos
        if len(group_clauses) == 1:
            return f'{ops_field} = ({group_clauses[0]})'
        elif field.group_operator.value == "AND":
            combined = " AND ".join(group_clauses)
        else:  # OR
            combined = " OR ".join(group_clauses)

        return f'{ops_field} = ({combined})'

    def _build_simple_cql(
        self,
        field: SimpleFieldQuery,
        ops_field: str,
    ) -> Optional[str]:
        """
        Constrói cláusula CQL para campo simples.

        Args:
            field: Campo simples com lista de valores.
            ops_field: Nome do campo na OPS API.

        Returns:
            String CQL ou None se vazio.
        """
        if not field.values:
            return None

        # TODO: Definir estratégia final para campos simples (= vs exact)

        escaped_values = [self._escape_cql_term(val) for val in field.values]

        if len(escaped_values) == 1:
            return f'{ops_field} = {escaped_values[0]}'
        else:
            value_clause = " OR ".join(escaped_values)
            return f'{ops_field} = ({value_clause})'

    def _build_date_cql(self, year_from: int, year_to: int) -> Optional[str]:
        """
        Constrói cláusula CQL de intervalo de anos.

        Args:
            year_from: Ano inicial.
            year_to: Ano final.

        Returns:
            String CQL ou None se inválido.
        """
        if year_from <= 0 or year_to <= 0 or year_from > year_to:
            return None

        # TODO: Confirmar campo de data na OPS (publication.date, filing.date)
        return f"publication.date >= {year_from}0101 AND publication.date <= {year_to}1231"

    @staticmethod
    def _escape_cql_term(term: str) -> str:
        """
        Escapa termo para CQL.

        Args:
            term: Termo a escapar.

        Returns:
            Termo escapado para CQL.
        """
        # Em CQL, aspas duplas escapam caracteres especiais
        if any(char in term for char in ['"', "'", "*", "?", " "]):
            return f'"{term}"'
        return term

    def _load_field_map(self) -> dict[str, dict[str, str]]:
        """
        Carrega mapa de campos da OPS API.

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
        Retorna mapa de campos padrão OPS.

        Returns:
            Mapa padrão com campos conhecidos.
        """
        return {
            "textual": {
                "title": "title",
                "abstract": "abstract",
                "claims": "claims",
                "description": "description",
                "full_text": "text",
            },
            "simple": {
                "ipc": "ipc",
                "cpc": "cpc",
                "authors": "inventor",
                "applicant": "applicant",
                "inventor": "inventor",
                "year": "publication.date",
            },
        }
