"""
Query builder para Lens Patent API com sintaxe query_string.

Gera queries Elasticsearch com:
- Sintaxe booleana (AND/OR/NOT) em query_string
- Support para campos textuais com grupos
- Campos simples como termos
- Paginação e sorting
- Include específico de campos
"""

from typing import Any, Optional

from core.config import settings
from core.logging import get_logger
from schemas.llm import LLMOutput, SimpleFieldQuery, TextualFieldQuery
from services.query_builders.base import BaseQueryBuilder

logger = get_logger(__name__)


class LensPatentQueryBuilder(BaseQueryBuilder):
    """
    Construtor de queries para Lens Patent API.

    Transforma LLMOutput em query Elasticsearch com sintaxe booleana.
    """

    _DEFAULT_INCLUDE = [
        "lens_id",
        "title",
        "abstract",
        "publication_date",
        "jurisdiction",
        "doc_key",
        "inventor",
        "applicant",
        "cpc_classifications",
        "ipc_classifications",
    ]

    def __init__(self, api_name: str = "lens_patent", search_mode: str = "general") -> None:
        """
        Inicializa o builder Lens Patent.

        Args:
            api_name: Nome da API.
            search_mode: 'probe' ou 'general'.
        """
        super().__init__(api_name, search_mode)

    @property
    def api_identifier(self) -> str:
        """Identificador Lens Patent."""
        return "lens.org/patent"

    @property
    def max_query_length(self) -> int:
        """Comprimento máximo de query para Lens Patent API."""
        return 50000

    def build_query(
        self,
        llm_output: LLMOutput,
        year_from: int = 0,
        year_to: int = 0,
    ) -> dict[str, Any]:
        """
        Constrói query para Lens Patent API.

        Args:
            llm_output: Saída normalizada do LLM.
            year_from: Ano inicial (0 = não usar).
            year_to: Ano final (0 = não usar).

        Returns:
            Query payload para Lens API.
        """
        payload = {
            "query": {"bool": {"must": []}},
        }

        # Construir query_string com sintaxe booleana
        query_parts = self._build_query_string_parts(llm_output)

        if query_parts:
            query_string = " AND ".join(query_parts)
            payload["query"]["bool"]["must"].append(
                {"query_string": {"query": query_string}}
            )

        # Adicionar range de anos se válido
        if year_from > 0 and year_to > 0 and year_from <= year_to:
            payload["query"]["bool"]["must"].append(
                {
                    "range": {
                        "date_published": {
                            "gte": f"{year_from}-01-01",
                            "lte": f"{year_to}-12-31",
                        }
                    }
                }
            )

        # Adicionar tamanho baseado em search_mode
        if self.search_mode == "probe":
            payload["size"] = getattr(settings, "probe_top_k", 10)
        else:
            payload["size"] = getattr(settings, "final_top_k", 100)

        payload["from"] = 0

        logger.info(
            "lens_patent_query_built",
            search_mode=self.search_mode,
            size=payload["size"],
            has_must_clauses=len(payload["query"]["bool"]["must"]),
        )

        return payload

    def _build_query_string_parts(self, llm_output: LLMOutput) -> list[str]:
        """
        Constrói partes da query_string com sintaxe booleana.

        Args:
            llm_output: Saída do LLM.

        Returns:
            Lista de partes que serão combinadas com AND.
        """
        parts = []

        # Processar campos textuais (usar nomes da Lens Patent API)
        textual_fields = [
            ("title", "title"),
            ("abstract", "abstract"),
            ("claims", "claim"),  # Lens Patent usa "claim" (singular)
            ("description", "description"),
            ("full_text", "full_text"),
        ]

        for field_attr, field_name in textual_fields:
            field_value = getattr(llm_output, field_attr)

            if not field_value.is_empty():
                field_query = self._build_textual_field_query(field_value, field_name)
                if field_query:
                    parts.append(field_query)

        # Processar campos simples (usar nomes da Lens Patent API)
        simple_fields = [
            ("ipc", "class_ipcr.symbol"),
            ("cpc", "class_cpc.symbol"),
            ("applicant", "applicant.name"),
            ("inventor", "inventor.name"),
        ]

        for field_attr, field_name in simple_fields:
            field_value = getattr(llm_output, field_attr)

            if not field_value.is_empty():
                field_query = self._build_simple_field_query(field_value, field_name)
                if field_query:
                    parts.append(field_query)

        return parts

    def _build_textual_field_query(
        self,
        field: TextualFieldQuery,
        field_name: str,
    ) -> Optional[str]:
        """
        Constrói parte de query_string para campo textual.

        Formato: field:(term1 OR term2) AND (term3 OR term4)

        Args:
            field: Campo textual com grupos.
            field_name: Nome do campo.

        Returns:
            String com sintaxe booleana ou None.
        """
        if not field.groups:
            return None

        group_parts = []

        for group in field.groups:
            if not group.terms:
                continue

            # Construir grupo com OR
            terms_str = " OR ".join(f'"{term}"' if " " in term else term for term in group.terms)

            if len(group.terms) > 1:
                group_part = f"({terms_str})"
            else:
                group_part = terms_str

            group_parts.append(group_part)

        if not group_parts:
            return None

        # Combinar grupos com AND (ou OR baseado em group_operator)
        if field.group_operator.value == "AND":
            return f"{field_name}:({' AND '.join(group_parts)})"
        else:  # OR
            return f"{field_name}:({' OR '.join(group_parts)})"

    def _build_simple_field_query(
        self,
        field: SimpleFieldQuery,
        field_name: str,
    ) -> Optional[str]:
        """
        Constrói parte de query_string para campo simples.

        Formato: field:(value1 OR value2)

        Args:
            field: Campo simples com valores.
            field_name: Nome do campo.

        Returns:
            String com sintaxe booleana ou None.
        """
        if not field.values:
            return None

        # Combinar valores com OR
        values_str = " OR ".join(f'"{v}"' if " " in v else v for v in field.values)

        if len(field.values) > 1:
            return f"{field_name}:({values_str})"
        else:
            return f"{field_name}:{values_str}"
