"""
Tests for intake validation and models.
"""

import pytest

from schemas.intake import InputIntake, DocumentTypeEnum


def test_intake_requires_theme():
    """
    Verifica que tema é obrigatório.
    """
    with pytest.raises(ValueError):
        InputIntake(theme="")


def test_intake_normalizes_document_type():
    """
    Verifica que document_type é normalizado para 'both'.
    """
    intake = InputIntake(
        theme="test",
        document_type="patent",
    )
    assert intake.document_type == DocumentTypeEnum.BOTH


def test_intake_validates_theme_length():
    """
    Verifica validação de comprimento do tema.
    """
    # Válido
    intake = InputIntake(theme="A" * 500)
    assert intake.theme is not None

    # Inválido (muito longo)
    with pytest.raises(ValueError):
        InputIntake(theme="A" * 501)


def test_intake_deduplicates_keywords():
    """
    Verifica que keywords são dedupadas.
    """
    intake = InputIntake(
        theme="test",
        initial_keywords=["ai", "AI", "machine learning", "machine learning"],
    )
    # Keywords devem ser dedupadas (case-insensitive)
    assert len(intake.initial_keywords) <= 3


def test_intake_removes_empty_keywords():
    """
    Verifica remoção de keywords vazias.
    """
    intake = InputIntake(
        theme="test",
        initial_keywords=["", "  ", "valid_keyword"],
    )
    assert "valid_keyword" in intake.initial_keywords
    assert len(intake.initial_keywords) == 1
