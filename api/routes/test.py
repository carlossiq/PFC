"""
Test routes for development and debugging.

Exposes internals of each pipeline stage for detailed inspection.
"""

import json
from typing import Any, Optional

from fastapi import APIRouter, Request

from core.config import settings
from core.logging import get_logger
from schemas.intake import InputIntake
from schemas.llm import LLMOutput
from schemas.response import SuccessResponse
from services.llm import (
    LLMOutputNormalizer,
    LLMServiceFactory,
    FieldSchemaService,
)
from services.nlp import (
    EmbeddingService,
    KeywordService,
    RelevanceService,
)
from services.prompt import PromptLoader
from services.query_builders import QueryBuilderFactory

logger = get_logger(__name__)

router = APIRouter(prefix="/test", tags=["test"])


@router.post("/llm-debug", response_model=SuccessResponse[dict[str, Any]])
async def test_llm_debug(
    request: Request,
    intake: InputIntake,
    search_mode: str = "probe",
) -> SuccessResponse[dict[str, Any]]:
    """
    Debug completo: mostra exatamente o que a LLM recebe e retorna.

    Exibe:
    1. Entrada do usuário (intake)
    2. Campos disponíveis na API
    3. Prompt COMPLETO enviado para LLM (base + enriquecimento)
    4. Resposta bruta da LLM
    5. Resposta normalizada

    Args:
        request: Objeto da requisição.
        intake: Entrada do usuário.
        search_mode: 'probe' ou 'general'.

    Returns:
        Response com todos os detalhes do processamento.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        # 1. ENTRADA DO USUÁRIO
        user_input = {
            "theme": intake.theme,
            "description": intake.description,
            "area_of_study": intake.area_of_study,
            "keywords": intake.keywords,
        }

        # 2. CARREGAR PROMPT BASE
        if search_mode == "probe":
            base_prompt = PromptLoader.load_probe_system_prompt()
            api_name = getattr(settings, "probe_api", "lens_patent")
        else:
            base_prompt = PromptLoader.load_general_system_prompt()
            api_name = "final_search"

        # 3. OBTER CAMPOS DISPONÍVEIS COM TIPOS
        field_service = FieldSchemaService()
        if search_mode == "probe":
            fields_with_types = field_service.get_fields_with_types_for_probe()
            available_fields = field_service.get_fields_for_probe()
        else:
            fields_with_types = field_service.get_fields_with_types_for_final()
            available_fields = field_service.get_fields_for_final()

        # 4. CRIAR ENRIQUECIMENTO COM NOVO FORMATO
        # Separar campos por tipo
        textual_fields = [f for f, t in fields_with_types.items() if t == "textual"]
        simple_fields = [f for f, t in fields_with_types.items() if t == "simple"]

        field_types_section = "\n".join(
            [f"- {field}: {fields_with_types[field]}" for field in sorted(fields_with_types.keys())]
        )

        # Construir seção de entrada do usuário
        user_context = f"""
## USER INPUT

Theme: {intake.theme}
"""
        if intake.description:
            user_context += f"Description: {intake.description}\n"

        if intake.area_of_study:
            user_context += f"Area of Study: {intake.area_of_study}\n"

        if intake.keywords:
            user_context += f"Keywords: {', '.join(intake.keywords)}\n"

        fields_section = f"""{user_context}

## DYNAMIC FIELD SPECIFICATION FOR THIS RUN

API: {api_name.upper()}

Return ONLY the fields listed below.
Do not include any other fields.
Use uppercase field names exactly as listed.
Do not rename fields.
Do not change the structure of any field.

### FIELD TYPES FOR THIS RUN

{field_types_section}


### REQUIRED OUTPUT FORMAT

For textual fields, always return:
{{
  "group_operator": "AND",
  "groups": [
    {{
      "operator": "OR",
      "terms": ["term1", "term2"]
    }}
  ]
}}

If empty:
{{
  "group_operator": "AND",
  "groups": []
}}

For simple fields, always return:
["value1", "value2"]

