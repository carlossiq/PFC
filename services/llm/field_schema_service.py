"""
Field schema service for managing LLM field configurations.
"""

import json
from pathlib import Path
from typing import Optional

from core.logging import get_logger
from schemas.llm import LLMOutput

logger = get_logger(__name__)


class FieldSchemaService:
    """
    Gerencia esquemas de campos para diferentes APIs e modos de busca.

    Carrega configurações de campos de arquivos JSON e fornece
    esquemas estruturados para o LLM e validação de output.
    """

    # Diretório de esquemas (relativo ao raiz do projeto)
    SCHEMA_DIR = Path(__file__).parent.parent.parent / "schemas_config"

    def __init__(self) -> None:
        """
        Inicializa o serviço de esquema de campos.

        Tenta carregar arquivo de campos geral se existir.
        """
        self.fields_cache: dict[str, dict] = {}
        self.api_maps: dict[str, dict] = {}

        # Criar diretório se não existir
        self.SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

        # Carregar campos gerais se existirem
        try:
            self._load_general_fields()
        except FileNotFoundError:
            logger.warning("General fields file not found, using defaults")

    def _load_general_fields(self) -> None:
        """
        Carrega arquivo geral de campos.

        Raises:
            FileNotFoundError: Se arquivo não existir.
        """
        fields_file = self.SCHEMA_DIR / "llm.fields.json"

        if not fields_file.exists():
            raise FileNotFoundError(f"Fields file not found: {fields_file}")

        with open(fields_file, "r") as f:
            self.fields_cache["general"] = json.load(f)

        logger.info("general_fields_loaded", file=str(fields_file))

    def get_llm_fields_for_api(
        self,
        api_name: str,
        search_mode: str,
        source_type: str,
    ) -> dict[str, dict]:
        """
        Obtém campos LLM para uma API específica.

        Carrega mapa de campos específico da API se disponível,
        caso contrário usa campos gerais.

        Args:
            api_name: Nome da API (e.g., 'uspto', 'wipo', 'scopus').
            search_mode: Modo de busca ('probe' ou 'full').
            source_type: Tipo de fonte ('patent' ou 'publication').

        Returns:
            Dicionário com esquema de campos para a API.
        """
        cache_key = f"{api_name}_{search_mode}_{source_type}"

        # Verificar cache
        if cache_key in self.fields_cache:
            return self.fields_cache[cache_key]

        # Tentar carregar arquivo específico da API
        api_file = self.SCHEMA_DIR / f"llm.fields.{api_name}.json"

        if api_file.exists():
            try:
                with open(api_file, "r") as f:
                    api_fields = json.load(f)

                # Filtrar por search_mode e source_type se estruturado assim
                if isinstance(api_fields, dict):
                    fields = api_fields.get(search_mode, {}).get(source_type, api_fields)
                else:
                    fields = api_fields

                self.fields_cache[cache_key] = fields
                logger.info(
                    "api_fields_loaded",
                    api=api_name,
                    search_mode=search_mode,
                    source_type=source_type,
                )
                return fields

            except Exception as exc:
                logger.warning(f"Failed to load API-specific fields: {exc}, using general")

        # Fallback para campos gerais
        if "general" in self.fields_cache:
            return self.fields_cache["general"]

        # Retornar schema padrão se nada estiver disponível
        return self._get_default_schema()

    def build_llm_output_contract(
        self,
        api_name: str,
        search_mode: str,
        source_type: str = "patent",
    ) -> dict:
        """
        Constrói contrato LLM output para uma API específica.

        Gera estrutura JSON que descreve quais campos devem ser
        preenchidos pelo LLM para uma dada API e modo de busca.

        Args:
            api_name: Nome da API.
            search_mode: Modo de busca ('probe' ou 'full').
            source_type: Tipo de fonte.

        Returns:
            Dicionário descrevendo o contrato esperado.
        """
        fields = self.get_llm_fields_for_api(api_name, search_mode, source_type)

        contract = {
            "api": api_name,
            "search_mode": search_mode,
            "source_type": source_type,
            "textual_fields": [
                field
                for field in fields.get("textual_fields", [])
                if field in self._get_default_textual_fields()
            ],
            "simple_fields": [
                field
                for field in fields.get("simple_fields", [])
                if field in self._get_default_simple_fields()
            ],
            "required_fields": fields.get("required_fields", []),
            "optional_fields": fields.get("optional_fields", []),
        }

        logger.info(
            "llm_output_contract_built",
            api=api_name,
            textual_count=len(contract["textual_fields"]),
            simple_count=len(contract["simple_fields"]),
        )

        return contract

    @staticmethod
    def _get_default_schema() -> dict:
        """
        Retorna esquema padrão se nenhum arquivo estiver disponível.

        Returns:
            Dicionário com campos padrão.
        """
        return {
            "textual_fields": [
                "TITLE",
                "ABSTRACT",
                "CLAIMS",
                "DESCRIPTION",
                "FULL_TEXT",
            ],
            "simple_fields": [
                "IPC",
                "CPC",
                "AUTHORS",
                "AFFILIATION",
                "APPLICANT",
                "INVENTOR",
                "FIELD_OF_STUDY",
                "KEYWORDS",
                "SOURCE_TITLE",
                "YEAR",
            ],
        }

    @staticmethod
    def _get_default_textual_fields() -> list[str]:
        """
        Retorna lista de campos textuais padrão.

        Returns:
            Lista de nomes de campos textuais.
        """
        return [
            "TITLE",
            "ABSTRACT",
            "CLAIMS",
            "DESCRIPTION",
            "FULL_TEXT",
        ]

    @staticmethod
    def _get_default_simple_fields() -> list[str]:
        """
        Retorna lista de campos simples padrão.

        Returns:
            Lista de nomes de campos simples.
        """
        return [
            "IPC",
            "CPC",
            "AUTHORS",
            "AFFILIATION",
            "APPLICANT",
            "INVENTOR",
            "FIELD_OF_STUDY",
            "KEYWORDS",
            "SOURCE_TITLE",
            "YEAR",
        ]

    def save_api_fields(self, api_name: str, fields: dict) -> None:
        """
        Salva configuração de campos para uma API.

        Args:
            api_name: Nome da API.
            fields: Dicionário com configuração de campos.
        """
        api_file = self.SCHEMA_DIR / f"llm.fields.{api_name}.json"

        try:
            with open(api_file, "w") as f:
                json.dump(fields, f, indent=2)

            logger.info("api_fields_saved", api=api_name, file=str(api_file))

        except Exception as exc:
            logger.error(f"Failed to save API fields: {exc}")
            raise

    def invalidate_cache(self, api_name: Optional[str] = None) -> None:
        """
        Invalida cache de campos.

        Args:
            api_name: Nome da API. Se None, limpa cache completo.
        """
        if api_name:
            keys_to_remove = [k for k in self.fields_cache.keys() if k.startswith(api_name)]
            for key in keys_to_remove:
                del self.fields_cache[key]
            logger.info("cache_invalidated_for_api", api=api_name)
        else:
            self.fields_cache.clear()
            logger.info("cache_invalidated_complete")
