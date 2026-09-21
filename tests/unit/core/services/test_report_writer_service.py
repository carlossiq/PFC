import pytest

from app.core.services.report_writer_service import (
    AI_SECTIONS,
    RAGUnavailableError,
    ReportWriterService,
    escape_latex,
)
from core.config import Settings


class FakeRAGService:
    """RAGService fake em memória - substitui ChromaDB nos testes."""

    def __init__(self) -> None:
        self.indexed_sessions: set[str] = set()
        self.index_calls: list[list[dict]] = []
        self.last_query_filter: dict | None = None

    async def query(self, query_text: str, top_k: int, filter_metadata: dict | None = None) -> list[dict]:
        self.last_query_filter = filter_metadata
        session_id = (filter_metadata or {}).get("session_id")
        if session_id in self.indexed_sessions:
            return [{"text": "chunk", "relevance_score": 0.9, "metadata": {"session_id": session_id}}]
        return []

    async def index_documents(self, documents: list[dict]) -> int:
        self.index_calls.append(documents)
        for doc in documents:
            self.indexed_sessions.add(doc["session_id"])
        return len(documents)

    async def get_context_for_section(
        self, section_name: str, section_description: str, top_k: int, filter_metadata: dict | None = None
    ) -> str:
        self.last_query_filter = filter_metadata
        return f"contexto para {section_name}"

    async def clear_by_metadata(self, filter_metadata: dict) -> None:
        session_id = filter_metadata.get("session_id")
        self.indexed_sessions.discard(session_id)


class FakeTextGeneration:
    def __init__(self, response: str = "Texto gerado pela IA.") -> None:
        self.response = response
        self.calls: list[tuple[str, str | None]] = []

    async def generate(self, prompt: str, system: str | None = None) -> str:
        self.calls.append((prompt, system))
        return self.response


class FakeLLMResolver:
    """Substitui LLMConfigResolver nos testes - resolve_text_generation
    sempre devolve o mesmo FakeTextGeneration, independente do call_site."""

    def __init__(self, text_generation: FakeTextGeneration) -> None:
        self._text_generation = text_generation

    async def resolve_text_generation(self, call_site: str) -> FakeTextGeneration:
        return self._text_generation


@pytest.fixture
def settings() -> Settings:
    return Settings(rag_top_k_per_section=3)


@pytest.fixture
def rag() -> FakeRAGService:
    return FakeRAGService()


@pytest.fixture
def text_generation() -> FakeTextGeneration:
    return FakeTextGeneration()


@pytest.fixture
def llm_resolver(text_generation) -> FakeLLMResolver:
    return FakeLLMResolver(text_generation)


@pytest.fixture
def svc(rag, llm_resolver, settings) -> ReportWriterService:
    return ReportWriterService(rag=rag, llm_resolver=llm_resolver, settings=settings)


# ---- escape_latex ----


def test_escape_latex_escapes_special_characters():
    assert escape_latex("100% & R&D_cost $5") == r"100\% \& R\&D\_cost \$5"


def test_escape_latex_empty_string():
    assert escape_latex("") == ""


# ---- AI_SECTIONS / ai_section_keys ----


def test_ai_section_keys_matches_seven_sections():
    assert len(ReportWriterService.ai_section_keys()) == 7
    assert set(ReportWriterService.ai_section_keys()) == set(AI_SECTIONS.keys())


def test_is_ai_section_rejects_static_sections():
    assert ReportWriterService.is_ai_section("finalidade") is True
    assert ReportWriterService.is_ai_section("metodologia") is False
    assert ReportWriterService.is_ai_section("referencias_bibliograficas") is False


# ---- ensure_session_indexed ----


@pytest.mark.asyncio
async def test_ensure_session_indexed_indexes_when_not_already(svc, rag):
    patents = [{"title": "T", "abstract": "A" * 150}]
    await svc.ensure_session_indexed(1, patents, [])
    assert len(rag.index_calls) == 1
    assert rag.index_calls[0][0]["session_id"] == "1"
    assert rag.index_calls[0][0]["document_type"] == "patent"


@pytest.mark.asyncio
async def test_ensure_session_indexed_skips_if_already_indexed(svc, rag):
    rag.indexed_sessions.add("1")
    await svc.ensure_session_indexed(1, [{"title": "T", "abstract": "A"}], [])
    assert len(rag.index_calls) == 0


@pytest.mark.asyncio
async def test_ensure_session_indexed_raises_when_rag_unavailable(text_generation, settings):
    svc = ReportWriterService(rag=None, llm_resolver=FakeLLMResolver(text_generation), settings=settings)
    with pytest.raises(RAGUnavailableError):
        await svc.ensure_session_indexed(1, [], [])


@pytest.mark.asyncio
async def test_reindex_session_clears_before_indexing(svc, rag):
    rag.indexed_sessions.add("1")
    await svc.reindex_session(1, [{"title": "T", "abstract": "A" * 150}], [])
    assert len(rag.index_calls) == 1


# ---- build_rag_context ----


@pytest.mark.asyncio
async def test_build_rag_context_filters_by_session_id(svc, rag):
    context = await svc.build_rag_context(42, "introducao")
    assert rag.last_query_filter == {"session_id": "42"}
    assert "Introdução" in context


@pytest.mark.asyncio
async def test_build_rag_context_rejects_invalid_section(svc):
    with pytest.raises(ValueError):
        await svc.build_rag_context(1, "metodologia")


# ---- generate_section_text ----


@pytest.mark.asyncio
async def test_generate_section_text_calls_text_generation_and_escapes(svc, text_generation):
    text_generation.response = "Crescimento de 10% ao ano & mais."
    result = await svc.generate_section_text("conclusao", "Tema X", "contexto", {})
    assert result == r"Crescimento de 10\% ao ano \& mais."
    assert len(text_generation.calls) == 1
    prompt, system = text_generation.calls[0]
    assert "Tema X" in prompt
    assert system is not None


@pytest.mark.asyncio
async def test_generate_section_text_rejects_invalid_section(svc):
    with pytest.raises(ValueError):
        await svc.generate_section_text("referencias", "Tema", "contexto", {})
