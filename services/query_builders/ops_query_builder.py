"""
Query builder for European Patent Office (OPS) API.

Gera queries CQL (Common Query Language) a partir de LLMOutput,
usando o mapa de campos definido em ops.fields.json.
"""

import json
from pathlib import Path
from typing import Any, Optional

from core.config import settings
from core.logging import get_logger
from schemas.llm import LLMOutput, SimpleFieldQuery, TextualFieldQuery
from services.query_builders.base import BaseQueryBuilder

logger = get_logger(__name__)


class OPSQueryBuilder(BaseQueryBuilder):
    """
    Construtor de consultas para OPS (European Patent Office) API.

    Transforma saída normalizada do LLM em CQL (Common Query Language)
    usando o mapa de campos do arquivo ops.fields.json.

    Campos mapeados:
    - Textuais: title, abstract, claims, full_text
    - Simples: ipc, cpc, applicant, inventor, year

    Campos ignorados (não existem no OPS): description, authors, affiliation, etc.
    """

    # Configurações
    _MAX_QUERY_LENGTH = 10000
    _FIELD_MAP_FILE = Path(__file__).parent.parent.parent / "config" / "dict" / "ops.fields.json"

    # Mapeamento de atributos LLMOutput para tipos
    _TEXTUAL_ATTRS = ["title", "abstract", "claims", "full_text"]
    _SIMPLE_ATTRS = ["ipc", "cpc", "applicant", "inventor", "year"]

    def __init__(self, api_name: str = "ops", search_mode: str = "general") -> None:
        """
        Inicializa o construtor OPS.

        Args:
            api_name: Nome da API (padrão: "ops").
            search_mode: Modo de busca ("probe" ou "general").
        """
        super().__init__(api_name, search_mode)
        self.field_map = self._load_field_map()

    @property
    def api_identifier(self) -> str:
        """Identificador único da OPS API."""
        return "espacenet.com/ops"

    @property
    def max_query_length(self) -> int:
        """Comprimento máximo de consulta CQL."""
        return self._MAX_QUERY_LENGTH

    def build_query(
        self,
        llm_output: LLMOutput,
        year_from: int,
        year_to: int,
    ) -> dict[str, Any]:
        """
        Constrói query CQL para OPS API a partir de LLMOutput.

        O range de resultados varia conforme search_mode:
        - probe: retorna até `probe_top_k` resultados (padrão: 10)
        - general: retorna até `final_top_k` resultados (padrão: 100)

        Args:
            llm_output: Saída normalizada do LLM com campos estruturados.
            year_from: Ano inicial de publicação.
            year_to: Ano final de publicação.

        Returns:
            Dicionário com chaves:
            - query: string CQL pronta para OPS
            - range: intervalo de resultados (ex: "1-10" para probe, "1-100" para general)
            - format: formato de resposta (padrão "json")
        """
        cql_clauses = []

        # Estratégia especial: title e abstract combinados com OR
        title_cql = None
        abstract_cql = None

        title_value = getattr(llm_output, "title")
        if not title_value.is_empty():
            ops_field = self.field_map.get("TITLE")
            if ops_field:
                title_cql = self._build_textual_cql(title_value, ops_field)

        abstract_value = getattr(llm_output, "abstract")
        if not abstract_value.is_empty():
            ops_field = self.field_map.get("ABSTRACT")
            if ops_field:
                abstract_cql = self._build_textual_cql(abstract_value, ops_field)

        # Combinar title e abstract com OR
        if title_cql and abstract_cql:
            cql_clauses.append(f"({title_cql} OR {abstract_cql})")
        elif title_cql:
            cql_clauses.append(title_cql)
        elif abstract_cql:
            cql_clauses.append(abstract_cql)

        # Processar outros campos textuais com AND
        other_textual_fields = ["claims", "full_text"]
        for attr_name in other_textual_fields:
            field_value = getattr(llm_output, attr_name)
            if not field_value.is_empty():
                ops_field = self.field_map.get(attr_name.upper())
                if ops_field:
                    cql_clause = self._build_textual_cql(field_value, ops_field)
                    if cql_clause:
                        cql_clauses.append(cql_clause)

        # Processar campos simples com AND
        for attr_name in self._SIMPLE_ATTRS:
            if attr_name == "year":
                # Year é tratado especialmente com data range
                continue

            field_value = getattr(llm_output, attr_name)
            if not field_value.is_empty():
                ops_field = self.field_map.get(attr_name.upper())
                if ops_field:
                    cql_clause = self._build_simple_cql(field_value, ops_field)
                    if cql_clause:
                        cql_clauses.append(cql_clause)

        # Processar data (year)
        year_values = llm_output.year.values if llm_output.year and not llm_output.year.is_empty() else None
        date_cql = self._build_date_cql(year_from, year_to, year_values=year_values)
        if date_cql:
            cql_clauses.append(date_cql)

        # Combinar cláusulas com AND, cada uma entre parênteses
        cql_query = " AND ".join([f"({clause})" for clause in cql_clauses])

        # Log de warning se query muito longa
        if len(cql_query) > self.max_query_length:
            logger.warning(
                "ops_query_exceeds_max_length",
                length=len(cql_query),
                max=self.max_query_length,
                search_mode=self.search_mode,
            )

        # Definir range baseado em search_mode
        if self.search_mode == "probe":
            top_k = getattr(settings, "probe_top_k", 10)
        else:
            top_k = getattr(settings, "final_top_k", 100)

        range_str = f"1-{top_k}"

        logger.info(
            "ops_query_built",
            search_mode=self.search_mode,
            clauses_count=len(cql_clauses),
            query_length=len(cql_query),
            top_k=top_k,
        )

        return {
            "query": cql_query,
            "range": range_str,
            "format": "json",
        }

    def _build_textual_cql(
        self,
        field: TextualFieldQuery,
        ops_field: str,
    ) -> Optional[str]:
        """
        Constrói cláusula CQL para campo textual.

        Cada termo vira um predicado independente (field = "term") e os
        predicados são combinados com os operadores do grupo/grupo-operator.

        Exemplo com group_operator=AND e 2 grupos:
        Input:  groups=[["machine learning", "deep learning"], ["healthcare"]]
        Output: (ti = "machine learning" OR ti = "deep learning") AND (ti = "healthcare")

        Args:
            field: Estrutura TextualFieldQuery com grupos de termos.
            ops_field: Nome do campo na CQL (ex: "ti", "ab").

        Returns:
            String CQL ou None se vazio.
        """
        if not field.groups:
            return None

        group_clauses = []

        for group in field.groups:
            if not group.terms:
                continue

            # Cada termo: field = "term"
            term_clauses = [
                f'{ops_field} = {self._escape_cql_term(term)}'
                for term in group.terms
            ]

            if len(term_clauses) == 1:
                group_clauses.append(term_clauses[0])
            else:
                operator = " OR " if group.operator.value == "OR" else " AND "
                group_clauses.append(f"({operator.join(term_clauses)})")

        if not group_clauses:
            return None

        if len(group_clauses) == 1:
            return group_clauses[0]

        group_op = " AND " if field.group_operator.value == "AND" else " OR "
        return group_op.join(group_clauses)

    def _build_simple_cql(
        self,
        field: SimpleFieldQuery,
        ops_field: str,
    ) -> Optional[str]:
        """
        Constrói cláusula CQL para campo simples.

        Cada valor vira um predicado independente (field = value).

        Exemplo com múltiplos valores:
        Input:  values=["Samsung", "Apple"]
        Output: (pa = "Samsung" OR pa = "Apple")

        Valor único:
        Output: pa = Samsung

        Args:
            field: Estrutura SimpleFieldQuery com lista de valores.
            ops_field: Nome do campo na CQL (ex: "pa", "ipc").

        Returns:
            String CQL ou None se vazio.
        """
        if not field.values:
            return None

        values = field.values
        if ops_field in ("ipc", "cpc"):
            # A notação oficial de IPC/CPC tem espaço (ex: "G06N 3/00"), mas a
            # OPS devolve erro 500 (SERVER.DomainAccess) se esse espaço for
            # incluído na CQL - precisa vir compacto ("G06N3/00"). A IA gera o
            # valor no formato oficial (com espaço), então normaliza aqui.
            values = [val.replace(" ", "") for val in values]

        term_clauses = [
            f'{ops_field} = {self._escape_cql_term(val)}'
            for val in values
        ]

        if len(term_clauses) == 1:
            return term_clauses[0]

        return "(" + " OR ".join(term_clauses) + ")"

    def _build_date_cql(self, year_from: int, year_to: int, year_values: Optional[list[str]] = None) -> Optional[str]:
        """
        Constrói cláusula CQL para range de anos.

        Usa o campo "pd" (publication date) do OPS.
        Formato: pd within "YYYYMMDD YYYYMMDD" (com espaço, não vírgula)

        Se year_values for fornecido: com 1 valor, usa esse ano como início E
        fim (busca de um ano só); com 2 ou mais valores, usa o menor como
        início e o maior como fim (intervalo). Caso contrário, usa year_from
        e year_to.

        Args:
            year_from: Ano inicial (ex: 2020).
            year_to: Ano final (ex: 2024).
            year_values: Valores de ano do LLMOutput (opcional).

        Returns:
            String CQL no formato "pd within \"YYYYMMDD YYYYMMDD\"" ou None.
        """
        if year_values:
            try:
                parsed_years = [int(v) for v in year_values[:2]]
                year_from = min(parsed_years)
                year_to = max(parsed_years)
            except (ValueError, IndexError):
                # Se houver erro na conversão, fallback para os parâmetros
                pass

        if year_from <= 0 or year_to <= 0 or year_from > year_to:
            return None

        # OPS usa formato YYYYMMDD para datas com operador within
        date_from = f"{year_from}0101"
        date_to = f"{year_to}1231"

        return f'pd within "{date_from} {date_to}"'

    @staticmethod
    def _escape_cql_term(term: str) -> str:
        """
        Escapa termo para CQL.

        Se contém espaços ou caracteres especiais, envolve com aspas duplas.

        Args:
            term: Termo original.

        Returns:
            Termo escapado para CQL.
        """
        # Caracteres que requerem escaping
        special_chars = ['"', "'", "*", "?", " ", "(", ")"]
        if any(char in term for char in special_chars):
            # Escapar aspas duplas dentro do termo
            escaped = term.replace('"', '\\"')
            return f'"{escaped}"'
        return term

    def _load_field_map(self) -> dict[str, str]:
        """
        Carrega mapa de campos OPS do arquivo JSON.

        Espera estrutura: {"field_map": {"TITLE": "ti", "ABSTRACT": "ab", ...}}
        Retorna dicionário flat: {"TITLE": "ti", "ABSTRACT": "ab", ...}

        Returns:
            Dicionário mapeando nomes de campos (UPPERCASE) para siglas OPS.
        """
        if not self._FIELD_MAP_FILE.exists():
            logger.warning(
                "ops_field_map_file_not_found",
                path=str(self._FIELD_MAP_FILE),
            )
            return self._get_default_field_map()

        try:
            with open(self._FIELD_MAP_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Extrair field_map do arquivo
                field_map = config.get("field_map", {})
                if not field_map:
                    logger.warning("ops_field_map_empty_in_file")
                    return self._get_default_field_map()
                return field_map
        except json.JSONDecodeError as exc:
            logger.error(
                "ops_field_map_json_error",
                error=str(exc),
                path=str(self._FIELD_MAP_FILE),
            )
            return self._get_default_field_map()
        except Exception as exc:
            logger.error(
                "ops_field_map_load_error",
                error=str(exc),
                path=str(self._FIELD_MAP_FILE),
            )
            return self._get_default_field_map()

    @staticmethod
    def _get_default_field_map() -> dict[str, str]:
        """
        Retorna mapa de campos padrão (fallback).

        Baseado em documentação OPS CQL:
        https://www.epo.org/searching-for-patents/technical/espacenet/cql/cql-syntax.html

        Returns:
            Dicionário mapeando nomes de campos para siglas OPS.
        """
        return {
            "TITLE": "ti",
            "ABSTRACT": "ab",
            "CLAIMS": "claims",
            "FULL_TEXT": "ftxt",
            "IPC": "ipc",
            "CPC": "cpc",
            "APPLICANT": "pa",
            "INVENTOR": "in",
            "YEAR": "pd",
        }
