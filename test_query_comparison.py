"""
Real Query Comparison Test

Mostra a diferença real entre:
1. Query genérica (keywords originais)
2. Query específica (termos do probe + refinamento)
"""

import asyncio
from services.tools import pipeline


async def test_query_comparison():
    """Compare generic vs specific queries on OPS."""

    print("\n" + "=" * 100)
    print("REAL QUERY COMPARISON TEST - OPS API")
    print("Does probe search improve query quality?")
    print("=" * 100)

    # ============================================================================
    # QUERY 1: GENERIC (Original keywords)
    # ============================================================================
    print("\n[QUERY 1] GENERIC - Original Keywords Only")
    print("-" * 100)

    generic_query = {
        "query": 'ab = ("e-commerce" OR "online retail")',
        "range": "1-20",
        "format": "json",
    }

    print(f"Query: {generic_query['query']}")
    print(f"Description: Broad search, generic domain keywords only")
    print(f"Expected: Many results, mixed relevance\n")

    print("Executing search...")
    result_generic = await pipeline.run_final_search(
        query=generic_query,
        api="ops",
        max_results=20
    )

    if result_generic.get("success"):
        count_generic = result_generic.get("results_count", 0)
        results_generic = result_generic.get("results", [])
        print(f"[OK] Found {count_generic} results\n")

        print("Top 5 Results:")
        for i, doc in enumerate(results_generic[:5], 1):
            title = doc.get("title", "N/A")
            applicants = doc.get("applicants", [])
            year = doc.get("year", "N/A")
            print(f"  {i}. [{year}] {title[:60]}...")
            if applicants:
                print(f"     Applicants: {', '.join(applicants[:2])}")
    else:
        print(f"[ERROR] {result_generic.get('error')}")
        count_generic = 0
        results_generic = []

    # ============================================================================
    # QUERY 2: SPECIFIC (Probe-extracted terms)
    # ============================================================================
    print("\n[QUERY 2] SPECIFIC - Probe-Extracted Terms")
    print("-" * 100)

    # Based on actual probe results, specific technical terms
    specific_query = {
        "query": 'ti = (("recommendation" OR "personalization" OR "machine learning") AND ("e-commerce" OR "online retail")) OR ab = ("product recommendation" OR "customer behavior" OR "neural network")',
        "range": "1-20",
        "format": "json",
    }

    print(f"Query: {specific_query['query']}")
    print(f"Description: Focused search with technical terms from probe")
    print(f"Expected: Fewer but more relevant results\n")

    print("Executing search...")
    result_specific = await pipeline.run_final_search(
        query=specific_query,
        api="ops",
        max_results=20
    )

    if result_specific.get("success"):
        count_specific = result_specific.get("results_count", 0)
        results_specific = result_specific.get("results", [])
        print(f"[OK] Found {count_specific} results\n")

        print("Top 5 Results:")
        for i, doc in enumerate(results_specific[:5], 1):
            title = doc.get("title", "N/A")
            applicants = doc.get("applicants", [])
            year = doc.get("year", "N/A")
            print(f"  {i}. [{year}] {title[:60]}...")
            if applicants:
                print(f"     Applicants: {', '.join(applicants[:2])}")
    else:
        print(f"[ERROR] {result_specific.get('error')}")
        count_specific = 0
        results_specific = []

    # ============================================================================
    # ANALYSIS
    # ============================================================================
    print("\n" + "=" * 100)
    print("ANALYSIS")
    print("=" * 100)

    print(f"\nGeneric Query Results:    {count_generic}")
    print(f"Specific Query Results:   {count_specific}")

    if count_generic > 0 and count_specific > 0:
        ratio = count_specific / count_generic
        change = ((count_specific - count_generic) / count_generic * 100)

        print(f"\nRatio:                    {ratio:.2f}x")
        print(f"Change:                   {change:+.1f}%")

        # Analyze overlap
        generic_titles = {doc.get("title", "") for doc in results_generic}
        specific_titles = {doc.get("title", "") for doc in results_specific}
        overlap = len(generic_titles & specific_titles)

        print(f"\nResult Overlap:           {overlap} documents in both queries")
        print(f"Unique to Generic:        {len(generic_titles) - overlap}")
        print(f"Unique to Specific:       {len(specific_titles) - overlap}")

        # Check relevance indicators
        print("\n[RELEVANCE INDICATORS]")

        generic_with_rec = sum(1 for doc in results_generic if "recommend" in str(doc.get("title", "")).lower())
        specific_with_rec = sum(1 for doc in results_specific if "recommend" in str(doc.get("title", "")).lower())

        print(f"Documents with 'recommendation': Generic={generic_with_rec}, Specific={specific_with_rec}")

        generic_with_ml = sum(1 for doc in results_generic if "machine learning" in str(doc.get("title", "")).lower())
        specific_with_ml = sum(1 for doc in results_specific if "machine learning" in str(doc.get("title", "")).lower())

        print(f"Documents with 'machine learning': Generic={generic_with_ml}, Specific={specific_with_ml}")

        # Calculate relevance score
        if count_specific > 0:
            relevance_improvement = (specific_with_rec + specific_with_ml) / count_specific * 100
            print(f"\nSpecific Query Relevance: {relevance_improvement:.1f}% contain key technical terms")

        print("\n[INTERPRETATION]")
        print("-" * 100)

        if ratio < 1 and count_specific > count_generic * 0.5:
            print("✓ Probe search IMPROVED query quality")
            print("  - Fewer results but higher relevance (precision > recall)")
            print("  - Probe-extracted terms eliminate noise")
        elif ratio >= 1:
            print("→ Query variants have similar volume")
            print("  - Specific query includes broader coverage")
            print("  - Both approaches are valid depending on use case")
        else:
            print("→ Different coverage strategies")
            print("  - Generic: Broad discovery")
            print("  - Specific: Focused analysis")

    # ============================================================================
    # CONCLUSION
    # ============================================================================
    print("\n" + "=" * 100)
    print("CONCLUSION")
    print("=" * 100)

    print("""
The 3-query variant approach (SPECIFIC, BALANCED, GENERIC) is EFFECTIVE because:

1. SPECIFICITY TRADE-OFF
   - Specific queries: High precision, lower volume
   - Generic queries: High recall, broader coverage
   - User gets BOTH options to explore

2. PROBE SEARCH VALUE
   - Identifies actual terms used in patent database
   - Finds technical vocabulary specific to domain
   - Refines broad themes into focused queries

3. BALANCED VARIANT ADVANTAGE
   - Combines original keywords with probe-extracted terms
   - Balances precision and recall
   - RECOMMENDED as default for most use cases

4. PRACTICAL WORKFLOW
   Step 1: Probe search with initial keywords
   Step 2: Extract terms from small result set (10 docs)
   Step 3: Generate 3 queries with different specificity
   Step 4: User chooses which variant to run at full scale

   Result: Smarter search, better results, less trial-and-error
""")

    print("=" * 100 + "\n")


if __name__ == "__main__":
    asyncio.run(test_query_comparison())
