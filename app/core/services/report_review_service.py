"""
Orquestra a revisão do .tex no editor (POST /report/{session_id}/review):
verificador de LaTeX + LanguageTool (ortografia, acentuação, concordância)
nos trechos em escopo + segunda opinião opcional por IA (ponto de uso
"report_review"), focada no que o LanguageTool deixa passar - concordância
com sujeito distante ("a concentração de depositantes ... indicam").

A lógica pura (o que revisar, como converter LaTeX, o que filtrar/aceitar)
fica em report_review.py; aqui só I/O: HTTP pro LanguageTool e o LLM.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Optional

import httpx

from app.core.services.report_review import (
    DISABLED_LANGUAGETOOL_RULES,
    ReviewResult,
    ScopeRange,
    Suggestion,
    languagetool_suggestions,
    lint_latex,
    overlaps,
    review_scope,
    to_annotated_text,
    validate_ai_suggestion,
)
from core.logging import get_logger
from services.llm.base import parse_llm_json

logger = get_logger(__name__)

_LANGUAGETOOL_CONCURRENCY = 4
_AI_CONCURRENCY = 2
# Parágrafo curto demais não vale uma chamada de IA.
_AI_MIN_PARAGRAPH_CHARS = 60

AI_REVIEW_SYSTEM_PROMPT = """Você é revisor de língua portuguesa (norma culta do Brasil) de relatórios técnicos.
Corrija SOMENTE erros de: concordância verbal, concordância nominal (número e gênero), acentuação e ortografia.
NÃO reescreva estilo, NÃO troque palavras corretas por sinônimos, NÃO altere números, siglas, nomes próprios, citações "(AUTOR, ano)" nem comandos LaTeX (\\textit{...}, \\ref{...}, \\%, \\&).
Responda APENAS com JSON no formato:
{"correcoes": [{"original": "<trecho EXATO copiado do texto, curto, contendo o erro>", "corrigido": "<o mesmo trecho corrigido>", "motivo": "concordância verbal|concordância nominal|acentuação|ortografia"}]}
Se não houver erros, responda {"correcoes": []}."""


class ReportReviewService:
    def __init__(self, languagetool_url: str, language: str, llm_resolver: Any, settings: Any = None) -> None:
        self._languagetool_url = languagetool_url.rstrip("/")
        self._default_language = language
        # Settings "vivo" (ver settings_sync_service.py): o idioma editado em
        # Configurações vale na próxima revisão, sem reiniciar o backend.
        self._settings = settings
        self._llm_resolver = llm_resolver
        self._client = httpx.AsyncClient(timeout=60)

    async def review(
        self,
        text: str,
        baseline: Optional[str],
        available_images: set[str],
        compile_log: Optional[str] = None,
        include_ai: bool = False,
    ) -> ReviewResult:
        result = ReviewResult()
        result.latex_issues = lint_latex(text, available_images, compile_log)
        result.scope = review_scope(text, baseline)
        if baseline is None:
            result.warnings.append(
                "Este relatório foi montado antes da revisão existir: só as seções geradas por IA foram "
                "revisadas (edições manuais fora delas não são detectadas). Use \"Remontar .tex\" para habilitar."
            )
        if not result.scope:
            return result

        lt_suggestions, lt_warning = await self._languagetool(text, result.scope)
        result.suggestions.extend(lt_suggestions)
        if lt_warning:
            result.warnings.append(lt_warning)

        if include_ai:
            ai_suggestions, ai_warning = await self._ai_review(text, result.scope)
            result.suggestions.extend(s for s in ai_suggestions if not any(overlaps(s, lt) for lt in lt_suggestions))
            if ai_warning:
                result.warnings.append(ai_warning)

        result.suggestions.sort(key=lambda s: s.offset)
        return result

    # ------------------------------------------------------------------
    # LanguageTool
    # ------------------------------------------------------------------

    async def _languagetool(self, text: str, scope: list[ScopeRange]) -> tuple[list[Suggestion], Optional[str]]:
        semaphore = asyncio.Semaphore(_LANGUAGETOOL_CONCURRENCY)

        async def check(scope_range: ScopeRange) -> list[Suggestion]:
            fragment = text[scope_range.start: scope_range.end]
            annotation = {"annotation": [segment.to_dict() for segment in to_annotated_text(fragment)]}
            async with semaphore:
                response = await self._client.post(
                    f"{self._languagetool_url}/v2/check",
                    data={
                        "language": self._language(),
                        "data": json.dumps(annotation, ensure_ascii=False),
                        "disabledRules": ",".join(DISABLED_LANGUAGETOOL_RULES),
                    },
                )
            response.raise_for_status()
            return languagetool_suggestions(
                fragment, scope_range.start, scope_range.section, response.json().get("matches", [])
            )

        try:
            batches = await asyncio.gather(*(check(r) for r in scope))
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("report_review_languagetool_failed", error=str(exc), url=self._languagetool_url)
            return [], (
                "Revisão de ortografia/concordância indisponível (LanguageTool não respondeu) - "
                "verifique o container 'languagetool'. Os problemas de LaTeX abaixo continuam válidos."
            )
        return [s for batch in batches for s in batch], None

    # ------------------------------------------------------------------
    # IA (segunda opinião)
    # ------------------------------------------------------------------

    async def _ai_review(self, text: str, scope: list[ScopeRange]) -> tuple[list[Suggestion], Optional[str]]:
        paragraphs: list[tuple[int, str, str]] = []
        for scope_range in scope:
            fragment = text[scope_range.start: scope_range.end]
            for match in re.finditer(r"[^\n](?:.|\n(?!\s*\n))*", fragment):
                paragraph = match.group(0)
                if len(paragraph.strip()) >= _AI_MIN_PARAGRAPH_CHARS and not paragraph.lstrip().startswith("\\"):
                    paragraphs.append((scope_range.start + match.start(), paragraph, scope_range.section))
        if not paragraphs:
            return [], None

        try:
            generator = await self._llm_resolver.resolve_text_generation("report_review")
        except Exception as exc:
            logger.warning("report_review_ai_unavailable", error=str(exc))
            return [], f"Revisão por IA indisponível: {exc}"

        semaphore = asyncio.Semaphore(_AI_CONCURRENCY)
        failures = 0

        async def review_paragraph(offset: int, paragraph: str, section: str) -> list[Suggestion]:
            nonlocal failures
            async with semaphore:
                try:
                    raw = await generator.generate(f"Texto a revisar:\n\n{paragraph}", system=AI_REVIEW_SYSTEM_PROMPT)
                    corrections = _parse_corrections(raw)
                except Exception as exc:
                    failures += 1
                    logger.warning("report_review_ai_paragraph_failed", error=str(exc))
                    return []
            suggestions = []
            for item in corrections:
                original, corrected = str(item.get("original", "")), str(item.get("corrigido", ""))
                position = validate_ai_suggestion(paragraph, original, corrected)
                if position is None:
                    continue
                suggestions.append(
                    Suggestion(
                        offset=offset + position,
                        length=len(original),
                        original=original,
                        replacements=[corrected],
                        message=f"Sugestão da revisão por IA ({item.get('motivo') or 'gramática'}).",
                        category=str(item.get("motivo") or "gramática"),
                        source="ia",
                        section=section,
                    )
                )
            return suggestions

        batches = await asyncio.gather(*(review_paragraph(*p) for p in paragraphs))
        warning = (
            f"A revisão por IA falhou em {failures} de {len(paragraphs)} parágrafos - tente de novo." if failures else None
        )
        return [s for batch in batches for s in batch], warning

    def _language(self) -> str:
        return getattr(self._settings, "languagetool_language", None) or self._default_language

    async def close(self) -> None:
        await self._client.aclose()


def _parse_corrections(raw: str) -> list[dict[str, Any]]:
    """JSON da IA, tolerante a texto em volta e a pequenos erros de formato."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return []
    # O modelo copia trechos LaTeX ("17,3\%") pra dentro das strings JSON sem
    # dobrar a barra - escape inválido pro json.loads. Dobra toda barra que
    # não inicia um escape JSON válido.
    candidate = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", match.group(0))
    data = parse_llm_json(candidate)
    corrections = data.get("correcoes") if isinstance(data, dict) else None
    return [c for c in corrections or [] if isinstance(c, dict)]
