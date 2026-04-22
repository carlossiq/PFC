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
from services.search import LensService

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


@router.post("/probe-search", response_model=SuccessResponse[dict[str, Any]])
async def test_probe_search(
    request: Request,
    intake: InputIntake,
) -> SuccessResponse[dict[str, Any]]:
    """
    Rota de teste para visualizar busca probe COMPLETA com API real.

    Executa pipeline completo de probe:
    1. Geração de estratégia via LLM
    2. Construção de query Lens Patent
    3. Busca na API Lens Patent (10 documentos)
    4. Extração de dados dos documentos

    Args:
        request: Objeto da requisição.
        intake: Entrada do usuário (theme, objective, keywords).

    Returns:
        Response com LLM strategy, query gerada e primeiros documentos encontrados.

    Raises:
        HTTPException: Se alguma etapa falhar.
    """
    import uuid

    run_id = str(uuid.uuid4())

    try:
        logger.info(
            "probe_search_test_started",
            run_id=run_id,
            theme=intake.theme,
        )

        # Etapa 1: Gerar estratégia via LLM
        llm_service = LLMServiceFactory.get_instance()
        field_schema_service = FieldSchemaService()

        # Carregar prompt para probe
        system_prompt = PromptLoader.load_probe_system_prompt()

        # Obter campos dinâmicos para probe
        probe_fields = field_schema_service.get_fields_for_probe()
        probe_api = getattr(settings, "probe_api", "lens_patent")

        logger.info(
            "probe_search_llm_started",
            run_id=run_id,
            probe_api=probe_api,
        )

        # Processar com LLM
        llm_output = await llm_service.process_intake(
            intake=intake,
            system_prompt=system_prompt,
        )

        # Normalizar saída
        normalized_output = LLMOutputNormalizer.normalize(
            llm_output,
            enabled_fields=probe_fields,
        )

        logger.info(
            "probe_search_llm_completed",
            run_id=run_id,
            active_fields=sum(normalized_output.get_active_fields().values()),
        )

        # Etapa 2: Construir query
        builder = QueryBuilderFactory.create(probe_api, search_mode="probe")
        logger.info("probe_search_builder_created", run_id=run_id, builder_type=type(builder).__name__, api=probe_api)

        query = builder.build_query(
            llm_output=normalized_output,
            year_from=getattr(settings, "search_year_from", 2015),
            year_to=getattr(settings, "search_year_to", 2026),
        )

        logger.info("probe_search_query_built_debug", run_id=run_id, query_type=type(query).__name__, query_keys=list(query.keys()) if isinstance(query, dict) else "not_dict")

        logger.info(
            "probe_search_query_built",
            run_id=run_id,
            query_size=query.get("size") or query.get("range") if isinstance(query, dict) else "unknown",
        )

        # Etapa 3: Executar busca na API configurada (Lens ou OPS)
        logger.info("probe_search_api_started", run_id=run_id, api=probe_api)

        if probe_api == "ops":
            from services.search import OPSService
            ops_service = OPSService()
            search_result = await ops_service.search(query, run_id=run_id)
            await ops_service.close()
        else:
            # Lens Patent é o padrão
            lens_service = LensService()
            search_result = await lens_service.search_patent(
                query=query,
                run_id=run_id,
            )
            lens_service.close()

        logger.info(
            "probe_search_api_completed",
            run_id=run_id,
            success=search_result.success,
            documents_found=search_result.results_returned,
            total_available=search_result.total_count,
        )

        # Etapa 4: Extrair dados dos documentos
        documents_sample = []
        if search_result.success and search_result.results:
            for i, doc in enumerate(search_result.results):
                try:
                    logger.info(f"Processing document {i}, type: {type(doc)}, is_dict: {isinstance(doc, dict)}")

                    # Tratamento diferenciado por API
                    if probe_api == "ops":
                        # OPS retorna estrutura JSON-converted-from-XML
                        doc_data = {
                            "api": "ops",
                            "doc_type": str(type(doc)),
                            "title": "OPS document (raw JSON structure)",
                            "raw": doc if isinstance(doc, dict) else str(doc)[:200],
                        }
                    elif probe_api == "scopus":
                        # Scopus retorna estrutura Elsevier XML
                        if isinstance(doc, dict):
                            doc_data = {
                                "api": "scopus",
                                "eid": doc.get("eid"),
                                "title": doc.get("dc:title"),
                                "authors": doc.get("dc:creator"),
                                "publication_date": doc.get("prism:publicationDate"),
                                "source": doc.get("prism:publicationName"),
                                "raw": str(doc)[:300],
                            }
                        else:
                            doc_data = {
                                "api": "scopus",
                                "doc_type": str(type(doc)),
                                "raw": str(doc)[:200],
                            }
                    elif probe_api in ["lens_patent", "lens_scholarly"]:
                        # Lens (Patent ou Scholarly) tem estrutura conhecida
                        if isinstance(doc, dict):
                            doc_data = {
                                "lens_id": doc.get("lens_id"),
                                "title": _extract_title_from_doc(doc) if probe_api == "lens_patent" else doc.get("title"),
                                "abstract": doc.get("abstract"),
                                "publication_date": doc.get("date_published") if probe_api == "lens_patent" else doc.get("year_published"),
                                "source": doc.get("source") or doc.get("source_title"),
                                "applicant": _extract_applicant_from_doc(doc) if probe_api == "lens_patent" else None,
                                "inventor": _extract_inventor_from_doc(doc) if probe_api == "lens_patent" else None,
                                "ipc_classifications": _extract_ipc_from_doc(doc) if probe_api == "lens_patent" else None,
                                "cpc_classifications": _extract_cpc_from_doc(doc) if probe_api == "lens_patent" else None,
                            }
                        else:
                            doc_data = {
                                "api": probe_api,
                                "doc_type": str(type(doc)),
                                "raw": str(doc)[:200],
                            }
                    else:
                        # Fallback para tipo desconhecido
                        doc_data = {
                            "api": probe_api,
                            "error": f"Unknown document type: {type(doc)}",
                            "raw": str(doc)[:200]
                        }

                    documents_sample.append(doc_data)
                except Exception as doc_error:
                    logger.error(f"Error processing document {i}: {doc_error}", exc_info=True)
                    documents_sample.append({
                        "error": str(doc_error),
                        "doc_type": str(type(doc))
                    })

        # Preparar resposta
        response_data = {
            "run_id": run_id,
            "intake": {
                "theme": intake.theme,
                "description": intake.description,
                "area_of_study": intake.area_of_study,
                "keywords": intake.keywords,
            },
            "llm_strategy": {
                "active_fields": normalized_output.get_active_fields(),
                "field_count": sum(normalized_output.get_active_fields().values()),
                "title": _safe_model_dump(normalized_output.title),
                "abstract": _safe_model_dump(normalized_output.abstract),
                "claims": _safe_model_dump(normalized_output.claims),
                "ipc": _safe_model_dump(normalized_output.ipc),
                "cpc": _safe_model_dump(normalized_output.cpc),
            },
            "query_generated": {
                "api": probe_api,
                "search_mode": "probe",
                "size": (
                    query.get("range") if probe_api == "ops"
                    else query.get("size") if probe_api in ["lens_patent", "lens_scholarly"]
                    else query.get("count") if probe_api == "scopus"
                    else None
                ),
                "from": (
                    "1" if probe_api == "ops"
                    else query.get("from") if probe_api in ["lens_patent", "lens_scholarly"]
                    else query.get("start") if probe_api == "scopus"
                    else None
                ),
                "has_query_bool": (
                    False if probe_api == "ops"
                    else (isinstance(query.get("query"), dict) and "bool" in query.get("query", {})) if probe_api in ["lens_patent", "lens_scholarly"]
                    else False if probe_api == "scopus"
                    else False
                ),
                "cql_query": query.get("query") if probe_api == "ops" else None,
                "scopus_query": query.get("query") if probe_api == "scopus" else None,
                "must_clauses_count": (
                    0 if probe_api == "ops"
                    else len(query.get("query", {}).get("bool", {}).get("must", [])) if isinstance(query.get("query"), dict) and "bool" in query.get("query", {})
                    else 0
                ),
                "full_query": query,
            },
            "api_results": {
                "api": probe_api,
                "success": search_result.success,
                "total_available": search_result.total_count,
                "results_returned": search_result.results_returned,
                "duration_seconds": round(search_result.duration_seconds, 2),
                "error": search_result.error_message if not search_result.success else None,
            },
            "documents": {
                "total_retrieved": len(documents_sample),
                "samples": documents_sample,
            },
        }

        logger.info(
            "probe_search_test_completed",
            run_id=run_id,
            success=True,
            documents_retrieved=len(documents_sample),
        )

        return SuccessResponse(
            success=True,
            data=response_data,
            message=f"Probe search completed: {len(documents_sample)} documents found",
            run_id=run_id,
        )

    except Exception as exc:
        import traceback
        logger.error(
            "probe_search_test_error",
            error=str(exc),
            error_type=type(exc).__name__,
            run_id=run_id,
            exc_info=True,
            traceback=traceback.format_exc(),
        )

        return SuccessResponse(
            success=False,
            data={"error": str(exc), "error_type": type(exc).__name__, "traceback": traceback.format_exc()},
            message=f"Probe search test failed: {str(exc)}",
            run_id=run_id,
        )


