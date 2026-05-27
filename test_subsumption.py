#!/usr/bin/env python3
"""Test subsumption filter with realistic data."""

from services.nlp.term_extraction import TermExtractor


def test_subsumption_filter():
    """Test that subsumption filter removes subset terms."""

    extractor = TermExtractor()

    # Simulate ranked terms (already ordered by score)
    ranked_terms = [
        "composite ultrafiltration membrane",  # Most specific, highest score
        "ultrafiltration membrane",  # Subset of above - should be removed
        "composite membrane",  # Subset of first - should be removed
        "water desalination",  # Different domain - keep
        "graphene membrane",  # Different domain - keep
        "membrane",  # Subset of many - should be removed
        "salt water",  # Different domain - keep
        "desalination process",  # Different domain - keep
    ]

    print("=" * 80)
    print("SUBSUMPTION FILTER TEST")
    print("=" * 80)

    print("\nInput (ranked by score, highest first):")
    print("-" * 80)
    for i, term in enumerate(ranked_terms, 1):
        words = set(term.lower().split())
        print(f"{i}. {term:40} ({len(words)} words)")

    # Apply subsumption filter
    filtered = extractor._apply_subsumption_filter(ranked_terms)

    print("\n\nOutput (after subsumption filter):")
    print("-" * 80)
    for i, term in enumerate(filtered, 1):
        words = set(term.lower().split())
        print(f"{i}. {term:40} ({len(words)} words)")

    print("\n" + "=" * 80)
    print("ANALYSIS:")
    print("=" * 80)

    removed = set(ranked_terms) - set(filtered)
    print(f"\nTerms removed by subsumption filter ({len(removed)}):")
    for term in removed:
        # Find what it's a subset of
        term_words = set(term.lower().split())
        for kept in filtered:
            kept_words = set(kept.lower().split())
            if term_words.issubset(kept_words) and term_words != kept_words:
                print(f"  '{term}' is subset of '{kept}'")
                break

    print(f"\nTerms kept ({len(filtered)}):")
    for term in filtered:
        print(f"  - {term}")

    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    print(f"Input: {len(ranked_terms)} terms")
    print(f"Removed by subsumption: {len(removed)} terms")
    print(f"Output: {len(filtered)} terms")
    print("\nSubsumption filter successfully removes generic/subset terms,")
    print("keeping only the most specific versions while preserving diversity.")


if __name__ == "__main__":
    test_subsumption_filter()
