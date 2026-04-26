#!/usr/bin/env python3
"""
Test final query generation with extracted terms.
"""

import asyncio
import json
from schemas.intake import InputIntake
from services.tools import pipeline


async def test_final_queries_generation():
    """Test generation of 3 query variations with extracted terms."""

    # Create intake
    intake = InputIntake(
        theme="internet technology for e-commerce",
        description="online transaction systems and platforms",
    )

    # Simulate extracted terms (normally from /extract-terms endpoint)
    extracted_terms = [
        {
            "term": "risk",
            "score": 0.529,
            "keybert_score": 0.214,
            "tf_idf_score": 1.0,
            "frequency": 6,
            "sources": ["abstract"],
        },
        {
            "term": "business",
            "score": 0.457,
            "keybert_score": 0.191,
            "tf_idf_score": 0.857,
            "frequency": 5,
            "sources": ["abstract"],
        },
        {
            "term": "high",
            "score": 0.392,
            "keybert_score": 0.081,
            "tf_idf_score": 0.857,
            "frequency": 6,
            "sources": ["abstract"],
        },
        {
            "term": "capital",
            "score": 0.219,
            "keybert_score": 0.174,
            "tf_idf_score": 0.286,
            "frequency": 2,
            "sources": ["abstract"],
        },
        {
            "term": "investment",
            "score": 0.217,
            "keybert_score": 0.172,
            "tf_idf_score": 0.286,
            "frequency": 2,
            "sources": ["abstract"],
        },
        {
            "term": "market",
            "score": 0.171,
            "keybert_score": 0.094,
            "tf_idf_score": 0.286,
            "frequency": 2,
            "sources": ["abstract"],
        },
        {
            "term": "system",
            "score": 0.171,
            "keybert_score": 0,
            "tf_idf_score": 0.429,
            "frequency": 3,
            "sources": ["abstract"],
        },
        {
            "term": "technology",
            "score": 0.165,
            "keybert_score": 0.125,
            "tf_idf_score": 0.286,
            "frequency": 3,
            "sources": ["title"],
        },
    ]

    print("=" * 80)
    print("FINAL QUERY GENERATION WITH EXTRACTED TERMS")
    print("=" * 80)

    print(f"\nOriginal Parameters:")
    print(f"  Theme: {intake.theme}")
    print(f"  Description: {intake.description}")

    print(f"\nExtracted Terms Summary:")
    print(f"  Total: {len(extracted_terms)}")
    high_score = sum(1 for t in extracted_terms if t["score"] > 0.4)
    mid_score = sum(1 for t in extracted_terms if 0.3 < t["score"] <= 0.4)
    low_score = sum(1 for t in extracted_terms if t["score"] <= 0.3)
    print(f"  High score (>0.4): {high_score}")
    print(f"  Mid score (>0.3): {mid_score}")
    print(f"  Low score (<=0.3): {low_score}")

    print(f"\nTerms by score:")
    for idx, term in enumerate(extracted_terms[:8], 1):
        print(f"  [{idx:2d}] {term['term']:15s}: {term['score']:.3f}")

    print("\n" + "=" * 80)
    print("CALLING: build_final_queries_with_extraction()")
    print("=" * 80)

    try:
        result = await pipeline.build_final_queries_with_extraction(
            intake=intake,
            extracted_terms=extracted_terms,
            api="ops",
        )

        if not result.get("success", False):
            print(f"\nError: {result.get('error', 'Unknown error')}")
            return

        print(f"\n[OK] Generation successful!")

        # Show summary
        queries = result.get("queries", {})
        print(f"\nQueries Generated:")

        for variant in ["specific", "balanced", "generic"]:
            q_data = queries.get(variant, {})
            success = q_data.get("success", False)
            complexity = q_data.get("complexity", {})
            score = complexity.get("score", 0)
            passed = complexity.get("passed", False)

            status = "[OK] PASSED" if passed else "[!] EXCEEDED"
            print(f"\n  {variant.upper()}: {status}")
            print(f"    Complexity: {score:.1f}/100 (passed: {passed})")
            print(f"    Expected precision: {q_data.get('expected_precision', 'N/A')}")
            print(f"    Focus areas: {len(q_data.get('focus_areas', []))} terms")

            if q_data.get("query"):
                query_str = q_data["query"].get("query", "")[:100]
                print(f"    Query preview: {query_str}...")

            if q_data.get("rationale"):
                rationale = q_data.get("rationale", "")[:100]
                print(f"    Rationale: {rationale}...")

        print("\n" + "=" * 80)
        print("FULL JSON RESPONSE (first 500 chars)")
        print("=" * 80)
        print(json.dumps(result, indent=2, default=str)[:500])

    except Exception as exc:
        print(f"\n[ERROR] {str(exc)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_final_queries_generation())