def _safe_model_dump(obj: Any) -> dict | None:
    """Converte modelo para dict de forma segura."""
    if hasattr(obj, "is_empty") and obj.is_empty():
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return None


def _extract_title_from_doc(doc: dict) -> str:
    """Extrai título do documento Lens Patent."""
    biblio = doc.get("biblio", {})
    invention_titles = biblio.get("invention_title", [])
    if invention_titles and isinstance(invention_titles, list):
        return invention_titles[0].get("text", "N/A")
    return "N/A"


def _extract_applicant_from_doc(doc: dict) -> str:
    """Extrai requerente do documento Lens Patent."""
    biblio = doc.get("biblio", {})
    parties = biblio.get("parties", {})
    applicants = parties.get("applicants", [])
    if applicants and isinstance(applicants, list):
        return applicants[0].get("extracted_name", {}).get("value", "N/A")
    return "N/A"


def _extract_inventor_from_doc(doc: dict) -> str:
    """Extrai inventor do documento Lens Patent."""
    biblio = doc.get("biblio", {})
    parties = biblio.get("parties", {})
    inventors = parties.get("inventors", [])
    if inventors and isinstance(inventors, list):
        return inventors[0].get("extracted_name", {}).get("value", "N/A")
    return "N/A"


def _extract_ipc_from_doc(doc: dict) -> list[str]:
    """Extrai classificações IPC do documento."""
    classifications = doc.get("classifications_ipcr", {})
    ipc_list = classifications.get("classifications", [])
    if ipc_list:
        return [c.get("symbol", "") for c in ipc_list[:3]]
    return []


def _extract_cpc_from_doc(doc: dict) -> list[str]:
    """Extrai classificações CPC do documento."""
    classifications = doc.get("classifications_cpc", {})
    cpc_list = classifications.get("classifications", [])
    if cpc_list:
        return [c.get("symbol", "") for c in cpc_list[:3]]
    return []
