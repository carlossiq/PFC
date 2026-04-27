"""
Schemas for report generation requests and responses.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ReportGenerationRequest(BaseModel):
    """Request to generate a technology prospecting report."""

    theme: str = Field(..., description="Research theme/topic")
    description: Optional[str] = Field(
        None,
        description="Detailed description of the research",
    )
    area_of_study: Optional[str] = Field(
        None,
        description="Area of study or field",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Key words/terms for the research",
    )
    period_start: Optional[int] = Field(
        None,
        description="Start year of analysis period",
    )
    period_end: Optional[int] = Field(
        None,
        description="End year of analysis period",
    )

    # Scientific data
    scientific_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated scientific data (articles, authors, journals)",
    )

    # Patent data
    patent_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated patent data (patents, applicants, classifications)",
    )

    # S-curve and trends data
    s_curve_data: dict[str, Any] = Field(
        default_factory=dict,
        description="S-curve data (phase, growth rate, peak year)",
    )

    # Chart file paths
    chart_paths: dict[str, str] = Field(
        default_factory=dict,
        description="Paths to generated chart images",
    )

    # References
    references: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of references (books, articles, websites)",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "theme": "Sistemas de Recomendação em E-commerce",
                "description": "Análise de tecnologias para personalização em varejo online",
                "area_of_study": "Inteligência Artificial, E-commerce",
                "keywords": ["recommendation", "personalization", "machine learning"],
                "period_start": 2018,
                "period_end": 2024,
                "scientific_data": {
                    "article_count": 245,
                    "top_journals": [
                        {"journal": "IEEE Transactions", "count": 12}
                    ],
                },
                "patent_data": {
                    "patent_count": 1523,
                    "top_applicants": [
                        {"name": "Company A", "count": 45}
                    ],
                },
                "chart_paths": {
                    "Histórico de Publicações": "charts/timeline.png",
                    "Curva-S": "charts/s_curve.png",
                },
            }
        }


class ReportSectionRequest(BaseModel):
    """Request to generate a single report section."""

    theme: str = Field(..., description="Research theme")
    section_name: str = Field(
        ...,
        description="Section name (e.g., 'Introdução', 'Metodologia')",
    )
    section_type: str = Field(
        ...,
        description="Section type identifier (introducao, metodologia, etc)",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Relevant data for section",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "theme": "Sistemas de Recomendação em E-commerce",
                "section_name": "Introdução",
                "section_type": "introducao",
                "data": {
                    "area_of_study": "Inteligência Artificial",
                    "keywords": ["recommendation", "personalization"],
                },
            }
        }


class RAGIndexRequest(BaseModel):
    """Request to index documents in RAG."""

    documents: list[dict[str, Any]] = Field(
        ...,
        description="List of documents to index, each with 'text' key",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "text": "Sistemas de recomendação baseados em filtragem colaborativa...",
                        "source": "Article_2023_01",
                        "type": "article",
                    },
                    {
                        "text": "Método de personalização usando redes neurais...",
                        "source": "Patent_US2023_12345",
                        "type": "patent",
                    },
                ]
            }
        }


class ReportResponse(BaseModel):
    """Response with generated report."""

    success: bool = Field(..., description="Whether generation was successful")
    report: Optional[str] = Field(None, description="Generated report in Markdown")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Generation metadata",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "report": "# Relatório de Prospecção Tecnológica\n\n## Finalidade\n...",
                "metadata": {
                    "generated_at": "2024-04-27T12:00:00Z",
                    "sections_generated": 10,
                },
            }
        }


class ReportSectionResponse(BaseModel):
    """Response with generated section."""

    success: bool = Field(..., description="Whether generation was successful")
    section: str = Field(..., description="Section name")
    content: Optional[str] = Field(None, description="Section content in Markdown")
    error: Optional[str] = Field(None, description="Error message if failed")
    generated_at: str = Field(..., description="Generation timestamp")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "section": "Introdução",
                "content": "## Introdução\n\nOs sistemas de recomendação...",
                "generated_at": "2024-04-27T12:00:00Z",
            }
        }


class HealthCheckResponse(BaseModel):
    """Response with health status."""

    ollama: dict[str, Any] = Field(..., description="Ollama service status")
    rag: dict[str, Any] = Field(..., description="RAG service status")
    timestamp: str = Field(..., description="Check timestamp")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "ollama": {
                    "healthy": True,
                    "status": "OK",
                },
                "rag": {
                    "collection_name": "research_documents",
                    "document_count": 42,
                    "status": "healthy",
                },
                "timestamp": "2024-04-27T12:00:00Z",
            }
        }


class RAGStatsResponse(BaseModel):
    """Response with RAG statistics."""

    collection_name: str = Field(..., description="Collection name")
    document_count: int = Field(..., description="Number of indexed documents")
    db_path: str = Field(..., description="Database path")
    status: str = Field(..., description="Collection status")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "collection_name": "research_documents",
                "document_count": 42,
                "db_path": ".chroma_db",
                "status": "healthy",
            }
        }
