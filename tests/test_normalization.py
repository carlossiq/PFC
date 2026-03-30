"""
Tests for metadata normalization service.
"""

import pytest

from schemas.normalized_metadata import (
    StandardizedPatentMetadata,
    StandardizedScholarlyMetadata,
)
from services.db.normalization_service import NormalizationService


def test_normalization_service_normalizes_patent():
    """
    Verifica normalização de patente.
    """
    service = NormalizationService()

    data = {
        "id": "US10123456B2",
        "title": "Machine Learning System",
        "abstract": "A system for ML",
        "publication_number": "US10123456B2",
        "applicants": ["Example Corp"],
        "inventors": ["John Doe"],
    }

    normalized = service.normalize_patent(data, source="test")

    assert isinstance(normalized, StandardizedPatentMetadata)
    assert normalized.title == data["title"]
    assert normalized.source == "test"


def test_normalization_service_normalizes_scholarly():
    """
    Verifica normalização de publicação.
    """
    service = NormalizationService()

    data = {
        "id": "10.1234/example",
        "title": "Deep Learning Applications",
        "abstract": "A paper about DL",
        "doi": "10.1234/example",
        "authors": ["Dr. Smith"],
    }

    normalized = service.normalize_scholarly(data, source="test")

    assert isinstance(normalized, StandardizedScholarlyMetadata)
    assert normalized.title == data["title"]
    assert normalized.doi == data["doi"]


def test_normalization_service_extracts_list_fields():
    """
    Verifica extração de campos de lista.
    """
    service = NormalizationService()

    # Campo como lista
    authors_list = service._extract_list_field(
        {"authors": ["John", "Jane"]},
        ["authors"],
    )
    assert len(authors_list) == 2

    # Campo como string
    authors_string = service._extract_list_field(
        {"authors": "John Doe"},
        ["authors"],
    )
    assert len(authors_string) == 1

    # Campo vazio
    authors_empty = service._extract_list_field({}, ["authors"])
    assert len(authors_empty) == 0


def test_normalization_service_extracts_year():
    """
    Verifica extração de ano.
    """
    service = NormalizationService()

    # Do campo "year"
    year1 = service._extract_year({"year": 2023})
    assert year1 == 2023

    # Da data string
    year2 = service._extract_year({}, "2023-06-15")
    assert year2 == 2023

    # Vazio
    year3 = service._extract_year({}, None)
    assert year3 is None
