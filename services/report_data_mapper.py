"""
Map research data from both patents (OPS) and articles (Scopus) to report format.

Consolidates data from both APIs into unified format for report generation.
"""

from typing import Any, Optional

from db.research_models import Research

from core.logging import get_logger

logger = get_logger(__name__)


class ReportDataMapper:
    """Maps Research records to report generation format."""

    @staticmethod
    def map_complete_research_data(research: Research) -> dict[str, Any]:
        """
        Map complete research data (patents + articles) for report.

        Args:
            research: Research record from database

        Returns:
            Dictionary with all data needed for report generation
        """
        try:
            # Patent data (OPS)
            patent_data = ReportDataMapper._extract_patent_data(research)

            # Article data (Scopus)
            article_data = ReportDataMapper._extract_article_data(research)

            # Metrics aggregation
            metrics_data = ReportDataMapper._extract_metrics(research)

            # Combined data
            combined = {
                "theme": research.title,
                "description": research.description or "",
                "area_of_study": (
                    research.chosen_candidate.get("area_of_study")
                    if research.chosen_candidate
                    else ""
                ),
                "keywords": (
                    research.chosen_candidate.get("keywords", [])
                    if research.chosen_candidate
                    else []
                ),
                "period_start": research.user_input.get("period_start"),
                "period_end": research.user_input.get("period_end"),
                "apis_used": ReportDataMapper._get_apis_used(research),
                # Patent data
                "patent_data": patent_data,
                # Article data
                "scientific_data": article_data,
                # Metrics
                "metrics": metrics_data,
                # S-Curve and trends
                "s_curve_data": ReportDataMapper._extract_s_curve(research),
            }

            logger.info(
                "research_data_mapped",
                research_id=research.research_id,
                patents=len(research.patent_documents),
                articles=len(research.scholarly_documents),
            )

            return combined

        except Exception as exc:
            logger.error(
                "research_data_mapping_failed",
                error=str(exc),
                research_id=research.research_id,
            )
            return {}

    @staticmethod
    def _extract_patent_data(research: Research) -> dict[str, Any]:
        """Extract and aggregate patent data from OPS."""
        try:
            patents = research.patent_documents or []

            # Count by year
            by_year = {}
            for patent in patents:
                year = patent.year
                if year:
                    by_year[year] = by_year.get(year, 0) + 1

            # Top applicants
            applicants = {}
            for patent in patents:
                if patent.applicants:
                    for app in patent.applicants:
                        applicants[app] = applicants.get(app, 0) + 1

            top_applicants = sorted(applicants.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]

            # Top CPC codes
            cpcs = {}
            for patent in patents:
                if patent.cpc_codes:
                    for cpc in patent.cpc_codes:
                        cpcs[cpc] = cpcs.get(cpc, 0) + 1

            top_cpcs = sorted(cpcs.items(), key=lambda x: x[1], reverse=True)[:10]

            # Top inventors
            inventors = {}
            for patent in patents:
                if patent.inventors:
                    for inv in patent.inventors:
                        inventors[inv] = inventors.get(inv, 0) + 1

            top_inventors = sorted(inventors.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]

            return {
                "patent_count": len(patents),
                "patent_by_year": by_year,
                "top_applicants": [
                    {"name": name, "count": count} for name, count in top_applicants
                ],
                "top_inventors": [
                    {"name": name, "count": count} for name, count in top_inventors
                ],
                "top_cpc_codes": [cpc[0] for cpc in top_cpcs[:10]],
                "cpc_distribution": {cpc[0]: cpc[1] for cpc in top_cpcs[:10]},
            }

        except Exception as exc:
            logger.warning("patent_data_extraction_failed", error=str(exc))
            return {}

    @staticmethod
    def _extract_article_data(research: Research) -> dict[str, Any]:
        """Extract and aggregate article data from Scopus."""
        try:
            articles = research.scholarly_documents or []

            # Count by year
            by_year = {}
            for article in articles:
                year = article.year
                if year:
                    by_year[year] = by_year.get(year, 0) + 1

            # Top journals
            journals = {}
            for article in articles:
                if article.journal_or_source:
                    journals[article.journal_or_source] = (
                        journals.get(article.journal_or_source, 0) + 1
                    )

            top_journals = sorted(journals.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]

            # Top fields of study
            fields = {}
            for article in articles:
                if article.field_of_study:
                    for field in article.field_of_study:
                        fields[field] = fields.get(field, 0) + 1

            top_fields = sorted(fields.items(), key=lambda x: x[1], reverse=True)[:10]

            # Top authors
            authors = {}
            for article in articles:
                if article.authors:
                    for author in article.authors:
                        authors[author] = authors.get(author, 0) + 1

            top_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:10]

            # Citation stats
            citations_sum = sum(a.citations or 0 for a in articles)
            avg_citations = (
                citations_sum / len(articles) if articles else 0
            )

            return {
                "article_count": len(articles),
                "article_by_year": by_year,
                "top_journals": [
                    {"journal": name, "count": count} for name, count in top_journals
                ],
                "top_fields": [field[0] for field in top_fields[:10]],
                "field_distribution": {field[0]: field[1] for field in top_fields[:10]},
                "top_authors": [
                    {"author": name, "count": count} for name, count in top_authors
                ],
                "citations": {
                    "total": citations_sum,
                    "average": round(avg_citations, 2),
                },
            }

        except Exception as exc:
            logger.warning("article_data_extraction_failed", error=str(exc))
            return {}

    @staticmethod
    def _extract_metrics(research: Research) -> dict[str, Any]:
        """Extract aggregated metrics from ResearchMetrics."""
        try:
            if not research.metrics:
                return {}

            metrics = research.metrics

            return {
                "patent_by_applicant": metrics.patent_by_applicant or {},
                "patent_by_ipc": metrics.patent_by_ipc or {},
                "patent_by_legal_status": metrics.patent_by_legal_status or {},
                "article_by_journal": metrics.article_by_journal or {},
                "article_by_field": metrics.article_by_field or {},
                "top_patent_applicants": metrics.top_patent_applicants or [],
                "top_article_authors": metrics.top_article_authors or [],
                "patent_growth_trend": metrics.patent_growth_trend or {},
                "article_growth_trend": metrics.article_growth_trend or {},
            }

        except Exception as exc:
            logger.warning("metrics_extraction_failed", error=str(exc))
            return {}

    @staticmethod
    def _extract_s_curve(research: Research) -> dict[str, Any]:
        """Extract S-curve data for technology lifecycle."""
        try:
            if not research.metrics or not research.metrics.patent_growth_trend:
                return {}

            trend = research.metrics.patent_growth_trend

            # Determine phase based on growth trend
            # (Este é um exemplo simplificado; ajuste conforme necessário)
            growth_rate = trend.get("growth_rate", 0)

            if growth_rate > 0.2:
                phase = "GROWTH"
            elif growth_rate > 0.05:
                phase = "EMERGING"
            elif growth_rate > -0.05:
                phase = "MATURITY"
            else:
                phase = "DECLINE"

            return {
                "phase": phase,
                "growth_rate": round(growth_rate, 3),
                "peak_year": trend.get("peak_year"),
                "trend": trend,
            }

        except Exception as exc:
            logger.warning("s_curve_extraction_failed", error=str(exc))
            return {}

    @staticmethod
    def _get_apis_used(research: Research) -> list[str]:
        """Determine which APIs were used based on results."""
        apis = []

        if research.patent_results_count and research.patent_results_count > 0:
            apis.append("OPS")

        if research.scholarly_results_count and research.scholarly_results_count > 0:
            apis.append("Scopus")

        return apis

    @staticmethod
    def convert_all_results_to_rag_documents(
        research: Research,
        max_patents: int = 50,
        max_articles: int = 50,
    ) -> list[dict]:
        """
        Convert all patents and articles to RAG documents.

        Args:
            research: Research record
            max_patents: Maximum patents to include
            max_articles: Maximum articles to include

        Returns:
            List of documents for RAG indexing
        """
        documents = []

        # Patent documents from OPS
        for patent in (research.patent_documents or [])[:max_patents]:
            doc_text = f"""
Título: {patent.title}

Resumo: {patent.abstract or 'N/A'}

Aplicantes: {', '.join(patent.applicants or [])}

Inventores: {', '.join(patent.inventors or [])}

Classificação CPC: {', '.join(patent.cpc_codes or [])}

Classificação IPC: {', '.join(patent.ipc_codes or [])}

Ano de Publicação: {patent.year}

Status Legal: {patent.legal_status}

Número de Publicação: {patent.publication_number}
"""
            documents.append(
                {
                    "text": doc_text.strip(),
                    "source": f"Patent_OPS_{patent.publication_number}",
                    "type": "patent",
                    "year": patent.year,
                    "api": "OPS",
                }
            )

        # Article documents from Scopus
        for article in (research.scholarly_documents or [])[:max_articles]:
            doc_text = f"""
Título: {article.title}

Resumo: {article.abstract or 'N/A'}

Autores: {', '.join(article.authors or [])}

Afiliações: {', '.join(article.affiliations or [])}

Periódico: {article.journal_or_source or 'N/A'}

Campos de Estudo: {', '.join(article.field_of_study or [])}

Palavras-chave: {', '.join(article.keywords or [])}

Ano de Publicação: {article.year}

Citações: {article.citations or 0}

DOI: {article.doi or 'N/A'}
"""
            documents.append(
                {
                    "text": doc_text.strip(),
                    "source": f"Article_Scopus_{article.doi or article.id}",
                    "type": "article",
                    "year": article.year,
                    "api": "Scopus",
                }
            )

        logger.info(
            "rag_documents_created",
            patents=len([d for d in documents if d["type"] == "patent"]),
            articles=len([d for d in documents if d["type"] == "article"]),
        )

        return documents
