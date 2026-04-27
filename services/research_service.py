"""
Service for managing research data persistence.

Handles creating, updating, and retrieving research records with all
their associated data (queries, results, metrics, reports).
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.research_models import (
    Research,
    ResearchMetrics,
    ResearchPatentDocument,
    ResearchPhase,
    ResearchScholarlyDocument,
    ResearchTokenUsage,
)

logger = get_logger(__name__)


class ResearchService:
    """Service for managing research data in database."""

    @staticmethod
    async def create_research(
        session: AsyncSession,
        title: str,
        description: Optional[str] = None,
        user_input: Optional[dict[str, Any]] = None,
    ) -> Research:
        """
        Create a new research record.

        Args:
            session: Database session
            title: Research title
            description: Research description
            user_input: Initial user parameters (theme, description, etc)

        Returns:
            Created Research object
        """
        research = Research(
            research_id=str(uuid.uuid4()),
            title=title,
            description=description,
            user_input=user_input or {},
            status="ongoing",
            timing={},
        )

        session.add(research)
        await session.flush()

        logger.info(
            "research_created",
            research_id=research.research_id,
            title=title,
        )

        return research

    @staticmethod
    async def update_refined_candidates(
        session: AsyncSession,
        research_id: int,
        candidates: list[dict[str, Any]],
        chosen: dict[str, Any],
    ) -> None:
        """
        Update research with refined candidates from LLM.

        Args:
            session: Database session
            research_id: Research ID
            candidates: 4 refined candidates from LLM
            chosen: User's chosen candidate
        """
        research = await session.get(Research, research_id)
        if not research:
            logger.error("research_not_found", research_id=research_id)
            return

        research.refined_candidates = candidates
        research.chosen_candidate = chosen
        research.updated_at = datetime.utcnow()

        await session.flush()

        logger.info("research_candidates_updated", research_id=research_id)

    @staticmethod
    async def update_probe_query(
        session: AsyncSession,
        research_id: int,
        query: dict[str, Any],
        api: str,
    ) -> None:
        """
        Update research with probe query.

        Args:
            session: Database session
            research_id: Research ID
            query: Query object (query, range, format)
            api: API used (ops, scopus, etc)
        """
        research = await session.get(Research, research_id)
        if not research:
            return

        research.probe_query = query
        research.probe_api = api
        research.updated_at = datetime.utcnow()

        await session.flush()
        logger.info("research_probe_query_updated", research_id=research_id, api=api)

    @staticmethod
    async def update_extracted_terms(
        session: AsyncSession,
        research_id: int,
        terms: list[dict[str, Any]],
    ) -> None:
        """
        Update research with extracted terms.

        Args:
            session: Database session
            research_id: Research ID
            terms: Extracted terms with scores
        """
        research = await session.get(Research, research_id)
        if not research:
            return

        research.extracted_terms = terms
        research.extracted_terms_count = len(terms)
        research.updated_at = datetime.utcnow()

        await session.flush()
        logger.info("research_terms_updated", research_id=research_id, count=len(terms))

    @staticmethod
    async def update_final_queries(
        session: AsyncSession,
        research_id: int,
        specific_query: dict[str, Any],
        balanced_query: dict[str, Any],
        generic_query: dict[str, Any],
        chosen: str,
    ) -> None:
        """
        Update research with final query variants.

        Args:
            session: Database session
            research_id: Research ID
            specific_query: Specific variant query
            balanced_query: Balanced variant query
            generic_query: Generic variant query
            chosen: Which variant was chosen (specific, balanced, generic)
        """
        research = await session.get(Research, research_id)
        if not research:
            return

        research.final_query_specific = specific_query
        research.final_query_balanced = balanced_query
        research.final_query_generic = generic_query
        research.chosen_final_query = chosen
        research.updated_at = datetime.utcnow()

        await session.flush()
        logger.info("research_final_queries_updated", research_id=research_id, chosen=chosen)

    @staticmethod
    async def add_patent_result(
        session: AsyncSession,
        research_id: int,
        patent_data: dict[str, Any],
        query_variant: str,
    ) -> None:
        """
        Add patent result to research.

        Args:
            session: Database session
            research_id: Research ID
            patent_data: Patent document data
            query_variant: Which query variant found this (specific, balanced, generic)
        """
        research = await session.get(Research, research_id)
        if not research:
            return

        patent_doc = ResearchPatentDocument(
            research_id=research_id,
            publication_number=patent_data.get("publication_number", ""),
            source=patent_data.get("source", "ops"),
            source_record_id=patent_data.get("source_record_id", ""),
            title=patent_data.get("title", ""),
            abstract=patent_data.get("abstract"),
            applicants=patent_data.get("applicants"),
            inventors=patent_data.get("inventors"),
            ipc_codes=patent_data.get("ipc_codes"),
            cpc_codes=patent_data.get("cpc_codes"),
            filing_date=patent_data.get("filing_date"),
            publication_date=patent_data.get("publication_date"),
            grant_date=patent_data.get("grant_date"),
            year=patent_data.get("year"),
            legal_status=patent_data.get("legal_status"),
            relevance_score=patent_data.get("relevance_score"),
            query_variant=query_variant,
            raw_payload=patent_data,
        )

        session.add(patent_doc)
        research.patent_results_count = (research.patent_results_count or 0) + 1
        research.total_results_count = (research.total_results_count or 0) + 1
        research.updated_at = datetime.utcnow()

        await session.flush()

    @staticmethod
    async def add_scholarly_result(
        session: AsyncSession,
        research_id: int,
        article_data: dict[str, Any],
        query_variant: str,
    ) -> None:
        """
        Add scholarly article result to research.

        Args:
            session: Database session
            research_id: Research ID
            article_data: Article document data
            query_variant: Which query variant found this
        """
        research = await session.get(Research, research_id)
        if not research:
            return

        article_doc = ResearchScholarlyDocument(
            research_id=research_id,
            doi=article_data.get("doi"),
            source=article_data.get("source", "scopus"),
            source_record_id=article_data.get("source_record_id", ""),
            title=article_data.get("title", ""),
            abstract=article_data.get("abstract"),
            authors=article_data.get("authors"),
            affiliations=article_data.get("affiliations"),
            journal_or_source=article_data.get("journal_or_source"),
            volume=article_data.get("volume"),
            issue=article_data.get("issue"),
            pages=article_data.get("pages"),
            publication_date=article_data.get("publication_date"),
            year=article_data.get("year"),
            keywords=article_data.get("keywords"),
            field_of_study=article_data.get("field_of_study"),
            citations=article_data.get("citations"),
            relevance_score=article_data.get("relevance_score"),
            query_variant=query_variant,
            raw_payload=article_data,
        )

        session.add(article_doc)
        research.scholarly_results_count = (research.scholarly_results_count or 0) + 1
        research.total_results_count = (research.total_results_count or 0) + 1
        research.updated_at = datetime.utcnow()

        await session.flush()

    @staticmethod
    async def update_metrics(
        session: AsyncSession,
        research_id: int,
        metrics_data: dict[str, Any],
    ) -> None:
        """
        Update research metrics for graphs and reports.

        Args:
            session: Database session
            research_id: Research ID
            metrics_data: Aggregated metrics (by year, applicant, etc)
        """
        research = await session.get(Research, research_id)
        if not research:
            return

        # Get or create metrics
        metrics = await session.get(ResearchMetrics, research_id, "research_id")
        if not metrics:
            metrics = ResearchMetrics(research_id=research_id)
            session.add(metrics)

        # Update metrics fields
        for field, value in metrics_data.items():
            if hasattr(metrics, field):
                setattr(metrics, field, value)

        metrics.calculated_at = datetime.utcnow()
        await session.flush()

        logger.info("research_metrics_updated", research_id=research_id)

    @staticmethod
    async def add_phase_timing(
        session: AsyncSession,
        research_id: int,
        phase_name: str,
        started_at: datetime,
        completed_at: datetime,
        status: str = "completed",
        error_message: Optional[str] = None,
    ) -> None:
        """
        Record timing for a research phase.

        Args:
            session: Database session
            research_id: Research ID
            phase_name: Phase name (refine, probe, extract, final, search)
            started_at: When phase started
            completed_at: When phase completed
            status: Phase status
            error_message: Error message if phase failed
        """
        duration = (completed_at - started_at).total_seconds()

        phase = ResearchPhase(
            research_id=research_id,
            phase_name=phase_name,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            status=status,
            error_message=error_message,
        )

        session.add(phase)

        # Update research timing dict
        research = await session.get(Research, research_id)
        if research:
            if not research.timing:
                research.timing = {}
            research.timing[phase_name] = duration
            research.updated_at = datetime.utcnow()

        await session.flush()

        logger.info(
            "research_phase_timed",
            research_id=research_id,
            phase=phase_name,
            duration=duration,
        )

    @staticmethod
    async def update_report(
        session: AsyncSession,
        research_id: int,
        latex_content: str,
        report_url: Optional[str] = None,
    ) -> None:
        """
        Update research with generated LaTeX report.

        Args:
            session: Database session
            research_id: Research ID
            latex_content: Generated LaTeX document
            report_url: URL to generated PDF (if available)
        """
        research = await session.get(Research, research_id)
        if not research:
            return

        research.latex_content = latex_content
        research.latex_generated_at = datetime.utcnow()
        research.report_url = report_url
        research.status = "completed"
        research.updated_at = datetime.utcnow()

        await session.flush()

        logger.info("research_report_generated", research_id=research_id)

    @staticmethod
    async def get_research(session: AsyncSession, research_id: int) -> Optional[Research]:
        """Get research by ID."""
        return await session.get(Research, research_id)

    @staticmethod
    async def get_research_by_uuid(session: AsyncSession, research_uuid: str) -> Optional[Research]:
        """Get research by UUID."""
        from sqlalchemy import select

        result = await session.execute(
            select(Research).where(Research.research_id == research_uuid)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def add_token_usage(
        session: AsyncSession,
        research_id: int,
        phase_name: str,
        llm_call_type: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        input_cost_usd: float,
        output_cost_usd: float,
        api_latency_ms: Optional[int] = None,
        call_number: int = 1,
        model_variant: Optional[str] = None,
        status: str = "success",
        metadata: Optional[dict[str, Any]] = None,
    ) -> ResearchTokenUsage:
        """
        Register LLM token usage for a research call.

        Args:
            session: Database session
            research_id: Research ID
            phase_name: Phase name (refine, probe, extract, final, search)
            llm_call_type: Call type (generate_candidate_topics, probe_search, etc)
            model: Model name (gemini, gpt-4, claude, etc)
            input_tokens: Input token count
            output_tokens: Output token count
            input_cost_usd: Input cost in USD
            output_cost_usd: Output cost in USD
            api_latency_ms: API response latency in milliseconds
            call_number: Call number for repeated phases (1st, 2nd, 3rd, etc)
            model_variant: Model variant (e.g. gemini-1.5-pro)
            status: Call status (success, failed, timeout)
            metadata: Additional metadata

        Returns:
            Created ResearchTokenUsage object
        """
        total_tokens = input_tokens + output_tokens
        total_cost = input_cost_usd + output_cost_usd

        token_usage = ResearchTokenUsage(
            research_id=research_id,
            phase_name=phase_name,
            llm_call_type=llm_call_type,
            model=model,
            model_variant=model_variant,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost_usd=input_cost_usd,
            output_cost_usd=output_cost_usd,
            total_cost_usd=total_cost,
            api_latency_ms=api_latency_ms,
            call_number=call_number,
            status=status,
            metadata=metadata or {},
        )

        session.add(token_usage)

        # Update research totals
        research = await session.get(Research, research_id)
        if research:
            research.total_tokens_used = (research.total_tokens_used or 0) + total_tokens
            research.total_cost_usd = (research.total_cost_usd or 0.0) + total_cost
            research.updated_at = datetime.utcnow()

        await session.flush()

        logger.info(
            "research_token_usage_recorded",
            research_id=research_id,
            phase=phase_name,
            tokens=total_tokens,
            cost_usd=total_cost,
        )

        return token_usage

    @staticmethod
    async def get_token_usage(
        session: AsyncSession,
        research_id: int,
    ) -> list[ResearchTokenUsage]:
        """
        Get all token usage records for a research.

        Args:
            session: Database session
            research_id: Research ID

        Returns:
            List of ResearchTokenUsage records ordered by created_at
        """
        from sqlalchemy import select

        result = await session.execute(
            select(ResearchTokenUsage)
            .where(ResearchTokenUsage.research_id == research_id)
            .order_by(ResearchTokenUsage.created_at)
        )
        return result.scalars().all()

    @staticmethod
    async def get_token_summary(
        session: AsyncSession,
        research_id: int,
    ) -> dict[str, Any]:
        """
        Get summary of token usage by phase.

        Args:
            session: Database session
            research_id: Research ID

        Returns:
            Dictionary with token usage summary:
            {
                "total_tokens": 15000,
                "total_cost_usd": 0.05,
                "by_phase": {
                    "refine": {"tokens": 3000, "cost_usd": 0.01, "calls": 2},
                    "probe": {"tokens": 5000, "cost_usd": 0.02, "calls": 1},
                    ...
                },
                "by_model": {
                    "gemini": {"tokens": 15000, "cost_usd": 0.05, "calls": 4},
                },
                "call_history": [...]
            }
        """
        from sqlalchemy import func, select

        result = await session.execute(
            select(ResearchTokenUsage)
            .where(ResearchTokenUsage.research_id == research_id)
            .order_by(ResearchTokenUsage.created_at)
        )
        usage_records = result.scalars().all()

        if not usage_records:
            return {
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "by_phase": {},
                "by_model": {},
                "call_history": [],
            }

        # Aggregate by phase
        by_phase = {}
        for record in usage_records:
            if record.phase_name not in by_phase:
                by_phase[record.phase_name] = {
                    "tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "calls": 0,
                }
            by_phase[record.phase_name]["tokens"] += record.total_tokens
            by_phase[record.phase_name]["input_tokens"] += record.input_tokens
            by_phase[record.phase_name]["output_tokens"] += record.output_tokens
            by_phase[record.phase_name]["cost_usd"] += record.total_cost_usd
            by_phase[record.phase_name]["calls"] += 1

        # Aggregate by model
        by_model = {}
        for record in usage_records:
            model_key = f"{record.model}"
            if record.model_variant:
                model_key = f"{record.model} ({record.model_variant})"

            if model_key not in by_model:
                by_model[model_key] = {
                    "tokens": 0,
                    "cost_usd": 0.0,
                    "calls": 0,
                }
            by_model[model_key]["tokens"] += record.total_tokens
            by_model[model_key]["cost_usd"] += record.total_cost_usd
            by_model[model_key]["calls"] += 1

        # Get totals
        total_tokens = sum(r.total_tokens for r in usage_records)
        total_cost = sum(r.total_cost_usd for r in usage_records)

        # Call history
        call_history = [
            {
                "timestamp": record.created_at.isoformat(),
                "phase": record.phase_name,
                "call_type": record.llm_call_type,
                "call_number": record.call_number,
                "model": record.model,
                "tokens": record.total_tokens,
                "cost_usd": record.total_cost_usd,
                "latency_ms": record.api_latency_ms,
                "status": record.status,
            }
            for record in usage_records
        ]

        return {
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "by_phase": by_phase,
            "by_model": by_model,
            "call_history": call_history,
        }
