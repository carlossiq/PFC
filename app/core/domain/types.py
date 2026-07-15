from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# --- Embedding ---
# Replaces np.ndarray; adapters convert numpy arrays before returning to the domain.
Embedding = list[float]


# --- Search ---

@dataclass
class SearchResult:
    api_name: str
    success: bool
    query: str
    results: list[dict[str, Any]] = field(default_factory=list)
    total_count: Optional[int] = None
    results_returned: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    duration_seconds: float = 0.0
    run_id: Optional[str] = None


@dataclass
class SearchError:
    api_name: str
    error_code: str
    error_message: str
    is_retryable: bool
    run_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None


# --- LLM ---
# Pure-Python mirrors of schemas/intake.py (InputIntake) and schemas/llm.py (LLMOutput).
# Adapters are responsible for converting InputIntake → LLMRequest and
# LLMResponse → LLMOutput at the boundary.

@dataclass
class LLMRequest:
    theme: str
    description: Optional[str] = None
    area_of_study: Optional[str] = None
    keywords: list[str] = field(default_factory=list)


@dataclass
class LLMUsage:
    """Duração e tokens de uma chamada real (ou mock) à LLM, medidos na origem."""

    provider: str
    model: str
    duration_ms: float
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


@dataclass
class TermGroup:
    terms: list[str] = field(default_factory=list)
    operator: str = "OR"  # "AND" | "OR"


@dataclass
class TextualQuery:
    groups: list[TermGroup] = field(default_factory=list)
    group_operator: str = "AND"  # "AND" | "OR"


@dataclass
class LLMResponse:
    # Textual fields
    title: TextualQuery = field(default_factory=TextualQuery)
    abstract: TextualQuery = field(default_factory=TextualQuery)
    claims: TextualQuery = field(default_factory=TextualQuery)
    description: TextualQuery = field(default_factory=TextualQuery)
    full_text: TextualQuery = field(default_factory=TextualQuery)
    # Simple fields — list[str] directly (SimpleFieldQuery.values unwrapped)
    ipc: list[str] = field(default_factory=list)
    cpc: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    affiliation: list[str] = field(default_factory=list)
    applicant: list[str] = field(default_factory=list)
    inventor: list[str] = field(default_factory=list)
    field_of_study: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    source_title: list[str] = field(default_factory=list)
    year: list[str] = field(default_factory=list)
