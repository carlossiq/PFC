"""
Mock LLM service for testing and development.

Returns realistic structured outputs respecting enabled fields and contract rules.
"""

import re
from typing import Optional

from schemas.intake import InputIntake
from schemas.llm import LLMOutput, OperatorEnum, SimpleFieldQuery, TermGroup, TextualFieldQuery
from services.llm.base import BaseLLMService
from services.llm.validators import clean_terms


class MockLLMService(BaseLLMService):
    """
    Mock LLM service that returns realistic structured outputs.

    Extracts semantic concepts from input and generates valid outputs
    respecting the contract:
    - Textual fields with group_operator and groups
    - Simple fields as flat lists
    - No stopwords or broken terms
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize mock service."""
        super().__init__(api_key)

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "mock"

    def is_available(self) -> bool:
        """Mock is always available."""
        return True

    async def process_intake(
        self,
        intake: InputIntake,
        system_prompt: str,
    ) -> LLMOutput:
        """
        Generate realistic mock LLM output respecting contract rules.

        Args:
            intake: User input (theme, description, area_of_study, keywords)
            system_prompt: System prompt (used to extract enabled fields)

        Returns:
            LLMOutput with realistic structured queries
        """
        # Extract semantic concepts from input
        concepts = self._extract_concepts(intake)

        # Build textual field queries
        title_query = self._build_textual_field(concepts, max_groups=2)
        abstract_query = self._build_textual_field(concepts, max_groups=4)
        claims_query = self._build_textual_field(concepts, max_groups=2)
        description_query = self._build_textual_field(concepts, max_groups=2)
        full_text_query = self._build_textual_field(concepts, max_groups=4)

        # Build simple field queries
        keywords_query = self._build_simple_field(concepts, max_terms=10)
        ipc_query = SimpleFieldQuery(values=[])
        cpc_query = SimpleFieldQuery(values=[])

        return LLMOutput(
            title=title_query,
            abstract=abstract_query,
            claims=claims_query,
            description=description_query,
            full_text=full_text_query,
            ipc=ipc_query,
            cpc=cpc_query,
            authors=SimpleFieldQuery(values=[]),
            affiliation=SimpleFieldQuery(values=[]),
            applicant=SimpleFieldQuery(values=[]),
            inventor=SimpleFieldQuery(values=[]),
            field_of_study=SimpleFieldQuery(values=[]),
            keywords=keywords_query,
            source_title=SimpleFieldQuery(values=[]),
            year=SimpleFieldQuery(values=[]),
        )

    def _extract_concepts(self, intake: InputIntake) -> list[list[str]]:
        """
        Extract semantic concepts from input.

        Returns list of concept groups, where each group contains
        synonyms/variations of a single concept.

        Args:
            intake: User input

        Returns:
            List of concept groups
        """
        concepts = []

        # Primary concept from theme
        if intake.theme:
            primary = self._extract_concept_from_text(intake.theme)
            if primary:
                concepts.append(primary)

        # Secondary concepts from description
        if intake.description:
            parts = re.split(r'[,;]', intake.description)
            for part in parts[:3]:  # Max 3 from description
                concept = self._extract_concept_from_text(part)
                if concept and concept not in concepts:
                    concepts.append(concept)

        # Add keywords as individual concepts
        if intake.keywords:
            for kw in intake.keywords[:3]:
                concept = [kw.lower().strip()]
                if concept and concept not in concepts:
                    concepts.append(concept)

        return concepts[:5]  # Max 5 concepts

    def _extract_concept_from_text(self, text: str) -> Optional[list[str]]:
        """
        Extract a single concept from text as a list of synonyms.

        Extracts meaningful multi-word phrases and their variations.

        Args:
            text: Text to extract from

        Returns:
            List of term variations for the concept
        """
        if not text or len(text.strip()) < 3:
            return None

        # Extract meaningful phrases (2+ word expressions)
        phrases = re.findall(r'\b[a-z][a-z\s\-]{2,}\b', text.lower())
        if not phrases:
            return None

        # Clean and deduplicate
        concept_terms = set()
        for phrase in phrases:
            cleaned = phrase.strip()
            if len(cleaned) >= 3 and cleaned not in {'the', 'and', 'for', 'with', 'from'}:
                concept_terms.add(cleaned)

                # Generate simple variation (hyphen to space and vice versa)
                if '-' in cleaned:
                    concept_terms.add(cleaned.replace('-', ' '))
                elif ' ' in cleaned and len(cleaned.split()) == 2:
                    concept_terms.add(cleaned.replace(' ', '-'))

        return sorted(list(concept_terms)) if concept_terms else None

    def _build_textual_field(
        self,
        concepts: list[list[str]],
        max_groups: int = 3,
    ) -> TextualFieldQuery:
        """
        Build a textual field query with groups of terms.

        Args:
            concepts: List of concept groups
            max_groups: Maximum number of groups to include

        Returns:
            TextualFieldQuery with proper structure
        """
        if not concepts:
            return TextualFieldQuery(group_operator=OperatorEnum.AND, groups=[])

        groups = []
        for concept in concepts[:max_groups]:
            if concept:
                # Clean terms and create group
                valid_terms = clean_terms(concept)
                if valid_terms:
                    groups.append(
                        TermGroup(
                            operator=OperatorEnum.OR,
                            terms=valid_terms,
                        )
                    )

        return TextualFieldQuery(
            group_operator=OperatorEnum.AND,
            groups=groups,
        )

    def _build_simple_field(
        self,
        concepts: list[list[str]],
        max_terms: int = 10,
    ) -> SimpleFieldQuery:
        """
        Build a simple field query as a flat list.

        Args:
            concepts: List of concept groups
            max_terms: Maximum number of terms to include

        Returns:
            SimpleFieldQuery with flat list of terms
        """
        if not concepts:
            return SimpleFieldQuery(values=[])

        # Flatten all terms from all concepts
        all_terms = []
        for concept in concepts:
            all_terms.extend(concept)

        # Clean terms and return as flat list
        cleaned = clean_terms(all_terms)
        return SimpleFieldQuery(values=cleaned[:max_terms])
