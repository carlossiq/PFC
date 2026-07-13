"""
Query builder for Scopus API.

Gera queries Scopus a partir de LLMOutput usando sintaxe de campos específica:
- TITLE() para título
- ABS() para abstract
- AUTH() para autores
- KEY() para keywords
- etc.
"""

import json
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

from core.config import settings
from core.logging import get_logger
from schemas.llm import LLMOutput, SimpleFieldQuery, TextualFieldQuery
from services.query_builders.base import BaseQueryBuilder
from services.query_builders.constants.scopus_subject_areas import resolve_asjc_code

logger = get_logger(__name__)


class ScopusQueryBuilder(BaseQueryBuilder):
    """
    Construtor de consultas para Scopus API.

    Transforma saída normalizada do LLM em parâmetros de requisição
    específicos da Scopus API para publicações acadêmicas e citações.
    """

    # Configurações da API
    _MAX_QUERY_LENGTH = 10000
    _FIELD_MAP_FILE = Path(__file__).parent.parent.parent / "config" / "dict" / "scopus_fields.json"

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

        Estratégia:
        - Title e Abstract: combinados com OR (buscar em um ou outro)
        - Outros campos: combinados com AND

        Args:
            llm_output: Saída normalizada do LLM.
            year_from: Ano inicial.
            year_to: Ano final.

        Returns:
            Dicionário com parâmetros para Scopus API.
        """
        # Construir partes da query
        query_parts = []

        # Estratégia especial: title e abstract combinados com OR
        title_query = None
        abstract_query = None

        title_value = getattr(llm_output, "title")
        if not title_value.is_empty():
            scopus_field = self.field_map.get("textual", {}).get("title")
            if scopus_field:
                title_query = self._build_textual_query(title_value, scopus_field)

        abstract_value = getattr(llm_output, "abstract")
        if not abstract_value.is_empty():
            scopus_field = self.field_map.get("textual", {}).get("abstract")
            if scopus_field:
                abstract_query = self._build_textual_query(abstract_value, scopus_field)

        # Combinar title e abstract com OR
        if title_query and abstract_query:
            query_parts.append(f"({title_query} OR {abstract_query})")
        elif title_query:
            query_parts.append(title_query)
        elif abstract_query:
            query_parts.append(abstract_query)

        # Processar outros campos textuais com AND
        for field_name in ["description", "full_text"]:
            field_value = getattr(llm_output, field_name)
            if not field_value.is_empty():
                scopus_field = self.field_map.get("textual", {}).get(field_name)
                if scopus_field:
                    query_part = self._build_textual_query(field_value, scopus_field)
                    if query_part:
                        query_parts.append(query_part)

        # Processar campos simples com AND
        for field_name in ["authors", "affiliation", "keywords", "source_title"]:
            field_value = getattr(llm_output, field_name)
            if not field_value.is_empty():
                scopus_field = self.field_map.get("simple", {}).get(field_name)
                if scopus_field:
                    query_part = self._build_simple_query(field_value, scopus_field)
                    if query_part:
                        query_parts.append(query_part)

        # field_of_study é tratado à parte: SUBJAREA não aceita texto livre
        # entre aspas como os outros campos simples (AUTH/AFFIL/KEY/SRCTITLE)
        # - exige um dos 27 códigos ASJC de 4 letras, sem aspas. Ver
        # services/query_builders/constants/scopus_subject_areas.py.
        field_of_study_value = getattr(llm_output, "field_of_study")
        if not field_of_study_value.is_empty():
            query_part = self._build_subject_area_query(field_of_study_value)
            if query_part:
                query_parts.append(query_part)

        # Adicionar intervalo de anos
        year_values = llm_output.year.values if llm_output.year and not llm_output.year.is_empty() else None
        date_query = self._build_date_query(year_from, year_to, year_values=year_values)
        if date_query:
            query_parts.append(date_query)

        # Restringir a artigos de revista (exclui review, conference paper,
        # editorial, carta, nota, errata etc - ruído que não interessa numa
        # busca de literatura técnica). Fixo, não vem do LLM.
        query_parts.append("DOCTYPE(ar)")

        # Combinar partes com AND - cada parte entre parênteses, mesmo que já
        # pareça "simples": qualquer parte que internamente use OR sem
        # parênteses próprios (ex: SUBJAREA(A) OR SUBJAREA(B), ou KEY("x") OR
        # KEY("y")) ficaria ambíguo com o AND externo sem isso. Mesmo padrão
        # já usado no OPS builder (" AND ".join([f"({c})" ...])).
        scopus_query = " AND ".join(f"({part})" for part in query_parts)

        # Validar comprimento
        if len(scopus_query) > self.max_query_length:
            logger.warning(
                "scopus_query_exceeds_max_length",
                length=len(scopus_query),
                max=self.max_query_length,
                search_mode=self.search_mode,
            )

        # Definir count baseado em search_mode
        if self.search_mode == "probe":
            count = getattr(settings, "probe_top_k", 10)
        else:
            count = getattr(settings, "final_top_k", 100)

        # Construir parâmetros da requisição
        # view=STANDARD (não COMPLETE): COMPLETE exige entitlement de Text
        # Mining/institucional que a API key não tem, retornando 401 em toda
        # busca - e mesmo com COMPLETE essa chave não retorna abstract
        # (dc:description) de qualquer forma, então não há perda real aqui.
        params = {
            "query": scopus_query,
            "count": count,
            "start": 0,
            "sort": "citedby-count",
            "view": "STANDARD",
        }

        logger.info(
            "scopus_query_built",
            search_mode=self.search_mode,
            query_length=len(scopus_query),
            count=count,
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

            # Scopus sintaxe: TITLE() ou ABSTRACT() etc. Termos SEMPRE entre
            # aspas: sem aspas, a Scopus trata frases de múltiplas palavras
            # como busca de proximidade implícita, e OR'ar duas ou mais
            # dessas frases sem aspas quebra o parser e zera os resultados
            # (confirmado testando direto na API - ver notes/pendencias.md).
            escaped_terms = [f'"{self._escape_scopus_term(term)}"' for term in group.terms]

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

        parts = [f'{scopus_field}("{v}")' for v in escaped_values]
        return " OR ".join(parts)

    def _build_subject_area_query(self, field: SimpleFieldQuery) -> Optional[str]:
        """
        Constrói a cláusula SUBJAREA a partir do field_of_study gerado pela
        LLM. Diferente de _build_simple_query, SUBJAREA não aceita texto
        livre entre aspas - exige um código ASJC de 4 letras sem aspas (ex:
        SUBJAREA(COMP)). Valores que não mapeiam pra nenhum código conhecido
        são descartados em vez de gerarem uma cláusula que nunca casa com
        nada (e derruba a busca inteira, já que é combinada com AND).

        Args:
            field: Campo field_of_study com a lista de valores da LLM.

        Returns:
            String de query (`SUBJAREA(A) OR SUBJAREA(B)`) ou None se
            nenhum valor mapear pra um código válido.
        """
        if not field.values:
            return None

        codes: list[str] = []
        for value in field.values:
            code = resolve_asjc_code(value)
            if code and code not in codes:
                codes.append(code)
            elif not code:
                logger.info("scopus_subject_area_unmapped", value=value)

        if not codes:
            return None

        return " OR ".join(f"SUBJAREA({code})" for code in codes)

    def _build_date_query(
        self, year_from: int, year_to: int, year_values: Optional[list[str]] = None
    ) -> Optional[str]:
        """
        Constrói cláusula de intervalo de anos Scopus.

        Se year_values for fornecido: com 1 valor, usa esse ano como início E
        fim (busca de um ano só); com 2 ou mais valores, usa o menor como
        início e o maior como fim (intervalo). Caso contrário, usa year_from
        e year_to (mesma lógica do OPSQueryBuilder._build_date_cql).

        Args:
            year_from: Ano inicial (fallback).
            year_to: Ano final (fallback).
            year_values: Valores de ano do LLMOutput (opcional).

        Returns:
            String de query ou None se inválido.
        """
        if year_values:
            try:
                parsed_years = [int(v) for v in year_values[:2]]
                year_from = min(parsed_years)
                year_to = max(parsed_years)
            except (ValueError, IndexError):
                pass

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
                data = json.load(f)
                return data.get("field_map", data)
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
