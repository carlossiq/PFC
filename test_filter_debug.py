#!/usr/bin/env python3
"""Debug why filtering and MMR are not removing problematic terms."""

import json
from pathlib import Path
from services.nlp.term_extraction import TermExtractor


def test_which_filtering():
    """Test if 'which' is being filtered."""
    extractor = TermExtractor()

    test_terms = [
        "which",
        "silicon",
        "composite ultrafiltration membrane",
        "ultrafiltration membrane",
        "composite membrane",
        "composite ultrafiltration",
        "graphene membrane",
    ]

    print("=" * 80)
    print("QUALITY FILTER DEBUG")
    print("=" * 80)

    # Check quality filter config
    print("\nQuality Filter Config Loaded:")
    print(f"  Boundary stopwords: {len(extractor.boundary_stopwords)}")
    print(f"  Patent structural words: {len(extractor.patent_structural_words)}")
    print(f"  Scholarly structural words: {len(extractor.scholarly_structural_words)}")

    # Check if "which" is in boundary stopwords
    if "which" in extractor.boundary_stopwords:
        print(f"  [OK] 'which' is in boundary_stopwords")
    else:
        print(f"  [WARNING] 'which' NOT in boundary_stopwords!")

    print("\nTesting quality filter on problem terms:")
    print("-" * 80)

    for term in test_terms:
        filtered = extractor._apply_quality_filters([term])
        kept = len(filtered) > 0

        # Check why it's kept/filtered
        words = term.lower().split()
        reasons = []

        if words:
            if words[0] in extractor.boundary_stopwords:
                reasons.append(f"starts with '{words[0]}' (boundary)")
            if words[-1] in extractor.boundary_stopwords:
                reasons.append(f"ends with '{words[-1]}' (boundary)")

        if any(w in extractor.patent_structural_words for w in words):
            reasons.append("contains patent structural word")
        if any(w in extractor.scholarly_structural_words for w in words):
            reasons.append("contains scholarly word")

        status = "KEPT" if kept else "FILTERED"
        reason = " | ".join(reasons) if reasons else "no filters matched"

        print(f"[{status:8}] {term:35} ({reason})")


def test_mmr_similarity():
    """Test Jaccard similarity for the problematic terms."""
    print("\n" + "=" * 80)
    print("MMR SIMILARITY DEBUG")
    print("=" * 80)

    extractor = TermExtractor()

    terms = [
        "composite ultrafiltration membrane",
        "ultrafiltration membrane",
        "composite membrane",
        "composite ultrafiltration",
        "graphene membrane",
    ]

    def jaccard_similarity(term_a: str, term_b: str) -> float:
        """Calculate Jaccard similarity."""
        words_a = set(term_a.lower().split())
        words_b = set(term_b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union > 0 else 0.0

    # Simulated scores from the response
    scores = {
        "composite ultrafiltration membrane": 0.926,
        "ultrafiltration membrane": 0.705,
        "composite membrane": 0.687,
        "composite ultrafiltration": 0.63,
        "graphene membrane": 0.587,
    }

    print("\nPairwise Similarity (Jaccard):")
    print("-" * 80)

    for i, term_a in enumerate(terms):
        for term_b in terms[i+1:]:
            sim = jaccard_similarity(term_a, term_b)
            print(f"{term_a:35} vs {term_b:35} = {sim:.2%}")

    print("\n\nMMR Ranking Simulation (λ=0.6):")
    print("-" * 80)
    print("If MMR were working correctly, similar terms should be skipped\n")

    selected = []
    print(f"[1] Select: {terms[0]:35} (score: {scores[terms[0]]})")
    selected.append(terms[0])

    for term_b in terms[1:]:
        relevance = scores[term_b]
        max_similarity = max(jaccard_similarity(term_b, sel) for sel in selected)
        mmr = 0.6 * relevance - 0.4 * max_similarity

        would_select = mmr > 0.2  # Assuming some threshold

        print(f"\n{term_b:35}")
        print(f"  Relevance: {relevance:.3f}")
        print(f"  Max Similarity: {max_similarity:.2%}")
        print(f"  MMR Score: {mmr:.3f}")
        print(f"  Would select: {would_select}")

        if would_select:
            selected.append(term_b)

    print("\n\nConclusion:")
    print("-" * 80)
    print("Problem: MMR with λ=0.6 is too lenient")
    print("Solution: Either:")
    print("  1. Lower λ to 0.4 or 0.3 (more aggressive diversity)")
    print("  2. Increase similarity threshold (skip >50% similar)")
    print("  3. Use different diversity metric (not Jaccard)")


if __name__ == "__main__":
    test_which_filtering()
    test_mmr_similarity()
