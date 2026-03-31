"""
Field validation and term cleaning helpers for LLM output.

Provides utilities for:
- Detecting field types (textual vs simple)
- Validating terms and rejecting stopwords
- Filtering outputs to enabled fields only
- Normalizing field structures
"""

from core.logging import get_logger

logger = get_logger(__name__)

# Stopwords to reject when appearing as isolated terms
STOPWORDS = {
    "in", "of", "for", "and", "or", "the", "a", "an", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "may", "might",
    "must", "can", "with", "by", "at", "to", "from", "as", "on", "it",
    "that", "this", "which", "who", "what", "where", "when", "why", "how"
}

# Generic weak single words to reject
GENERIC_TERMS = {
    "machine", "learning", "system", "data", "model", "network",
    "storage", "materials", "device", "method", "technology",
    "application", "process", "structure", "element", "component",
    "solution", "approach", "technique", "tool", "framework"
}


def is_textual_field(field_name: str) -> bool:
    """
    Checks if a field name is a textual field (supports boolean logic).

    Args:
        field_name: Field name in uppercase (e.g., 'TITLE', 'ABSTRACT')

    Returns:
        True if field is textual (TITLE, ABSTRACT, CLAIMS, DESCRIPTION, FULL_TEXT, KEYWORDS)
    """
    textual = {"TITLE", "ABSTRACT", "CLAIMS", "DESCRIPTION", "FULL_TEXT", "KEYWORDS"}
    return field_name.upper() in textual


def is_simple_field(field_name: str) -> bool:
    """
    Checks if a field name is a simple field (flat list, no boolean logic).

    Args:
        field_name: Field name in uppercase

    Returns:
        True if field is simple (IPC, CPC, AUTHORS, AFFILIATION, etc.)
    """
    simple = {
        "IPC", "CPC", "AUTHORS", "AFFILIATION", "APPLICANT", "INVENTOR",
        "FIELD_OF_STUDY", "SOURCE_TITLE", "YEAR"
    }
    return field_name.upper() in simple


def is_valid_term(term: str, allow_generic: bool = False) -> bool:
    """
    Validates a single term.

    Rejects:
    - Empty or whitespace-only strings
    - Terms shorter than 2 characters
    - Isolated stopwords like "in", "of", "for"
    - Isolated weak generic terms like "machine", "learning" (if allow_generic=False)

    Args:
        term: Term to validate
        allow_generic: If False, also reject isolated generic terms

    Returns:
        True if term is valid
    """
    if not isinstance(term, str):
        return False

    cleaned = term.lower().strip()

    # Must be at least 2 chars
    if len(cleaned) < 2:
        return False

    # Reject isolated stopwords
    if cleaned in STOPWORDS:
        return False

    # Reject isolated generic terms (unless allow_generic)
    if not allow_generic and cleaned in GENERIC_TERMS:
        return False

    return True


def clean_terms(terms: list[str]) -> list[str]:
    """
    Cleans a list of terms by:
    - Removing invalid terms
    - Removing duplicates
    - Converting to lowercase
    - Sorting

    Args:
        terms: List of terms to clean

    Returns:
        Cleaned, deduplicated, sorted list
    """
    if not terms:
        return []

    cleaned = set()
    for term in terms:
        if is_valid_term(term):
            cleaned.add(term.lower().strip())

    return sorted(list(cleaned))


def validate_group(group: dict) -> bool:
    """
    Validates a term group structure.

    Checks:
    - Has 'operator' field (AND or OR)
    - Has 'terms' field (list)
    - Has at least one valid term

    Args:
        group: Dict with operator and terms

    Returns:
        True if valid
    """
    if not isinstance(group, dict):
        return False

    if "operator" not in group or "terms" not in group:
        return False

    operator = group.get("operator", "").upper()
    if operator not in {"AND", "OR"}:
        return False

    terms = group.get("terms", [])
    if not isinstance(terms, list):
        return False

    # At least one valid term
    valid_terms = [t for t in terms if is_valid_term(t)]
    return len(valid_terms) > 0


def filter_to_enabled_fields(llm_output_dict: dict, enabled_fields: list[str]) -> dict:
    """
    Filters LLMOutput dict to only include enabled fields.

    Removes any fields not in enabled_fields list.

    Args:
        llm_output_dict: Dict representation of LLMOutput
        enabled_fields: List of uppercase field names to keep

    Returns:
        Filtered dict
    """
    if not enabled_fields:
        return {}

    enabled_upper = {f.upper() for f in enabled_fields}
    filtered = {}

    for field_name, field_value in llm_output_dict.items():
        if field_name.upper() in enabled_upper:
            filtered[field_name] = field_value

    return filtered


def normalize_textual_field_structure(field_value) -> dict:
    """
    Ensures a textual field has correct structure.

    Converts various input shapes to:
    {
      "group_operator": "AND",
      "groups": [{"operator": "OR", "terms": [...]}]
    }

    Args:
        field_value: Raw field value (dict, object, etc.)

    Returns:
        Normalized dict or empty structure
    """
    if isinstance(field_value, dict):
        return {
            "group_operator": field_value.get("group_operator", "AND"),
            "groups": field_value.get("groups", [])
        }

    return {
        "group_operator": "AND",
        "groups": []
    }


def normalize_simple_field_structure(field_value) -> list:
    """
    Ensures a simple field is a flat list.

    Converts various input shapes to a flat list of strings.

    Args:
        field_value: Raw field value (dict, list, object, etc.)

    Returns:
        Flat list of values
    """
    if isinstance(field_value, list):
        return [str(v).strip() for v in field_value if v]

    if isinstance(field_value, dict):
        values = field_value.get("values", [])
        if isinstance(values, list):
            return [str(v).strip() for v in values if v]
        return []

    if hasattr(field_value, "values"):
        values = getattr(field_value, "values", [])
        if isinstance(values, list):
            return [str(v).strip() for v in values if v]

    return []
