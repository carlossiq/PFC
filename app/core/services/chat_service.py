from __future__ import annotations

import asyncio
from typing import Any, Optional

from app.core.domain.types import LLMRequest
from app.core.services.query_complexity import QueryComplexityAnalyzer
from core.config import Settings
from core.logging import get_logger

logger = get_logger(__name__)

_QB_ADAPTERS: dict[str, type] = {}


def _get_qb_adapter(api: str, search_mode: str) -> Any:
    """Instancia o query builder adapter correto para (api, search_mode)."""
    if api == "ops":
        from app.adapters.driven.query_builders.ops_query_builder_adapter import OPSQueryBuilderAdapter
        return OPSQueryBuilderAdapter(search_mode=search_mode)
    if api == "scopus":
        from app.adapters.driven.query_builders.scopus_query_builder_adapter import ScopusQueryBuilderAdapter
        return ScopusQueryBuilderAdapter(search_mode=search_mode)
    if api == "lens_patent":
        from app.adapters.driven.query_builders.lens_patent_query_builder_adapter import LensPatentQueryBuilderAdapter
        return LensPatentQueryBuilderAdapter(search_mode=search_mode)
    if api == "lens_scholarly":
        from app.adapters.driven.query_builders.lens_scholarly_query_builder_adapter import LensScholarlyQueryBuilderAdapter
        return LensScholarlyQueryBuilderAdapter(search_mode=search_mode)
    raise ValueError(f"Unsupported api: {api}")


