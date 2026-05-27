#!/usr/bin/env python3
"""
Test term extraction and ranking.
"""

import asyncio
import json
from services.nlp.term_extraction import TermExtractor
from services.tools import pipeline


async def test_term_extraction():
    """Test term extraction from enriched results."""

    # Original search parameters
    original_params = {
        "theme": "internet",
        "description": "internet technology for e-commerce",
    }

    # Get enriched results
    query = {
        "query": '((ti = internet) AND (pd within "20150101 20161231"))',
        "range": "1-10",
        "format": "json"
    }

    print("Testing term extraction and ranking\n")

    search_result = await pipeline.run_probe_search(query=query, api="ops")

    if not search_result.get('success'):
        print(f"Search failed: {search_result.get('error')}")
        return

    results = search_result.get('results', [])
    if not results:
        print("No results")
        return

    print(f"Got {len(results)} enriched results\n")

    # Extract terms
    extractor = TermExtractor()

    extracted_terms = extractor.extract_and_rank_terms(
        original_params=original_params,
        enriched_results=results,
        top_k=15,
    )

    print(f"=== EXTRACTED AND RANKED TERMS ({len(extracted_terms)}) ===\n")

    for idx, term_data in enumerate(extracted_terms, 1):
        penalty = term_data.get('penalty_factor', 1.0)
        print(f"[{idx}] {term_data['term']}")
        print(f"    Score: {term_data['score']} (Penalty: {penalty}x)")
        print(f"    KeyBERT: Title={term_data['keybert_score_title']}, Abstract={term_data['keybert_score_abstract']}")
        print(f"    TF-IDF: Title={term_data['tf_idf_score_title']}, Abstract={term_data['tf_idf_score_abstract']}")
        print(f"    Frequency: {term_data['frequency']}, Sources: {term_data['sources']}")
        print()

    # Show structure for LLM
    print("\n=== JSON for LLM ===\n")
    print(json.dumps(extracted_terms[:5], indent=2))


if __name__ == "__main__":
    asyncio.run(test_term_extraction())
