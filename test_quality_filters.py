#!/usr/bin/env python3
"""Test string quality filters and MMR ranking."""

import json
from services.nlp.term_extraction import TermExtractor


def test_quality_filters():
    """Test that quality filters are applied correctly."""
    extractor = TermExtractor()

    # Test cases with expected results
    test_terms = [
        # Should be FILTERED (boundary stopwords)
        ("the internet", False, "starts with 'the'"),
        ("internet of", False, "ends with 'of'"),
        ("to design", False, "starts with 'to'"),

        # Should be FILTERED (patent structural words)
        ("internet comprising", False, "contains 'comprising'"),
        ("wherein systems", False, "contains 'wherein'"),
        ("said device", False, "contains 'said'"),
        ("first method", False, "contains 'first'"),

        # Should be FILTERED (scholarly structural words)
        ("proposed method", False, "contains 'proposed'"),
        ("novel approach", False, "contains 'novel'"),
        ("results analysis", False, "contains 'analysis'"),
        ("demonstrated finding", False, "contains 'findings'"),

        # Should be KEPT (good terms)
        ("internet gateway", True, "good term"),
        ("fleet management", True, "good term"),
        ("iot platform", True, "good term"),
        ("blockchain ledger", True, "good term"),  # 'ledger' is not in filter lists
        ("vehicle network", True, "good term"),
    ]

    print("=== QUALITY FILTER TESTS ===\n")

    for term, should_keep, reason in test_terms:
        filtered = extractor._apply_quality_filters([term])
        kept = len(filtered) > 0

        status = "[PASS]" if kept == should_keep else "[FAIL]"
        action = "KEPT" if kept else "FILTERED"

        print(f"{status} [{action}] '{term}'")
        print(f"    Reason: {reason}")

        if kept != should_keep:
            print(f"    ERROR: Expected {'KEPT' if should_keep else 'FILTERED'}")
        print()


def test_mmr_ranking():
    """Test that MMR ranking selects diverse terms."""
    extractor = TermExtractor()

    # Create similar and diverse terms with scores
    candidates = [
        "internet gateway device",      # High score, similar to next
        "internet gateway devices",     # Medium score, similar to previous
        "internet protocol security",   # High score, similar to above
        "fleet management system",      # Medium score, diverse
        "local area networks",          # Low score, diverse
        "vehicle control network",      # Low score, diverse
        "iot platform server",          # Medium score, diverse
    ]

    scores = {
        "internet gateway device": 0.95,
        "internet gateway devices": 0.93,
        "internet protocol security": 0.92,
        "fleet management system": 0.80,
        "local area networks": 0.60,
        "vehicle control network": 0.55,
        "iot platform server": 0.85,
    }

    # Rank with MMR (lambda=0.6: 60% relevance, 40% diversity)
    ranked = extractor._calculate_mmr_ranking(
        candidates=candidates,
        scores=scores,
        lambda_param=0.6,
        top_k=5,
    )

    print("=== MMR RANKING TEST ===\n")
    print(f"Lambda: 0.6 (60% relevance, 40% diversity)")
    print(f"Top-5 selection from {len(candidates)} candidates:\n")

    for i, term in enumerate(ranked, 1):
        score = scores.get(term, 0)
        print(f"[{i}] {term}")
        print(f"    Score: {score}")

    print("\n=== DIVERSITY ANALYSIS ===")
    print("Expected: First term is highest score (0.95)")
    print("Expected: Second term should NOT be 'internet gateway devices' (too similar)")
    print("Expected: Include diverse terms like 'fleet management', 'local area networks'")


if __name__ == "__main__":
    test_quality_filters()
    print("\n" + "=" * 60 + "\n")
    test_mmr_ranking()
