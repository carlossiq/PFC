#!/usr/bin/env python3
"""
Test term extraction API directly (skips LLM call for query building).
"""

import asyncio
import json
from services.tools import pipeline


async def test_term_extraction_api():
    """Test term extraction with a pre-built query."""

    # Pre-built query (simpler, more likely to have biblio data)
    query = {
        "query": '((ti = internet) AND (pd within "20150101 20161231"))',
        "range": "1-10",
        "format": "json"
    }

    original_params = {
        "theme": "internet technology",
        "description": "technology for e-commerce applications",
    }

    print("=" * 80)
    print("STEP 1: Run probe search (with enrichment)")
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

    # Show structure of first result
    if enriched_results:
        first = enriched_results[0]
        print(f"\nFirst result structure:")
        print(f"  - publication_number: {first.get('publication_number')}")
        if first.get("biblio"):
            biblio = first.get("biblio", {})
            print(f"  - has title: {bool(biblio.get('title'))}")
            print(f"  - has abstract: {bool(biblio.get('abstract'))}")
            if biblio.get("title"):
                print(f"  - title preview: {biblio.get('title')[:80]}...")

    # STEP 2: Extract terms using the new API function
    print("\n" + "=" * 80)
    print("STEP 2: Extract relevant terms")
    print("=" * 80)

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

    for idx, term_data in enumerate(terms[:12], 1):
        print(f"[{idx}] {term_data['term']}")
        print(f"    Score: {term_data['score']} (KeyBERT: {term_data['keybert_score']}, TF-IDF: {term_data['tf_idf_score']})")
        print(f"    Frequency: {term_data['frequency']} appearances")
        print()

    print("\n" + "=" * 80)
    print("JSON RESPONSE (first 5 terms for LLM consumption)")
    print("=" * 80)
    print(json.dumps(extract_result["terms"][:5], indent=2))


if __name__ == "__main__":
    asyncio.run(test_term_extraction_api())
