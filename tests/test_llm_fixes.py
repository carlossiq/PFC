"""
Tests for LLM output normalization fixes.

Validates:
1. Mock output respects enabled fields and contract
2. Normalizer filters to enabled fields only
3. Simple fields use correct flat list structure
4. Term validation removes stopwords and invalid terms
"""

import pytest
from schemas.intake import InputIntake
from schemas.llm import LLMOutput, OperatorEnum, SimpleFieldQuery, TermGroup, TextualFieldQuery
from services.llm.mock_service import MockLLMService
from services.llm.normalizer import LLMOutputNormalizer
from services.llm.validators import (
    clean_terms,
    is_simple_field,
    is_textual_field,
    is_valid_term,
)


class TestValidators:
    """Tests for field validation helpers."""

    def test_is_textual_field(self):
        """Test textual field detection."""
        assert is_textual_field("TITLE")
        assert is_textual_field("ABSTRACT")
        assert is_textual_field("KEYWORDS")
        assert not is_textual_field("IPC")
        assert not is_textual_field("APPLICANT")

    def test_is_simple_field(self):
        """Test simple field detection."""
        assert is_simple_field("IPC")
        assert is_simple_field("CPC")
        assert is_simple_field("APPLICANT")
        assert not is_simple_field("TITLE")
        assert not is_simple_field("ABSTRACT")

    def test_is_valid_term_rejects_stopwords(self):
        """Test that stopwords are rejected."""
        assert not is_valid_term("in")
        assert not is_valid_term("of")
        assert not is_valid_term("for")
        assert not is_valid_term("and")

    def test_is_valid_term_rejects_generic_isolated(self):
        """Test that isolated generic terms are rejected."""
        assert not is_valid_term("machine")
        assert not is_valid_term("learning")
        assert not is_valid_term("storage")
        assert not is_valid_term("materials")

    def test_is_valid_term_accepts_multi_word(self):
        """Test that multi-word expressions are accepted."""
        assert is_valid_term("machine learning")
        assert is_valid_term("solid-state batteries")
        assert is_valid_term("electric vehicles")

    def test_is_valid_term_accepts_technical_terms(self):
        """Test that valid technical terms are accepted."""
        assert is_valid_term("solid-state")
        assert is_valid_term("lithium-metal")
        assert is_valid_term("battery")

    def test_clean_terms_removes_stopwords(self):
        """Test that clean_terms removes stopwords."""
        terms = ["machine", "learning", "in", "artificial", "intelligence", "for"]
        result = clean_terms(terms)
        assert "machine" not in result
        assert "learning" not in result
        assert "artificial" in result
        assert "intelligence" in result

    def test_clean_terms_deduplicates(self):
        """Test deduplication."""
        terms = ["battery", "battery", "BATTERY"]
        result = clean_terms(terms)
        assert len(result) == 1
        assert result[0] == "battery"

    def test_clean_terms_preserves_multi_word(self):
        """Test that multi-word expressions are preserved."""
        terms = ["machine learning", "deep learning", "neural networks"]
        result = clean_terms(terms)
        assert "machine learning" in result
        assert "deep learning" in result


class TestMockService:
    """Tests for improved mock LLM service."""

    @pytest.mark.asyncio
    async def test_mock_extracts_concepts(self):
        """Test that mock extracts meaningful concepts."""
        intake = InputIntake(
            theme="Solid-State Batteries for Electric Vehicles",
            description="Focus on solid electrolytes and lithium metal anodes",
            area_of_study="Energy Storage",
            keywords=["ceramic", "electrolyte"],
        )

        service = MockLLMService()
        output = await service.process_intake(intake, "dummy prompt")

        # TITLE should have groups
        assert output.title.groups
        assert len(output.title.groups) > 0

        # ABSTRACT should have groups
        assert output.abstract.groups

        # All terms should be valid (no "solid", "state", "for" in isolation)
        all_terms = []
        for field in [output.title, output.abstract]:
            for group in field.groups:
                all_terms.extend(group.terms)

        for term in all_terms:
            assert is_valid_term(term), f"Invalid term found: {term}"

    @pytest.mark.asyncio
    async def test_mock_preserves_multi_word_expressions(self):
        """Test that mock preserves multi-word technical expressions."""
        intake = InputIntake(
            theme="Machine Learning for Healthcare Diagnostics",
            description="Deep learning models for medical imaging",
            area_of_study="Healthcare",
            keywords=["diagnostic AI"],
        )

        service = MockLLMService()
        output = await service.process_intake(intake, "dummy prompt")

        # Should contain multi-word expressions, not split words
        all_terms = []
        for field in [output.title, output.abstract]:
            for group in field.groups:
                all_terms.extend(group.terms)

        # Should have multi-word terms
        multi_word_terms = [t for t in all_terms if " " in t or "-" in t]
        assert len(multi_word_terms) > 0

    @pytest.mark.asyncio
    async def test_mock_returns_empty_non_textual_fields(self):
        """Test that mock returns empty simple fields."""
        intake = InputIntake(
            theme="Test",
            description=None,
            area_of_study=None,
            keywords=[],
        )

        service = MockLLMService()
        output = await service.process_intake(intake, "dummy prompt")

        # Simple fields should be empty
        assert output.ipc.values == []
        assert output.cpc.values == []
        assert output.applicant.values == []


