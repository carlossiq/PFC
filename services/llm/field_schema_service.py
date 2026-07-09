"""
Field schema service for managing LLM field configurations.

Gerencia esquemas de campos dinâmicos baseados em:
- Campos globais (disponíveis em todas as APIs)
- Campos específicos de API (apenas em certas APIs)
"""

import json
from pathlib import Path

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class FieldSchemaService:
    """
    Gerencia esquemas de campos para diferentes APIs e modos de busca.

    Carrega configurações de campos de llm.fields.json e fornece
    listas de campos disponíveis com base em:
    - PROBE_API configurada (busca inicial)
    - PROBE_API_EXT (busca secundária inicial, opcional)
    - Todas as APIs habilitadas (busca final/exploratória)

    A classificação de campos (textual vs simple) é responsabilidade
    do QueryBuilder, não deste serviço. Aqui apenas retornamos a lista
    de campos disponíveis que a LLM deve preencher.
    """

    # Diretório de esquemas
    SCHEMA_DIR = Path(__file__).parent.parent.parent / "config" / "dict"

    def __init__(self) -> None:
        """
        Inicializa o serviço e carrega esquema de campos.
        """
        self.schema: dict = {}
        self.cache: dict[str, dict] = {}

        # Criar diretório se não existir
        self.SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

        # Carregar esquema de campos
        self._load_schema()

    def _load_schema(self) -> None:
        """
        Carrega llm.fields.json com estrutura:
        {
            "global_fields": {...},
            "api_specific_fields": {...}
        }
        """
        schema_file = self.SCHEMA_DIR / "llm.fields.json"

        if not schema_file.exists():
            logger.warning(f"Schema file not found: {schema_file}, using defaults")
            self.schema = self._get_default_schema()
            return

        try:
            with open(schema_file, "r") as f:
                self.schema = json.load(f)
            logger.info("schema_loaded", file=str(schema_file))
        except Exception as exc:
            logger.error(f"Failed to load schema: {exc}, using defaults")
            self.schema = self._get_default_schema()

    def get_fields_for_probe(self) -> list[str]:
        """
        Retorna lista de campos para busca PROBE.

        Busca probe retorna APENAS campos GLOBAIS (TITLE, ABSTRACT)
        que são universais e não dependem de API específica.

        Isso garante que a busca probe seja agnóstica à API
        e foque em termos amplos, não em metadados específicos.

        Returns:
            Lista de nomes de campos globais para a busca probe.
            Ex: ["TITLE", "ABSTRACT"]
        """
        cache_key = "probe"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Retornar APENAS campos globais para busca probe
        global_fields = self.schema.get("global_fields", {})
        fields = sorted(list(global_fields.keys()))

        self.cache[cache_key] = fields

        logger.info(
            "probe_fields_resolved",
            field_count=len(fields),
            fields=fields,
        )

        return fields

    def get_fields_with_types_for_probe(self) -> dict[str, str]:
        """
        Retorna dicionário {field_name: field_type} para busca PROBE.

        Retorna APENAS campos globais (TITLE, ABSTRACT) com seus tipos.

        Returns:
            Dict com campos globais e seus tipos. Ex: {"TITLE": "textual", "ABSTRACT": "textual"}
        """
        cache_key = "probe_with_types"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Retornar APENAS campos globais com seus tipos
        global_fields = self.schema.get("global_fields", {})
        fields_with_types = {}

        for field_name, field_config in global_fields.items():
            field_type = field_config.get("field_type", "textual")
            fields_with_types[field_name] = field_type

        # Ordenar por nome
        fields_with_types = dict(sorted(fields_with_types.items()))

        self.cache[cache_key] = fields_with_types

        return fields_with_types

    def get_fields_for_final(self) -> list[str]:
        """
        Retorna lista de campos para busca final/exploratória.

        Inclui campos de TODAS as APIs habilitadas:
        - lens_patent (se lens_patent_enabled)
        - lens_scholarly (se lens_scholarly_enabled)
        - ops (se ops_enabled)
        - scopus (se scopus_enabled)

        Returns:
            Lista de nomes de campos disponíveis para a busca final.
            Ex: ["TITLE", "ABSTRACT", "KEYWORDS", "IPC", "CPC", "AUTHORS", ...]
        """
        cache_key = "final"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Determinar quais APIs estão habilitadas
        enabled_apis = set()

        # Verificar flags individuais (novos) com fallback para lens_enabled (antigo)
        if getattr(settings, "lens_patent_enabled", None) is not None:
            if settings.lens_patent_enabled:
                enabled_apis.add("lens_patent")
        elif getattr(settings, "lens_enabled", True):
            enabled_apis.add("lens_patent")

        if getattr(settings, "lens_scholarly_enabled", None) is not None:
            if settings.lens_scholarly_enabled:
                enabled_apis.add("lens_scholarly")
        elif getattr(settings, "lens_enabled", True):
            enabled_apis.add("lens_scholarly")

        if getattr(settings, "ops_enabled", True):
            enabled_apis.add("ops")

        if getattr(settings, "scopus_enabled", True):
            enabled_apis.add("scopus")

        fields = self._filter_fields_by_apis(enabled_apis)
        self.cache[cache_key] = fields

        logger.info(
            "final_fields_resolved",
            enabled_apis=list(enabled_apis),
            field_count=len(fields),
        )

        return fields

    def get_fields_with_types_for_final(self) -> dict[str, str]:
        """
        Retorna dicionário {field_name: field_type} para busca FINAL.

        Returns:
            Dict com campos e seus tipos. Ex: {"TITLE": "textual", "IPC": "simple"}
        """
        cache_key = "final_with_types"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Determinar quais APIs estão habilitadas (mesmo que get_fields_for_final)
        enabled_apis = set()

        if getattr(settings, "lens_patent_enabled", None) is not None:
            if settings.lens_patent_enabled:
                enabled_apis.add("lens_patent")
        elif getattr(settings, "lens_enabled", True):
            enabled_apis.add("lens_patent")

        if getattr(settings, "lens_scholarly_enabled", None) is not None:
            if settings.lens_scholarly_enabled:
                enabled_apis.add("lens_scholarly")
        elif getattr(settings, "lens_enabled", True):
            enabled_apis.add("lens_scholarly")

        if getattr(settings, "ops_enabled", True):
            enabled_apis.add("ops")

        if getattr(settings, "scopus_enabled", True):
            enabled_apis.add("scopus")

        fields_with_types = self._filter_fields_by_apis_with_types(enabled_apis)
        self.cache[cache_key] = fields_with_types

        return fields_with_types

    def _filter_fields_by_apis(self, api_names: set[str]) -> list[str]:
        """
        Filtra campos que contêm alguma das APIs especificadas.

        Retorna a lista de nomes de campos disponíveis para as APIs fornecidas.
        A classificação em textual vs simple é responsabilidade do QueryBuilder.

        Args:
            api_names: Conjunto de nomes de API (ex: {"lens_patent", "lens_scholarly"})

        Returns:
            Lista de nomes de campos disponíveis. Ex: ["TITLE", "ABSTRACT", "IPC", ...]
        """
        fields = set()

        # Processar global_fields
        global_fields = self.schema.get("global_fields", {})
        for field_name, field_config in global_fields.items():
            field_apis = set(field_config.get("api", []))
            if field_apis & api_names:  # Interseção: campo está em alguma API selecionada
                fields.add(field_name)

        # Processar api_specific_fields
        api_specific = self.schema.get("api_specific_fields", {})
        for field_name, field_config in api_specific.items():
            field_apis = set(field_config.get("api", []))
            if field_apis & api_names:  # Interseção
                fields.add(field_name)

        return sorted(list(fields))

    def _filter_fields_by_apis_with_types(self, api_names: set[str]) -> dict[str, str]:
        """
        Filtra campos com seus tipos (textual/simple).

        Retorna dicionário {field_name: field_type} para as APIs fornecidas.

        Args:
            api_names: Conjunto de nomes de API (ex: {"lens_patent", "lens_scholarly"})

        Returns:
            Dict como {"TITLE": "textual", "IPC": "simple", ...}
        """
        fields_dict = {}

        # Processar global_fields
        global_fields = self.schema.get("global_fields", {})
        for field_name, field_config in global_fields.items():
            field_apis = set(field_config.get("api", []))
            if field_apis & api_names:
                field_type = field_config.get("field_type", "textual")
                fields_dict[field_name] = field_type

        # Processar api_specific_fields
        api_specific = self.schema.get("api_specific_fields", {})
        for field_name, field_config in api_specific.items():
            field_apis = set(field_config.get("api", []))
            if field_apis & api_names:
                field_type = field_config.get("field_type", "simple")
                fields_dict[field_name] = field_type

        # Retornar ordenado por nome
        return dict(sorted(fields_dict.items()))

    def build_llm_output_contract(
        self,
        api_name: str,
        search_mode: str,
        source_type: str = "patent",
    ) -> dict:
        """
        Constrói contrato LLM output para uma API específica.

        DEPRECADO: Use get_fields_for_probe() ou get_fields_for_final() ao invés.

        Args:
            api_name: Nome da API.
            search_mode: Modo de busca ('probe' ou 'general').
            source_type: Tipo de fonte (deprecated).

        Returns:
            Dicionário com campos esperados.
        """
        if search_mode == "probe":
            fields = self.get_fields_for_probe()
        else:
            fields = self.get_fields_for_final()

        return {
            "api": api_name,
            "search_mode": search_mode,
            "source_type": source_type,
            "textual_fields": fields["textual_fields"],
            "simple_fields": fields["simple_fields"],
        }

    @staticmethod
    def _get_default_schema() -> dict:
        """
        Retorna esquema padrão.

        Returns:
            Dicionário com campos padrão.
        """
        return {
            "global_fields": {
                "TITLE": {
                    "description": "Busca no título",
                    "api": ["lens_patent", "lens_scholarly", "ops", "scopus"],
                },
                "ABSTRACT": {
                    "description": "Busca no resumo",
                    "api": ["lens_patent", "lens_scholarly", "ops", "scopus"],
                },
                "YEAR": {
                    "description": "Filtro temporal",
                    "api": ["lens_patent", "lens_scholarly", "ops", "scopus"],
                },
            },
            "api_specific_fields": {
                "KEYWORDS": {
                    "description": "Palavras-chave",
                    "api": ["lens_scholarly", "scopus"],
                },
                "AUTHORS": {"description": "Autores", "api": ["lens_scholarly", "scopus"]},
                "AFFILIATION": {
                    "description": "Afiliação",
                    "api": ["lens_scholarly", "scopus"],
                },
                "SOURCE_TITLE": {
                    "description": "Nome da fonte",
                    "api": ["lens_scholarly", "scopus"],
                },
                "FIELD_OF_STUDY": {
                    "description": "Área de estudo",
                    "api": ["lens_scholarly", "scopus"],
                },
                "APPLICANT": {"description": "Depositante", "api": ["lens_patent", "ops"]},
                "INVENTOR": {"description": "Inventor", "api": ["lens_patent", "ops"]},
                "CLAIMS": {
                    "description": "Reivindicações",
                    "api": ["lens_patent", "ops"],
                },
                "DESCRIPTION": {
                    "description": "Descrição",
                    "api": ["lens_patent"],
                },
                "FULL_TEXT": {
                    "description": "Texto completo",
                    "api": ["lens_patent", "lens_scholarly", "ops"],
                },
                "IPC": {"description": "Classificação IPC", "api": ["lens_patent", "ops"]},
                "CPC": {"description": "Classificação CPC", "api": ["lens_patent", "ops"]},
            },
        }

    def invalidate_cache(self) -> None:
        """
        Invalida cache de campos.
        """
        self.cache.clear()