class ChatService:
    """
    Orquestra os steps individuais do workflow de prospecção,
    chamados um a um pelo frontend com auditoria entre etapas.
    """

    def __init__(
        self,
        llm: Any,
        patent_pairs: list[tuple[Any, Any]],
        scholarly_pairs: list[tuple[Any, Any]],
        settings: Settings,
    ) -> None:
        self.llm = llm
        self.patent_pairs = patent_pairs
        self.scholarly_pairs = scholarly_pairs
        self.settings = settings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_search_adapter(self, api: str) -> Optional[Any]:
        for search, _ in self.patent_pairs + self.scholarly_pairs:
            if search.api_name == api:
                return search
        return None

    def _intake_to_request(self, intake: Any) -> LLMRequest:
        return LLMRequest(
            theme=intake.theme,
            description=intake.description,
            area_of_study=intake.area_of_study,
            keywords=intake.keywords or [],
        )

    def _complexity_from_query(self, cql_query: str) -> dict[str, Any]:
        analysis = QueryComplexityAnalyzer(cql_query).analyze()
        return {
            "score": analysis["complexity_score"],
            "level": analysis["complexity_level"],
            "operators": analysis["operator_counts"],
            "nesting_depth": analysis["nesting_depth"]["max_depth"],
            "term_count": analysis["term_count"]["total_terms"],
            "warnings": analysis["warnings"],
            "recommendations": analysis["recommendations"],
        }

    def _simplification_suffix(self, complexity: dict[str, Any], attempt: int) -> str:
        max_score = getattr(self.settings, "llm_max_query_complexity", 0.6) * 100
        return (
            f"\n\n[CRITICAL RETRY #{attempt}] "
            f"Previous query was TOO COMPLEX (score: {complexity['score']:.1f}/100, max: {max_score:.0f}). "
            f"\nComplexity breakdown:\n"
            f"- OR operators: {complexity['operators'].get('OR', 0)}\n"
            f"- AND operators: {complexity['operators'].get('AND', 0)}\n"
            f"- Nesting depth: {complexity['nesting_depth']}\n"
            f"- Total terms: {complexity['term_count']}\n"
            f"\nMUST simplify by:\n"
            f"- Use ONLY 1-2 most important concepts (reduce terms)\n"
            f"- Minimize OR operators within groups\n"
            f"- Remove nesting: avoid complex AND/OR combinations\n"
            f"- Use broader, more general search terms\n"
            f"- Maximum 2 groups per field, 2-3 terms per group\n"
            f"Keep it simple and focused!"
        )

    @staticmethod
    def _flatten_llm_response_fields(llm_response: Any) -> dict[str, list[str]]:
        """
        Achata um LLMResponse (domain, retornado por llm.process_intake) em
        {campo: [termos]} plano. Perde a granularidade de múltiplos grupos
        AND/OR entre grupos textuais — simplificação aceita para permitir
        edição estruturada simples no frontend (mesmo espírito do Step2
        tratar keywords/studyArea como listas simples).
        """
        def flat(tq: Any) -> list[str]:
            seen: list[str] = []
            for g in tq.groups:
                for t in g.terms:
                    if t not in seen:
                        seen.append(t)
            return seen

        return {
            "title": flat(llm_response.title),
            "abstract": flat(llm_response.abstract),
            "claims": flat(llm_response.claims),
            "ipc": list(llm_response.ipc),
            "cpc": list(llm_response.cpc),
            "applicant": list(llm_response.applicant),
            "inventor": list(llm_response.inventor),
            "year": list(llm_response.year),
        }

    @staticmethod
    def _query_fields_to_llm_output(fields: dict[str, list[str]]) -> Any:
        """
        Reconstrói um schemas.llm.LLMOutput a partir dos campos estruturados
        simplificados editados pelo usuário. Cada campo vira um único grupo OR
        (mesma simplificação de _flatten_llm_response_fields, no sentido
        inverso). Usado só pelo rebuild síncrono (sem LLM).
        """
        from schemas.llm import LLMOutput, SimpleFieldQuery, TermGroup, TextualFieldQuery

        def textual(values: Optional[list[str]]) -> TextualFieldQuery:
            clean = [v.strip() for v in (values or []) if isinstance(v, str) and v.strip()]
            if not clean:
                return TextualFieldQuery()
            return TextualFieldQuery(group_operator="OR", groups=[TermGroup(operator="OR", terms=clean)])

        def simple(values: Optional[list[str]]) -> SimpleFieldQuery:
            return SimpleFieldQuery(values=[v.strip() for v in (values or []) if isinstance(v, str) and v.strip()])

        return LLMOutput(
            title=textual(fields.get("title")),
            abstract=textual(fields.get("abstract")),
            claims=textual(fields.get("claims")),
            ipc=simple(fields.get("ipc")),
            cpc=simple(fields.get("cpc")),
            applicant=simple(fields.get("applicant")),
            inventor=simple(fields.get("inventor")),
            year=simple(fields.get("year")),
        )

    async def _build_query_with_retry(
        self,
        intake: Any,
        api: str,
        search_mode: str,
        prompt_loader_method: str,
    ) -> dict[str, Any]:
        """
        Chama LLM → QueryBuilder → QueryComplexityAnalyzer em loop de até
        max_attempts tentativas. Retenta tanto por complexidade excessiva
        quanto por falhas transitórias da LLM (ex: resposta com JSON
        malformado) - nesse segundo caso não há métricas de complexidade da
        tentativa anterior pra injetar no prompt, então a próxima tentativa
        usa o prompt base normalmente.
        """
        from services.prompt.prompt_loader import PromptLoader

        max_complexity = getattr(self.settings, "llm_max_query_complexity", 0.6)
        max_score = max_complexity * 100
        max_attempts = 3
        attempts_history: list[dict] = []
        complexity: Optional[dict] = None
        last_error: Optional[Exception] = None

        year_from = getattr(self.settings, "search_year_from", 2015)
        year_to = getattr(self.settings, "search_year_to", 2026)
        year_range = {"from": year_from, "to": year_to}

        llm_request = self._intake_to_request(intake)
        qb = _get_qb_adapter(api, search_mode)

        for attempt in range(1, max_attempts + 1):
            base_prompt = getattr(PromptLoader, prompt_loader_method)()
            system_prompt = base_prompt
            if attempt > 1 and complexity is not None:
                system_prompt += self._simplification_suffix(complexity, attempt)

            try:
                llm_response = await self.llm.process_intake(llm_request, system_prompt)
                query = qb.build_query(
                    strategy=llm_response,
                    year_from=year_from,
                    year_to=year_to,
                    search_mode=search_mode,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "query_attempt_llm_error",
                    api=api,
                    mode=search_mode,
                    attempt=attempt,
                    error=str(exc),
                )
                continue

            cql_query = query.get("query", "")
            complexity = self._complexity_from_query(cql_query)
            passed = complexity["score"] <= max_score
            fields = self._flatten_llm_response_fields(llm_response)

            attempts_history.append({"attempt": attempt, "query": query, "complexity": complexity, "fields": fields})

            logger.info(
                "query_complexity_check",
                api=api,
                mode=search_mode,
                attempt=attempt,
                score=complexity["score"],
                max_score=max_score,
                passed=passed,
            )

            if passed:
                return {
                    "success": True,
                    "api": api,
                    "query": query,
                    "complexity": complexity,
                    "attempt": attempt,
                    "fields": fields,
                    "year_range": year_range,
                }

        if not attempts_history:
            # Todas as tentativas falharam antes de conseguir montar uma query
            # (ex: erro de parsing da LLM em todas elas) - não há "melhor
            # tentativa" pra devolver.
            logger.error(
                "query_all_attempts_failed",
                api=api,
                mode=search_mode,
                max_attempts=max_attempts,
                error=str(last_error),
            )
            return {
                "success": False,
                "api": api,
                "error": f"Falha ao gerar query após {max_attempts} tentativas: {last_error}",
            }

        best = min(attempts_history, key=lambda x: x["complexity"]["score"])
        logger.warning(
            "query_complexity_exceeded_returning_best",
            api=api,
            best_attempt=best["attempt"],
            best_score=best["complexity"]["score"],
        )
        max_allowed = max_complexity * 100
        return {
            "success": True,
            "api": api,
            "query": best["query"],
            "complexity": best["complexity"],
            "attempt": best["attempt"],
            "fields": best["fields"],
            "year_range": year_range,
            "warning": (
                f"Query complexity ({best['complexity']['score']:.1f}/100) exceeds limit "
                f"({max_allowed:.0f}) after {max_attempts} attempts. "
                f"Returning attempt #{best['attempt']} (least complex)."
            ),
        }

    # ------------------------------------------------------------------
    # Config / info
    # ------------------------------------------------------------------

    async def list_available_apis(self) -> dict[str, Any]:
        patent_names = {s.api_name for s, _ in self.patent_pairs}
        scholarly_names = {s.api_name for s, _ in self.scholarly_pairs}
        return {
            "success": True,
            "apis": {
                "ops": "ops" in patent_names,
                "lens_patent": "lens_patent" in patent_names,
                "scopus": "scopus" in scholarly_names,
                "lens_scholarly": "lens_scholarly" in scholarly_names,
            },
        }

    async def list_available_models(self) -> dict[str, Any]:
        return {
            "success": True,
            "models": {
                "anthropic": {
                    "model": getattr(self.settings, "llm_anthropic_model", "claude-3-5-sonnet-20241022"),
                    "available": bool(getattr(self.settings, "llm_anthropic_api_key", None)),
                },
                "gemini": {
                    "model": getattr(self.settings, "llm_gemini_model", "gemini-2.0-flash-exp"),
                    "available": bool(getattr(self.settings, "llm_gemini_api_key", None)),
                },
            },
        }

    async def get_current_provider(self) -> dict[str, Any]:
        return {
            "success": True,
            "provider": self.llm.provider_name,
            "available": self.llm.is_available(),
        }

    async def get_system_prompt(self) -> dict[str, Any]:
        from services.prompt.prompt_loader import PromptLoader
        content = PromptLoader.load_general_system_prompt()
        return {"success": True, "prompt": content}

    # ------------------------------------------------------------------
    # OPS token
    # ------------------------------------------------------------------

    async def check_ops_token_status(self) -> dict[str, Any]:
        try:
            from datetime import datetime
            from services.search.ops_service import OPSService

            ops_service = OPSService(
                consumer_key=getattr(self.settings, "ops_consumer_key", ""),
                consumer_secret=getattr(self.settings, "ops_consumer_secret", ""),
            )
            await ops_service._ensure_valid_token()

            if not ops_service.token:
                return {"success": False, "error": "Failed to obtain OPS token"}

            token_dict = ops_service.token.to_dict()
            is_expired = ops_service.token.is_expired()
            now = datetime.utcnow()
            time_until_expiration = (ops_service.token.expiration_time - now).total_seconds()

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
            return {"success": False, "error": f"OPS credentials error: {exc}"}
        except Exception as exc:
            logger.error("ops_token_check_error", error=str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Topic refinement
    # ------------------------------------------------------------------

    @staticmethod
    def _build_intake_user_input(intake: Any) -> str:
        """Monta o bloco textual base (Tema/Descrição/Área/Palavras-chave) enviado à LLM."""
        user_input = f"Tema: {intake.theme}"
        if intake.description:
            user_input += f"\nDescrição: {intake.description}"
        if intake.area_of_study:
            user_input += f"\nÁrea de Estudo: {intake.area_of_study}"
        if intake.keywords:
            user_input += f"\nPalavras-chave: {', '.join(intake.keywords)}"
        return user_input

    async def generate_candidate_topics(self, intake: Any) -> dict[str, Any]:
        from services.prompt.prompt_loader import PromptLoader

        user_provided = {
            "theme": True,
            "area_of_study": intake.area_of_study is not None,
            "keywords": intake.keywords is not None,
        }

        user_input = self._build_intake_user_input(intake)
        user_input += "\n\nCampos fornecidos pelo usuário (retorne APENAS estes):\n"
        user_input += "- theme: SIM (sempre refine em 4 variações)\n"
        user_input += "- description: SIM (gere sempre uma descrição nova para cada variação, mesmo que nenhuma tenha sido informada)\n"
        if user_provided["area_of_study"]:
            user_input += f"- area_of_study: SIM (PRESERVE exatamente: '{intake.area_of_study}')\n"
        if user_provided["keywords"]:
            user_input += f"- keywords: SIM (PRESERVE exatamente: {intake.keywords})\n"

        system_prompt = PromptLoader.load_refine_topic_system_prompt()

        try:
            raw = await self.llm.call_raw_json(system_prompt, user_input)
        except Exception as exc:
            logger.error("generate_candidate_topics_llm_error", error=str(exc))
            return {"success": False, "error": str(exc)}

        candidates = raw.get("candidates", [])
        processed = []
        for candidate in candidates:
            item: dict[str, Any] = {"theme": candidate.get("theme")}
            if candidate.get("description"):
                item["description"] = candidate["description"]
            if user_provided["area_of_study"]:
                item["area_of_study"] = intake.area_of_study
            if user_provided["keywords"]:
                item["keywords"] = intake.keywords
            item["user_input"] = intake.model_dump()
            processed.append(item)

        return {"success": True, "candidates": processed}

    async def specify_topic(self, intake: Any) -> dict[str, Any]:
        """
        Aprofunda um único tema já selecionado em uma versão mais específica
        e estreita do mesmo assunto (ao contrário de generate_candidate_topics,
        que gera 4 variações diversas). area_of_study/keywords, se existirem,
        são sempre preservados como estão - a LLM nunca os gera nem os vê como
        algo a ser modificado.
        """
        from services.prompt.prompt_loader import PromptLoader

        user_input = self._build_intake_user_input(intake)
        user_input += (
            "\n\nEspecifique o tema acima em uma versão mais estreita e "
            "aprofundada do mesmo assunto (não uma alternativa diferente)."
        )

        system_prompt = PromptLoader.load_prompt("specify_topic_system_prompt.txt")

        try:
            raw = await self.llm.call_raw_json(system_prompt, user_input)
        except Exception as exc:
            logger.error("specify_topic_llm_error", error=str(exc))
            return {"success": False, "error": str(exc)}

        theme = raw.get("theme")
        if not theme:
            logger.warning("specify_topic_no_theme", raw_response=raw)
            return {"success": False, "error": "LLM did not return a theme"}

        result: dict[str, Any] = {"theme": theme}
        if intake.description and raw.get("description"):
            result["description"] = raw["description"]
        if intake.area_of_study:
            result["area_of_study"] = intake.area_of_study
        if intake.keywords:
            result["keywords"] = intake.keywords
        result["user_input"] = intake.model_dump()

        return {"success": True, **result}

    # ------------------------------------------------------------------
    # Query analysis (static, utilitário de debug)
    # ------------------------------------------------------------------

    def analyze_query(self, query_string: str) -> dict[str, Any]:
        try:
            complexity = self._complexity_from_query(query_string)
            return {"success": True, **complexity}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Query building
    # ------------------------------------------------------------------

    async def build_probe_query(self, intake: Any, api: str) -> dict[str, Any]:
        try:
            return await self._build_query_with_retry(
                intake=intake,
                api=api,
                search_mode="probe",
                prompt_loader_method="load_probe_system_prompt",
            )
        except Exception as exc:
            logger.error("build_probe_query_error", error=str(exc))
            return {"success": False, "error": str(exc)}

    async def build_probe_queries_multi(self, intake: Any, api: str, count: int = 2) -> dict[str, Any]:
        """
        Gera N tentativas independentes de query em modo probe, direto do
        intake. O probe é sempre "específico" por natureza (poucos resultados,
        alta relevância, ver probe_system_prompt.txt) — não faz sentido variar
        precisão/cobertura nesta etapa (isso é reservado pra query final, que
        já tem extracted_terms de uma busca probe anterior para calibrar
        specific/balanced/generic via build_final_queries_multi). As N
        chamadas usam o mesmo prompt; a diversidade entre elas vem da
        variação natural da LLM entre chamadas.
        """
        async def _attempt(option: int) -> dict[str, Any]:
            try:
                return await self._build_query_with_retry(
                    intake=intake,
                    api=api,
                    search_mode="probe",
                    prompt_loader_method="load_probe_system_prompt",
                )
            except Exception as exc:
                logger.error(
                    "build_probe_queries_multi_option_error",
                    option=option,
                    api=api,
                    error=str(exc),
                )
                return {"success": False, "error": str(exc)}

        # As N tentativas são independentes (mesmo intake, mesmo prompt) - rodar
        # em paralelo em vez de sequencialmente evita serializar até 3N chamadas
        # de LLM (cada tentativa já retenta até 3x internamente por complexidade).
        queries = await asyncio.gather(*(_attempt(i) for i in range(count)))
        success = any(q.get("success") for q in queries)

        result: dict[str, Any] = {
            "success": success,
            "api": api,
            "user_input": intake.model_dump(),
            "queries": queries,
        }
        if not success:
            # Nenhuma tentativa deu certo - propaga o erro real (ex: rate
            # limit da IA) em vez de deixar o chamador sem detalhe nenhum.
            errors = [q["error"] for q in queries if q.get("error")]
            result["error"] = errors[0] if errors else "Falha ao gerar queries com IA."
        return result

    async def rebuild_probe_query(self, fields: dict[str, list[str]], api: str = "ops") -> dict[str, Any]:
        """
        Reconstrói a CQL a partir de campos estruturados editados pelo
        usuário, sem chamar a LLM (síncrono e determinístico).
        """
        if api != "ops":
            return {"success": False, "error": f"Structured rebuild ainda não suportado para api='{api}'"}
        try:
            from services.query_builders.ops_query_builder import OPSQueryBuilder

            year_from = getattr(self.settings, "search_year_from", 2015)
            year_to = getattr(self.settings, "search_year_to", 2026)

            llm_output = self._query_fields_to_llm_output(fields)
            builder = OPSQueryBuilder(api_name="ops", search_mode="probe")
            query = builder.build_query(
                llm_output=llm_output,
                year_from=year_from,
                year_to=year_to,
            )
            complexity = self._complexity_from_query(query.get("query", ""))
            return {
                "success": True,
                "api": api,
                "query": query,
                "fields": fields,
                "complexity": complexity,
                "year_range": {"from": year_from, "to": year_to},
            }
        except Exception as exc:
            logger.error("rebuild_probe_query_error", api=api, error=str(exc))
            return {"success": False, "error": str(exc)}

    async def build_final_query(self, intake: Any, api: str) -> dict[str, Any]:
        try:
            return await self._build_query_with_retry(
                intake=intake,
                api=api,
                search_mode="final",
                prompt_loader_method="load_probe_system_prompt",
            )
        except Exception as exc:
            logger.error("build_final_query_error", error=str(exc))
            return {"success": False, "error": str(exc)}

    _VARIANT_INSTRUCTIONS: dict[str, str] = {
        "specific": (
            "Build a FOCUSED, HIGH-PRECISION query. "
            "Use only the highest-scoring extracted terms. "
            "Combine core concepts with AND. Limit OR groups to 3–4 terms."
        ),
        "balanced": (
            "Build a BALANCED query with good recall and precision. "
            "Use mid-range scoring extracted terms. "
            "Allow broader OR groups (4–6 terms). Limit AND combinations to 1–2."
        ),
        "generic": (
            "Build a BROAD, HIGH-RECALL query. "
            "Include all extracted terms above the score threshold. "
            "Minimize AND operators. Maximize coverage."
        ),
    }

    def _variant_instructions_block(self, variant: str, api: str) -> str:
        doc_type = "PATENT" if api in ("ops", "lens_patent") else "SCHOLARLY"
        return (
            f"\n\n## DOCUMENT TYPE\n\n{doc_type}\n\n"
            f"## SEARCH VARIANT: {variant.upper()}\n\n"
            f"{self._VARIANT_INSTRUCTIONS.get(variant, '')}\n"
        )

    def _terms_context_suffix(
        self,
        extracted_terms: list[dict[str, Any]],
        variant: str,
        api: str,
    ) -> str:
        thresholds = {"specific": 0.4, "balanced": 0.3, "generic": 0.2}
        threshold = thresholds.get(variant, 0.3)
        terms = [t for t in extracted_terms if t.get("score", 0) > threshold]

        terms_str = (
            "\n".join(
                f"- {t.get('term', '')} (score: {t.get('score', 0):.3f}, freq: {t.get('frequency', 0)})"
                for t in terms[:20]
            )
            if terms
            else "- None available"
        )

        return (
            f"{self._variant_instructions_block(variant, api)}\n"
            f"## EXTRACTED TERMS (score > {threshold})\n\n"
            f"{terms_str}\n"
        )

    async def _build_final_variant_query(
        self,
        intake: Any,
        api: str,
        extracted_terms: list[dict[str, Any]],
        variant: str,
    ) -> dict[str, Any]:
        from services.prompt.prompt_loader import PromptLoader

        max_complexity = getattr(self.settings, "llm_max_query_complexity", 0.6)
        max_score = max_complexity * 100
        max_attempts = 3
        attempts_history: list[dict] = []
        complexity: Optional[dict] = None

        llm_request = self._intake_to_request(intake)
        qb = _get_qb_adapter(api, search_mode="final")
        context_suffix = self._terms_context_suffix(extracted_terms, variant, api)

        for attempt in range(1, max_attempts + 1):
            base_prompt = PromptLoader.load_prompt("final_system_prompt.md")
            system_prompt = base_prompt + context_suffix
            if attempt > 1:
                system_prompt += self._simplification_suffix(complexity, attempt)

            llm_response = await self.llm.process_intake(llm_request, system_prompt)

            query = qb.build_query(
                strategy=llm_response,
                year_from=getattr(self.settings, "search_year_from", 2015),
                year_to=getattr(self.settings, "search_year_to", 2026),
                search_mode="final",
            )

            cql_query = query.get("query", "")
            complexity = self._complexity_from_query(cql_query)
            passed = complexity["score"] <= max_score

            attempts_history.append({"attempt": attempt, "query": query, "complexity": complexity})

            logger.info(
                "final_variant_complexity_check",
                api=api,
                variant=variant,
                attempt=attempt,
                score=complexity["score"],
                max_score=max_score,
                passed=passed,
            )

            if passed:
                return {
                    "success": True,
                    "query": query,
                    "complexity": complexity,
                    "attempt": attempt,
                }

        best = min(attempts_history, key=lambda x: x["complexity"]["score"])
        logger.warning(
            "final_variant_complexity_exceeded",
            api=api,
            variant=variant,
            best_attempt=best["attempt"],
            best_score=best["complexity"]["score"],
        )
        return {
            "success": True,
            "query": best["query"],
            "complexity": best["complexity"],
            "attempt": best["attempt"],
            "warning": (
                f"Query complexity ({best['complexity']['score']:.1f}/100) exceeds limit "
                f"({max_score:.0f}) after {max_attempts} attempts. "
                f"Returning least complex attempt."
            ),
        }

    async def build_final_queries_multi(
        self,
        intake: Any,
        extracted_terms: list[dict[str, Any]],
        api: str,
    ) -> dict[str, Any]:
        thresholds = {"specific": 0.4, "balanced": 0.3, "generic": 0.2}
        results: dict[str, Any] = {
            "success": True,
            "api": api,
            "user_input": intake.model_dump(),
            "extracted_terms_summary": {
                "total": len(extracted_terms),
                "high_score": len([t for t in extracted_terms if t.get("score", 0) > thresholds["specific"]]),
                "mid_score": len([t for t in extracted_terms if t.get("score", 0) > thresholds["balanced"]]),
                "all_score": len([t for t in extracted_terms if t.get("score", 0) > thresholds["generic"]]),
            },
            "queries": {},
        }

        for variant in ("specific", "balanced", "generic"):
            try:
                results["queries"][variant] = await self._build_final_variant_query(
                    intake=intake,
                    api=api,
                    extracted_terms=extracted_terms,
                    variant=variant,
                )
            except Exception as exc:
                logger.error(
                    "build_final_queries_multi_variant_error",
                    variant=variant,
                    api=api,
                    error=str(exc),
                )
                results["queries"][variant] = {"success": False, "error": str(exc)}

        return results

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def run_probe_search(
        self,
        query: dict[str, Any],
        api: str,
        top_k: int = 10,
    ) -> dict[str, Any]:
        adapter = self._find_search_adapter(api)
        if adapter is None:
            return {"success": False, "api": api, "error": f"API '{api}' not enabled or not found"}

        effective_top_k = min(top_k + 5, 100)
        try:
            if api == "ops" and hasattr(adapter, "search_with_biblio"):
                result = await adapter.search_with_biblio(query, top_k=effective_top_k)
            else:
                result = await adapter.search(query)
            items = result.results[:effective_top_k] if result.success else []
            return {
                "success": result.success,
                "api": api,
                "results_count": len(items),
                "total_available": result.total_count,
                "results": items,
                "error": result.error_message if not result.success else None,
            }
        except Exception as exc:
            logger.error("run_probe_search_error", api=api, error=str(exc))
            return {"success": False, "api": api, "error": str(exc)}

    async def run_final_search(
        self,
        query: dict[str, Any],
        api: str,
        max_results: int = 500,
    ) -> dict[str, Any]:
        adapter = self._find_search_adapter(api)
        if adapter is None:
            return {"success": False, "api": api, "error": f"API '{api}' not enabled or not found"}

        try:
            if api == "ops" and hasattr(adapter, "search_with_biblio"):
                result = await adapter.search_with_biblio(query, top_k=min(max_results, 100))
            else:
                result = await adapter.search(query)
            items = result.results[:max_results] if result.success else []
            return {
                "success": result.success,
                "api": api,
                "results_count": len(items),
                "total_available": result.total_count,
                "results": items,
                "error": result.error_message if not result.success else None,
            }
        except Exception as exc:
            logger.error("run_final_search_error", api=api, error=str(exc))
            return {"success": False, "api": api, "error": str(exc)}

    # ------------------------------------------------------------------
    # NLP
    # ------------------------------------------------------------------

    async def extract_terms(
        self,
        items: list[dict[str, Any]],
        original_params: Optional[dict[str, Any]] = None,
        top_k: int = 20,
    ) -> dict[str, Any]:
        from services.nlp.term_extraction import TermExtractor

        if not items:
            return {"success": False, "error": "No items provided"}

        valid = [
            item for item in items
            if (item.get("title") or "").strip() or (item.get("abstract") or "").strip()
        ]
        if not valid:
            return {"success": False, "error": "No items with non-empty title or abstract"}

        enriched = [
            {
                "biblio": {
                    "invention_title": (item.get("title") or "").strip(),
                    "title": (item.get("title") or "").strip(),
                    "abstract": (item.get("abstract") or "").strip(),
                },
                "publication_number": f"item_{idx}",
            }
            for idx, item in enumerate(valid)
        ]

        try:
            extractor = TermExtractor()
            terms = extractor.extract_and_rank_terms(
                original_params=original_params or {},
                enriched_results=enriched,
                top_k=top_k,
            )
            return {"success": True, "terms": terms, "count": len(terms)}
        except Exception as exc:
            logger.error("extract_terms_error", error=str(exc))
            return {"success": False, "error": str(exc)}
