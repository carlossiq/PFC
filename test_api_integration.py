#!/usr/bin/env python3
"""
Test the full API workflow: probe query → probe search → term extraction.
"""

import asyncio
import json
from services.tools import pipeline
from schemas.intake import InputIntake


async def test_full_workflow():
    """Test complete workflow from probe query to term extraction."""

    # Step 1: Create intake
    intake = InputIntake(
        theme="internet technology",
        description="technology for e-commerce applications",
    )

    print("=" * 80)
    print("STEP 1: Build probe query")
    print("=" * 80)

    # Step 1: Build probe query
    query_result = await pipeline.build_probe_query(intake, api="ops")

    if not query_result.get("success"):
        print(f"Failed to build query: {query_result.get('error')}")
        return

    query = query_result.get("query")
    print(f"\nQuery built:\n{json.dumps(query, indent=2)}\n")

    # Step 2: Run probe search
    print("=" * 80)
    print("STEP 2: Run probe search (with enrichment)")
    print("=" * 80)

    search_result = await pipeline.run_probe_search(query=query, api="ops")

    if not search_result.get("success"):
        print(f"Failed to search: {search_result.get('error')}")
        return

    enriched_results = search_result.get("results", [])
    results_count = search_result.get("results_count", 0)
    print(f"\nGot {results_count} enriched results")

    if results_count == 0:
        print("No results to process")
        return

    # Show first result structure
    if enriched_results:
        first = enriched_results[0]
        print(f"\nFirst result structure:")
        print(f"  - publication_number: {first.get('publication_number')}")
        if first.get("biblio"):
            biblio = first.get("biblio", {})
            print(f"  - has title: {bool(biblio.get('title'))}")
            print(f"  - has abstract: {bool(biblio.get('abstract'))}")

    # Step 3: Extract terms
    print("\n" + "=" * 80)
    print("STEP 3: Extract relevant terms")
    print("=" * 80)

    # Prepare original params for filtering
    original_params = {
        "theme": intake.theme,
        "description": intake.description,
    }

    extract_result = await pipeline.extract_relevant_terms(
        enriched_results=enriched_results,
        original_params=original_params,
        top_k=15,
    )

    if not extract_result.get("success"):
        print(f"Failed to extract terms: {extract_result.get('error')}")
        return

    terms = extract_result.get("terms", [])
    print(f"\nExtracted {len(terms)} terms:\n")

    for idx, term_data in enumerate(terms[:10], 1):
        print(f"[{idx}] {term_data['term']}")
        print(f"    Score: {term_data['score']} (KeyBERT: {term_data['keybert_score']}, TF-IDF: {term_data['tf_idf_score']})")
        print(f"    Frequency: {term_data['frequency']} appearances")
        print()

    print("\n" + "=" * 80)
    print("FULL JSON RESPONSE (first 5 terms)")
    print("=" * 80)
    print(json.dumps(extract_result["terms"][:5], indent=2))


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
