#!/usr/bin/env python3
"""
Verify that MMR ranking is actually being applied to final results.
"""

import asyncio
from services.nlp.term_extraction import TermExtractor
from services.tools import pipeline


async def test_mmr_applied():
    """Test if MMR is actually applied to results."""

    # Search for internet patents
    query = {
        "query": '((ti = internet) AND (pd within "20150101 20161231"))',
        "range": "1-10",
        "format": "json"
    }

    original_params = {
        "theme": "internet",
        "description": "internet technology for e-commerce",
    }

    print("=" * 90)
    print("TESTING MMR APPLICATION IN TERM EXTRACTION")
    print("=" * 90)

    # Get results
    search_result = await pipeline.run_probe_search(query=query, api="ops")
    if not search_result.get('success'):
        print(f"Search failed: {search_result.get('error')}")
        return

    results = search_result.get('results', [])[:10]
    if not results:
        print("No results")
        return

    print(f"\nProcessing {len(results)} documents...\n")

    # Extract terms
    extractor = TermExtractor()
    extracted_terms = extractor.extract_and_rank_terms(
        original_params=original_params,
        enriched_results=results,
        top_k=10,
    )

    print("TOP 10 TERMS (should be diverse due to MMR):\n")
    print(f"{'Rank':<6} {'Term':<40} {'Score':<8} {'Diversity Check':<30}")
    print("-" * 90)

    # Check for similarity between consecutive terms
    def word_similarity(term_a: str, term_b: str) -> float:
        """Calculate word overlap ratio (Jaccard similarity)."""
        words_a = set(term_a.lower().split())
        words_b = set(term_b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union > 0 else 0.0

    for idx, term_data in enumerate(extracted_terms, 1):
        term = term_data['term']
        score = term_data['score']

        # Check similarity to all previous terms
        max_similarity = 0.0
        similar_to = ""
        for prev_term in [t['term'] for t in extracted_terms[:idx-1]]:
            sim = word_similarity(term, prev_term)
            if sim > max_similarity:
                max_similarity = sim
                similar_to = prev_term

        if similar_to:
            diversity = f"Similar to: {similar_to[:25]:<25} ({max_similarity:.2f})"
        else:
            diversity = "DIVERSE (no previous similar)"

        print(f"{idx:<6} {term[:39]:<40} {score:<8.3f} {diversity:<30}")

    print("\n" + "=" * 90)
    print("ANALYSIS:")
    print("=" * 90)

    # Check if there are near-duplicates
    near_duplicates = 0
    for i, term_a in enumerate(extracted_terms):
        for term_b in extracted_terms[i+1:]:
            sim = word_similarity(term_a['term'], term_b['term'])
            if sim > 0.6:  # More than 60% similar
                near_duplicates += 1
                print(f"WARNING: Near-duplicate found!")
                print(f"  - {term_a['term']} (score: {term_a['score']})")
                print(f"  - {term_b['term']} (score: {term_b['score']})")
                print(f"  - Similarity: {sim:.2%}\n")

    if near_duplicates == 0:
        print("[OK] SUCCESS: No near-duplicate terms found in top-10")
        print("    MMR ranking is working - preventing similar terms\n")
    else:
        print(f"[!] WARNING: Found {near_duplicates} near-duplicate pairs")
        print("    MMR ranking may not be working correctly\n")

    # Check domain diversity
    domains = set()
    for term in extracted_terms:
        t = term['term'].lower()
        if 'vehicle' in t or 'fleet' in t or 'vehicle' in t:
            domains.add('vehicles')
        if 'internet' in t or 'gateway' in t or 'protocol' in t:
            domains.add('networking')
        if 'iot' in t or 'platform' in t or 'server' in t:
            domains.add('iot')
        if 'market' in t or 'capital' in t or 'company' in t:
            domains.add('finance')
        if 'coap' in t or 'multicast' in t:
            domains.add('protocols')
        if 'emergency' in t or 'notification' in t:
            domains.add('emergency')

    print(f"Domain diversity: {len(domains)} domains represented")
    print(f"Domains: {', '.join(sorted(domains))}\n")

    if len(domains) >= 3:
        print("[OK] Good domain diversity - MMR is promoting diverse topics\n")
    else:
        print("[!] Limited domain diversity - check if MMR is working\n")


if __name__ == "__main__":
    asyncio.run(test_mmr_applied())