If empty:
[]


### STRICT RULES

- Return ONLY the fields listed above
- Do not include YEAR
- Do not return {{"values": [...]}} — this is invalid
- Do not return flat term lists for textual fields
- Do not omit fields even if empty
- Always respect the declared field type
"""

        complete_prompt = base_prompt + fields_section

        # 5. PROCESSAR COM LLM
        llm_service = LLMServiceFactory.get_instance()
        llm_output = await llm_service.process_intake(
            intake=intake,
            system_prompt=complete_prompt,
        )

        # 6. NORMALIZAR, filtrando apenas campos habilitados para este modo de busca
        normalized = LLMOutputNormalizer.normalize(llm_output, enabled_fields=available_fields)

        return SuccessResponse(
            success=True,
            data={
                "run_id": run_id,
                "pipeline": {
                    "search_mode": search_mode,
                    "api": api_name,
                    "llm_provider": llm_service.provider_name,
                },
                "step_1_user_input": user_input,
                "step_2_available_fields": {
                    "list": available_fields,
                    "count": len(available_fields),
                    "with_types": fields_with_types,
                    "textual_count": len(textual_fields),
                    "simple_count": len(simple_fields),
                },
                "step_3_prompt_sent_to_llm": {
                    "base_prompt_length": len(base_prompt),
                    "field_specification_length": len(fields_section),
                    "total_prompt_length": len(complete_prompt),
                    "complete_prompt": complete_prompt,  # PROMPT COMPLETO AQUI
                },
                "step_4_raw_llm_response": {
                    "title": {
                        "group_operator": llm_output.title.group_operator,
                        "groups_count": len(llm_output.title.groups) if llm_output.title.groups else 0,
                        "first_group": (
                            {
                                "operator": llm_output.title.groups[0].operator,
                                "terms": llm_output.title.groups[0].terms,
                            }
                            if llm_output.title.groups
                            else None
                        ),
                    },
                    "abstract": {
                        "group_operator": llm_output.abstract.group_operator,
                        "groups_count": len(llm_output.abstract.groups) if llm_output.abstract.groups else 0,
                    },
                    "claims": {
                        "groups_count": len(llm_output.claims.groups) if llm_output.claims.groups else 0,
                    },
                    "ipc": {
                        "values_count": len(llm_output.ipc.values) if llm_output.ipc.values else 0,
                        "values": llm_output.ipc.values[:5] if llm_output.ipc.values else [],
                    },
                    "cpc": {
                        "values_count": len(llm_output.cpc.values) if llm_output.cpc.values else 0,
                        "values": llm_output.cpc.values[:5] if llm_output.cpc.values else [],
                    },
                    "keywords": {
                        "values_count": len(llm_output.keywords.values) if llm_output.keywords.values else 0,
                        "values": llm_output.keywords.values[:5] if llm_output.keywords.values else [],
                    },
                    "full_json": llm_output.model_dump(exclude_none=True),
                },
                "step_5_normalized_output": {
                    "active_fields": normalized.get_active_fields(),
                    "total_active_fields": sum(normalized.get_active_fields().values()),
                    "title_groups": len(normalized.title.groups) if normalized.title.groups else 0,
                    "abstract_groups": len(normalized.abstract.groups) if normalized.abstract.groups else 0,
                    "ipc_sample": normalized.ipc.values[:3] if normalized.ipc.values else [],
                    "keywords_sample": normalized.keywords.values[:3] if normalized.keywords.values else [],
                },
            },
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(f"test_llm_debug_error: {exc}", run_id=run_id, exc_info=True)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            run_id=run_id,
        )


@router.post("/llm-enriched", response_model=SuccessResponse[dict[str, Any]])
async def test_llm_enriched(
    request: Request,
    intake: InputIntake,
    search_mode: str = "probe",
) -> SuccessResponse[dict[str, Any]]:
    """
    Testa LLM com enriquecimento dinâmico de campos.

    Simula o comportamento real do pipeline:
    1. Carrega prompt base (probe ou general)
    2. Enriquece prompt com campos disponíveis da API
    3. Chama LLM com prompt enriquecido
    4. Retorna saída bruta e normalizada

    Args:
        request: Objeto da requisição.
        intake: Entrada do usuário (theme, description, area_of_study, keywords).
        search_mode: 'probe' ou 'general' (padrão: 'probe').

    Returns:
        Response com:
        - Prompt enriquecido completo
        - Campos disponíveis para a API
        - Saída bruta do LLM
        - Saída normalizada
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        # Carregar prompt base
        if search_mode == "probe":
            system_prompt = PromptLoader.load_probe_system_prompt()
            api_name = getattr(settings, "probe_api", "lens_patent")
        else:
            system_prompt = PromptLoader.load_general_system_prompt()
            api_name = "final_search"

        # Obter campos disponíveis
        field_service = FieldSchemaService()
        if search_mode == "probe":
            available_fields = field_service.get_fields_for_probe()
        else:
            available_fields = field_service.get_fields_for_final()

        # Enriquecer prompt com campos dinâmicos
        fields_section = f"""

## DYNAMIC FIELD SPECIFICATION FOR THIS {search_mode.upper()} SEARCH

**API: {api_name.upper()}**

Return ONLY these fields in your JSON response. Do not include any other fields.

### Available Fields:
{', '.join(available_fields) if available_fields else 'NONE'}

### RULES:
- For textual fields (TITLE, ABSTRACT, CLAIMS, DESCRIPTION, FULL_TEXT, KEYWORDS):
  {{"group_operator":"AND", "groups":[{{"operator":"OR","terms":["term1","term2"]}}]}}
- For simple fields (IPC, CPC, AUTHORS, AFFILIATION, APPLICANT, INVENTOR, FIELD_OF_STUDY, SOURCE_TITLE, YEAR):
  ["value1", "value2"]
"""

        enriched_prompt = system_prompt + fields_section

        # Processar com LLM
        llm_service = LLMServiceFactory.get_instance()
        llm_output = await llm_service.process_intake(
            intake=intake,
            system_prompt=enriched_prompt,
        )

        # Normalizar, filtrando apenas campos habilitados para este modo de busca
        normalized = LLMOutputNormalizer.normalize(llm_output, enabled_fields=available_fields)

        return SuccessResponse(
            success=True,
            data={
                "run_id": run_id,
                "search_mode": search_mode,
                "api": api_name,
                "provider": llm_service.provider_name,
                "available_fields": available_fields,
                "available_fields_count": len(available_fields),
                "enriched_prompt_length": len(enriched_prompt),
                "intake": {
                    "theme": intake.theme,
                    "description": intake.description,
                    "area_of_study": intake.area_of_study,
                    "keywords": intake.keywords,
                },
                "raw_llm_output": {
                    "title": {
                        "has_groups": bool(llm_output.title.groups),
                        "group_count": len(llm_output.title.groups) if llm_output.title.groups else 0,
                    },
                    "abstract": {
                        "has_groups": bool(llm_output.abstract.groups),
                        "group_count": len(llm_output.abstract.groups) if llm_output.abstract.groups else 0,
                    },
                    "claims": {
                        "has_groups": bool(llm_output.claims.groups),
                        "group_count": len(llm_output.claims.groups) if llm_output.claims.groups else 0,
                    },
                    "ipc": {
                        "has_values": bool(llm_output.ipc.values),
                        "value_count": len(llm_output.ipc.values) if llm_output.ipc.values else 0,
                    },
                    "cpc": {
                        "has_values": bool(llm_output.cpc.values),
                        "value_count": len(llm_output.cpc.values) if llm_output.cpc.values else 0,
                    },
                },
                "normalized_output": {
                    "active_fields": normalized.get_active_fields(),
                    "active_fields_count": sum(normalized.get_active_fields().values()),
                    "title_groups": len(normalized.title.groups) if normalized.title.groups else 0,
                    "abstract_groups": len(normalized.abstract.groups) if normalized.abstract.groups else 0,
                    "claims_groups": len(normalized.claims.groups) if normalized.claims.groups else 0,
                    "ipc_values": normalized.ipc.values[:3] if normalized.ipc.values else [],
                    "cpc_values": normalized.cpc.values[:3] if normalized.cpc.values else [],
                },
                "raw_json_output": llm_output.model_dump(exclude_none=True),
            },
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(f"test_llm_enriched_error: {exc}", run_id=run_id, exc_info=True)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            run_id=run_id,
        )


