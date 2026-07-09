"""
Tests for deduplication service.
"""

import pytest

from app.core.services.dedup_service import DedupService


def test_dedup_service_deduplicates_patents():
    """
    Verifica deduplicação de patentes.
    """
    service = DedupService()

    docs = [
        {
            "publication_number": "US10123456B2",
            "title": "System A",
            "year": 2023,
        },
        {
            "publication_number": "US10123456B2",  # Duplicata
            "title": "System A",
            "year": 2023,
        },
        {
            "publication_number": "US20234567B2",
            "title": "System B",
            "year": 2023,
        },
    ]

    unique, duplicates = service.deduplicate_patents(docs)

    assert len(unique) == 2
    assert len(duplicates) == 1


def test_dedup_service_patent_dedup_key_primary():
    """
    Verifica que primary key é publication_number.
    """
    service = DedupService()

    key = service._get_patent_dedup_key({
        "publication_number": "US10123456B2",
        "title": "test",
        "year": 2023,
    })

    assert "US10123456B2" in key


def test_dedup_service_patent_dedup_key_fallback():
    """
    Verifica fallback para normalized_title + year.
    """
    service = DedupService()

    key = service._get_patent_dedup_key({
        "title": "Machine Learning System",
        "year": 2023,
    })

    assert "machine" in key.lower()
    assert "2023" in key


def test_dedup_service_deduplicates_scholarly():
    """
    Verifica deduplicação de publicações.
    """
    service = DedupService()

    docs = [
        {
            "doi": "10.1234/example",
            "title": "Paper A",
            "year": 2023,
        },
        {
            "doi": "10.1234/example",  # Duplicata
            "title": "Paper A",
            "year": 2023,
        },
        {
            "doi": "10.5678/other",
            "title": "Paper B",
            "year": 2023,
        },
    ]

    unique, duplicates = service.deduplicate_scholarly(docs)

    assert len(unique) == 2
    assert len(duplicates) == 1


def test_dedup_service_text_normalization():
    """
    Verifica normalização de texto para dedup.
    """
    service = DedupService()

    normalized1 = service._normalize_text("Machine Learning System")
    normalized2 = service._normalize_text("machine learning system")
    normalized3 = service._normalize_text("MACHINE-LEARNING-SYSTEM")

    assert normalized1 == normalized2 == normalized3
