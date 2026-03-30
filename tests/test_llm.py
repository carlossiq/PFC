"""
Tests for LLM services and factories.
"""

import pytest

from schemas.intake import InputIntake
from services.llm import LLMServiceFactory, LLMOutputNormalizer


@pytest.mark.asyncio
async def test_llm_factory_creates_instance():
    """
    Verifica que factory cria instância de LLM.
    """
    llm = LLMServiceFactory.create(provider="mock")
    assert llm is not None
    assert llm.provider_name == "mock"


@pytest.mark.asyncio
async def test_llm_factory_returns_mock_in_test_mode(test_mode_enabled):
    """
    Verifica que TEST_MODE força uso de MockLLMService.
    """
    llm = LLMServiceFactory.create(provider="anthropic")
    assert llm.provider_name == "mock"


@pytest.mark.asyncio
async def test_mock_llm_processes_intake():
    """
    Verifica que mock LLM processa intake corretamente.
    """
    llm = LLMServiceFactory.create(provider="mock")
    intake = InputIntake(theme="machine learning")

    output = await llm.process_intake(
        intake=intake,
        system_prompt="test prompt",
    )

    assert output is not None
    assert output.has_any_queries()


def test_llm_output_normalizer_removes_empty_terms():
    """
    Verifica que normalizador remove termos vazios.
    """
    from schemas.llm import TextualFieldQuery, TermGroup

    field = TextualFieldQuery(
        groups=[
            TermGroup(terms=["valid", "", "  ", "valid2"]),
        ]
    )

    normalized = LLMOutputNormalizer._normalize_textual_field(
        field,
        "test_field",
    )

    assert "valid" in [t for group in normalized.groups for t in group.terms]
    assert "" not in [t for group in normalized.groups for t in group.terms]


def test_llm_output_normalizer_removes_short_terms():
    """
    Verifica que termos com menos de 2 caracteres são removidos.
    """
    from schemas.llm import SimpleFieldQuery

    field = SimpleFieldQuery(values=["a", "ab", "abc", "a "])

    normalized = LLMOutputNormalizer._normalize_simple_field(field)

    assert all(len(v) >= 2 for v in normalized.values)
    assert "abc" in normalized.values


def test_llm_output_normalizer_deduplicates():
    """
    Verifica que normalizador remove duplicatas.
    """
    from schemas.llm import SimpleFieldQuery

    field = SimpleFieldQuery(values=["test", "test", "TEST", "other"])

    normalized = LLMOutputNormalizer._normalize_simple_field(field)

    assert "test" in normalized.values
    assert len([v for v in normalized.values if v == "test"]) == 1
