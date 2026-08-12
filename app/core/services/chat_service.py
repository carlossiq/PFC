from __future__ import annotations

import asyncio
import json
import random
import re
import time
from collections import Counter
from typing import Any, Optional

from app.core.domain.types import LLMRequest, LLMUsage
from app.core.services.query_complexity import QueryComplexityAnalyzer
from core.config import Settings
from core.logging import get_logger
from services.llm.base import LLMJSONParseError
from services.nlp.fuzzy_grouping import fuzzy_group_names

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
        openalex: Any = None,
    ) -> None:
        self.llm = llm
        self.patent_pairs = patent_pairs
        self.scholarly_pairs = scholarly_pairs
        self.settings = settings
        self.openalex = openalex

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

    @staticmethod
    def _aggregate_usage(usages: list[LLMUsage], step: str) -> Optional[dict[str, Any]]:
        """
        Agrega uma ou mais chamadas de LLM (ex: tentativas sequenciais de um
        mesmo _build_query_with_retry) num único ai_usage. Duração é somada
        porque as tentativas rodam sequencialmente (um await após o outro) -
        soma sequencial = tempo de parede real. Tokens são sempre somados
        (custo é aditivo, independe de paralelismo).
        """
        if not usages:
            return None

        def _sum_field(field: str) -> Optional[int]:
            values = [getattr(u, field) for u in usages if getattr(u, field) is not None]
            return sum(values) if values else None

        return {
            "step": step,
            "provider": usages[0].provider,
            "model": usages[0].model,
            "duration_ms": sum(u.duration_ms for u in usages),
            "input_tokens": _sum_field("input_tokens"),
            "output_tokens": _sum_field("output_tokens"),
            "total_tokens": _sum_field("total_tokens"),
            "attempts": len(usages),
        }

    @staticmethod
    def _aggregate_multi_usage(
        results: list[dict[str, Any]],
        step: str,
        duration_ms: float,
    ) -> Optional[dict[str, Any]]:
        """
        Agrega os ai_usage já calculados de N sub-chamadas independentes
        (ex: as N tentativas de build_probe_queries_multi, rodadas em
        paralelo via asyncio.gather, ou as 3 variantes sequenciais de
        build_final_queries_multi). Ao contrário de _aggregate_usage, a
        duração NÃO é derivada somando as sub-durações (isso superestimaria
        o tempo real quando as chamadas rodam em paralelo) - é medida
        diretamente pelo chamador ao redor do bloco inteiro (gather ou loop)
        e recebida aqui pronta. Tokens continuam sendo somados.
        """
        usages = [r["ai_usage"] for r in results if r.get("ai_usage")]
        if not usages:
            return None

        def _sum_field(field: str) -> Optional[int]:
            values = [u[field] for u in usages if u.get(field) is not None]
            return sum(values) if values else None

        return {
            "step": step,
            "provider": usages[0]["provider"],
            "model": usages[0]["model"],
            "duration_ms": duration_ms,
            "input_tokens": _sum_field("input_tokens"),
            "output_tokens": _sum_field("output_tokens"),
            "total_tokens": _sum_field("total_tokens"),
            "attempts": sum(u.get("attempts", 1) for u in usages),
        }

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

    # Instrui a LLM sobre quais campos preencher dependendo do tipo de
    # documento buscado (a mesma chamada de _build_query_with_retry é usada
    # tanto pra patentes quanto pra artigos - só muda o `api`). O prompt base
    # (probe_system_prompt.txt) é cross-domain por natureza, mas o exemplo de
    # saída dele só mostra campos de patente, então sem essa dica a LLM tende
    # a nunca preencher os campos relevantes pra artigos (authors, keywords,
    # field_of_study etc).
    _API_FIELD_HINTS: dict[str, str] = {
        "ops": (
            "This search targets PATENT documents. Populate TITLE, ABSTRACT, and "
            "IPC (technology classification) based on the theme. Leave other "
            "fields (CPC, APPLICANT, INVENTOR, AUTHORS, KEYWORDS, etc) empty "
            "unless explicitly mentioned in the input."
        ),
        "scopus": (
            "This search targets SCHOLARLY ARTICLES, not patents. Populate TITLE, "
            "ABSTRACT, and FIELD_OF_STUDY (subject area) based on the theme. Do "
            "NOT populate patent-only fields (IPC, CPC, APPLICANT, INVENTOR, "
            "CLAIMS). Leave AUTHORS, AFFILIATION, KEYWORDS, SOURCE_TITLE empty "
            "unless explicitly mentioned in the input."
        ),
    }

    def _api_field_hint(self, api: str) -> str:
        hint = self._API_FIELD_HINTS.get(api)
        if not hint:
            return ""
        return f"\n\n## RELEVANT FIELDS FOR THIS SEARCH\n\n{hint}\n"

    # Campos textuais no LLMResponse/LLMOutput (grupos AND/OR); todo o resto é
    # campo simples (lista de valores).
    _TEXTUAL_LLM_FIELDS = {"title", "abstract", "claims", "description", "full_text"}

    # Quais campos são relevantes pra edição/exibição na busca probe, por API
    # - patentes (ops) usam IPC como classificação ampla de tecnologia;
    # artigos (scopus) usam Field of Study como classificação ampla de área.
    # Os demais campos (cpc/applicant/inventor pra patente, authors/
    # affiliation/keywords/source_title pra artigo) são específicos demais
    # pra uma exploração inicial - ficam de fora daqui, mas continuam
    # disponíveis pra IA usar internamente se fizer sentido.
    _PROBE_FIELDS_BY_API: dict[str, list[str]] = {
        "ops": ["title", "abstract", "ipc", "year"],
        "scopus": ["title", "abstract", "field_of_study", "year"],
    }
    _DEFAULT_PROBE_FIELDS = ["title", "abstract", "year"]

    @staticmethod
    def _flatten_llm_response_fields(llm_response: Any, fields: list[str]) -> dict[str, list[str]]:
        """
        Achata um LLMResponse (domain, retornado por llm.process_intake) em
        {campo: [termos]} plano, só pros campos pedidos. Perde a
        granularidade de múltiplos grupos AND/OR entre grupos textuais —
        simplificação aceita para permitir edição estruturada simples no
        frontend (mesmo espírito do Step2 tratar keywords/studyArea como
        listas simples).
        """
        def flat(tq: Any) -> list[str]:
            seen: list[str] = []
            for g in tq.groups:
                for t in g.terms:
                    if t not in seen:
                        seen.append(t)
            return seen

        return {
            # llm_response aqui é o LLMResponse de domínio (app/core/domain/
            # types.py), não o schemas.llm.LLMOutput cru - o adapter
            # (_converters.py:output_to_response) já desembrulha os campos
            # simples de SimpleFieldQuery pra list[str] simples antes de
            # chegar aqui, então list(getattr(...)) já é o valor certo.
            name: (flat(getattr(llm_response, name)) if name in ChatService._TEXTUAL_LLM_FIELDS
                   else list(getattr(llm_response, name)))
            for name in fields
        }

    @staticmethod
    def _query_fields_to_llm_output(fields: dict[str, list[str]]) -> Any:
        """
        Reconstrói um schemas.llm.LLMOutput a partir dos campos estruturados
        simplificados editados pelo usuário (quaisquer que sejam - varia por
        API). Cada campo vira um único grupo OR (mesma simplificação de
        _flatten_llm_response_fields, no sentido inverso). Usado só pelo
        rebuild síncrono (sem LLM).
        """
        from schemas.llm import LLMOutput, SimpleFieldQuery, TermGroup, TextualFieldQuery

        def textual(values: Optional[list[str]]) -> TextualFieldQuery:
            clean = [v.strip() for v in (values or []) if isinstance(v, str) and v.strip()]
            if not clean:
                return TextualFieldQuery()
            return TextualFieldQuery(group_operator="OR", groups=[TermGroup(operator="OR", terms=clean)])

        def simple(values: Optional[list[str]]) -> SimpleFieldQuery:
            return SimpleFieldQuery(values=[v.strip() for v in (values or []) if isinstance(v, str) and v.strip()])

        kwargs = {
            name: (textual(values) if name in ChatService._TEXTUAL_LLM_FIELDS else simple(values))
            for name, values in fields.items()
        }
        return LLMOutput(**kwargs)

    async def _build_query_with_retry(
        self,
        intake: Any,
        api: str,
        search_mode: str,
        prompt_loader_method: str,
        step: str,
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
        usages: list[LLMUsage] = []

        year_from = getattr(self.settings, "search_year_from", 2015)
        year_to = getattr(self.settings, "search_year_to", 2026)
        year_range = {"from": year_from, "to": year_to}

        llm_request = self._intake_to_request(intake)
        qb = _get_qb_adapter(api, search_mode)

        probe_fields = self._PROBE_FIELDS_BY_API.get(api, self._DEFAULT_PROBE_FIELDS)

        for attempt in range(1, max_attempts + 1):
            base_prompt = getattr(PromptLoader, prompt_loader_method)()
            system_prompt = base_prompt + self._api_field_hint(api)
            if attempt > 1 and complexity is not None:
                system_prompt += self._simplification_suffix(complexity, attempt)

            try:
                llm_response, usage = await self.llm.process_intake(llm_request, system_prompt)
                usages.append(usage)
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
            fields = self._flatten_llm_response_fields(llm_response, probe_fields)

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
                    "ai_usage": self._aggregate_usage(usages, step),
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
                "ai_usage": self._aggregate_usage(usages, step),
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
            "ai_usage": self._aggregate_usage(usages, step),
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
    def _salvage_candidates(raw_response: str) -> list[dict[str, Any]]:
        """
        Recupera candidatos individualmente válidos de uma resposta JSON
        malformada (ex: quando só um dos 4 candidatos tem uma aspa não
        escapada no meio da description, quebrando o parse do array
        inteiro). Localiza o array "candidates" e extrai cada objeto
        top-level por contagem de chaves (não é sensível a strings, mas a
        corrupção típica de LLM é só de aspas dentro de texto livre, não de
        chaves desbalanceadas); cada objeto extraído é parseado sozinho e os
        que falharem são simplesmente descartados, em vez de derrubar a
        resposta inteira.
        """
        def parse_with_repair(obj_str: str) -> dict[str, Any]:
            try:
                return json.loads(obj_str)
            except json.JSONDecodeError:
                repaired = re.sub(r",\s*([}\]])", r"\1", obj_str)
                return json.loads(repaired)

        idx = raw_response.find('"candidates"')
        if idx == -1:
            return []
        array_start = raw_response.find("[", idx)
        if array_start == -1:
            return []

        candidates: list[dict[str, Any]] = []
        depth = 0
        obj_start: Optional[int] = None
        for i in range(array_start, len(raw_response)):
            ch = raw_response[i]
            if ch == "{":
                if depth == 0:
                    obj_start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and obj_start is not None:
                    obj_str = raw_response[obj_start : i + 1]
                    try:
                        candidates.append(parse_with_repair(obj_str))
                    except json.JSONDecodeError:
                        pass
                    obj_start = None
            elif ch == "]" and depth == 0:
                break

        return candidates

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

        usage: Optional[LLMUsage] = None
        try:
            raw, usage = await self.llm.call_raw_json(system_prompt, user_input)
        except LLMJSONParseError as exc:
            candidates = self._salvage_candidates(exc.raw_response)
            if not candidates:
                logger.error("generate_candidate_topics_llm_error", error=str(exc))
                return {
                    "success": False,
                    "error": "Não foi possível gerar variações do tema no momento. Tente novamente.",
                }
            logger.warning(
                "generate_candidate_topics_partial_recovery",
                recovered=len(candidates),
                error=str(exc),
            )
            raw = {"candidates": candidates}
        except Exception as exc:
            logger.error("generate_candidate_topics_llm_error", error=str(exc))
            return {
                "success": False,
                "error": "Não foi possível gerar variações do tema no momento. Tente novamente.",
            }

        candidates = raw.get("candidates", [])
        processed = []
        for candidate in candidates:
            if not candidate.get("theme"):
                continue
            item: dict[str, Any] = {"theme": candidate.get("theme")}
            if candidate.get("description"):
                item["description"] = candidate["description"]
            if user_provided["area_of_study"]:
                item["area_of_study"] = intake.area_of_study
            if user_provided["keywords"]:
                item["keywords"] = intake.keywords
            item["user_input"] = intake.model_dump()
            processed.append(item)

        if not processed:
            logger.error("generate_candidate_topics_no_valid_candidates", raw_response=raw)
            return {
                "success": False,
                "error": "Não foi possível gerar variações do tema no momento. Tente novamente.",
            }

        result: dict[str, Any] = {"success": True, "candidates": processed}
        if usage is not None:
            result["ai_usage"] = self._aggregate_usage([usage], step="refine_topic")
        if len(processed) < 4:
            result["warning"] = f"Apenas {len(processed)} de 4 variações puderam ser geradas."
        return result

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
            raw, usage = await self.llm.call_raw_json(system_prompt, user_input)
        except Exception as exc:
            logger.error("specify_topic_llm_error", error=str(exc))
            return {
                "success": False,
                "error": "Não foi possível especificar o tema no momento. Tente novamente.",
            }

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
        result["ai_usage"] = self._aggregate_usage([usage], step="specify_topic")

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
                    step="probe_query",
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
        # Medido com perf_counter ao redor do gather (não somando as durações
        # individuais de cada tentativa) porque elas rodam concorrentemente -
        # somar superestimaria o tempo de espera real do usuário.
        start = time.perf_counter()
        queries = await asyncio.gather(*(_attempt(i) for i in range(count)))
        duration_ms = (time.perf_counter() - start) * 1000
        success = any(q.get("success") for q in queries)

        result: dict[str, Any] = {
            "success": success,
            "api": api,
            "user_input": intake.model_dump(),
            "queries": queries,
            "ai_usage": self._aggregate_multi_usage(queries, step="probe_queries_multi", duration_ms=duration_ms),
        }
        if not success:
            # Nenhuma tentativa deu certo - propaga o erro real (ex: rate
            # limit da IA) em vez de deixar o chamador sem detalhe nenhum.
            errors = [q["error"] for q in queries if q.get("error")]
            result["error"] = errors[0] if errors else "Falha ao gerar queries com IA."
        return result

    @staticmethod
    def _get_raw_query_builder(api: str, search_mode: str) -> Any:
        """
        Dá o query builder "cru" (não o adapter) pra reconstrução síncrona
        (sem LLM) - diferente de _get_qb_adapter (módulo-level), que espera
        um LLMResponse (domain) e converte internamente; aqui já temos um
        LLMOutput (schema) pronto, então instanciamos o builder direto.
        """
        if api == "ops":
            from services.query_builders.ops_query_builder import OPSQueryBuilder
            return OPSQueryBuilder(api_name="ops", search_mode=search_mode)
        if api == "scopus":
            from services.query_builders.scopus_query_builder import ScopusQueryBuilder
            return ScopusQueryBuilder(api_name="scopus", search_mode=search_mode)
        raise ValueError(f"Rebuild não suportado para api='{api}'")

    async def _rebuild_query(
        self, fields: dict[str, list[str]], api: str, search_mode: str
    ) -> dict[str, Any]:
        """
        Reconstrói a query a partir de campos estruturados editados pelo
        usuário, sem chamar a LLM (síncrono e determinístico) - usado tanto
        pela edição de query probe quanto final (search_mode muda só o
        template usado pelo query builder).
        """
        try:
            year_from = getattr(self.settings, "search_year_from", 2015)
            year_to = getattr(self.settings, "search_year_to", 2026)

            llm_output = self._query_fields_to_llm_output(fields)
            builder = self._get_raw_query_builder(api, search_mode)
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
            logger.error(f"rebuild_{search_mode}_query_error", api=api, error=str(exc))
            return {"success": False, "error": str(exc)}

    async def rebuild_probe_query(self, fields: dict[str, list[str]], api: str = "ops") -> dict[str, Any]:
        return await self._rebuild_query(fields, api, "probe")

    async def rebuild_final_query(self, fields: dict[str, list[str]], api: str = "ops") -> dict[str, Any]:
        return await self._rebuild_query(fields, api, "final")

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
        step: str,
    ) -> dict[str, Any]:
        from services.prompt.prompt_loader import PromptLoader

        max_complexity = getattr(self.settings, "llm_max_query_complexity", 0.6)
        max_score = max_complexity * 100
        max_attempts = 2
        attempts_history: list[dict] = []
        complexity: Optional[dict] = None
        usages: list[LLMUsage] = []

        year_from = getattr(self.settings, "search_year_from", 2015)
        year_to = getattr(self.settings, "search_year_to", 2026)
        year_range = {"from": year_from, "to": year_to}

        llm_request = self._intake_to_request(intake)
        qb = _get_qb_adapter(api, search_mode="final")
        context_suffix = self._terms_context_suffix(extracted_terms, variant, api)
        probe_fields = self._PROBE_FIELDS_BY_API.get(api, self._DEFAULT_PROBE_FIELDS)

        for attempt in range(1, max_attempts + 1):
            base_prompt = PromptLoader.load_prompt("final_system_prompt.md")
            system_prompt = base_prompt + context_suffix
            if attempt > 1:
                system_prompt += self._simplification_suffix(complexity, attempt)

            llm_response, usage = await self.llm.process_intake(llm_request, system_prompt)
            usages.append(usage)

            query = qb.build_query(
                strategy=llm_response,
                year_from=year_from,
                year_to=year_to,
                search_mode="final",
            )

            cql_query = query.get("query", "")
            complexity = self._complexity_from_query(cql_query)
            passed = complexity["score"] <= max_score
            fields = self._flatten_llm_response_fields(llm_response, probe_fields)

            attempts_history.append(
                {"attempt": attempt, "query": query, "complexity": complexity, "fields": fields}
            )

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
                    "fields": fields,
                    "year_range": year_range,
                    "ai_usage": self._aggregate_usage(usages, step),
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
            "fields": best["fields"],
            "year_range": year_range,
            "ai_usage": self._aggregate_usage(usages, step),
            "warning": (
                f"Query complexity ({best['complexity']['score']:.1f}/100) exceeds limit "
                f"({max_score:.0f}) after {max_attempts} attempts. "
                f"Returning least complex attempt."
            ),
        }

    async def build_final_query_variant(
        self,
        intake: Any,
        extracted_terms: list[dict[str, Any]],
        variant: str,
        api: str,
    ) -> dict[str, Any]:
        try:
            return await self._build_final_variant_query(
                intake=intake,
                api=api,
                extracted_terms=extracted_terms,
                variant=variant,
                step="final_query",
            )
        except Exception as exc:
            logger.error("build_final_query_variant_error", variant=variant, api=api, error=str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def _enrich_scopus_abstracts(
        self,
        items: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        A Scopus Search API não devolve abstract (dc:description) pra essa
        API key - falta entitlement de Text Mining na Elsevier (ver
        notes/pendencias.md). Busca o abstract complementar no OpenAlex via
        DOI (prism:doi, público e sem key) e descarta os itens sem abstract
        disponível em nenhuma das duas fontes, ou com abstract em idioma
        diferente do inglês,
        priorizando qualidade sobre quantidade. Janela de candidatos com
        margem (3x top_k) porque nem todo DOI está indexado no OpenAlex ou
        tem abstract liberado pela editora (~70% de cobertura observada em
        teste manual).
        """
        from services.nlp.language_filter import is_non_english_abstract

        if not self.openalex or not items:
            return items[:top_k]

        candidate_window = items[: max(top_k * 3, top_k)]
        dois = [item["prism:doi"] for item in candidate_window if item.get("prism:doi")]
        openalex_data = await self.openalex.fetch_metadata_batch(dois)

        enriched: list[dict[str, Any]] = []
        discarded_non_english = 0
        for item in candidate_window:
            doi = item.get("prism:doi")
            meta = openalex_data.get(doi) if doi else None
            abstract = meta.get("abstract") if meta else None
            if not abstract:
                continue
            if is_non_english_abstract(abstract):
                discarded_non_english += 1
                continue
            enriched.append({
                **item,
                "dc:description": abstract,
                "openalex_field_of_study": meta.get("field_of_study") or [],
            })
            if len(enriched) >= top_k:
                break

        logger.info(
            "scopus_abstract_enrichment",
            candidates=len(candidate_window),
            with_abstract=len(enriched),
            discarded_non_english=discarded_non_english,
            requested=top_k,
        )
        return enriched

    # Faixas de anos (mais recente -> mais antiga) e o peso de cada uma na
    # amostra final - dá ênfase ao mais recente sem excluir o resto, evitando
    # que a probe (sem nenhum critério de relevância no OPS/Scopus - ver
    # notes/pendencias.md) venha inteira de uma janela estreita de tempo.
    # Compartilhado entre OPS e Scopus - é só matemática de faixa de ano, não
    # depende da sintaxe de query de nenhuma API específica.
    _YEAR_BUCKET_OFFSETS: list[tuple[int, int, float]] = [
        (1, 0, 0.4),  # últimos 2 anos
        (4, 2, 0.3),  # 3-5 anos atrás
        (7, 5, 0.3),  # 6-8 anos atrás
        (None, 8, 0.1),  # o resto (9+ anos atrás até year_from)
    ]

    # Limite por requisição da busca final do Scopus (ver
    # ScopusService._FINAL_SEARCH_PAGE_SIZE, mesmo valor duplicado aqui - o
    # OPS segue o mesmo padrão de repetir _OPS_PAGE_SIZE=100 como literal em
    # _run_ops_search_by_range/_run_ops_search_by_year em vez de importar).
    _SCOPUS_FINAL_PAGE_SIZE = 200

    @classmethod
    def _year_buckets(cls, year_from: int, year_to: int) -> list[tuple[int, int, float]]:
        """
        Recorta [year_from, year_to] em faixas com peso decrescente conforme
        a idade. Faixas que caem fora do range configurado são descartadas e
        os pesos das restantes são renormalizados pra somar 1.
        """
        raw = []
        for from_offset, to_offset, weight in cls._YEAR_BUCKET_OFFSETS:
            b_to = year_to - to_offset
            b_from = year_from if from_offset is None else year_to - from_offset
            raw.append((b_from, b_to, weight))

        valid = [
            (max(b_from, year_from), min(b_to, year_to), weight)
            for b_from, b_to, weight in raw
            if b_to >= year_from and b_from <= year_to
        ]
        valid = [(f, t, w) for f, t, w in valid if f <= t]

        total_weight = sum(w for _, _, w in valid)
        if not valid or total_weight <= 0:
            return [(year_from, year_to, 1.0)]

        return [(f, t, w / total_weight) for f, t, w in valid]

    @staticmethod
    def _bucket_quotas(buckets: list[tuple[int, int, float]], top_k: int) -> list[int]:
        """Converte os pesos das faixas em nº de itens, garantindo que a soma bata com top_k."""
        quotas = [max(1, round(top_k * weight)) for _, _, weight in buckets]
        quotas[0] += top_k - sum(quotas)
        quotas[0] = max(1, quotas[0])
        return quotas

    @staticmethod
    def _ops_replace_date_clause(cql_query: str, year_from: int, year_to: int) -> str:
        """Substitui a cláusula `(pd within "...")` da CQL original pelo intervalo da faixa."""
        new_clause = f'(pd within "{year_from}0101 {year_to}1231")'
        pattern = r'\(pd within "\d{8} \d{8}"\)'
        if re.search(pattern, cql_query):
            return re.sub(pattern, new_clause, cql_query)
        return f"{cql_query} AND {new_clause}" if cql_query else new_clause

    @staticmethod
    def _scopus_replace_date_clause(scopus_query: str, year_from: int, year_to: int) -> str:
        """Substitui a cláusula `(PUBYEAR > X AND PUBYEAR < Y)` da query original pelo intervalo da faixa (ver ScopusQueryBuilder._build_date_query)."""
        new_clause = f"(PUBYEAR > {year_from - 1} AND PUBYEAR < {year_to + 1})"
        pattern = r"\(PUBYEAR > \d+ AND PUBYEAR < \d+\)"
        if re.search(pattern, scopus_query):
            return re.sub(pattern, new_clause, scopus_query)
        return f"{scopus_query} AND {new_clause}" if scopus_query else new_clause

    async def _run_ops_year_diversified_search(
        self,
        adapter: Any,
        query: dict[str, Any],
        top_k: int,
        fetch_cap: int = 100,
    ) -> tuple[list[dict[str, Any]], Optional[int]]:
        """
        O OPS não tem nenhum critério de relevância/ordenação na busca (ver
        notes/pendencias.md) - por padrão devolve sempre os mais recentes, o
        que pode enviesar a probe inteira pra uma janela de tempo estreita
        quando o tema tem muita atividade recente. Busca por faixa de ano
        (mais cota pras faixas recentes) e sorteia uma amostra dentro de
        cada faixa, em vez de pegar sempre os N mais recentes de cada uma.
        Descarta itens com abstract em idioma diferente do inglês antes de
        sortear a amostra de cada faixa (ver services/nlp/language_filter.py).

        fetch_cap: teto de itens buscados por faixa (antes do filtro de
            idioma) - o padrão (100) preserva o comportamento de sempre pra
            probe (run_probe_search, top_k baixo, nunca bate nesse teto).
            run_final_search passa um valor maior, já que busca faixas bem
            maiores (até 250) e o OPS agora pagina internamente além de 100
            por requisição (ver OPSService.search_with_abstracts).
        """
        from services.nlp.language_filter import filter_english_abstracts

        cql_query = query.get("query", "")
        year_from = getattr(self.settings, "search_year_from", 2015)
        year_to = getattr(self.settings, "search_year_to", 2026)

        buckets = self._year_buckets(year_from, year_to)
        quotas = self._bucket_quotas(buckets, top_k)

        collected: list[dict[str, Any]] = []
        total_available = 0

        for (b_from, b_to, _weight), quota in zip(buckets, quotas):
            bucket_query = {**query, "query": self._ops_replace_date_clause(cql_query, b_from, b_to)}
            fetch_n = min(max(quota * 3, quota), fetch_cap)
            try:
                result = await adapter.search_with_biblio(bucket_query, top_k=fetch_n)
            except Exception as exc:
                logger.warning(
                    "ops_year_bucket_search_failed",
                    year_from=b_from,
                    year_to=b_to,
                    error=str(exc),
                )
                continue

            if not result.success:
                continue

            total_available += result.total_count or 0
            candidates = filter_english_abstracts(result.results)
            collected.extend(random.sample(candidates, min(quota, len(candidates))))

        logger.info(
            "ops_year_diversified_search",
            buckets=[(f, t) for f, t, _ in buckets],
            quotas=quotas,
            collected=len(collected),
            requested=top_k,
        )
        return collected, (total_available or None)

    async def _run_scopus_year_diversified_search(
        self,
        adapter: Any,
        query: dict[str, Any],
        top_k: int,
        fetch_cap: int = 100,
    ) -> tuple[list[dict[str, Any]], Optional[int]]:
        """
        Mesma ideia de _run_ops_year_diversified_search, mas pro Scopus: a
        ordenação default da API não tem nenhum critério de relevância
        explícito, então um tema com muita atividade recente pode vir com a
        probe inteira concentrada num único ano. Busca por faixa de ano
        (PUBYEAR) e enriquece (abstract via OpenAlex + filtro de idioma)
        cada faixa separadamente, respeitando a cota de cada uma - não dá
        pra combinar todas as faixas antes de enriquecer, porque o corte por
        top_k do enriquecimento poderia descartar as faixas mais antigas só
        por ordem de chegada na lista combinada.

        fetch_cap: teto de itens buscados por faixa (antes do enriquecimento/
            filtro) - o padrão (100) preserva o comportamento de sempre pra
            probe (run_probe_search). run_final_search passa um valor maior,
            já que o enriquecimento via OpenAlex descarta boa parte dos itens
            (sem abstract disponível ou não-inglês) e precisa de mais margem
            bruta por faixa pra sobrar perto da cota pedida.
        """
        scopus_query = query.get("query", "")
        year_from = getattr(self.settings, "search_year_from", 2015)
        year_to = getattr(self.settings, "search_year_to", 2026)

        buckets = self._year_buckets(year_from, year_to)
        quotas = self._bucket_quotas(buckets, top_k)

        collected: list[dict[str, Any]] = []
        total_available = 0

        for (b_from, b_to, _weight), quota in zip(buckets, quotas):
            bucket_query = {**query, "query": self._scopus_replace_date_clause(scopus_query, b_from, b_to)}
            fetch_n = min(max(quota * 3, quota), fetch_cap)
            try:
                result = await adapter.search(bucket_query, max_results=fetch_n)
            except Exception as exc:
                logger.warning(
                    "scopus_year_bucket_search_failed",
                    year_from=b_from,
                    year_to=b_to,
                    error=str(exc),
                )
                continue

            if not result.success:
                continue

            total_available += result.total_count or 0
            collected.extend(await self._enrich_scopus_abstracts(result.results, top_k=quota))

        logger.info(
            "scopus_year_diversified_search",
            buckets=[(f, t) for f, t, _ in buckets],
            quotas=quotas,
            collected=len(collected),
            requested=top_k,
        )
        return collected, (total_available or None)

    def _aggregate_scopus_final_items(
        self,
        items: list[dict[str, Any]],
    ) -> tuple[dict[str, int], list[str]]:
        """
        Agrega os itens enxutos (title/institutions/year - ver
        services.search.scopus_service._extract_final_fields) coletados por
        _run_scopus_final_search em institutions/title. Compartilhado pelas
        duas estratégias (range e ano) - só muda de onde `items` veio.
        Equivalente a _aggregate_ops_final_items, mas sem CPC: a área de
        estudo do Scopus não é extraída item-a-item (a API não expõe
        subject-area por item nessa key), é contada à parte por
        _run_scopus_area_of_study_counts.
        """
        institutions: Counter = Counter()
        title: list[str] = []
        for item in items:
            institutions.update(item.get("institutions") or [])
            if item.get("title"):
                title.append(item["title"])
        return self._fuzzy_group_institutions(dict(institutions)), title

    async def _run_scopus_search_by_range(
        self,
        adapter: Any,
        query: dict[str, Any],
        max_requests: int,
        year_from: int,
        year_to: int,
        run_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Pagina a query inteira em janelas sequenciais de
        _SCOPUS_FINAL_PAGE_SIZE (200) - 0-200, 200-400, ... - até
        max_requests requisições ou até a API devolver menos que uma página
        cheia (sinal de que não há mais resultados). Equivalente a
        _run_ops_search_by_range, mas a data é aplicada uma vez só antes do
        loop (a Scopus não tem um parâmetro `year_range` separado do corpo
        da query, como o fetch_biblio_page da OPS).
        """
        range_query = {
            **query,
            "query": self._scopus_replace_date_clause(query.get("query", ""), year_from, year_to),
        }
        collected: list[dict[str, Any]] = []
        for page_idx in range(max_requests):
            start = page_idx * self._SCOPUS_FINAL_PAGE_SIZE
            result = await adapter.fetch_results_page(
                range_query, start=start, count=self._SCOPUS_FINAL_PAGE_SIZE, run_id=run_id
            )
            if not result.success:
                logger.warning("scopus_final_range_page_failed", start=start, error=result.error_message)
                continue
            collected.extend(result.results)
            if len(result.results) < self._SCOPUS_FINAL_PAGE_SIZE:
                break
        return collected

    async def _run_scopus_search_by_year(
        self,
        adapter: Any,
        query: dict[str, Any],
        year_from: int,
        year_to: int,
        run_id: Optional[str] = None,
        iteration: int = 0,
    ) -> tuple[list[dict[str, Any]], dict[int, int]]:
        """
        Uma requisição por ano cobrindo todo o intervalo pedido - usado
        quando o volume total de resultados é grande demais pra caber num
        nº de páginas menor que o nº de anos (ver _run_scopus_final_search),
        garantindo cobertura de todo o intervalo em vez de só dos itens mais
        recentes. Equivalente a _run_ops_search_by_year.

        `iteration` seleciona QUAL bloco de _SCOPUS_FINAL_PAGE_SIZE (200)
        buscar por ano (0 = 0-200, default; 1 = 200-400; ...) - não é
        cumulativo, cada chamada busca só esse bloco (ver docstring de
        run_final_search pro raciocínio completo). O total-result-count de
        cada resposta já é a contagem exata de artigos daquele ano (igual em
        qualquer iteração), então é devolvido separado dos itens em si (a
        amostra de itens continua limitada a _SCOPUS_FINAL_PAGE_SIZE/ano/
        iteração).
        """
        collected: list[dict[str, Any]] = []
        articles_by_year: dict[int, int] = {}
        scopus_query = query.get("query", "")
        start = iteration * self._SCOPUS_FINAL_PAGE_SIZE
        for year in range(year_from, year_to + 1):
            year_query = {**query, "query": self._scopus_replace_date_clause(scopus_query, year, year)}
            result = await adapter.fetch_results_page(
                year_query, start=start, count=self._SCOPUS_FINAL_PAGE_SIZE, run_id=run_id
            )
            if not result.success:
                logger.warning("scopus_final_year_page_failed", year=year, error=result.error_message)
                continue
            collected.extend(result.results)
            articles_by_year[year] = result.total_count or 0
        return collected, articles_by_year

    async def _run_scopus_area_of_study_counts(
        self,
        adapter: Any,
        query: dict[str, Any],
        year_from: int,
        year_to: int,
        run_id: Optional[str] = None,
    ) -> dict[str, int]:
        """
        Conta documentos por área de estudo ASJC (as 27 áreas maiores da
        Scopus - ver ASJC_SUBJECT_AREAS) via uma requisição count=1 por área
        (query original AND SUBJAREA(CODE)) - diferente do CPC do OPS
        (extraído dos itens já buscados), a Scopus não expõe subject-area
        por item nessa API key, então a única forma confiável de contar por
        área é filtrar a busca inteira por SUBJAREA. As 27 requisições
        rodam concorrentemente (asyncio.gather) - independentes entre si,
        sem motivo pra serializar.

        Chaves do resultado são o NOME completo da área
        (ASJC_SUBJECT_AREAS[code]), não a sigla; áreas sem nenhum resultado
        são omitidas (mesmo padrão de cpc/depositants, que só trazem
        valores presentes).
        """
        from services.query_builders.constants.scopus_subject_areas import ASJC_SUBJECT_AREAS

        base_query = self._scopus_replace_date_clause(query.get("query", ""), year_from, year_to)

        async def _count_area(code: str) -> tuple[str, int]:
            area_query = {**query, "query": f"{base_query} AND SUBJAREA({code})"}
            result = await adapter.count(area_query, run_id)
            total = result.total_count if result.success and result.total_count else 0
            return code, total

        counts = await asyncio.gather(*(_count_area(code) for code in ASJC_SUBJECT_AREAS))
        return {ASJC_SUBJECT_AREAS[code]: total for code, total in counts if total > 0}

    async def _run_scopus_final_search(
        self,
        adapter: Any,
        query: dict[str, Any],
        year_from: int,
        year_to: int,
        run_id: Optional[str] = None,
        iteration: int = 0,
    ) -> dict[str, Any]:
        """
        Equivalente a _run_ops_final_search, pro Scopus: descobre o total de
        resultados via uma requisição count=1 (ScopusService.count) e
        escolhe entre paginar por range ou por ano - mesmo critério (menos
        requisições vence). área de estudo é sempre calculada (independente
        da estratégia escolhida e de `iteration` - ver
        _run_scopus_area_of_study_counts), já que vem de requisições
        próprias (contagens exatas por SUBJAREA), não dos itens buscados.

        `iteration` (ver docstring de run_final_search) só afeta a
        estratégia por ano - repassado pra _run_scopus_search_by_year, que
        seleciona qual bloco de _SCOPUS_FINAL_PAGE_SIZE buscar por ano. A
        decisão range-vs-ano (`threshold` abaixo) usa sempre o page_size
        base, independente de `iteration`: range já é exaustiva, então
        `iteration` não muda nada nela.

        Returns:
            Dict com institutions, area_of_study, title, articles_by_year,
            strategy ("range" ou "year") e total_count - o compilado
            retornado por run_final_search para api="scopus".
        """
        count_query = {
            **query,
            "query": self._scopus_replace_date_clause(query.get("query", ""), year_from, year_to),
        }
        count_result = await adapter.count(count_query, run_id)
        total_count = count_result.total_count if count_result.success else None

        area_of_study = await self._run_scopus_area_of_study_counts(adapter, query, year_from, year_to, run_id)

        n_years = year_to - year_from + 1

        if total_count is None:
            logger.warning("scopus_final_total_count_unavailable")
            # Caso degradado (contagem indisponível) - sem base pra decidir
            # estratégia, então sempre busca a página 1 (iteration
            # deliberadamente ignorado aqui, ver docstring).
            items = await self._run_scopus_search_by_range(
                adapter, query, max_requests=1, year_from=year_from, year_to=year_to, run_id=run_id
            )
            institutions, title = self._aggregate_scopus_final_items(items)
            return {
                "institutions": institutions,
                "area_of_study": area_of_study,
                "title": title,
                "articles_by_year": {},
                "strategy": "range",
                "total_count": None,
            }

        threshold = n_years * self._SCOPUS_FINAL_PAGE_SIZE - (self._SCOPUS_FINAL_PAGE_SIZE - 1)
        if total_count < threshold:
            max_requests = (total_count + self._SCOPUS_FINAL_PAGE_SIZE - 1) // self._SCOPUS_FINAL_PAGE_SIZE
            items = await self._run_scopus_search_by_range(adapter, query, max_requests, year_from, year_to, run_id)
            institutions, title = self._aggregate_scopus_final_items(items)
            articles_by_year = dict(Counter(item["year"] for item in items if item.get("year") is not None))
            strategy = "range"
        else:
            items, articles_by_year = await self._run_scopus_search_by_year(
                adapter, query, year_from, year_to, run_id, iteration=iteration
            )
            institutions, title = self._aggregate_scopus_final_items(items)
            strategy = "year"

        return {
            "institutions": institutions,
            "area_of_study": area_of_study,
            "title": title,
            "articles_by_year": articles_by_year,
            "strategy": strategy,
            "total_count": total_count,
        }

    async def _run_ops_search_by_range(
        self,
        adapter: Any,
        query: dict[str, Any],
        max_requests: int,
        year_from: int,
        year_to: int,
        run_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Pagina a query inteira em janelas sequenciais de 100 - 1-100, 101-200,
        ... - até max_requests requisições ou até a API devolver menos que
        uma página cheia (sinal de que não há mais resultados). year_from/
        year_to são sempre repassados como year_range explícito (em vez de
        None, como antes) pra garantir que a busca usa o intervalo pedido na
        rota, não o que ficou embutido na query no momento em que ela foi
        gerada.
        """
        collected: list[dict[str, Any]] = []
        for page_idx in range(max_requests):
            start = page_idx * 100 + 1
            result = await adapter.fetch_biblio_page(
                query, start=start, page_size=100, year_range=(year_from, year_to), run_id=run_id
            )
            if not result.success:
                logger.warning(
                    "ops_final_range_page_failed", start=start, error=result.error_message
                )
                continue
            collected.extend(result.results)
            if len(result.results) < 100:
                break
        return collected

    async def _run_ops_search_by_year(
        self,
        adapter: Any,
        query: dict[str, Any],
        year_from: int,
        year_to: int,
        run_id: Optional[str] = None,
        iteration: int = 0,
    ) -> tuple[list[dict[str, Any]], dict[int, int]]:
        """
        Uma requisição por ano cobrindo todo o intervalo pedido - usado
        quando o volume total de resultados é grande demais pra caber num
        nº de páginas menor que o nº de anos (ver _run_ops_final_search),
        garantindo cobertura de todo o intervalo em vez de só dos itens mais
        recentes.

        `iteration` seleciona QUAL bloco de 100 buscar por ano (0 = 1-100,
        default; 1 = 101-200; ...) - não é cumulativo, cada chamada busca só
        esse bloco (ver docstring de run_final_search pro raciocínio
        completo). O total-result-count de cada resposta já é a contagem
        exata de patentes daquele ano (igual em qualquer iteração), então é
        devolvido separado dos itens em si (a amostra de itens continua
        limitada a 100/ano/iteração, usada só pra agregar
        depositants/cpc/title).
        """
        collected: list[dict[str, Any]] = []
        patents_by_year: dict[int, int] = {}
        start = iteration * 100 + 1
        for year in range(year_from, year_to + 1):
            result = await adapter.fetch_biblio_page(
                query, start=start, page_size=100, year_range=(year, year), run_id=run_id
            )
            if not result.success:
                logger.warning("ops_final_year_page_failed", year=year, error=result.error_message)
                continue
            collected.extend(result.results)
            patents_by_year[year] = result.total_count or 0
        return collected, patents_by_year

    def _fuzzy_group_depositants(self, counts: dict[str, int]) -> dict[str, int]:
        """Depositantes de patente (OPS) - ver
        services.nlp.fuzzy_grouping.fuzzy_group_names. threshold vem de
        settings.depositant_fuzzy_match_threshold (configurável, nunca
        hardcoded aqui) - ver core/config.py."""
        threshold = getattr(self.settings, "depositant_fuzzy_match_threshold", 90.0)
        return fuzzy_group_names(counts, threshold)

    def _fuzzy_group_institutions(self, counts: dict[str, int]) -> dict[str, int]:
        """Instituições de artigo (Scopus) - ver
        services.nlp.fuzzy_grouping.fuzzy_group_names. Reusa o mesmo
        settings.depositant_fuzzy_match_threshold de
        _fuzzy_group_depositants (mesma natureza de problema - ver
        core/config.py)."""
        threshold = getattr(self.settings, "depositant_fuzzy_match_threshold", 90.0)
        return fuzzy_group_names(counts, threshold)

    def _aggregate_ops_final_items(
        self,
        items: list[dict[str, Any]],
    ) -> tuple[dict[str, int], dict[str, int], list[str]]:
        """
        Agrega os itens enxutos (title/applicants/cpc/year - ver
        OPSService._extract_final_fields) coletados por _run_ops_final_search
        em depositants/cpc/title. Compartilhado pelas duas estratégias
        (range e ano) - só muda de onde `items` veio.
        """
        depositants: Counter = Counter()
        cpc: Counter = Counter()
        title: list[str] = []
        for item in items:
            depositants.update(item.get("applicants") or [])
            # Agrupa pelos 4 primeiros caracteres (a classe CPC, ex. "B64G"
            # em "B64G 1/2222") em vez do subgrupo completo - soma
            # subgrupos da mesma classe num único bucket.
            cpc.update(str(code)[:4] for code in (item.get("cpc") or []) if code)
            if item.get("title"):
                title.append(item["title"])
        return self._fuzzy_group_depositants(dict(depositants)), dict(cpc), title

    async def _run_ops_final_search(
        self,
        adapter: Any,
        query: dict[str, Any],
        year_from: int,
        year_to: int,
        run_id: Optional[str] = None,
        iteration: int = 0,
    ) -> dict[str, Any]:
        """
        Descobre o total de resultados via /published-data/search (sem
        biblio, requisição leve) e escolhe entre paginar por range ou por
        ano: se o total couber em menos páginas que o nº de anos pedido,
        range é suficiente (a busca já é exaustiva, ordem não importa);
        caso contrário, uma página por ano garante cobertura de todo o
        intervalo em vez de ficar concentrado nos resultados mais recentes
        (comportamento padrão do OPS, sem ranking por relevância).

        year_from/year_to vêm da rota (obrigatórios - ver run_final_search),
        não mais de settings. A query de contagem tem sua cláusula de data
        sobrescrita com eles antes de contar (_ops_replace_date_clause), pra
        a contagem refletir o intervalo pedido agora, não o que ficou
        embutido na query no momento em que ela foi gerada.

        `iteration` (ver docstring de run_final_search) só afeta a
        estratégia por ano - repassado pra _run_ops_search_by_year, que
        seleciona qual bloco de 100 buscar por ano. A decisão range-vs-ano
        (`threshold` abaixo) usa sempre o page_size base (100), independente
        de `iteration`: range já é exaustiva (cobre tudo numa chamada só),
        então `iteration` não muda nada nela - pedir outra iteração de uma
        query resolvida como range simplesmente devolve o mesmo conjunto
        completo de novo.

        Returns:
            Dict com depositants, cpc, title, patents_by_year, strategy
            ("range" ou "year") e total_count - o compilado retornado por
            run_final_search para api="ops".
        """
        count_query = {**query, "query": self._ops_replace_date_clause(query.get("query", ""), year_from, year_to)}
        count_result = await adapter.search(count_query, run_id)
        total_count = count_result.total_count if count_result.success else None

        n_years = year_to - year_from + 1

        if total_count is None:
            logger.warning("ops_final_total_count_unavailable")
            # Caso degradado (contagem indisponível) - sem base pra decidir
            # estratégia, então sempre busca a página 1 (iteration
            # deliberadamente ignorado aqui, ver docstring).
            items = await self._run_ops_search_by_range(
                adapter, query, max_requests=1, year_from=year_from, year_to=year_to, run_id=run_id
            )
            depositants, cpc, title = self._aggregate_ops_final_items(items)
            return {
                "depositants": depositants,
                "cpc": cpc,
                "title": title,
                "patents_by_year": {},
                "strategy": "range",
                "total_count": None,
            }

        threshold = n_years * 100 - 99
        if total_count < threshold:
            max_requests = (total_count + 99) // 100
            items = await self._run_ops_search_by_range(adapter, query, max_requests, year_from, year_to, run_id)
            depositants, cpc, title = self._aggregate_ops_final_items(items)
            patents_by_year = dict(Counter(item["year"] for item in items if item.get("year") is not None))
            strategy = "range"
        else:
            items, patents_by_year = await self._run_ops_search_by_year(
                adapter, query, year_from, year_to, run_id, iteration=iteration
            )
            depositants, cpc, title = self._aggregate_ops_final_items(items)
            strategy = "year"

        return {
            "depositants": depositants,
            "cpc": cpc,
            "title": title,
            "patents_by_year": patents_by_year,
            "strategy": strategy,
            "total_count": total_count,
        }

    async def run_probe_search(
        self,
        query: dict[str, Any],
        api: str,
        top_k: int = 10,
    ) -> dict[str, Any]:
        from services.nlp.language_filter import filter_english_abstracts

        adapter = self._find_search_adapter(api)
        if adapter is None:
            return {"success": False, "api": api, "error": f"API '{api}' not enabled or not found"}

        # +10 (não +5): além dos itens sem abstract (Scopus), agora também
        # descartamos abstracts em idioma diferente do inglês - margem maior
        # pra compensar os dois motivos de descarte.
        effective_top_k = min(top_k + 10, 100)
        try:
            if api == "ops" and hasattr(adapter, "search_with_biblio"):
                items, total_available = await self._run_ops_year_diversified_search(
                    adapter, query, top_k=effective_top_k
                )
                return {
                    "success": True,
                    "api": api,
                    "results_count": len(items),
                    "total_available": total_available,
                    "results": items,
                    "error": None,
                }

            if api == "scopus":
                items, total_available = await self._run_scopus_year_diversified_search(
                    adapter, query, top_k=effective_top_k
                )
                return {
                    "success": True,
                    "api": api,
                    "results_count": len(items),
                    "total_available": total_available,
                    "results": items,
                    "error": None,
                }

            result = await adapter.search(query)

            if not result.success:
                return {"success": False, "api": api, "error": result.error_message}

            items = filter_english_abstracts(result.results)[:effective_top_k]

            return {
                "success": True,
                "api": api,
                "results_count": len(items),
                "total_available": result.total_count,
                "results": items,
                "error": None,
            }
        except Exception as exc:
            logger.error("run_probe_search_error", api=api, error=str(exc))
            return {"success": False, "api": api, "error": str(exc)}

    async def run_final_search(
        self,
        query: dict[str, Any],
        api: str,
        year_from: int,
        year_to: int,
        iteration: int = 0,
    ) -> dict[str, Any]:
        """
        year_from/year_to vêm sempre da rota (obrigatórios - ver
        chat_router.py) - nenhuma das duas fontes abaixo lê mais
        settings.search_year_from/to pra busca final (isso continua valendo
        só pra probe search e pra geração de query, que não foram alteradas).

        `iteration` (default 0, sem teto) é um seletor de JANELA da amostra
        por ano, não um multiplicador cumulativo: `iteration=N` devolve só a
        página N daquele ano (OPS: bloco de 100; Scopus: bloco de 200) - não
        as páginas 0..N somadas. Quem quiser uma amostra maior (o futuro
        módulo de inferência estatística) chama esta rota várias vezes com
        `iteration` crescente e junta os pedaços do lado de fora - este
        método continua stateless, sem cache/merge entre chamadas. Custo por
        chamada não muda com `iteration` (sempre 1 requisição/ano na
        estratégia por ano), por isso não há necessidade de teto. Na
        estratégia range (já exaustiva, decisão independente de `iteration` -
        ver _run_ops_final_search/_run_scopus_final_search) `iteration` não
        se aplica: qualquer valor devolve o mesmo conjunto completo. Rota
        chamada hoje sempre com o default (0); o parâmetro só existe pro uso
        futuro citado acima.

        OPS: usa _run_ops_final_search - esquema determinístico por
        range/ano, sem filtro de idioma - devolve só o compilado agregado
        (depositants/cpc/title/patents_by_year/strategy), não mais a lista
        bruta de itens.

        Scopus: usa _run_scopus_final_search - mesmo esquema determinístico
        da OPS (range/ano, o que exigir menos requisições, sem filtro de
        idioma), devolvendo o compilado agregado
        (institutions/area_of_study/title/articles_by_year/strategy) em vez
        da lista bruta de itens. institutions vem com fuzzy matching (mesmo
        mecanismo de depositants da OPS); area_of_study é contado à parte
        via SUBJAREA (a API não expõe subject-area por item nessa API key) e
        usa o nome completo da área, não a sigla.

        Outras APIs (lens_patent/lens_scholarly/openalex): busca simples via
        adapter.search(query), sem corte artificial de tamanho - cada
        adapter já controla seu próprio limite de paginação internamente.
        `iteration` é aceito mas ignorado aqui por enquanto (nenhuma dessas
        APIs tem hoje um esquema exaustivo range/ano como OPS/Scopus pra
        `iteration` selecionar uma janela de) - ponto de extensão pra quando
        alguma migrar pro mesmo esquema.
        """
        adapter = self._find_search_adapter(api)
        if adapter is None:
            return {"success": False, "api": api, "error": f"API '{api}' not enabled or not found"}

        try:
            if api == "ops" and hasattr(adapter, "fetch_biblio_page"):
                compiled = await self._run_ops_final_search(adapter, query, year_from, year_to, iteration=iteration)
                return {
                    "success": True,
                    "api": api,
                    "depositants": compiled["depositants"],
                    "cpc": compiled["cpc"],
                    "title": compiled["title"],
                    "patents_by_year": compiled["patents_by_year"],
                    "strategy": compiled["strategy"],
                    "error": None,
                }

            if api == "scopus" and hasattr(adapter, "fetch_results_page"):
                compiled = await self._run_scopus_final_search(
                    adapter, query, year_from, year_to, iteration=iteration
                )
                return {
                    "success": True,
                    "api": api,
                    "institutions": compiled["institutions"],
                    "area_of_study": compiled["area_of_study"],
                    "title": compiled["title"],
                    "articles_by_year": compiled["articles_by_year"],
                    "strategy": compiled["strategy"],
                    "error": None,
                }

            from services.nlp.language_filter import filter_english_abstracts

            result = await adapter.search(query)
            if not result.success:
                return {"success": False, "api": api, "error": result.error_message}
            items = filter_english_abstracts(result.results)
            total_available = result.total_count

            return {
                "success": True,
                "api": api,
                "results_count": len(items),
                "total_available": total_available,
                "results": items,
                "error": None,
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
        from services.nlp.term_extraction import get_term_extractor

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

        start = time.perf_counter()
        try:
            extractor = get_term_extractor()
            terms = extractor.extract_and_rank_terms(
                original_params=original_params or {},
                enriched_results=enriched,
                top_k=top_k,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            return {
                "success": True,
                "terms": terms,
                "count": len(terms),
                "ai_usage": {
                    "step": "extract_terms",
                    "provider": "internal",
                    "model": self.settings.llm_keybert_model,
                    "duration_ms": duration_ms,
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "attempts": 1,
                },
            }
        except Exception as exc:
            logger.error("extract_terms_error", error=str(exc))
            return {"success": False, "error": str(exc)}
