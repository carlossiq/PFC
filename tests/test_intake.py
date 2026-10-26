"""
Tests for intake validation and models.
"""

import pytest

from schemas.intake import InputIntake


def test_intake_requires_theme():
    """
    Verifica que tema é obrigatório.
    """
    with pytest.raises(ValueError):
        InputIntake(theme="")


def test_intake_strips_theme_whitespace():
    """
    Verifica que o tema é normalizado (espaços nas pontas removidos).
    """
    intake = InputIntake(theme="  test  ")
    assert intake.theme == "test"


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
    Verifica que keywords repetidas são removidas (duplicata exata).
    """
    intake = InputIntake(
        theme="test",
        keywords=["ai", "AI", "machine learning", "machine learning"],
    )
    assert sorted(intake.keywords) == sorted({"ai", "AI", "machine learning"})


def test_intake_removes_empty_keywords():
    """
    Verifica remoção de keywords vazias.
    """
    intake = InputIntake(
        theme="test",
        keywords=["", "  ", "valid_keyword"],
    )
    assert intake.keywords == ["valid_keyword"]
