"""Schemas for the report-graphics generation endpoint (POST /report/{session_id}/graphics)."""

from pydantic import BaseModel


class GeneratedChart(BaseModel):
    """Um PNG gerado pelo ReportService."""

    filename: str
    path: str
    chart: str
    document_type: str


class ReportGraphicsResponse(BaseModel):
    """Manifesto dos gráficos gerados (ou pulados por falta de dado) para uma sessão."""

    session_id: int
    output_dir: str
    patents_used: int
    articles_used: int
    charts: list[GeneratedChart] = []
    skipped: list[str] = []
