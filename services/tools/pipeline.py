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


async def check_ops_token_status() -> dict[str, Any]:
    """
    Verifica o status do token OAuth2 do OPS.

    Retorna informações sobre o token atual: se está válido, quando expira, etc.
    Se expirado, tenta renovar automaticamente.

    Returns:
        Dict com status do token:
        - is_valid: Token está válido e não expirado
        - is_expired: Token expirou
        - access_token: Token (primeiros 20 chars por segurança)
        - created_at: Quando foi criado
        - expiration_time: Quando vai expirar
        - time_until_expiration_seconds: Segundos até expiração
        - token_type: Bearer ou similar
    """
    try:
        from services.search.ops_service import OPSService

        ops_service = OPSService()

        # Verificar/renovar token
        await ops_service._ensure_valid_token()

        if not ops_service.token:
            logger.warning("ops_token_check_no_token")
            return {
                "success": False,
                "error": "Failed to obtain OPS token - check consumer_key and consumer_secret",
            }

        token_dict = ops_service.token.to_dict()
        is_expired = ops_service.token.is_expired()

        # Calcular tempo até expiração
        from datetime import datetime

        now = datetime.utcnow()
        expiration = ops_service.token.expiration_time
        time_until_expiration = (expiration - now).total_seconds()

        logger.info(
            "ops_token_status_checked",
            is_expired=is_expired,
            time_until_expiration=time_until_expiration,
        )

        return {
            "success": True,
            "is_valid": not is_expired,
            "is_expired": is_expired,
            "access_token": token_dict["access_token"][:20] + "...",
            "created_at": token_dict["created_at"],
            "expiration_time": token_dict["expiration_time"],
            "time_until_expiration_seconds": int(time_until_expiration),
            "expires_in_seconds": ops_service.token.expires_in,
        }

    except ValueError as exc:
        logger.error("ops_token_check_credentials_error", error=str(exc))
        return {
            "success": False,
            "error": f"OPS credentials error: {str(exc)}",
            "hint": "Check OPS_CONSUMER_KEY and OPS_CONSUMER_SECRET in .env",
        }
    except Exception as exc:
        logger.error("ops_token_check_error", error=str(exc), exc_info=True)
        return {
            "success": False,
            "error": str(exc),
        }


async def analyze_query_complexity(query_string: str) -> dict[str, Any]:
    """
    Analisa complexidade de uma query booleana (CQL, SQL, etc).

    Util para debugar por que queries estao falhando no OPS.
    Score alto (>70) geralmente causa HTTP 404 no OPS.

    Args:
        query_string: Query a analisar (CQL, SQL, ou expressao booleana).

    Returns:
        Dict com metricas de complexidade:
        - complexity_score: Score 0-100 (quanto maior, mais complexa)
        - complexity_level: Simples, Moderado, Complexo, Muito Complexo
        - operator_counts: Contagem de AND, OR, NOT
        - nesting_depth: Profundidade de parenteses
        - term_count: Numero de termos
        - warnings: Lista de problemas identificados
        - recommendations: Sugestoes para simplificar
    """
    try:
        from services.tools.query_complexity import QueryComplexityAnalyzer

        analyzer = QueryComplexityAnalyzer(query_string)
        analysis = analyzer.analyze()

        logger.info(
            "query_complexity_analyzed",
            score=analysis["complexity_score"],
            level=analysis["complexity_level"],
        )

        return {
            "success": True,
            "complexity_score": analysis["complexity_score"],
            "complexity_level": analysis["complexity_level"],
            "operator_counts": analysis["operator_counts"],
            "nesting_depth": analysis["nesting_depth"],
            "term_count": analysis["term_count"],
            "warnings": analysis["warnings"],
            "recommendations": analysis["recommendations"],
        }

    except Exception as exc:
        logger.error("query_complexity_error", error=str(exc))
        return {
            "success": False,
            "error": str(exc),
        }


