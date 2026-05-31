from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.research_models import (
    Research,
    ResearchMetrics,
    ResearchPatentDocument,
    ResearchScholarlyDocument,
)

logger = get_logger(__name__)


class MetricsAggregator:
    """
    Calcula métricas agregadas para gráficos e relatórios.

    Processa documentos de patentes e artigos para extrair:
    - Distribuição por ano
    - Distribuição por aplicante/autor
    - Distribuição por classificação/tema
    - Rankings de entidades principais
    - Tendências de crescimento
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def calculate_and_store_metrics(self, research_id: int) -> Optional[ResearchMetrics]:
        try:
            metrics_data = await self.calculate_metrics(research_id)

            stmt = select(ResearchMetrics).where(ResearchMetrics.research_id == research_id)
            result = await self.session.execute(stmt)
            metrics = result.scalar_one_or_none()

            if not metrics:
                metrics = ResearchMetrics(research_id=research_id)
                self.session.add(metrics)

            for field, value in metrics_data.items():
                if hasattr(metrics, field):
                    setattr(metrics, field, value)

            from datetime import datetime

            metrics.calculated_at = datetime.utcnow()
            await self.session.flush()

            logger.info("metrics_calculated_and_stored", research_id=research_id)
            return metrics

        except Exception as exc:
            logger.error("metrics_calculation_error", research_id=research_id, error=str(exc))
            return None

    async def calculate_metrics(self, research_id: int) -> dict[str, Any]:
        metrics = {}
        metrics.update(await self._calculate_patent_metrics(research_id))
        metrics.update(await self._calculate_article_metrics(research_id))
        metrics.update(await self._calculate_top_entities(research_id))
        metrics.update(await self._calculate_trends(research_id))
        metrics.update(await self._calculate_comparison(research_id))
        return metrics

    async def _calculate_patent_metrics(self, research_id: int) -> dict[str, Any]:
        metrics = {}

        stmt = (
            select(
                ResearchPatentDocument.year,
                func.count(ResearchPatentDocument.id).label("count"),
            )
            .where(ResearchPatentDocument.research_id == research_id)
            .where(ResearchPatentDocument.year.isnot(None))
            .group_by(ResearchPatentDocument.year)
            .order_by(ResearchPatentDocument.year)
        )
        result = await self.session.execute(stmt)
        metrics["patent_by_year"] = {str(row[0]): row[1] for row in result}

        stmt = (
            select(ResearchPatentDocument.applicants)
            .where(ResearchPatentDocument.research_id == research_id)
            .where(ResearchPatentDocument.applicants.isnot(None))
        )
        result = await self.session.execute(stmt)
        applicant_counts: dict[str, int] = {}
        for (applicants,) in result:
            if applicants:
                for app in applicants:
                    applicant_counts[app] = applicant_counts.get(app, 0) + 1
        metrics["patent_by_applicant"] = dict(
            sorted(applicant_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        )

        stmt = (
            select(ResearchPatentDocument.ipc_codes)
            .where(ResearchPatentDocument.research_id == research_id)
            .where(ResearchPatentDocument.ipc_codes.isnot(None))
        )
        result = await self.session.execute(stmt)
        ipc_counts: dict[str, int] = {}
        for (ipc_codes,) in result:
            if ipc_codes:
                for code in ipc_codes:
                    ipc_counts[code] = ipc_counts.get(code, 0) + 1
        metrics["patent_by_ipc"] = dict(
            sorted(ipc_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        )

        stmt = (
            select(
                ResearchPatentDocument.legal_status,
                func.count(ResearchPatentDocument.id).label("count"),
            )
            .where(ResearchPatentDocument.research_id == research_id)
            .where(ResearchPatentDocument.legal_status.isnot(None))
            .group_by(ResearchPatentDocument.legal_status)
        )
        result = await self.session.execute(stmt)
        metrics["patent_by_legal_status"] = {row[0]: row[1] for row in result}

        stmt = (
            select(
                ResearchPatentDocument.query_variant,
                func.count(ResearchPatentDocument.id).label("count"),
            )
            .where(ResearchPatentDocument.research_id == research_id)
            .group_by(ResearchPatentDocument.query_variant)
        )
        result = await self.session.execute(stmt)
        metrics["patent_by_query_variant"] = {row[0]: row[1] for row in result}

        return metrics

    async def _calculate_article_metrics(self, research_id: int) -> dict[str, Any]:
        metrics = {}

        stmt = (
            select(
                ResearchScholarlyDocument.year,
                func.count(ResearchScholarlyDocument.id).label("count"),
            )
            .where(ResearchScholarlyDocument.research_id == research_id)
            .where(ResearchScholarlyDocument.year.isnot(None))
            .group_by(ResearchScholarlyDocument.year)
            .order_by(ResearchScholarlyDocument.year)
        )
        result = await self.session.execute(stmt)
        metrics["article_by_year"] = {str(row[0]): row[1] for row in result}

        stmt = (
            select(
                ResearchScholarlyDocument.journal_or_source,
                func.count(ResearchScholarlyDocument.id).label("count"),
            )
            .where(ResearchScholarlyDocument.research_id == research_id)
            .where(ResearchScholarlyDocument.journal_or_source.isnot(None))
            .group_by(ResearchScholarlyDocument.journal_or_source)
            .order_by(func.count(ResearchScholarlyDocument.id).desc())
        )
        result = await self.session.execute(stmt)
        metrics["article_by_journal"] = {row[0]: row[1] for row in result[:20]}

        stmt = (
            select(ResearchScholarlyDocument.field_of_study)
            .where(ResearchScholarlyDocument.research_id == research_id)
            .where(ResearchScholarlyDocument.field_of_study.isnot(None))
        )
        result = await self.session.execute(stmt)
        field_counts: dict[str, int] = {}
        for (fields,) in result:
            if fields:
                for field in fields:
                    field_counts[field] = field_counts.get(field, 0) + 1
        metrics["article_by_field"] = dict(
            sorted(field_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        )

        stmt = select(ResearchScholarlyDocument.citations).where(
            ResearchScholarlyDocument.research_id == research_id
        )
        result = await self.session.execute(stmt)
        citation_ranges = {"0-10": 0, "11-50": 0, "51-100": 0, "100+": 0}
        for (citations,) in result:
            if citations is not None:
                if citations <= 10:
                    citation_ranges["0-10"] += 1
                elif citations <= 50:
                    citation_ranges["11-50"] += 1
                elif citations <= 100:
                    citation_ranges["51-100"] += 1
                else:
                    citation_ranges["100+"] += 1
        metrics["article_by_citations"] = citation_ranges

        stmt = (
            select(
                ResearchScholarlyDocument.query_variant,
                func.count(ResearchScholarlyDocument.id).label("count"),
            )
            .where(ResearchScholarlyDocument.research_id == research_id)
            .group_by(ResearchScholarlyDocument.query_variant)
        )
        result = await self.session.execute(stmt)
        metrics["article_by_query_variant"] = {row[0]: row[1] for row in result}

        return metrics

    async def _calculate_top_entities(self, research_id: int) -> dict[str, Any]:
        metrics = {}

        stmt = (
            select(ResearchPatentDocument.applicants)
            .where(ResearchPatentDocument.research_id == research_id)
            .where(ResearchPatentDocument.applicants.isnot(None))
        )
        result = await self.session.execute(stmt)
        applicant_patents: dict[str, list[str]] = {}
        for (applicants,) in result:
            if applicants:
                for app in applicants:
                    if app not in applicant_patents:
                        applicant_patents[app] = []
                    applicant_patents[app].append(str(app))
        metrics["top_patent_applicants"] = [
            {"name": app, "count": len(patents), "patents": patents[:5]}
            for app, patents in sorted(applicant_patents.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        ]

        stmt = (
            select(ResearchPatentDocument.inventors)
            .where(ResearchPatentDocument.research_id == research_id)
            .where(ResearchPatentDocument.inventors.isnot(None))
        )
        result = await self.session.execute(stmt)
        inventor_patents: dict[str, list[str]] = {}
        for (inventors,) in result:
            if inventors:
                for inv in inventors:
                    if inv not in inventor_patents:
                        inventor_patents[inv] = []
                    inventor_patents[inv].append(str(inv))
        metrics["top_patent_inventors"] = [
            {"name": inv, "count": len(patents), "patents": patents[:5]}
            for inv, patents in sorted(inventor_patents.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        ]

        stmt = (
            select(ResearchScholarlyDocument.authors)
            .where(ResearchScholarlyDocument.research_id == research_id)
            .where(ResearchScholarlyDocument.authors.isnot(None))
        )
        result = await self.session.execute(stmt)
        author_articles: dict[str, list[str]] = {}
        for (authors,) in result:
            if authors:
                for auth in authors:
                    if auth not in author_articles:
                        author_articles[auth] = []
                    author_articles[auth].append(str(auth))
        metrics["top_article_authors"] = [
            {"name": auth, "count": len(articles), "articles": articles[:5]}
            for auth, articles in sorted(author_articles.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        ]

        stmt = (
            select(ResearchScholarlyDocument.journal_or_source)
            .where(ResearchScholarlyDocument.research_id == research_id)
            .where(ResearchScholarlyDocument.journal_or_source.isnot(None))
        )
        result = await self.session.execute(stmt)
        journal_count: dict[str, int] = {}
        for (journal,) in result:
            journal_count[journal] = journal_count.get(journal, 0) + 1
        metrics["top_article_journals"] = [
            {"name": journal, "count": count}
            for journal, count in sorted(journal_count.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return metrics

    async def _calculate_trends(self, research_id: int) -> dict[str, Any]:
        metrics = {}

        stmt = (
            select(
                ResearchPatentDocument.year,
                func.count(ResearchPatentDocument.id).label("count"),
            )
            .where(ResearchPatentDocument.research_id == research_id)
            .where(ResearchPatentDocument.year.isnot(None))
            .group_by(ResearchPatentDocument.year)
            .order_by(ResearchPatentDocument.year)
        )
        result = await self.session.execute(stmt)
        metrics["patent_growth_trend"] = {str(year): count for year, count in result}

        stmt = (
            select(
                ResearchScholarlyDocument.year,
                func.count(ResearchScholarlyDocument.id).label("count"),
            )
            .where(ResearchScholarlyDocument.research_id == research_id)
            .where(ResearchScholarlyDocument.year.isnot(None))
            .group_by(ResearchScholarlyDocument.year)
            .order_by(ResearchScholarlyDocument.year)
        )
        result = await self.session.execute(stmt)
        metrics["article_growth_trend"] = {str(year): count for year, count in result}

        return metrics

    async def _calculate_comparison(self, research_id: int) -> dict[str, Any]:
        metrics = {}

        stmt = (
            select(
                ResearchPatentDocument.query_variant,
                func.count(ResearchPatentDocument.id).label("patent_count"),
            )
            .where(ResearchPatentDocument.research_id == research_id)
            .group_by(ResearchPatentDocument.query_variant)
        )
        result = await self.session.execute(stmt)
        variant_comparison = {f"{variant}_patents": count for variant, count in result}

        stmt = (
            select(
                ResearchScholarlyDocument.query_variant,
                func.count(ResearchScholarlyDocument.id).label("article_count"),
            )
            .where(ResearchScholarlyDocument.research_id == research_id)
            .group_by(ResearchScholarlyDocument.query_variant)
        )
        result = await self.session.execute(stmt)
        for variant, count in result:
            variant_comparison[f"{variant}_articles"] = count
        metrics["query_variant_comparison"] = variant_comparison

        stmt = select(func.count(ResearchPatentDocument.id)).where(
            ResearchPatentDocument.research_id == research_id
        )
        patent_count = (await self.session.execute(stmt)).scalar() or 0

        stmt = select(func.count(ResearchScholarlyDocument.id)).where(
            ResearchScholarlyDocument.research_id == research_id
        )
        article_count = (await self.session.execute(stmt)).scalar() or 0

        metrics["patent_vs_article_ratio"] = {"patents": patent_count, "articles": article_count}

        return metrics
