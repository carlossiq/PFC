from __future__ import annotations

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

    async def _build_query_with_retry(
        self,
        intake: Any,
        api: str,
        search_mode: str,
        prompt_loader_method: str,
    ) -> dict[str, Any]:
        """
        Chama LLM → QueryBuilder → QueryComplexityAnalyzer em loop de até 3 tentativas.
        Na falha de complexidade, injeta as métricas no system_prompt para retry.
        """
        from services.prompt.prompt_loader import PromptLoader

        max_complexity = getattr(self.settings, "llm_max_query_complexity", 0.6)
        max_score = max_complexity * 100
        max_attempts = 3
        attempts_history: list[dict] = []
        complexity: Optional[dict] = None

        llm_request = self._intake_to_request(intake)
        qb = _get_qb_adapter(api, search_mode)

        for attempt in range(1, max_attempts + 1):
            base_prompt = getattr(PromptLoader, prompt_loader_method)()
            system_prompt = base_prompt if attempt == 1 else base_prompt + self._simplification_suffix(complexity, attempt)

            llm_response = await self.llm.process_intake(llm_request, system_prompt)

            query = qb.build_query(
                strategy=llm_response,
                year_from=getattr(self.settings, "search_year_from", 2015),
                year_to=getattr(self.settings, "search_year_to", 2026),
                search_mode=search_mode,
            )

            cql_query = query.get("query", "")
            complexity = self._complexity_from_query(cql_query)
            passed = complexity["score"] <= max_score

            attempts_history.append({"attempt": attempt, "query": query, "complexity": complexity})

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

    async def generate_candidate_topics(self, intake: Any) -> dict[str, Any]:
        from services.prompt.prompt_loader import PromptLoader

        user_provided = {
            "theme": True,
            "description": intake.description is not None,
            "area_of_study": intake.area_of_study is not None,
            "keywords": intake.keywords is not None,
        }

        user_input = f"Tema: {intake.theme}"
        if intake.description:
            user_input += f"\nDescrição: {intake.description}"
        if intake.area_of_study:
            user_input += f"\nÁrea de Estudo: {intake.area_of_study}"
        if intake.keywords:
            user_input += f"\nPalavras-chave: {', '.join(intake.keywords)}"

        user_input += "\n\nCampos fornecidos pelo usuário (retorne APENAS estes):\n"
        user_input += "- theme: SIM (sempre refine em 4 variações)\n"
        if user_provided["description"]:
            user_input += "- description: SIM (gere descrições para cada variação)\n"
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
            if user_provided["description"] and candidate.get("description"):
                item["description"] = candidate["description"]
            if user_provided["area_of_study"]:
                item["area_of_study"] = intake.area_of_study
            if user_provided["keywords"]:
                item["keywords"] = intake.keywords
            item["user_input"] = intake.model_dump()
            processed.append(item)

        return {"success": True, "candidates": processed}

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

    async def build_final_queries_multi(
        self,
        intake: Any,
        extracted_terms: list[dict[str, Any]],
        api: str,
    ) -> dict[str, Any]:
        from services.prompt.prompt_loader import PromptLoader

        max_score = getattr(self.settings, "llm_max_query_complexity", 0.6) * 100

        top_specific = [t for t in extracted_terms if t.get("score", 0) > 0.4]
        top_balanced = [t for t in extracted_terms if t.get("score", 0) > 0.3]
        top_generic = [t for t in extracted_terms if t.get("score", 0) > 0.2]

        def _fmt(terms: list[dict]) -> str:
            if not terms:
                return "- None available"
            return "\n".join(
                f"- {t.get('term', '')} (score: {t.get('score', 0):.3f}, freq: {t.get('frequency', 0)})"
                for t in terms[:20]
            )

        system_prompt = PromptLoader.load_prompt("final_system_prompt.md")
        user_message = (
            f"Generate THREE search query variations for {api.upper()} database:\n\n"
            f"## Original Search Parameters\n"
            f"- Theme: {intake.theme}\n"
            f"- Description: {intake.description}\n"
            f"- Area of Study: {intake.area_of_study}\n"
            f"- Keywords: {', '.join(intake.keywords) if intake.keywords else 'None'}\n\n"
            f"## Extracted Relevant Terms\n\n"
            f"### High-Scoring Terms (score > 0.4) - For SPECIFIC query:\n{_fmt(top_specific)}\n\n"
            f"### Mid-Scoring Terms (score > 0.3) - For BALANCED query:\n{_fmt(top_balanced)}\n\n"
            f"### All Relevant Terms (score > 0.2) - For GENERIC query:\n{_fmt(top_generic)}\n\n"
            f"## Requirements\n"
            f"- All queries must have complexity score < {max_score:.0f}\n"
            f"- Prefer extracted terms over original parameters when synonyms exist\n"
            f"- Use ABSTRACT OR TITLE as primary search fields\n"
            f"- Return JSON with keys: specific, balanced, generic\n\n"
            f"Target API: {api}\n"
            f"Query Syntax: {'CQL' if api == 'ops' else 'Boolean'}\n"
        )

        try:
            queries_json = await self.llm.call_raw_json(system_prompt, user_message)
        except Exception as exc:
            logger.error("build_final_queries_multi_llm_error", error=str(exc))
            return {"success": False, "error": f"LLM call failed: {exc}"}

        results: dict[str, Any] = {
            "success": True,
            "api": api,
            "user_input": intake.model_dump(),
            "extracted_terms_summary": {
                "total": len(extracted_terms),
                "high_score": len(top_specific),
                "mid_score": len(top_balanced),
                "all_score": len(top_generic),
            },
            "queries": {},
        }

        for variant in ("specific", "balanced", "generic"):
            query_data = queries_json.get(variant, {})
            query_str = query_data.get("query", "")
            if not query_str:
                results["queries"][variant] = {"success": False, "error": f"No query for {variant}"}
                continue

            complexity = self._complexity_from_query(query_str)
            passed = complexity["score"] <= max_score

            entry: dict[str, Any] = {
                "success": passed or variant == "generic",
                "query": {"query": query_str, "format": "json"},
                "rationale": query_data.get("rationale", ""),
                "expected_precision": query_data.get("expected_precision", ""),
                "focus_areas": query_data.get("focus_areas", []),
                "complexity": {**complexity, "passed": passed},
            }
            if not passed and variant != "generic":
                entry["warning"] = (
                    f"Query complexity ({complexity['score']:.1f}/100) exceeds limit ({max_score:.0f}). "
                    f"Consider the GENERIC variant."
                )
            results["queries"][variant] = entry

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