@router.post("/query-builder", response_model=SuccessResponse[dict[str, Any]])
async def test_query_builder(
    request: Request,
    intake: InputIntake,
    api: str = "lens_patent",
    search_mode: str = "probe",
) -> SuccessResponse[dict[str, Any]]:
    """
    Debug: mostra a query completa que será enviada para API.

    Args:
        request: Objeto da requisição.
        intake: Entrada do usuário.
        api: API a usar (lens_patent, lens_scholarly, ops, scopus).
        search_mode: 'probe' ou 'general'.

    Returns:
        Response com query e detalhes.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        # Obter campos disponíveis e criar LLM output mock
        field_service = FieldSchemaService()
        if search_mode == "probe":
            available_fields = field_service.get_fields_for_probe()
        else:
            available_fields = field_service.get_fields_for_final()

        # Obter prompt apropriado
        if search_mode == "probe":
            system_prompt = PromptLoader.load_probe_system_prompt()
        else:
            system_prompt = PromptLoader.load_general_system_prompt()

        # Enriquecer prompt com campos disponíveis
        fields_with_types = (
            field_service.get_fields_with_types_for_probe()
            if search_mode == "probe"
            else field_service.get_fields_with_types_for_final()
        )

        field_types_section = "\n".join(
            [f"- {field}: {fields_with_types[field]}" for field in sorted(fields_with_types.keys())]
        )

        user_context = f"""