async def get_current_llm_provider() -> dict[str, Any]:
    """
    Retorna o provider e model LLM atual em uso.

    Returns:
        Dict com provider (nome), model (versão), e available (boolean).
        Ex: {
            "provider": "gemini",
            "model": "gemini-2.0-flash-exp",
            "available": true
        }
    """
    try:
        llm_service = LLMServiceFactory.get_instance()
        provider_name = llm_service.provider_name
        is_available = llm_service.is_available()

        # Obter o modelo da instância de serviço
        model = getattr(llm_service, "model", None)

        logger.info(
            "current_llm_provider_retrieved",
            provider=provider_name,
            available=is_available,
        )

        return {
            "success": True,
            "provider": provider_name,
            "model": model,
            "available": is_available,
        }

    except Exception as exc:
        logger.error("get_current_llm_provider_error", error=str(exc))
        return {
            "success": False,
            "error": str(exc),
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


async def generate_candidate_topics(intake: InputIntake) -> dict[str, Any]:
    """
    Gera 4 tópicos mais específicos usando LLM baseado na entrada do usuário.

    A LLM analisa os parâmetros fornecidos e sugere 4 variações
    mais específicas e focadas, retornando APENAS os campos que o usuário forneceu.

    Regras:
    - area_of_study: Se fornecido pelo usuário, preservado em todos os candidatos
    - keywords: Se fornecidas pelo usuário, preservadas em todos os candidatos
    - theme: Sempre gerado com 4 variações específicas e diferentes
    - description: Gerado apenas se o usuário forneceu description como entrada
    - Campos não fornecidos são omitidos da resposta

    Args:
        intake: InputIntake com theme (obrigatório), description, area_of_study, keywords.

    Returns:
        Dict com 4 tópicos candidatos. Cada candidato contém:
        - theme: Sempre presente (refinado)
        - description: Presente apenas se foi entrada do usuário
        - area_of_study: Presente apenas se foi entrada (preservado como-é)
        - keywords: Presente apenas se foi entrada (preservadas como-são)
        - user_input: Campos originais fornecidos pelo usuário
    """
    try:
        llm_service = LLMServiceFactory.get_instance()

        # Determinar quais campos o usuário forneceu
        user_provided_fields = {
            "theme": True,  # Sempre obrigatório
            "description": intake.description is not None,
            "area_of_study": intake.area_of_study is not None,
            "keywords": intake.keywords is not None,
        }

        # Construir entrada do usuário com instruções sobre campos fornecidos
        user_input = f"Tema: {intake.theme}"
        if intake.description:
            user_input += f"\nDescrição: {intake.description}"
        if intake.area_of_study:
            user_input += f"\nÁrea de Estudo: {intake.area_of_study}"
        if intake.keywords:
            user_input += f"\nPalavras-chave: {', '.join(intake.keywords)}"

        # Adicionar informação sobre campos fornecidos para a LLM
        user_input += f"\n\nCampos fornecidos pelo usuário (retorne APENAS estes):\n"
        user_input += f"- theme: SIM (sempre refine em 4 variações)\n"
        if user_provided_fields["description"]:
            user_input += f"- description: SIM (gere descrições para cada variação)\n"
        if user_provided_fields["area_of_study"]:
            user_input += f"- area_of_study: SIM (PRESERVE exatamente: '{intake.area_of_study}')\n"
        if user_provided_fields["keywords"]:
            user_input += f"- keywords: SIM (PRESERVE exatamente: {intake.keywords})\n"

        # Carregar prompt do sistema
        system_prompt = PromptLoader.load_refine_topic_system_prompt()

        logger.info(
            "generate_topics_llm_started",
            theme=intake.theme,
            user_provided_fields=user_provided_fields,
        )

        # Chamar LLM para obter JSON bruto com candidatos
        raw_json = await llm_service.call_raw_json(system_prompt, user_input)

        logger.info(
            "generate_topics_llm_completed",
            theme=intake.theme,
            json_keys=list(raw_json.keys()),
        )

        # Extrair candidates da resposta da LLM
        candidates = raw_json.get("candidates", [])

        if not candidates:
            logger.warning(
                "generate_topics_no_candidates",
                theme=intake.theme,
                raw_response=raw_json,
            )
            return {
                "success": True,
                "candidates": [],
                "message": "LLM retornou candidates vazio",
            }

        # Processar candidatos: remover campos não fornecidos e preservar os que foram
        processed_candidates = []
        for candidate in candidates:
            processed = {"theme": candidate.get("theme")}

            # description: incluir apenas se foi entrada
            if user_provided_fields["description"] and candidate.get("description"):
                processed["description"] = candidate["description"]

            # area_of_study: incluir apenas se foi entrada, e preservar o original
            if user_provided_fields["area_of_study"]:
                processed["area_of_study"] = intake.area_of_study

            # keywords: incluir apenas se foi entrada, e preservar os originais
            if user_provided_fields["keywords"]:
                processed["keywords"] = intake.keywords

            # Adicionar contexto do usuário
            processed["user_input"] = intake.model_dump()

            processed_candidates.append(processed)

        logger.info(
            "generate_topics_candidates_processed",
            theme=intake.theme,
            count=len(processed_candidates),
            user_provided_fields=user_provided_fields,
        )

        return {
            "success": True,
            "candidates": processed_candidates,
        }

    except Exception as exc:
        logger.error("generate_topics_error", error=str(exc), exc_info=True)
        return {
            "success": False,
            "error": str(exc),
        }


async def _analyze_query_complexity(cql_query: str) -> dict[str, Any]:
    """
    Analisa complexidade de uma query CQL.

    Args:
        cql_query: Query CQL a analisar.

    Returns:
        Dict com análise de complexidade.
    """
    from services.tools.query_complexity import QueryComplexityAnalyzer

    analyzer = QueryComplexityAnalyzer(cql_query)
    analysis = analyzer.analyze()

    return {
        "score": analysis["complexity_score"],
        "level": analysis["complexity_level"],
        "operators": analysis["operator_counts"],
        "nesting_depth": analysis["nesting_depth"]["max_depth"],
        "term_count": analysis["term_count"]["total_terms"],
        "warnings": analysis["warnings"],
        "recommendations": analysis["recommendations"],
    }


async def _validate_and_retry_query(
    intake: InputIntake,
    cql_query: str,
    api: str,
    attempt: int = 1,
    max_attempts: int = 3,
) -> tuple[bool, dict[str, Any]]:
    """
    Valida complexidade da query e retorna análise.

    Args:
        intake: InputIntake original.
        cql_query: Query CQL gerada.
        api: Nome da API.
        attempt: Número da tentativa (1-indexed).
        max_attempts: Máximo de tentativas de retry.

    Returns:
        Tuple (passed, analysis) onde:
        - passed: True se complexidade <= max_allowed, False caso contrário
        - analysis: Dict com métricas de complexidade
    """
    max_complexity = getattr(settings, "llm_max_query_complexity", 0.6)
    max_score = max_complexity * 100

    # Analisar complexidade
    analysis = await _analyze_query_complexity(cql_query)
    score = analysis["score"]

    logger.info(
        "query_complexity_check",
        api=api,
        attempt=attempt,
        score=score,
        max_score=max_score,
        passed=(score <= max_score),
    )

    # Se passou, retornar True
    if score <= max_score:
        logger.info(
            "query_complexity_passed",
            api=api,
            score=score,
            max_score=max_score,
        )
        return True, analysis

    # Se excedeu, retornar False
    logger.warning(
        "query_complexity_exceeded",
        api=api,
        attempt=attempt,
        score=score,
        max_score=max_score,
    )

    return False, analysis


async def build_probe_query(
    intake: InputIntake,
    api: str = "ops",
) -> dict[str, Any]:
    """
    Constrói query de probe search usando LLM + QueryBuilder com validação de complexidade.

    Valida se a query gerada respeita o limite de complexidade máximo
    (settings.llm_max_query_complexity). Se exceder, tenta regenerar com
    instruções mais fortes para simplificar.

    Args:
        intake: InputIntake com theme (obrigatório), description, area_of_study, keywords.
        api: API específica (default: ops).

    Returns:
        Dict com query construída e metadados.
    """
    try:
        llm_service = LLMServiceFactory.get_instance()
        field_schema_service = FieldSchemaService()
        max_complexity = getattr(settings, "llm_max_query_complexity", 0.6)
        max_attempts = 3
        attempt = 0

        while attempt < max_attempts:
            attempt += 1

            # 1. Gerar estratégia com LLM
            if attempt == 1:
                # Primeiro try: usar prompt normal
                system_prompt = PromptLoader.load_probe_system_prompt()
            else:
                # Retries: usar prompt com instrução mais forte
                system_prompt = PromptLoader.load_probe_system_prompt()
                simplification_instruction = (
                    f"\n\n[CRITICAL RETRY #{attempt}] "
                    f"Previous query was too complex (complexity > {max_complexity}). "
                    f"MUST simplify:\n"
                    f"- Use ONLY the 2 most important concepts\n"
                    f"- Limit each group to 2-3 terms maximum\n"
                    f"- Remove all secondary concepts\n"
                    f"- Use broader, more general terms\n"
                    f"- Minimize OR operators\n"
                    f"Keep it simple and focused!"
                )
                system_prompt += simplification_instruction

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

            cql_query = query.get("query", "")

            # 4. Validar complexidade
            passed, complexity_analysis = await _validate_and_retry_query(
                intake=intake,
                cql_query=cql_query,
                api=api,
                attempt=attempt,
                max_attempts=max_attempts,
            )

            if passed:
                # Query passou na validação
                logger.info(
                    "probe_query_built",
                    api=api,
                    attempt=attempt,
                    query_type=type(query).__name__,
                    complexity_score=complexity_analysis["score"],
                )

                return {
                    "success": True,
                    "api": api,
                    "query": query,
                    "llm_strategy": normalized.get_active_fields(),
                    "user_input": intake.model_dump(),
                    "complexity": {
                        "score": complexity_analysis["score"],
                        "level": complexity_analysis["level"],
                        "operators": complexity_analysis["operators"],
                        "nesting_depth": complexity_analysis["nesting_depth"],
                        "term_count": complexity_analysis["term_count"],
                        "warnings": complexity_analysis["warnings"],
                        "recommendations": complexity_analysis["recommendations"],
                    },
                    "attempt": attempt,
                }

            # Se chegou aqui, precisa retry
            if attempt < max_attempts:
                logger.info(
                    "probe_query_retry",
                    api=api,
                    attempt=attempt,
                    next_attempt=attempt + 1,
                    complexity_score=complexity_analysis["score"],
                )

        # Se saiu do loop sem passar na validação, a variável complexity_analysis contém a última análise
        logger.error(
            "probe_query_complexity_failed",
            api=api,
            max_attempts=max_attempts,
            max_complexity=max_complexity,
            final_score=complexity_analysis["score"],
        )

        return {
            "success": False,
            "error": f"Query exceeded complexity limit ({max_complexity}) after {max_attempts} attempts",
            "hint": "Try a more specific or narrower topic",
            "complexity": {
                "score": complexity_analysis["score"],
                "level": complexity_analysis["level"],
                "warnings": complexity_analysis["warnings"],
                "recommendations": complexity_analysis["recommendations"],
            },
        }

    except Exception as exc:
        logger.error("build_probe_query_error", error=str(exc), exc_info=True)
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
    intake: InputIntake,
    api: str = "ops",
) -> dict[str, Any]:
    """
    Constrói query final usando temas expandidos com validação de complexidade.

    Semelhante ao probe_query, mas com limite de resultados maior (final_top_k).
    Valida se a query respeta o limite de complexidade máxima e tenta regenerar
    se necessário.

    Args:
        intake: InputIntake com theme (obrigatório), description, area_of_study, keywords.
        api: API específica (default: ops).

    Returns:
        Dict com query final pronta para busca de produção.
    """
    try:
        llm_service = LLMServiceFactory.get_instance()
        field_schema_service = FieldSchemaService()
        max_complexity = getattr(settings, "llm_max_query_complexity", 0.6)
        max_attempts = 3
        attempt = 0

        while attempt < max_attempts:
            attempt += 1

            # 1. Gerar estratégia com LLM
            if attempt == 1:
                # Primeiro try: usar prompt normal
                system_prompt = PromptLoader.load_probe_system_prompt()
            else:
                # Retries: usar prompt com instrução mais forte
                system_prompt = PromptLoader.load_probe_system_prompt()
                simplification_instruction = (
                    f"\n\n[CRITICAL RETRY #{attempt}] "
                    f"Previous query was too complex (complexity > {max_complexity}). "
                    f"MUST simplify:\n"
                    f"- Use ONLY the 2-3 most important concepts\n"
                    f"- Limit each group to 2-3 terms maximum\n"
                    f"- Minimize secondary concepts\n"
                    f"- Use broader, more general terms\n"
                    f"- Minimize OR operators\n"
                    f"Keep it simple and focused!"
                )
                system_prompt += simplification_instruction

            llm_output = await llm_service.process_intake(intake, system_prompt)

            # 2. Normalizar saída
            final_fields = field_schema_service.get_fields_for_final_search()
            normalized = LLMOutputNormalizer.normalize(llm_output, enabled_fields=final_fields)

            # 3. Construir query final
            builder = QueryBuilderFactory.create(api, search_mode="final")
            query = builder.build_query(
                llm_output=normalized,
                year_from=getattr(settings, "search_year_from", 2015),
                year_to=getattr(settings, "search_year_to", 2026),
            )

            cql_query = query.get("query", "")

            # 4. Validar complexidade
            passed, complexity_analysis = await _validate_and_retry_query(
                intake=intake,
                cql_query=cql_query,
                api=api,
                attempt=attempt,
                max_attempts=max_attempts,
            )

            if passed:
                # Query passou na validação
                logger.info(
                    "final_query_built",
                    api=api,
                    attempt=attempt,
                    query_type=type(query).__name__,
                    complexity_score=complexity_analysis["score"],
                )

                return {
                    "success": True,
                    "api": api,
                    "query": query,
                    "llm_strategy": normalized.get_active_fields(),
                    "user_input": intake.model_dump(),
                    "complexity": {
                        "score": complexity_analysis["score"],
                        "level": complexity_analysis["level"],
                        "operators": complexity_analysis["operators"],
                        "nesting_depth": complexity_analysis["nesting_depth"],
                        "term_count": complexity_analysis["term_count"],
                        "warnings": complexity_analysis["warnings"],
                        "recommendations": complexity_analysis["recommendations"],
                    },
                    "attempt": attempt,
                }

            # Se chegou aqui, precisa retry
            if attempt < max_attempts:
                logger.info(
                    "final_query_retry",
                    api=api,
                    attempt=attempt,
                    next_attempt=attempt + 1,
                    complexity_score=complexity_analysis["score"],
                )

        # Se saiu do loop sem passar na validação, a variável complexity_analysis contém a última análise
        logger.error(
            "final_query_complexity_failed",
            api=api,
            max_attempts=max_attempts,
            max_complexity=max_complexity,
            final_score=complexity_analysis["score"],
        )

        return {
            "success": False,
            "error": f"Query exceeded complexity limit ({max_complexity}) after {max_attempts} attempts",
            "hint": "Try a more specific or narrower topic",
            "complexity": {
                "score": complexity_analysis["score"],
                "level": complexity_analysis["level"],
                "warnings": complexity_analysis["warnings"],
                "recommendations": complexity_analysis["recommendations"],
            },
        }

    except Exception as exc:
        logger.error("build_final_query_error", error=str(exc), exc_info=True)
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
