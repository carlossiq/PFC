"""Schemas for the REPTEC/AGITEC LaTeX report document endpoints (POST
/report/{session_id}/sections/{section_key}/rag|generate, /sections/static,
/assemble, /compile-pdf) - separado de schemas/report.py (que cobre só os
PNGs gerados por ReportService)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SectionRagResponse(BaseModel):
    """Resultado de POST /report/{session_id}/sections/{section_key}/rag."""

    section_key: str
    rag_context: str
    status: str


class SectionGenerateResponse(BaseModel):
    """Resultado de POST /report/{session_id}/sections/{section_key}/generate."""

    section_key: str
    generated_text: str
    status: str


class SignatureBlock(BaseModel):
    nome: str = ""
    posto_funcao: str = ""


class SignaturesInput(BaseModel):
    elaborado_por: Optional[SignatureBlock] = None
    revisado_por: Optional[SignatureBlock] = None
    aprovado_por: Optional[SignatureBlock] = None


class StaticSectionsRequest(BaseModel):
    """Corpo de POST /report/{session_id}/sections/static - monta Capa,
    Sumário, Metodologia, Referências (administrativas), Referências
    Bibliográficas e Assinaturas localmente, sem LLM/RAG (ver
    config/prompts/report_static_sections.py)."""

    numero: str = Field(..., description="Número do REPTEC, ex.: '001'")
    ano: str = Field(..., description="Ano do REPTEC, ex.: '2026'")
    referencias_administrativas: list[str] = Field(
        default_factory=list,
        description="Ex.: 'DIEx Nº 115-A3/DCT de 6 de janeiro de 2023' - editado pelo usuário.",
    )
    referencias_bibliograficas_adicionais: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list, description="Ex.: ['Lens.org', 'Scopus']")
    assinaturas: Optional[SignaturesInput] = None


class StaticSectionsResponse(BaseModel):
    metodologia: str
    referencias_administrativas: list[str]
    referencias_bibliograficas: list[str]


class AssembleRequest(BaseModel):
    """Corpo de POST /report/{session_id}/assemble - dados da capa e
    assinaturas (referências administrativas e demais seções vêm do que já
    foi persistido pelas rotas de seção/estáticas)."""

    numero: str
    ano: str
    tema: str
    referencias_administrativas: list[str] = Field(default_factory=list)
    assinaturas: Optional[SignaturesInput] = None


class AssembleResponse(BaseModel):
    """Resultado de POST /report/{session_id}/assemble - só produz o .tex
    (nunca compila PDF, ver POST /compile-pdf)."""

    tex_object_key: str
    tex_content: str
    sections_missing: list[str] = []
    charts_missing: list[str] = []


class CompilePdfResponse(BaseModel):
    """Resultado de POST /report/{session_id}/compile-pdf - rota separada,
    só chamada quando o usuário decidir compilar."""

    success: bool
    pdf_object_key: Optional[str] = None
    pdf_base64: Optional[str] = None
    log: Optional[str] = None


class LLMTestRequest(BaseModel):
    """Corpo de POST /report/llm-test - sanity check manual do LLM
    configurado em OLLAMA_BASE_URL/OLLAMA_API_KEY/OLLAMA_MODEL (Ollama local
    ou endpoint da intranet), sem sessão/RAG envolvidos."""

    prompt: str = Field(..., min_length=1, description="Texto livre enviado direto ao LLM")
    system: Optional[str] = Field(default=None, description="System prompt opcional")


class LLMTestResponse(BaseModel):
    base_url: str
    model: str
    response: str
