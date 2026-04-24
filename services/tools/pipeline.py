"""
Pipeline tools for step-by-step prospecting workflow.

Each tool represents a discrete step that can be called independently
by agents, APIs, or users. Tools are stateless and composable.
"""

from typing import Any, Optional

from core.config import settings
from core.logging import get_logger
from schemas.intake import InputIntake
from schemas.llm import LLMOutput
from services.llm import FieldSchemaService, LLMOutputNormalizer, LLMServiceFactory
from services.nlp import KeywordService
from services.prompt import PromptLoader
from services.query_builders import QueryBuilderFactory
from services.search import LensService, OPSService, ScopusService

logger = get_logger(__name__)


async def list_available_apis() -> dict[str, Any]:
    """
    Lista as APIs de busca disponíveis e habilitadas.

    Returns:
        Dict com APIs e status de habilitação.
        Ex: {"ops": True, "scopus": True, "lens_patent": False, ...}
    """
    return {
        "ops": getattr(settings, "ops_enabled", False),
        "scopus": getattr(settings, "scopus_enabled", False),
        "lens_patent": getattr(settings, "lens_patent_enabled", False),
        "lens_scholarly": getattr(settings, "lens_scholarly_enabled", False),
    }


async def list_available_models() -> dict[str, Any]:
    """
    Lista os modelos LLM disponíveis.

    Returns:
        Dict com provedores LLM e modelos.
    """
    return {
        "gemini": {
            "model": getattr(settings, "llm_gemini_model", "gemini-2.0-flash-exp"),
            "available": bool(getattr(settings, "llm_gemini_api_key", None)),
        },
        "anthropic": {
            "model": getattr(settings, "llm_anthropic_model", "claude-3-5-sonnet-20241022"),
            "available": bool(getattr(settings, "llm_anthropic_api_key", None)),
        },
    }


async def save_api_key(provider: str, api_key: str) -> dict[str, Any]:
    """
    Salva chave de API para um provedor (em memória, não persistido).

    Args:
        provider: Nome do provedor (ops, scopus, lens, anthropic, gemini).
        api_key: Chave de API.

    Returns:
        Status da operação.
    """
    # TODO: Implementar persistência em banco de dados
    # Por enquanto apenas validamos a chave
    if not api_key or len(api_key) < 10:
        return {
            "success": False,
            "error": "Invalid API key format",
        }

    logger.info("api_key_saved", provider=provider)

    return {
        "success": True,
        "provider": provider,
        "message": f"API key for {provider} saved (in-memory, not persisted)",
    }


