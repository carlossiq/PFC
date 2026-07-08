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

    A LLM analisa os parâmetros fornecidos e sugere 4 variações mais específicas
    e focadas. Campos que o usuário já preencheu são preservados como-são; campos
    que o usuário deixou em branco são gerados pela própria LLM.

    Regras:
    - theme: Sempre gerado com 4 variações específicas e diferentes
    - description: Gerado apenas se o usuário forneceu description como entrada
    - area_of_study: Se fornecido pelo usuário, preservado em todos os candidatos;
      caso contrário, gerado pela LLM (pode variar por candidato)
    - keywords: Se fornecidas pelo usuário, preservadas em todos os candidatos;
      caso contrário, geradas pela LLM (podem variar por candidato)

    Args:
        intake: InputIntake com theme (obrigatório), description, area_of_study, keywords.

    Returns:
        Dict com 4 tópicos candidatos. Cada candidato contém:
        - theme: Sempre presente (refinado)
        - description: Presente apenas se foi entrada do usuário
        - area_of_study: Sempre presente (preservado se foi entrada, senão gerado pela LLM)
        - keywords: Sempre presente (preservadas se foram entrada, senão geradas pela LLM)
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

        # Processar candidatos: preservar campos fornecidos pelo usuário como-são,
        # e usar o que a LLM gerou para os campos que o usuário deixou em branco.
        processed_candidates = []
        for candidate in candidates:
            processed = {"theme": candidate.get("theme")}

            # description: incluir apenas se foi entrada (não geramos do zero)
            if user_provided_fields["description"] and candidate.get("description"):
                processed["description"] = candidate["description"]

            # area_of_study: preservar o original se fornecido, senão usar o gerado pela LLM
            if user_provided_fields["area_of_study"]:
                processed["area_of_study"] = intake.area_of_study
            elif candidate.get("area_of_study"):
                processed["area_of_study"] = candidate["area_of_study"]

            # keywords: preservar os originais se fornecidos, senão usar os gerados pela LLM.
            # A LLM às vezes retorna uma string separada por vírgulas em vez de um array
            # (apesar da instrução no prompt) - normalizamos para lista aqui como salvaguarda.
            if user_provided_fields["keywords"]:
                processed["keywords"] = intake.keywords
            elif candidate.get("keywords"):
                raw_keywords = candidate["keywords"]
                if isinstance(raw_keywords, str):
                    raw_keywords = [kw.strip() for kw in raw_keywords.split(",") if kw.strip()]
                if raw_keywords:
                    processed["keywords"] = raw_keywords

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
    instruções mais fortes para simplificar. Se todas as 3 tentativas falharem,
    retorna a menos complexa com um aviso.

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

        complexity_analysis = None  # Track complexity from previous attempt
        attempts_history = []  # Store all 3 attempts

        while attempt < max_attempts:
            attempt += 1

            # 1. Gerar estratégia com LLM
            if attempt == 1:
                # Primeiro try: usar prompt normal
                system_prompt = PromptLoader.load_probe_system_prompt()
            else:
                # Retries: usar prompt com instrução mais forte, incluindo métricas de complexidade
                system_prompt = PromptLoader.load_probe_system_prompt()
                simplification_instruction = (
                    f"\n\n[CRITICAL RETRY #{attempt}] "
                    f"Previous query was TOO COMPLEX (score: {complexity_analysis['score']:.1f}/100, max: {max_complexity*100:.0f}). "
                    f"\nComplexity breakdown:\n"
                    f"- OR operators: {complexity_analysis['operators'].get('OR', 0)}\n"
                    f"- AND operators: {complexity_analysis['operators'].get('AND', 0)}\n"
                    f"- Nesting depth: {complexity_analysis['nesting_depth']}\n"
                    f"- Total terms: {complexity_analysis['term_count']}\n"
                    f"\nMUST simplify by:\n"
                    f"- Use ONLY 1-2 most important concepts (reduce terms)\n"
                    f"- Minimize OR operators within groups\n"
                    f"- Remove nesting: avoid complex AND/OR combinations\n"
                    f"- Use broader, more general search terms\n"
                    f"- Maximum 2 groups per field, 2-3 terms per group\n"
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

            # Armazenar tentativa no histórico
            attempts_history.append({
                "attempt": attempt,
                "query": query,
                "normalized": normalized,
                "complexity": complexity_analysis,
            })

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

        # Todas as 3 tentativas falharam - retornar a menos complexa
        best_attempt = min(attempts_history, key=lambda x: x["complexity"]["score"])
        best_complexity = best_attempt["complexity"]

        logger.warning(
            "probe_query_complexity_exceeded_returning_best",
            api=api,
            max_attempts=max_attempts,
            max_allowed=max_complexity*100,
            best_attempt_num=best_attempt["attempt"],
            best_score=best_complexity["score"],
        )

        return {
            "success": True,
            "api": api,
            "query": best_attempt["query"],
            "llm_strategy": best_attempt["normalized"].get_active_fields(),
            "user_input": intake.model_dump(),
            "complexity": {
                "score": best_complexity["score"],
                "level": best_complexity["level"],
                "operators": best_complexity["operators"],
                "nesting_depth": best_complexity["nesting_depth"],
                "term_count": best_complexity["term_count"],
                "warnings": best_complexity["warnings"],
                "recommendations": best_complexity["recommendations"],
            },
            "attempt": best_attempt["attempt"],
            "warning": f"Query complexity ({best_complexity['score']:.1f}/100) exceeds limit ({max_complexity*100:.0f}) "
                      f"after {max_attempts} simplification attempts. Returning attempt #{best_attempt['attempt']} "
                      f"(the least complex version). Consider using a simpler or more focused topic.",
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
    top_k: int = 10,
) -> dict[str, Any]:
    """
    Executa probe search em uma API específica com abstracts.

    Usa endpoints otimizados que já retornam abstracts (ex: /search/abstract do OPS).
    Renova token OAuth2 antes de fazer a requisição.

    Nota: Busca top_k + 5 resultados para compensar abstracts em idiomas não-ingleses,
    garantindo mais opções com abstracts em inglês.

    Args:
        query: Query já construída.
        api: Nome da API (ops, scopus, lens_patent, lens_scholarly).
        top_k: Número de resultados a retornar (1-100, default 10).

    Returns:
        Dict com resultados da busca já contendo abstracts.
    """
    try:
        # Buffer de resultados para compensar abstracts em outros idiomas
        effective_top_k = min(top_k + 5, 100)

        # Renovar/garantir token válido ANTES da busca
        if api == "ops":
            from services.search.ops_token_manager import ops_token_manager
            token = await ops_token_manager.get_valid_token()
            if not token:
                # Obter mensagem de erro específica do Token Manager
                error_reason = "Unknown error obtaining token"
                if hasattr(ops_token_manager, '_last_error'):
                    error_reason = ops_token_manager._last_error

                logger.error("ops_probe_search_token_failed", reason=error_reason)
                return {
                    "success": False,
                    "api": api,
                    "has_abstracts": True,
                    "error": f"Failed to obtain OPS authentication token: {error_reason}",
                }

        if api == "ops":
            service = OPSService()
            result = await service.search_with_abstracts(query, top_k=effective_top_k)
            await service.close()
        elif api == "scopus":
            service = ScopusService()
            result = await service.search(query, top_k=effective_top_k)
            await service.close()
        else:
            # Lens Patent ou Scholarly
            service = LensService()
            if api == "lens_patent":
                result = await service.search_patent(query=query, top_k=effective_top_k)
            else:
                result = await service.search_scholarly(query=query, top_k=effective_top_k)
            service.close()

        return {
            "success": result.success,
            "api": api,
            "results_count": result.results_returned,
            "total_available": result.total_count,
            "results": result.results if result.success else [],
            "has_abstracts": True,
            "error": result.error_message if not result.success else None,
        }

    except Exception as exc:
        logger.error("run_probe_search_error", error=str(exc), api=api)
        return {
            "success": False,
            "api": api,
            "has_abstracts": True,
            "error": str(exc),
        }


async def enrich_probe_results(
    results: list[dict[str, Any]],
    api: str,
    top_k: int = 10,
) -> dict[str, Any]:
    """
    Enriquece resultados brutos com dados bibliográficos.

    Apenas APIs que suportam enriquecimento (atualmente: OPS) serão processadas.
    Enriquece até top_k resultados com dados completos (título, abstract, inventors, applicants).

    Args:
        results: Resultados brutos da busca (do /probe/search endpoint).
        api: Nome da API (ops, scopus, lens_patent, lens_scholarly).
        top_k: Número de resultados a enriquecer (default 10).

    Returns:
        Dict com resultados enriquecidos e estatísticas.
    """
    try:
        if api != "ops":
            return {
                "success": False,
                "api": api,
                "error": f"API '{api}' does not support enrichment. Only 'ops' is supported.",
                "enriched_count": 0,
                "total": len(results),
            }

        if not results:
            return {
                "success": True,
                "api": api,
                "results": [],
                "enriched_count": 0,
                "total": 0,
            }

        service = OPSService()
        enriched_results = await service.enrich_results_with_biblio(
            results=results,
            max_results=top_k,
        )
        await service.close()

        # Contar enriquecimentos bem-sucedidos
        enriched_count = sum(1 for r in enriched_results if r.get("biblio") is not None)

        logger.info(
            "probe_results_enriched",
            api=api,
            total_results=len(results),
            enriched_count=enriched_count,
            top_k=top_k,
        )

        return {
            "success": True,
            "api": api,
            "results": enriched_results,
            "enriched_count": enriched_count,
            "total": len(enriched_results),
            "total_with_abstracts": sum(1 for r in enriched_results if (r.get("biblio") or {}).get("abstract")),
            "total_with_titles": sum(1 for r in enriched_results if (r.get("biblio") or {}).get("title")),
        }

    except Exception as exc:
        logger.error("enrich_probe_results_error", error=str(exc), api=api)
        return {
            "success": False,
            "api": api,
            "error": str(exc),
        }


async def extract_relevant_terms(
    items: list[dict[str, Any]],
    original_params: Optional[dict[str, Any]] = None,
    top_k: int = 20,
) -> dict[str, Any]:
    """
    Extrai termos relevantes de uma lista de items (title + abstract) usando TermExtractor.

    Processa título e abstract separadamente com pesos configuráveis (título 3.0, abstract 1.0).
    Combina KeyBERT (relevância semântica) e TF-IDF (importância estatística)
    para identificar novos termos não presentes nos parâmetros originais.

    Args:
        items: Lista de dicts com 'title' e 'abstract' para extração de termos.
        original_params: Parâmetros originais da busca (theme, description, etc) para filtrar termos.
        top_k: Número de termos a extrair.

    Returns:
        Dict com termos relevantes, scores por fonte (title/abstract), e detalhes.
    """
    try:
        from services.nlp.term_extraction import TermExtractor

        if not items:
            return {
                "success": False,
                "error": "No items provided",
            }

        # Filtrar items que tenham title ou abstract não-vazio
        valid_items = [
            item for item in items
            if (item.get("title") and item.get("title").strip()) or
               (item.get("abstract") and item.get("abstract").strip())
        ]

        if not valid_items:
            return {
                "success": False,
                "error": "No valid items with non-empty title or abstract",
            }

        # Usar parâmetros vazios se não fornecidos
        if original_params is None:
            original_params = {}

        # Converter items simples para formato esperado pelo TermExtractor
        enriched_results = [
            {
                "biblio": {
                    "invention_title": item.get("title", "").strip() if item.get("title") else "",
                    "title": item.get("title", "").strip() if item.get("title") else "",
                    "abstract": item.get("abstract", "").strip() if item.get("abstract") else "",
                },
                "publication_number": f"item_{idx}",
            }
            for idx, item in enumerate(valid_items)
        ]

        # Criar extrator e extrair termos
        extractor = TermExtractor()
        terms = extractor.extract_and_rank_terms(
            original_params=original_params,
            enriched_results=enriched_results,
            top_k=top_k,
        )

        logger.info(
            "terms_extracted",
            count=len(terms),
            items_count=len(items),
            top_k=top_k,
        )

        return {
            "success": True,
            "terms": terms,
            "count": len(terms),
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
        complexity_analysis = None  # Track complexity from previous attempt
        attempts_history = []  # Store all 3 attempts

        while attempt < max_attempts:
            attempt += 1

            # 1. Gerar estratégia com LLM
            if attempt == 1:
                # Primeiro try: usar prompt normal
                system_prompt = PromptLoader.load_probe_system_prompt()
            else:
                # Retries: usar prompt com instrução mais forte, incluindo métricas de complexidade
                system_prompt = PromptLoader.load_probe_system_prompt()
                simplification_instruction = (
                    f"\n\n[CRITICAL RETRY #{attempt}] "
                    f"Previous query was TOO COMPLEX (score: {complexity_analysis['score']:.1f}/100, max: {max_complexity*100:.0f}). "
                    f"\nComplexity breakdown:\n"
                    f"- OR operators: {complexity_analysis['operators'].get('OR', 0)}\n"
                    f"- AND operators: {complexity_analysis['operators'].get('AND', 0)}\n"
                    f"- Nesting depth: {complexity_analysis['nesting_depth']}\n"
                    f"- Total terms: {complexity_analysis['term_count']}\n"
                    f"\nMUST simplify by:\n"
                    f"- Use ONLY 1-2 most important concepts (reduce terms)\n"
                    f"- Minimize OR operators within groups\n"
                    f"- Remove nesting: avoid complex AND/OR combinations\n"
                    f"- Use broader, more general search terms\n"
                    f"- Maximum 2 groups per field, 2-3 terms per group\n"
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

            # Armazenar tentativa no histórico
            attempts_history.append({
                "attempt": attempt,
                "query": query,
                "normalized": normalized,
                "complexity": complexity_analysis,
            })

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

        # Todas as 3 tentativas falharam - retornar a menos complexa
        best_attempt = min(attempts_history, key=lambda x: x["complexity"]["score"])
        best_complexity = best_attempt["complexity"]

        logger.warning(
            "final_query_complexity_exceeded_returning_best",
            api=api,
            max_attempts=max_attempts,
            max_allowed=max_complexity*100,
            best_attempt_num=best_attempt["attempt"],
            best_score=best_complexity["score"],
        )

        return {
            "success": True,
            "api": api,
            "query": best_attempt["query"],
            "llm_strategy": best_attempt["normalized"].get_active_fields(),
            "user_input": intake.model_dump(),
            "complexity": {
                "score": best_complexity["score"],
                "level": best_complexity["level"],
                "operators": best_complexity["operators"],
                "nesting_depth": best_complexity["nesting_depth"],
                "term_count": best_complexity["term_count"],
                "warnings": best_complexity["warnings"],
                "recommendations": best_complexity["recommendations"],
            },
            "attempt": best_attempt["attempt"],
            "warning": f"Query complexity ({best_complexity['score']:.1f}/100) exceeds limit ({max_complexity*100:.0f}) "
                      f"after {max_attempts} simplification attempts. Returning attempt #{best_attempt['attempt']} "
                      f"(the least complex version). Consider using a simpler or more focused topic.",
        }

    except Exception as exc:
        logger.error("build_final_query_error", error=str(exc), exc_info=True)
        return {
            "success": False,
            "error": str(exc),
        }


async def build_final_queries_with_extraction(
    intake: InputIntake,
    extracted_terms: list[dict[str, Any]],
    api: str = "ops",
) -> dict[str, Any]:
    """
    Constrói 3 variações de query final (específica, balanceada, genérica)
    usando parâmetros originais e termos extraídos com scores.

    Gera queries em diferentes níveis de especificidade:
    - SPECIFIC: Alta precisão, apenas termos com score > 0.4
    - BALANCED: Equilíbrio, termos com score > 0.3 (RECOMENDADO)
    - GENERIC: Alta cobertura, termos com score > 0.2

    Args:
        intake: InputIntake com theme (obrigatório), description, etc.
        extracted_terms: Lista de termos extraídos com {term, score, keybert_score, tf_idf_score, frequency}
        api: API específica (ops, scopus, lens_patent, lens_scholarly).

    Returns:
        Dict com 3 queries (specific, balanced, generic), cada uma com validação de complexidade.
    """
    try:
        llm_service = LLMServiceFactory.get_instance()
        max_complexity = getattr(settings, "llm_max_query_complexity", 0.6)
        max_score = max_complexity * 100

        # Carregar prompt system para queries finais
        system_prompt = PromptLoader.load_prompt("final_system_prompt.md")

        # Construir mensagem com parâmetros e termos extraídos
        top_terms_specific = [t for t in extracted_terms if t.get("score", 0) > 0.4]
        top_terms_balanced = [t for t in extracted_terms if t.get("score", 0) > 0.3]
        top_terms_generic = [t for t in extracted_terms if t.get("score", 0) > 0.2]

        user_message = f"""
Generate THREE search query variations for {api.upper()} database:

## Original Search Parameters
- Theme: {intake.theme}
- Description: {intake.description}
- Area of Study: {intake.area_of_study}
- Keywords: {', '.join(intake.keywords) if intake.keywords else 'None'}

## Extracted Relevant Terms (from search results)

### High-Scoring Terms (score > 0.4) - For SPECIFIC query:
{_format_terms_for_prompt(top_terms_specific)}

### Mid-Scoring Terms (score > 0.3) - For BALANCED query:
{_format_terms_for_prompt(top_terms_balanced)}

### All Relevant Terms (score > 0.2) - For GENERIC query:
{_format_terms_for_prompt(top_terms_generic)}

## Requirements
- All queries must have complexity score < {max_score:.0f}
- Prefer extracted terms over original parameters when synonyms exist
- Use ABSTRACT OR TITLE as primary search fields
- Use minimal AND operators (max 3 for specific, 1-2 for balanced, 0-1 for generic)
- Group related terms with OR
- Return JSON format with queries for each variation

Target API: {api}
Query Syntax: {'CQL' if api == 'ops' else 'Boolean'}
"""

        logger.info(
            "final_queries_generation_start",
            api=api,
            original_params=intake.model_dump(),
            total_extracted_terms=len(extracted_terms),
            specific_terms=len(top_terms_specific),
            balanced_terms=len(top_terms_balanced),
            generic_terms=len(top_terms_generic),
        )

        # Chamar LLM para gerar 3 queries com formato JSON customizado
        try:
            queries_json = await llm_service.call_raw_json(
                prompt=system_prompt,
                user_input=user_message,
            )
        except Exception as exc:
            logger.error(
                "final_queries_llm_call_failed",
                error=str(exc),
                api=api,
            )
            return {
                "success": False,
                "error": f"LLM call failed: {str(exc)}",
            }

        # Validar resposta
        if not queries_json:
            return {
                "success": False,
                "error": "LLM returned empty response",
            }

        if not queries_json:
            return {
                "success": False,
                "error": "No queries generated in LLM response",
            }

        # Validar complexidade de cada query
        results = {
            "success": True,
            "api": api,
            "user_input": intake.model_dump(),
            "extracted_terms_summary": {
                "total": len(extracted_terms),
                "high_score": len(top_terms_specific),
                "mid_score": len(top_terms_balanced),
                "all_score": len(top_terms_generic),
            },
            "queries": {}
        }

        for variant in ["specific", "balanced", "generic"]:
            query_data = queries_json.get(variant, {})
            query_str = query_data.get("query", "")

            if not query_str:
                results["queries"][variant] = {
                    "success": False,
                    "error": f"No query generated for {variant}",
                }
                continue

            # Analisar complexidade
            complexity = await _analyze_query_complexity(query_str)
            score = complexity["score"]
            passed = score <= max_score

            logger.info(
                "final_query_complexity_check",
                variant=variant,
                api=api,
                score=score,
                max_score=max_score,
                passed=passed,
            )

            results["queries"][variant] = {
                "success": passed or variant == "generic",  # Generic always returned even if complex
                "query": {
                    "query": query_str,
                    "range": f"1-{getattr(settings, 'final_top_k', 100)}",
                    "format": "json",
                },
                "rationale": query_data.get("rationale", ""),
                "expected_precision": query_data.get("expected_precision", ""),
                "focus_areas": query_data.get("focus_areas", []),
                "complexity": {
                    "score": score,
                    "level": complexity["level"],
                    "passed": passed,
                    "warnings": complexity["warnings"],
                },
            }

            if not passed and variant != "generic":
                results["queries"][variant]["warning"] = (
                    f"Query complexity ({score:.1f}/100) exceeds limit ({max_score:.0f}). "
                    f"Consider using the GENERIC variant for broader coverage."
                )

        logger.info(
            "final_queries_generation_complete",
            api=api,
            specific_passed=results["queries"].get("specific", {}).get("success", False),
            balanced_passed=results["queries"].get("balanced", {}).get("success", False),
            generic_returned=results["queries"].get("generic", {}).get("success", False),
        )

        return results

    except Exception as exc:
        logger.error("build_final_queries_with_extraction_error", error=str(exc), exc_info=True)
        return {
            "success": False,
            "error": str(exc),
        }


def _format_terms_for_prompt(terms: list[dict[str, Any]]) -> str:
    """Format extracted terms for LLM prompt display."""
    if not terms:
        return "- None available"

    lines = []
    for term_data in terms[:20]:  # Max 20 terms per section
        term = term_data.get("term", "")
        score = term_data.get("score", 0)
        freq = term_data.get("frequency", 0)
        lines.append(f"- {term} (score: {score:.3f}, freq: {freq})")

    return "\n".join(lines)


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
        if api == "ops":
            service = OPSService()
            result = await service.search(query)
            await service.close()
        elif api == "scopus":
            service = ScopusService()
            result = await service.search(query, max_results=max_results)
            await service.close()
        elif api == "lens_patent":
            service = LensService()
            result = await service.search_patent(query=query, max_results=max_results)
            service.close()
        elif api == "lens_scholarly":
            service = LensService()
            result = await service.search_scholarly(query=query, max_results=max_results)
            service.close()
        else:
            return {
                "success": False,
                "error": f"Unsupported API: {api}",
            }

        return {
            "success": result.success,
            "api": api,
            "results_count": result.results_returned,
            "total_available": result.total_count,
            "results": result.results if result.success else [],
            "error": result.error_message if not result.success else None,
        }

    except Exception as exc:
        logger.error("run_final_search_error", error=str(exc), api=api)
        return {
            "success": False,
            "api": api,
            "error": str(exc),
        }
