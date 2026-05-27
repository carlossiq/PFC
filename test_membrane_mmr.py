#!/usr/bin/env python3
"""Test MMR with the actual membrane data provided by user."""

from services.nlp.term_extraction import TermExtractor


def test_membrane_mmr():
    """Test that MMR removes similar membrane terms."""

    # Create fresh extractor to load latest config
    import importlib
    import services.nlp.term_extraction as term_extraction_module
    importlib.reload(term_extraction_module)
    from services.nlp.term_extraction import TermExtractor

    extractor = TermExtractor()

    # Terms from the user's actual response
    terms_with_scores = {
        "composite ultrafiltration membrane": 0.926,
        "nanoporous graphene membrane": 0.789,
        "water desalination": 0.507,
        "purification treatment device": 0.382,
        "base membrane layer": 0.498,
        "flowing salt water": 0.487,
        "desalinated water exiting": 0.457,
        "membrane": 0.506,
        "oxidized graphene layer": 0.41,
        "ultrafiltration membrane": 0.705,
        "composite membrane": 0.687,
        "hydrophilic performance": 0.188,
        "composite ultrafiltration": 0.63,
        "hydrophobic materials": 0.166,
        "single layer membrane": 0.49,
        "polysulphone base membrane": 0.482,
        "graphene membrane": 0.587,
        "supporting layer": 0.302,
        "dissolution resistance": 0.112,
        "water purification treatment": 0.445,
        "nanopores": 0.089,
        "substantial absence": 0.069,
        "pore edges": 0.069,
        "salt water": 0.503,
        "ultrafiltration": 0.392,
        "mechanical strength": 0.045,
        "brackish water desalination": 0.487,
        "seawater treatment": 0.196,
        "silicon": 0.0,
        "which": 0.0,
    }

    print("=" * 90)
    print("MMR FILTERING TEST - MEMBRANE DATA")
    print("=" * 90)

    # Apply MMR ranking
    ranked = extractor._calculate_mmr_ranking(
        candidates=list(terms_with_scores.keys()),
        scores=terms_with_scores,
        lambda_param=0.4,
        top_k=15,
        similarity_threshold=0.5,
    )

    print("\nTop 15 Terms After MMR (lambda=0.4, similarity_threshold=0.5):\n")
    print(f"{'Rank':<6} {'Term':<40} {'Score':<8}")
    print("-" * 90)

    for idx, term in enumerate(ranked, 1):
        score = terms_with_scores.get(term, 0)
        print(f"{idx:<6} {term[:39]:<40} {score:<8.3f}")

    print("\n" + "=" * 90)
    print("ANALYSIS:")
    print("=" * 90)

    # Check for similar terms
    print("\nSimilar terms that SHOULD be filtered:")
    print("-" * 90)

    similar_groups = [
        ("composite ultrafiltration membrane", "ultrafiltration membrane"),
        ("composite ultrafiltration membrane", "composite membrane"),
        ("ultrafiltration membrane", "ultrafiltration"),
        ("composite membrane", "composite ultrafiltration"),
        ("graphene membrane", "nanoporous graphene membrane"),
    ]

    print(f"{'Group':<50} {'In Results':<12} {'Status':<20}")
    print("-" * 90)

    for term_a, term_b in similar_groups:
        in_results_a = term_a in ranked
        in_results_b = term_b in ranked

        if in_results_a and in_results_b:
            status = "FAILED - Both present"
        elif not in_results_a or not in_results_b:
            status = "OK - One filtered"
        else:
            status = "OK - One selected"

        print(f"{f'{term_a} vs {term_b}':<50} {f'{in_results_a} {in_results_b}':<12} {status:<20}")

    print("\n" + "=" * 90)
    print("PROBLEMATIC TERMS CHECK:")
    print("=" * 90)

    bad_terms = ["which", "silicon", "substantial absence", "pore edges"]
    print(f"\nTerms that should be filtered out:\n")

    for term in bad_terms:
        in_results = term in ranked
        status = "STILL PRESENT" if in_results else "FILTERED"
        print(f"  {term:<40} {status:<20}")

    print("\n" + "=" * 90)


if __name__ == "__main__":
    test_membrane_mmr()
