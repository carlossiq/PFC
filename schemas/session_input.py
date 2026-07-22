"""
Schemas for saving a prospecting session's input parameters - either partially,
mid-wizard ("save progress", completed=False), or as a full finalization
(completed=True). The same request/response shape backs both the create path
(POST /session-input) and the update path (PUT /research-session/{id}).
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class SessionInputRoot(BaseModel):
    """Input original do usuário (Step1), raiz da cadeia de session_input."""

    theme: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Tema principal da prospecção tecnológica (obrigatório)",
    )
    description: Optional[str] = Field(default=None, max_length=2000)
    area_of_study: Optional[str] = Field(default=None, max_length=500)
    keywords: Optional[list[str]] = Field(default=None, max_items=50)
    year_from: Optional[int] = Field(default=None)
    year_to: Optional[int] = Field(default=None)

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str) -> str:
        return value.strip()

    @field_validator("description", "area_of_study", mode="before")
    @classmethod
    def validate_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            return stripped if stripped else None
        return None

    @field_validator("keywords", mode="before")
    @classmethod
    def validate_keywords(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return None
        normalized = [kw.strip() for kw in value if isinstance(kw, str) and kw.strip()]
        return list(set(normalized)) if normalized else None


class SessionInputGenerated(BaseModel):
    """Variante gerada/refinada por IA escolhida para seguir adiante."""

    theme: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=2000)
    iterations: int = Field(default=0, ge=0)


class TermInput(BaseModel):
    """
    Termo extraído por NLP local (spaCy + KeyBERT + TF-IDF, não é IA) na Amostragem de Termos, a partir dos
    documentos de uma probe query, com a flag `selected` indicando se o
    usuário marcou esse termo pra usar na construção da query final. Ver
    ProbeQueryTerm.
    """

    term: str = Field(..., min_length=1, max_length=255)
    score: float
    frequency: int = Field(default=0, ge=0)
    selected: bool = Field(default=False)


class SessionProbeQueryInput(BaseModel):
    """
    Query do Step3 (patente ou artigo) selecionada pelo usuário, ou a query
    final escolhida na Amostragem de Termos/Escolha da Query Final -
    diferenciadas por `tipo` (None = probe, "specific"|"balanced"|"generic"
    = a variante final escolhida). Ver SessionProbeQuery.
    """

    fonte: str = Field(..., pattern="^(ops|scopus)$")
    tipo: Optional[str] = Field(default=None, pattern="^(specific|balanced|generic)$")
    query_text: str = Field(..., min_length=1)
    fields: Optional[dict[str, list[str]]] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    complexity_score: Optional[float] = None
    complexity_level: Optional[str] = None
    iterations: int = Field(default=1, ge=1)
    result_count: Optional[int] = Field(default=None, ge=0)
    patents: list[dict[str, Any]] = Field(default_factory=list, max_items=200)
    articles: list[dict[str, Any]] = Field(default_factory=list, max_items=200)
    # Termos da Amostragem de Termos (todos os extraídos, com `selected`
    # marcando os escolhidos) - só preenchido em linhas de probe (tipo=None).
    terms: list[TermInput] = Field(default_factory=list, max_items=100)


class SessionAiCallInput(BaseModel):
    """Uma chamada de IA (refino de tema, especificação, geração de query
    probe/final) medida no backend e reenviada pelo frontend junto do save -
    sempre acrescentada como linha nova (log), nunca upsertada."""

    step: str = Field(..., max_length=50)
    provider: str = Field(..., max_length=50)
    model: str = Field(..., max_length=100)
    duration_ms: float = Field(..., ge=0)
    input_tokens: Optional[int] = Field(default=None, ge=0)
    output_tokens: Optional[int] = Field(default=None, ge=0)
    total_tokens: Optional[int] = Field(default=None, ge=0)
    attempts: int = Field(default=1, ge=1)


class SessionAiCallRow(SessionAiCallInput):
    """Representação persistida de uma linha session_ai_call."""

    id: int
    session_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SessionProbeQueryRow(SessionProbeQueryInput):
    """Representação persistida de uma linha session_probe_query."""

    id: int
    session_id: int
    result_count: Optional[int] = None
    # Documentos persistidos (patent/article) vinculados a essa query,
    # reconstruídos no formato "cru" que o probe search devolveria (ver
    # patent_to_raw_item/article_to_raw_item) - só populado por GET
    # /research-session/{id} (retomar sessão), não faz parte do payload de save.
    documents: list[dict[str, Any]] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SessionInputSaveRequest(BaseModel):
    """Payload enviado ao salvar/atualizar uma sessão: nome + input raiz +
    gerado (opcional) + queries de probe (opcionais) + se a sessão deve ficar
    marcada como concluída ou apenas salva em progresso."""

    name: str = Field(..., min_length=1, max_length=255)
    root: SessionInputRoot
    generated: Optional[SessionInputGenerated] = None
    # Até 4: 1 linha de probe + 1 de query final, por fonte (ops/scopus).
    probe_queries: list[SessionProbeQueryInput] = Field(default_factory=list, max_items=4)
    ai_calls: list[SessionAiCallInput] = Field(default_factory=list)
    completed: bool = Field(default=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip()


class SessionInputRow(BaseModel):
    """Representação persistida de uma linha session_input."""

    id: int
    session_id: int
    parent_id: Optional[int] = None
    theme: str
    description: Optional[str] = None
    area_of_study: Optional[str] = None
    keywords: Optional[list[str]] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    iterations: int

    class Config:
        from_attributes = True


class SessionInputSaveResponse(BaseModel):
    """Resultado do save/update: sessão + linhas de input persistidas."""

    session_id: int
    session_public_id: str
    session_name: str
    completed: bool
    root: SessionInputRow
    generated: Optional[SessionInputRow] = None
    probe_queries: list[SessionProbeQueryRow] = Field(default_factory=list)
    ai_calls: list[SessionAiCallRow] = Field(default_factory=list)