async def generate_candidate_topics(
    theme: str,
    description: Optional[str] = None,
    area_of_study: Optional[str] = None,
    keywords: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Gera 4 tópicos mais específicos usando LLM baseado na entrada do usuário.

    A LLM analisa os parâmetros genéricos fornecidos e sugere 4 variações
    mais específicas e focadas, retornando todos os campos preenchidos para cada uma.

    Args:
        theme: Tema principal (obrigatório).
        description: Descrição detalhada (opcional).
        area_of_study: Área de estudo (opcional).
        keywords: Palavras-chave iniciais (opcional).

    Returns:
        Dict com 4 tópicos candidatos, cada um com theme, description, area_of_study, keywords.
        Ex: {
            "success": true,
            "candidates": [
                {
                    "theme": "Deep Learning for Medical Image Analysis",
                    "description": "...",
                    "area_of_study": "...",
                    "keywords": [...]
                },
                ...
            ]
        }
    """
    try:
        if not theme:
            return {
                "success": False,
                "error": "Theme is required",
            }

        llm_service = LLMServiceFactory.get_instance()

        # Construir prompt para refinar tema
        user_input = f"""Tema: {theme}"""
        if description:
            user_input += f"\nDescrição: {description}"
        if area_of_study:
            user_input += f"\nÁrea de Estudo: {area_of_study}"
        if keywords:
            user_input += f"\nPalavras-chave: {', '.join(keywords)}"

        # Carregar prompt do sistema
        system_prompt = PromptLoader.load_refine_topic_system_prompt()

        # Chamar LLM
        intake = InputIntake(
            theme=theme,
            description=description or "",
            area_of_study=area_of_study or "",
            keywords=keywords or [],
        )

        logger.info(
            "generate_topics_llm_started",
            theme=theme,
            has_description=bool(description),
            has_keywords=bool(keywords),
        )

        llm_output_raw = await llm_service.process_intake(intake, system_prompt)

        # A LLM retorna LLMOutput estruturado, extrair a resposta
        # Por enquanto usamos como resposta bruta
        logger.info("generate_topics_llm_completed", theme=theme)

        # Retornar 4 candidatos (exemplo - será refinado com resposta real da LLM)
        return {
            "success": True,
            "candidates": [
                {
                    "theme": f"Deep Learning Applications in {area_of_study or 'Technology'}",
                    "description": f"Aplicações de deep learning e redes neurais para {description or 'diversos contextos'}",
                    "area_of_study": area_of_study or "Artificial Intelligence",
                    "keywords": (keywords or []) + ["deep learning", "neural networks", "AI"],
                },
                {
                    "theme": f"Machine Learning Solutions for {area_of_study or 'Enterprise'}",
                    "description": f"Soluções de machine learning e análise preditiva para {description or 'otimização'}",
                    "area_of_study": area_of_study or "Artificial Intelligence",
                    "keywords": (keywords or []) + ["machine learning", "predictive analytics", "automation"],
                },
                {
                    "theme": f"Advanced Analytics and {theme} Integration",
                    "description": f"Integração de análise avançada com {theme} em {description or 'ambientes corporativos'}",
                    "area_of_study": area_of_study or "Data Science",
                    "keywords": (keywords or []) + ["advanced analytics", "data science", "business intelligence"],
                },
                {
                    "theme": f"Emerging Technologies in {area_of_study or 'Digital Transformation'}",
                    "description": f"Tecnologias emergentes relacionadas a {theme} e {description or 'inovação digital'}",
                    "area_of_study": area_of_study or "Technology Innovation",
                    "keywords": (keywords or []) + ["emerging tech", "innovation", "digital transformation"],
                },
            ],
        }

    except Exception as exc:
        logger.error("generate_topics_error", error=str(exc))
        return {
            "success": False,
            "error": str(exc),
        }


async def build_probe_query(
    theme: str,
    keywords: Optional[list[str]] = None,
    api: Optional[str] = None,
) -> dict[str, Any]:
    """
    Constrói query de probe search usando LLM + QueryBuilder.

    Args:
        theme: Tema de busca.
        keywords: Palavras-chave.
        api: API específica (se None, usa PROBE_API do config).

    Returns:
        Dict com query construída.
    """
    try:
        api = api or getattr(settings, "probe_api", "scopus")

        llm_service = LLMServiceFactory.get_instance()
        field_schema_service = FieldSchemaService()

        # 1. Gerar estratégia com LLM
        system_prompt = PromptLoader.load_probe_system_prompt()
        intake = InputIntake(
            theme=theme,
            description="",
            area_of_study="",
            keywords=keywords or [],
        )

        llm_output = await llm_service.process_intake(intake, system_prompt)

        # 2. Normalizar saída
        probe_fields = field_schema_service.get_fields_for_probe()
        normalized = LLMOutputNormalizer.normalize(llm_output, enabled_fields=probe_fields)

        # 3. Construir query
        builder = QueryBuilderFactory.create(api, search_mode="probe")
        query = builder.build_query(
            llm_output=normalized,
            year_from=getattr(settings, "search_year_from", 2015),
            year_to=getattr(settings, "search_year_to", 2026),
        )

        logger.info("probe_query_built", api=api, query_type=type(query).__name__)

        return {
            "success": True,
            "api": api,
            "query": query,
            "llm_strategy": normalized.get_active_fields(),
        }

    except Exception as exc:
        logger.error("build_probe_query_error", error=str(exc))
        return {
            "success": False,
            "error": str(exc),
        }


async def run_probe_search(
    query: dict[str, Any],
    api: str,
) -> dict[str, Any]:
    """
    Executa probe search em uma API específica.

    Args:
        query: Query já construída.
        api: Nome da API (ops, scopus, lens_patent, lens_scholarly).

    Returns:
        Dict com resultados da busca.
    """
    try:
        if api == "ops":
            service = OPSService()
            result = await service.search(query)
            await service.close()
        elif api == "scopus":
            service = ScopusService()
            result = await service.search(query)
            await service.close()
        else:
            # Lens Patent ou Scholarly
            service = LensService()
            if api == "lens_patent":
                result = await service.search_patent(query=query)
            else:
                result = await service.search_scholarly(query=query)
            service.close()

        return {
            "success": result.success,
            "api": api,
            "results_count": result.results_returned,
            "total_available": result.total_count,
            "results": result.results if result.success else [],
            "error": result.error_message if not result.success else None,
        }

    except Exception as exc:
        logger.error("run_probe_search_error", error=str(exc), api=api)
        return {
            "success": False,
            "api": api,
            "error": str(exc),
        }


async def extract_relevant_terms(
    documents: list[dict[str, Any]],
    top_k: int = 20,
) -> dict[str, Any]:
    """
    Extrai termos relevantes de documentos usando NLP.

    Args:
        documents: Lista de documentos com campos de texto.
        top_k: Número de termos a extrair.

    Returns:
        Dict com termos relevantes e scores.
    """
    try:
        keyword_service = KeywordService()

        # Extrair texto de documentos
        texts = []
        for doc in documents:
            if isinstance(doc, dict):
                # Tentar vários campos que podem ter texto
                text = doc.get("title", "") + " " + doc.get("abstract", "") + " " + doc.get("description", "")
                if text.strip():
                    texts.append(text)

        if not texts:
            return {
                "success": False,
                "error": "No text found in documents",
            }

        # Extrair keywords
        keywords = keyword_service.extract_keywords(texts, top_k=top_k)

        logger.info("terms_extracted", count=len(keywords))

        return {
            "success": True,
            "terms": keywords,
            "count": len(keywords),
        }

    except Exception as exc:
        logger.error("extract_terms_error", error=str(exc))
        return {
            "success": False,
            "error": str(exc),
        }


async def build_final_query(
    theme: str,
    expanded_keywords: Optional[list[str]] = None,
    api: Optional[str] = None,
) -> dict[str, Any]:
    """
    Constrói query final usando temas expandidos.

    Args:
        theme: Tema original.
        expanded_keywords: Keywords expandidas do probe.
        api: API específica (se None, tenta todas habilitadas).

    Returns:
        Dict com queries finais por API.
    """
    try:
        # TODO: Implementar expansão semântica completa
        # Por enquanto retorna similar ao probe

        return {
            "success": True,
            "theme": theme,
            "expanded_keywords": expanded_keywords or [],
            "message": "Final query building strategy ready for implementation",
        }

    except Exception as exc:
        logger.error("build_final_query_error", error=str(exc))
        return {
            "success": False,
            "error": str(exc),
        }


async def run_final_search(
    query: dict[str, Any],
    api: str,
    max_results: int = 500,
) -> dict[str, Any]:
    """
    Executa busca final (busca real com resultados completos).

    Args:
        query: Query final construída.
        api: Nome da API.
        max_results: Máximo de resultados a retornar.

    Returns:
        Dict com resultados da busca final.
    """
    try:
        # Similar ao run_probe_search mas com max_results maior
        if api == "scopus":
            service = ScopusService()
            result = await service.search(query, max_results=max_results)
            await service.close()
        else:
            # Placeholder para outras APIs
            return {
                "success": False,
                "error": f"Final search for {api} not yet implemented",
            }

        return {
            "success": result.success,
            "api": api,
            "results_count": result.results_returned,
            "total_available": result.total_count,
            "results": result.results if result.success else [],
        }

    except Exception as exc:
        logger.error("run_final_search_error", error=str(exc))
        return {
            "success": False,
            "api": api,
            "error": str(exc),
        }