class TestNormalizer:
    """Tests for normalizer with field filtering."""

    def test_normalizer_filters_to_enabled_fields(self):
        """Test that normalizer only keeps enabled fields."""
        # Create output with all fields populated
        output = LLMOutput(
            title=TextualFieldQuery(
                groups=[TermGroup(terms=["test"])]
            ),
            abstract=TextualFieldQuery(
                groups=[TermGroup(terms=["abstract"])]
            ),
            claims=TextualFieldQuery(groups=[]),
            description=TextualFieldQuery(groups=[]),
            full_text=TextualFieldQuery(groups=[]),
            keywords=SimpleFieldQuery(values=["kw"]),
            ipc=SimpleFieldQuery(values=["IPC123"]),
            cpc=SimpleFieldQuery(values=["CPC123"]),
            authors=SimpleFieldQuery(values=["author"]),
            affiliation=SimpleFieldQuery(values=["affil"]),
            applicant=SimpleFieldQuery(values=["appl"]),
            inventor=SimpleFieldQuery(values=["inv"]),
            field_of_study=SimpleFieldQuery(values=["fos"]),
            source_title=SimpleFieldQuery(values=["st"]),
            year=SimpleFieldQuery(values=["2020"]),
        )

        # Normalize keeping only TITLE, ABSTRACT, IPC, CPC
        enabled = ["TITLE", "ABSTRACT", "IPC", "CPC"]
        normalized = LLMOutputNormalizer.normalize(output, enabled_fields=enabled)

        # Check enabled fields are populated
        assert normalized.title.groups  # Has content
        assert normalized.abstract.groups  # Has content
        assert normalized.ipc.values  # Has content
        assert normalized.cpc.values  # Has content

        # Check disabled fields are empty
        assert not normalized.keywords.values  # Empty
        assert not normalized.authors.values  # Empty
        assert not normalized.applicant.values  # Empty
        assert not normalized.inventor.values  # Empty

    def test_normalizer_removes_stopwords(self):
        """Test that normalizer removes stopwords."""
        output = LLMOutput(
            title=TextualFieldQuery(
                groups=[TermGroup(terms=["machine", "learning", "in", "ai"])]
            ),
        )

        normalized = LLMOutputNormalizer.normalize(
            output,
            enabled_fields=["TITLE"],
        )

        # "machine", "learning" are isolated generics, "in" is stopword
        # Should only have "ai"
        assert normalized.title.groups
        all_terms = []
        for group in normalized.title.groups:
            all_terms.extend(group.terms)

        assert "ai" in all_terms
        assert "in" not in all_terms

    def test_normalizer_preserves_valid_terms(self):
        """Test that valid terms are preserved."""
        output = LLMOutput(
            abstract=TextualFieldQuery(
                groups=[
                    TermGroup(terms=["solid-state batteries", "lithium metal anodes"])
                ]
            ),
        )

        normalized = LLMOutputNormalizer.normalize(
            output,
            enabled_fields=["ABSTRACT"],
        )

        all_terms = []
        for group in normalized.abstract.groups:
            all_terms.extend(group.terms)

        assert "solid-state batteries" in all_terms
        assert "lithium metal anodes" in all_terms

    def test_normalizer_simple_field_is_flat_list(self):
        """Test that simple fields normalize to flat lists."""
        # Create output where IPC has {"values": [...]} structure
        output = LLMOutput(
            ipc=SimpleFieldQuery(values=["C01B", "H01M"]),
        )

        normalized = LLMOutputNormalizer.normalize(
            output,
            enabled_fields=["IPC"],
        )

        # Check structure is flat list
        assert isinstance(normalized.ipc.values, list)
        # clean_terms lowercases and sorts all values for consistency
        assert set(normalized.ipc.values) == {"c01b", "h01m"}

    def test_normalizer_textual_field_structure(self):
        """Test that textual fields maintain correct structure."""
        output = LLMOutput(
            title=TextualFieldQuery(
                group_operator=OperatorEnum.AND,
                groups=[
                    TermGroup(operator=OperatorEnum.OR, terms=["term1", "term2"]),
                ],
            ),
        )

        normalized = LLMOutputNormalizer.normalize(
            output,
            enabled_fields=["TITLE"],
        )

        # Check structure
        assert normalized.title.group_operator == OperatorEnum.AND
        assert len(normalized.title.groups) > 0
        assert normalized.title.groups[0].operator == OperatorEnum.OR

    def test_normalizer_defaults_none_enabled_to_all(self):
        """Test backward compatibility when enabled_fields is None."""
        output = LLMOutput(
            title=TextualFieldQuery(
                groups=[TermGroup(terms=["test"])]
            ),
            keywords=SimpleFieldQuery(values=["kw"]),
        )

        # None should keep all fields
        normalized = LLMOutputNormalizer.normalize(output, enabled_fields=None)

        # Both should be present
        assert normalized.title.groups
        assert normalized.keywords.values