## USER INPUT

Theme: {intake.theme}
"""
        if intake.description:
            user_context += f"Description: {intake.description}\n"

        if intake.area_of_study:
            user_context += f"Area of Study: {intake.area_of_study}\n"

        if intake.keywords:
            user_context += f"Keywords: {', '.join(intake.keywords)}\n"

        fields_section = f"""{user_context}

## DYNAMIC FIELD SPECIFICATION FOR THIS RUN

Return ONLY the fields listed below with their specified types.

### FIELD TYPES FOR THIS RUN

{field_types_section}
"""

        enriched_prompt = system_prompt + fields_section

        # Chamar LLM real (não mock)
        llm_service = LLMServiceFactory.get_instance()
        llm_output = await llm_service.process_intake(intake, enriched_prompt)

        # Normalizar
        llm_output = LLMOutputNormalizer.normalize(
            llm_output,
            enabled_fields=available_fields,
        )

        # Construir query
        builder = QueryBuilderFactory.create(api, search_mode=search_mode)
        year_from = getattr(settings, "search_year_from", 0)
        year_to = getattr(settings, "search_year_to", 0)

        query = builder.build_query(llm_output, year_from, year_to)

        return SuccessResponse(
            success=True,
            data={
                "run_id": run_id,
                "intake": {
                    "theme": intake.theme,
                    "description": intake.description,
                    "area_of_study": intake.area_of_study,
                    "keywords": intake.keywords,
                },
                "config": {
                    "api": api,
                    "search_mode": search_mode,
                    "year_from": year_from,
                    "year_to": year_to,
                    "probe_top_k": getattr(settings, "probe_top_k", 10),
                    "final_top_k": getattr(settings, "final_top_k", 100),
                },
                "llm_output": {
                    "active_fields": llm_output.get_active_fields(),
                    "has_queries": llm_output.has_any_queries(),
                    "title_groups": len(llm_output.title.groups) if llm_output.title.groups else 0,
                    "abstract_groups": len(llm_output.abstract.groups) if llm_output.abstract.groups else 0,
                    "ipc_values": llm_output.ipc.values[:3] if llm_output.ipc.values else [],
                },
                "query": query,
                "query_json_pretty": json.dumps(query, indent=2),
            },
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(f"test_query_builder_error: {exc}", run_id=run_id, exc_info=True)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            run_id=run_id,
        )


@router.post("/nlp", response_model=SuccessResponse[dict[str, Any]])
async def test_nlp(
    request: Request,
    text: str,
    top_k_keywords: int = 10,
) -> SuccessResponse[dict[str, Any]]:
    """
    Testa NLP services (keyword extraction + embeddings).

    Expõe: keywords extraídos, embedding dimensionality.

    Args:
        request: Objeto da requisição.
        text: Texto para processar.
        top_k_keywords: Número de keywords.

    Returns:
        Response com resultados NLP.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        # Extrair keywords
        keyword_service = KeywordService()
        keywords = keyword_service.extract_keywords(text, top_k=top_k_keywords)

        # Gerar embedding
        embedding_service = EmbeddingService()
        embedding = embedding_service.embed_text(text)

        return SuccessResponse(
            success=True,
            data={
                "run_id": run_id,
                "text_length": len(text),
                "keywords_extracted": len(keywords),
                "top_keywords": keywords[:5],
                "embedding_dimension": len(embedding) if embedding is not None else None,
                "embedding_available": embedding is not None,
            },
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(f"test_nlp_error: {exc}", run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            run_id=run_id,
        )


@router.post("/query-builder", response_model=SuccessResponse[dict[str, Any]])
async def test_query_builder(
    request: Request,
    api_name: str,
    intake: InputIntake,
    search_mode: str = "general",
) -> SuccessResponse[dict[str, Any]]:
    """
    Testa query builder para uma API.

    Expõe: API usada, modo de busca, query gerada.

    Args:
        request: Objeto da requisição.
        api_name: Nome da API (lens_patent, ops, scopus, etc).
        intake: Entrada do usuário.
        search_mode: 'probe' ou 'general'.

    Returns:
        Response com query gerada.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        # Gerar estratégia LLM
        llm_service = LLMServiceFactory.get_instance()
        system_prompt = PromptLoader.load_general_system_prompt()
        llm_output = await llm_service.process_intake(intake, system_prompt)
        normalized = LLMOutputNormalizer.normalize(llm_output)

        # Construir query
        builder = QueryBuilderFactory.create(api_name, search_mode=search_mode)
        query = builder.build_query(
            llm_output=normalized,
            year_from=2015,
            year_to=2024,
        )

        return SuccessResponse(
            success=True,
            data={
                "run_id": run_id,
                "api_name": api_name,
                "search_mode": search_mode,
                "builder_class": builder.__class__.__name__,
                "query_type": type(query).__name__,
                "max_query_length": builder.max_query_length,
                "query_length": len(str(query)),
            },
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(f"test_query_builder_error: {exc}", run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            run_id=run_id,
        )


@router.post("/field-schema", response_model=SuccessResponse[dict[str, Any]])
async def test_field_schema(
    request: Request,
    api_name: str,
    search_mode: str = "general",
) -> SuccessResponse[dict[str, Any]]:
    """
    Testa field schema service.

    Expõe: campos textuais, campos simples, campos obrigatórios.

    Args:
        request: Objeto da requisição.
        api_name: Nome da API.
        search_mode: Modo de busca.

    Returns:
        Response com schema de campos.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        field_service = FieldSchemaService()
        contract = field_service.build_llm_output_contract(
            api_name=api_name,
            search_mode=search_mode,
        )

        return SuccessResponse(
            success=True,
            data={
                "run_id": run_id,
                "api": api_name,
                "search_mode": search_mode,
                "textual_fields": len(contract.get("textual_fields", [])),
                "simple_fields": len(contract.get("simple_fields", [])),
                "required_fields": contract.get("required_fields", []),
            },
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(f"test_field_schema_error: {exc}", run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            run_id=run_id,
        )
