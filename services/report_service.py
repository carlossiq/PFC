"""
Report generation service using Ollama and RAG.

Generates technology prospecting reports in REPTEC/AGITEC style.
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from db.research_models import Research

from core.logging import get_logger
from prompts.report_prompts import (
    REPORT_SYSTEM_PROMPT,
    get_section_prompt,
)
from services.ollama_service import OllamaService
from services.rag_service import RAGService
from services.report_data_mapper import ReportDataMapper

logger = get_logger(__name__)

# Report sections in order
REPORT_SECTIONS = [
    ("Finalidade", "finalidade"),
    ("Referências", "referencias"),
    ("Objetivo", "objetivo"),
    ("Introdução", "introducao"),
    ("Metodologia", "metodologia"),
    ("Informações Científicas", "informacoes_cientificas"),
    ("Informações Tecnológicas", "informacoes_tecnologicas"),
    ("Tendências e Ciclo de Vida da Tecnologia", "tendencias_ciclo_vida"),
    ("Conclusão", "conclusao"),
    ("Referências Bibliográficas", "referencias_bibliograficas"),
]


class ReportGenerationError(Exception):
    """Error during report generation."""

    pass


class ReportService:
    """Service for generating technology prospecting reports."""

    def __init__(
        self,
        ollama_service: OllamaService,
        rag_service: RAGService,
    ):
        """
        Initialize report service.

        Args:
            ollama_service: OllamaService instance
            rag_service: RAGService instance
        """
        self.ollama = ollama_service
        self.rag = rag_service

    async def generate_full_report(
        self,
        theme: str,
        description: str = "",
        data: dict[str, Any] = None,
        chart_paths: dict[str, str] = None,
        metadata: dict[str, Any] = None,
    ) -> str:
        """
        Generate complete report with all sections.

        Args:
            theme: Research theme
            description: Description of research
            data: Aggregated research data
            chart_paths: Paths to generated charts
            metadata: Additional metadata

        Returns:
            Complete report in Markdown
        """
        if data is None:
            data = {}
        if chart_paths is None:
            chart_paths = {}
        if metadata is None:
            metadata = {}

        logger.info("report_generation_start", theme=theme)

        try:
            # Check Ollama health
            if not await self.ollama.health_check():
                raise ReportGenerationError(
                    "Ollama server not running. Start with: ollama serve"
                )

            # Build report header
            header = self._build_report_header(theme, description, metadata)

            # Generate each section
            sections_content = []
            for section_name, section_type in REPORT_SECTIONS:
                logger.info("generating_section", section=section_name)

                try:
                    section_content = await self.generate_section(
                        section_name=section_name,
                        section_type=section_type,
                        theme=theme,
                        data=data,
                        chart_paths=chart_paths,
                    )
                    sections_content.append(section_content)
                except Exception as exc:
                    logger.warning(
                        "section_generation_failed",
                        section=section_name,
                        error=str(exc),
                    )
                    # Add placeholder for failed section
                    sections_content.append(f"\n## {section_name}\n\n[Seção não gerada: {str(exc)}]\n")

            # Add chart section
            charts_section = self._build_charts_section(chart_paths)
            if charts_section:
                sections_content.append(charts_section)

            # Combine all sections
            full_report = header + "\n\n" + "\n\n".join(sections_content)

            logger.info("report_generation_success")
            return full_report

        except ReportGenerationError as exc:
            logger.error("report_generation_error", error=str(exc))
            raise
        except Exception as exc:
            logger.error("report_generation_unexpected_error", error=str(exc))
            raise ReportGenerationError(f"Erro na geração do relatório: {str(exc)}")

    async def generate_section(
        self,
        section_name: str,
        section_type: str,
        theme: str,
        data: dict[str, Any],
        chart_paths: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Generate a single report section.

        Args:
            section_name: Display name of section
            section_type: Type identifier for prompt selection
            theme: Research theme
            data: Research data
            chart_paths: Optional chart paths

        Returns:
            Section content in Markdown
        """
        if chart_paths is None:
            chart_paths = {}

        try:
            # Retrieve context from RAG
            context = await self.rag.get_context_for_section(
                section_name=section_name,
                section_description=f"Informações sobre {theme}",
                top_k=5,
            )

            # Generate prompt
            prompt = get_section_prompt(
                section_name=section_name,
                section_type=section_type,
                theme=theme,
                context=context or "[Contexto não disponível]",
                data=data,
            )

            # Generate text
            section_text = await self.ollama.generate_text(
                prompt=prompt,
                system=REPORT_SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=2000,
            )

            # Format section
            formatted_section = f"## {section_name}\n\n{section_text}"

            return formatted_section

        except Exception as exc:
            logger.error(
                "generate_section_error",
                section=section_name,
                error=str(exc),
            )
            raise

    async def generate_section_sync(
        self,
        section_name: str,
        section_type: str,
        theme: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate section and return structured response.

        Args:
            section_name: Section name
            section_type: Section type
            theme: Research theme
            data: Research data

        Returns:
            Dict with section content and metadata
        """
        try:
            content = await self.generate_section(
                section_name=section_name,
                section_type=section_type,
                theme=theme,
                data=data,
            )

            return {
                "success": True,
                "section": section_name,
                "content": content,
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as exc:
            logger.error("section_sync_generation_failed", error=str(exc))
            return {
                "success": False,
                "section": section_name,
                "error": str(exc),
                "generated_at": datetime.utcnow().isoformat(),
            }

    async def generate_report_from_research(
        self,
        research: "Research",
        chart_paths: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Generate complete report from Research object (OPS + Scopus consolidated).

        Handles the full workflow:
        1. Consolidate OPS and Scopus data using ReportDataMapper
        2. Create RAG documents from both patent and article sources
        3. Index documents in RAG
        4. Generate report with consolidated data

        Args:
            research: Research object from database
            chart_paths: Optional paths to visualization charts

        Returns:
            Complete report in Markdown format
        """
        try:
            logger.info(
                "research_report_generation_start",
                research_id=research.research_id,
            )

            # Consolidate data from OPS (patents) and Scopus (articles)
            consolidated_data = ReportDataMapper.map_complete_research_data(research)

            # Create RAG documents from both sources
            rag_documents = (
                ReportDataMapper.convert_all_results_to_rag_documents(research)
            )

            # Index documents in RAG
            chunk_count = await self.add_documents_to_rag(rag_documents)
            logger.info(
                "research_documents_indexed",
                research_id=research.research_id,
                chunks=chunk_count,
            )

            # Generate report with consolidated data
            report = await self.generate_full_report(
                theme=consolidated_data["theme"],
                description=consolidated_data["description"],
                data=consolidated_data,
                chart_paths=chart_paths or {},
                metadata={
                    "area_of_study": consolidated_data["area_of_study"],
                    "keywords": consolidated_data["keywords"],
                    "period_start": consolidated_data["period_start"],
                    "period_end": consolidated_data["period_end"],
                },
            )

            logger.info(
                "research_report_generation_success",
                research_id=research.research_id,
            )
            return report

        except Exception as exc:
            logger.error(
                "research_report_generation_failed",
                error=str(exc),
                research_id=research.research_id,
            )
            raise ReportGenerationError(
                f"Erro ao gerar relatório para pesquisa {research.research_id}: {str(exc)}"
            )

    def _build_report_header(
        self,
        theme: str,
        description: str,
        metadata: dict[str, Any],
    ) -> str:
        """
        Build report header with title and metadata.

        Args:
            theme: Research theme
            description: Research description
            metadata: Additional metadata

        Returns:
            Formatted report header
        """
        timestamp = datetime.utcnow().strftime("%d de %B de %Y")
        title = f"# Relatório de Prospecção Tecnológica: {theme}"

        parts = [title, ""]

        if description:
            parts.append(f"**Descrição:** {description}")
            parts.append("")

        parts.append(f"**Data de Geração:** {timestamp}")
        parts.append(f"**Período de Análise:** {metadata.get('period_start', 'N/A')} a {metadata.get('period_end', 'N/A')}")

        area = metadata.get("area_of_study", "")
        if area:
            parts.append(f"**Área de Estudo:** {area}")

        keywords = metadata.get("keywords", [])
        if keywords:
            parts.append(f"**Palavras-chave:** {', '.join(keywords)}")

        parts.append("")
        parts.append("---")

        return "\n".join(parts)

    def _build_charts_section(self, chart_paths: dict[str, str]) -> str:
        """
        Build section with embedded chart references.

        Args:
            chart_paths: Dict of chart names and paths

        Returns:
            Formatted charts section
        """
        if not chart_paths:
            return ""

        parts = [
            "\n## Visualizações e Gráficos",
            "",
            "Esta seção contém os gráficos gerados durante a análise:",
            "",
        ]

        for chart_name, chart_path in chart_paths.items():
            # Format chart reference
            parts.append(f"### {chart_name}")
            parts.append("")
            parts.append(f"![{chart_name}]({chart_path})")
            parts.append("")

        return "\n".join(parts)

    async def add_documents_to_rag(self, documents: list[dict]) -> int:
        """
        Add documents to RAG for retrieval.

        Args:
            documents: List of dicts with 'text' key

        Returns:
            Number of chunks indexed
        """
        try:
            chunk_count = await self.rag.index_documents(documents)
            logger.info("documents_added_to_rag", chunks=chunk_count)
            return chunk_count
        except Exception as exc:
            logger.error("add_documents_error", error=str(exc))
            raise

    async def clear_rag(self) -> bool:
        """
        Clear all documents from RAG.

        Returns:
            True if successful
        """
        return await self.rag.clear_collection()

    def get_rag_stats(self) -> dict[str, Any]:
        """
        Get RAG collection statistics.

        Returns:
            Collection stats
        """
        return self.rag.get_stats()

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of all services.

        Returns:
            Health status of Ollama and RAG
        """
        ollama_healthy = await self.ollama.health_check()
        rag_stats = self.get_rag_stats()

        return {
            "ollama": {
                "healthy": ollama_healthy,
                "status": "OK" if ollama_healthy else "ERRO",
            },
            "rag": rag_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
