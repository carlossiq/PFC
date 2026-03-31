"""
LLM output normalization with enabled field filtering.

Normalizes and validates LLM output while respecting:
- Only enabled fields are kept in output
- Textual fields maintain {group_operator, groups} structure
- Simple fields are flat lists, never {"values": [...]}
- Invalid terms and stopwords are removed
"""

from core.config import settings
from core.logging import get_logger
from schemas.llm import LLMOutput, OperatorEnum, SimpleFieldQuery, TermGroup, TextualFieldQuery
from services.llm.validators import (
    clean_terms,
    filter_to_enabled_fields,
    is_simple_field,
    is_textual_field,
    normalize_simple_field_structure,
    normalize_textual_field_structure,
)

logger = get_logger(__name__)

# All possible field names (internal attribute names in LLMOutput)
ALL_FIELD_NAMES = {
    "title",
    "abstract",
    "claims",
    "description",
    "full_text",
    "ipc",
    "cpc",
    "authors",
    "affiliation",
    "applicant",
    "inventor",
    "field_of_study",
    "keywords",
    "source_title",
    "year",
}


class LLMOutputNormalizer:
    """
    Normalizes LLM output with filtering to enabled fields.

    Rules:
    - Only fields explicitly enabled are kept
    - Textual fields use {group_operator, groups} structure
    - Simple fields are flat lists
    - Invalid terms and stopwords are removed
    - Empty fields are preserved but with empty structure
    """

    MIN_TERM_LENGTH = 2

    @staticmethod
    def normalize(
        llm_output: LLMOutput,
        enabled_fields: list[str] = None,
        inject_year: bool = True,
    ) -> LLMOutput:
        """
        Normalizes LLM output filtering to enabled fields only.

        Args:
            llm_output: Raw LLM output
            enabled_fields: List of uppercase field names to keep.
                          If None, keeps all fields (legacy behavior).
            inject_year: If True, injects YEAR from config

        Returns:
            Normalized LLMOutput with only enabled fields populated
        """
        # If no enabled_fields specified, normalize all (backward compatible)
        if enabled_fields is None:
            enabled_fields = list(ALL_FIELD_NAMES)

        enabled_upper = {f.upper() for f in enabled_fields}

        logger.info(
            "normalizer_enabled_fields_debug",
            enabled_fields_list=list(enabled_upper),
            enabled_fields_count=len(enabled_upper),
        )

        # Log raw LLM output BEFORE normalization
        logger.info(
            "llm_output_before_normalization",
            title_groups=len(llm_output.title.groups) if llm_output.title.groups else 0,
            abstract_groups=len(llm_output.abstract.groups) if llm_output.abstract.groups else 0,
            claims_groups=len(llm_output.claims.groups) if llm_output.claims.groups else 0,
            description_groups=len(llm_output.description.groups) if llm_output.description.groups else 0,
            full_text_groups=len(llm_output.full_text.groups) if llm_output.full_text.groups else 0,
            title_preview=str(llm_output.title.groups[0].terms[:2]) if llm_output.title.groups else "EMPTY",
            abstract_preview=str(llm_output.abstract.groups[0].terms[:2]) if llm_output.abstract.groups else "EMPTY",
        )

        # Normalize only enabled textual fields
        if "TITLE" in enabled_upper:
            llm_output.title = LLMOutputNormalizer._normalize_textual_field(llm_output.title)
        else:
            llm_output.title = TextualFieldQuery()

        if "ABSTRACT" in enabled_upper:
            llm_output.abstract = LLMOutputNormalizer._normalize_textual_field(
                llm_output.abstract
            )
        else:
            llm_output.abstract = TextualFieldQuery()

        if "CLAIMS" in enabled_upper:
            llm_output.claims = LLMOutputNormalizer._normalize_textual_field(llm_output.claims)
        else:
            llm_output.claims = TextualFieldQuery()

        if "DESCRIPTION" in enabled_upper:
            llm_output.description = LLMOutputNormalizer._normalize_textual_field(
                llm_output.description
            )
        else:
            llm_output.description = TextualFieldQuery()

        if "FULL_TEXT" in enabled_upper:
            llm_output.full_text = LLMOutputNormalizer._normalize_textual_field(
                llm_output.full_text
            )
        else:
            llm_output.full_text = TextualFieldQuery()

        if "KEYWORDS" in enabled_upper:
            llm_output.keywords = LLMOutputNormalizer._normalize_simple_field(
                llm_output.keywords
            )
        else:
            llm_output.keywords = SimpleFieldQuery()

        # Normalize only enabled simple fields
        if "IPC" in enabled_upper:
            llm_output.ipc = LLMOutputNormalizer._normalize_simple_field(llm_output.ipc)
        else:
            llm_output.ipc = SimpleFieldQuery()

        if "CPC" in enabled_upper:
            llm_output.cpc = LLMOutputNormalizer._normalize_simple_field(llm_output.cpc)
        else:
            llm_output.cpc = SimpleFieldQuery()

        if "AUTHORS" in enabled_upper:
            llm_output.authors = LLMOutputNormalizer._normalize_simple_field(llm_output.authors)
        else:
            llm_output.authors = SimpleFieldQuery()

        if "AFFILIATION" in enabled_upper:
            llm_output.affiliation = LLMOutputNormalizer._normalize_simple_field(
                llm_output.affiliation
            )
        else:
            llm_output.affiliation = SimpleFieldQuery()

        if "APPLICANT" in enabled_upper:
            llm_output.applicant = LLMOutputNormalizer._normalize_simple_field(
                llm_output.applicant
            )
        else:
            llm_output.applicant = SimpleFieldQuery()

        if "INVENTOR" in enabled_upper:
            llm_output.inventor = LLMOutputNormalizer._normalize_simple_field(
                llm_output.inventor
            )
        else:
            llm_output.inventor = SimpleFieldQuery()

        if "FIELD_OF_STUDY" in enabled_upper:
            llm_output.field_of_study = LLMOutputNormalizer._normalize_simple_field(
                llm_output.field_of_study
            )
        else:
            llm_output.field_of_study = SimpleFieldQuery()

        if "SOURCE_TITLE" in enabled_upper:
            llm_output.source_title = LLMOutputNormalizer._normalize_simple_field(
                llm_output.source_title
            )
        else:
            llm_output.source_title = SimpleFieldQuery()

        if "YEAR" in enabled_upper:
            llm_output.year = LLMOutputNormalizer._normalize_simple_field(llm_output.year)
        else:
            llm_output.year = SimpleFieldQuery()

        # Inject YEAR if enabled
        if inject_year and "YEAR" in enabled_upper:
            llm_output = LLMOutputNormalizer._inject_year(llm_output)

        logger.info(
            "llm_output_normalized",
            enabled_fields_count=len(enabled_upper),
            has_queries=llm_output.has_any_queries(),
            active_fields_count=sum(llm_output.get_active_fields().values()),
        )

        return llm_output

    @staticmethod
    def _normalize_textual_field(field: TextualFieldQuery) -> TextualFieldQuery:
        """
        Normalizes a textual field.

        Ensures structure is {group_operator, groups} with clean terms.

        Args:
            field: Textual field to normalize

        Returns:
            Normalized textual field
        """
        if not field or not field.groups:
            return TextualFieldQuery(group_operator=OperatorEnum.AND, groups=[])

        normalized_groups = []

        for group in field.groups:
            # Clean terms: remove stopwords, invalid, etc.
            original_terms = group.terms if group.terms else []
            normalized_terms = clean_terms(original_terms)

            # Log se todos os termos foram rejeitados
            if original_terms and not normalized_terms:
                logger.info(
                    "textual_field_all_terms_rejected",
                    original_terms=original_terms,
                    normalized_terms=normalized_terms,
                )

            # Keep group only if it has valid terms
            if normalized_terms:
                normalized_groups.append(
                    TermGroup(
                        operator=group.operator,
                        terms=normalized_terms,
                    )
                )

        # Validate and default group_operator
        try:
            LLMOutputNormalizer._validate_operator(field.group_operator.value)
            group_op = field.group_operator
        except (ValueError, AttributeError):
            group_op = OperatorEnum.AND

        return TextualFieldQuery(
            group_operator=group_op,
            groups=normalized_groups,
        )

    @staticmethod
    def _normalize_simple_field(field: SimpleFieldQuery) -> SimpleFieldQuery:
        """
        Normalizes a simple field to flat list structure.

        Handles various input shapes (list, dict with values, etc.)
        and returns SimpleFieldQuery with clean values.

        Args:
            field: Simple field to normalize

        Returns:
            Normalized simple field (flat list)
        """
        if not field or not field.values:
            return SimpleFieldQuery(values=[])

        # Clean and deduplicate values
        normalized_values = clean_terms(field.values if field.values else [])

        return SimpleFieldQuery(values=normalized_values)

    @staticmethod
    def _validate_operator(operator: str) -> None:
        """
        Validates operator is AND or OR.

        Args:
            operator: Operator string

        Raises:
            ValueError: If invalid
        """
        valid_operators = {op.value for op in OperatorEnum}

        if operator.upper() not in valid_operators:
            raise ValueError(f"Invalid operator: {operator}")

    @staticmethod
    def _inject_year(llm_output: LLMOutput) -> LLMOutput:
        """
        Injects YEAR from config if available.

        Args:
            llm_output: Output to inject into

        Returns:
            Output with YEAR populated if config available
        """
        year_range = getattr(settings, "year_range", None)

        if year_range:
            years = [year_range] if isinstance(year_range, str) else (
                year_range if isinstance(year_range, list) else []
            )

            if years:
                llm_output.year = SimpleFieldQuery(values=years)
                logger.info("llm_year_injected", years=years)

        return llm_output

    @staticmethod
    def validate_structure(llm_output: LLMOutput) -> bool:
        """
        Validates structure of LLMOutput.

        Checks operators, group structure, etc.

        Args:
            llm_output: Output to validate

        Returns:
            True if valid
        """
        try:
            # Validate textual fields
            for field in [
                llm_output.title,
                llm_output.abstract,
                llm_output.claims,
                llm_output.description,
                llm_output.full_text,
            ]:
                LLMOutputNormalizer._validate_operator(field.group_operator.value)

                for group in field.groups:
                    LLMOutputNormalizer._validate_operator(group.operator.value)

            return True

        except Exception as exc:
            logger.error(f"Structure validation failed: {exc}")
            return False
