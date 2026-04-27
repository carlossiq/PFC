"""
Full workflow test: Input theme -> Probe search -> Term extraction -> 3 final queries.

Demonstrates the complete flow from initial input to final query variants.
"""

import asyncio
from datetime import datetime

from core.config import settings
from schemas.intake import InputIntake
from services.tools import pipeline


async def main():
    """Execute complete workflow and show input vs output queries."""

    print("\n" + "=" * 80)
    print("TECHNOLOGY PROSPECTING WORKFLOW TEST")
    print("=" * 80)

    # ============================================================================
    # STEP 1: INPUT - Define the initial theme
    # ============================================================================
    initial_input = {
        "theme": "e-commerce",
        "description": "online retail technologies",
        "area_of_study": "Information Technology",
        "keywords": ["payment", "logistics", "platform"],
    }

    print("\n[STEP 1] INITIAL INPUT")
    print("-" * 80)
    print(f"Theme:           {initial_input['theme']}")
    print(f"Description:     {initial_input['description']}")
    print(f"Area of Study:   {initial_input['area_of_study']}")
    print(f"Keywords:        {', '.join(initial_input['keywords'])}")

    # ============================================================================
    # STEP 2: REFINE TOPIC - Get 4 candidates
    # ============================================================================
    print("\n[STEP 2] REFINING TOPIC")
    print("-" * 80)

    refine_result = await pipeline.generate_candidate_topics(
        intake=InputIntake(
            theme=initial_input["theme"],
            description=initial_input["description"],
            area_of_study=initial_input["area_of_study"],
            keywords=initial_input["keywords"],
        )
    )

    if not refine_result.get("success"):
        print(f"[ERROR] Failed to refine topic: {refine_result.get('error')}")
        return

    candidates = refine_result.get("candidates", [])
    print(f"Generated {len(candidates)} refined candidates:")

    chosen_candidate = candidates[0]  # Use first candidate
    print(f"\nUsing candidate: {chosen_candidate['theme']}")
    print(f"  Description: {chosen_candidate['description']}")
    print(f"  Keywords: {chosen_candidate.get('keywords', [])}")

    # ============================================================================
    # STEP 3: BUILD PROBE QUERY
    # ============================================================================
    print("\n[STEP 3] BUILDING PROBE QUERY")
    print("-" * 80)

    intake = InputIntake(
        theme=chosen_candidate["theme"],
        description=chosen_candidate["description"],
        area_of_study=chosen_candidate.get("area_of_study"),
        keywords=chosen_candidate.get("keywords"),
    )

    probe_query_result = await pipeline.build_probe_query(intake, api="ops")

    if not probe_query_result.get("success"):
        print(f"[ERROR] Failed to build probe query: {probe_query_result.get('error')}")
        return

    probe_query = probe_query_result.get("query")
    print(f"Probe Query (CQL):\n  {probe_query.get('query')}")
    print(f"Complexity: {probe_query_result.get('complexity')}")

    # ============================================================================
    # STEP 4: EXECUTE PROBE SEARCH
    # ============================================================================
    print("\n[STEP 4] EXECUTING PROBE SEARCH")
    print("-" * 80)

    start_time = datetime.utcnow()
    probe_search_result = await pipeline.run_probe_search(query=probe_query, api="ops")
    elapsed = (datetime.utcnow() - start_time).total_seconds()

    if not probe_search_result.get("success"):
        print(f"[ERROR] Probe search failed: {probe_search_result.get('error')}")
        return

    results = probe_search_result.get("results", [])
    print(f"Found {len(results)} results in {elapsed:.2f}s")

    if results:
        print(f"\nSample results:")
        for i, doc in enumerate(results[:3], 1):
            title = doc.get("title", "N/A")
            abstract = doc.get("abstract", "N/A")
            if abstract and len(abstract) > 100:
                abstract = abstract[:100] + "..."
            print(f"\n  {i}. {title}")
            print(f"     Abstract: {abstract}")

    # ============================================================================
    # STEP 5: EXTRACT RELEVANT TERMS
    # ============================================================================
    print("\n[STEP 5] EXTRACTING RELEVANT TERMS")
    print("-" * 80)

    original_params = {
        "theme": chosen_candidate["theme"],
        "description": chosen_candidate["description"],
        "keywords": chosen_candidate.get("keywords", []),
    }

    extract_result = await pipeline.extract_relevant_terms(
        enriched_results=results,
        original_params=original_params,
        top_k=20,
    )

    if not extract_result.get("success"):
        print(f"[ERROR] Term extraction failed: {extract_result.get('error')}")
        return

    extracted_terms = extract_result.get("terms", [])
    print(f"Extracted {len(extracted_terms)} relevant terms:")

    for i, term in enumerate(extracted_terms[:15], 1):
        score = term.get("score", 0)
        freq = term.get("frequency", 0)
        print(f"  {i:2d}. {term['term']:30s} | Score: {score:.3f} | Freq: {freq}")

    # ============================================================================
    # STEP 6: BUILD FINAL QUERIES (3 VARIANTS)
    # ============================================================================
    print("\n[STEP 6] BUILDING 3 FINAL QUERY VARIANTS")
    print("-" * 80)

    final_queries_result = await pipeline.build_final_queries_with_extraction(
        intake=intake,
        extracted_terms=extracted_terms,
        api="ops",
    )

    if not final_queries_result.get("success"):
        print(f"[ERROR] Failed to build final queries: {final_queries_result.get('error')}")
        return

    queries = final_queries_result.get("queries", {})

    # ============================================================================
    # STEP 7: COMPARISON - Input vs Output Queries
    # ============================================================================
    print("\n[STEP 7] COMPARISON: INPUT vs OUTPUT QUERIES")
    print("=" * 80)

    print("\nINPUT PARAMETERS:")
    print("-" * 80)
    print(f"Original Theme:    {initial_input['theme']}")
    print(f"Description:       {initial_input['description']}")
    print(f"Keywords:          {', '.join(initial_input['keywords'])}")

    print("\n" + "=" * 80)
    print("OUTPUT: 3 QUERY VARIANTS")
    print("=" * 80)

    variants = ["specific", "balanced", "generic"]

    for variant in variants:
        query_data = queries.get(variant, {})

        print(f"\n{variant.upper()} VARIANT")
        print("-" * 80)

        if query_data.get("success"):
            query_obj = query_data.get("query", {})
            cql_query = query_obj.get("query", "")
            complexity = query_data.get("complexity", {})

            print(f"CQL Query:\n{cql_query}\n")
            print(f"Complexity Score:  {complexity.get('score', 'N/A')}")
            print(f"Complexity Level:  {complexity.get('level', 'N/A')}/100")
            print(f"Passes Validation: {complexity.get('passed', False)}")

            if query_data.get("rationale"):
                print(f"Rationale:         {query_data['rationale']}")

            if query_data.get("focus_areas"):
                print(f"Focus Areas:       {', '.join(query_data['focus_areas'])}")
        else:
            print(f"[ERROR] {query_data.get('error', 'Unknown error')}")

    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nInput Theme Refinement:")
    print(f"  Original: '{initial_input['theme']}'")
    print(f"  Refined:  '{chosen_candidate['theme']}'")

    print(f"\nProbe Search Results:")
    print(f"  Results Found: {len(results)}")
    print(f"  Execution Time: {elapsed:.2f}s")

    print(f"\nTerm Extraction:")
    print(f"  Terms Extracted: {len(extracted_terms)}")
    print(f"  Recommended Terms: {len([t for t in extracted_terms if t.get('score', 0) > 0.3])}")

    print(f"\nQuery Variants Generated:")
    successful = sum(1 for q in queries.values() if q.get("success"))
    print(f"  Successful: {successful}/3")

    for variant in variants:
        if queries.get(variant, {}).get("success"):
            complexity = queries[variant].get("complexity", {}).get("score", 0)
            status = "[OK]" if queries[variant].get("complexity", {}).get("passed") else "[OVER LIMIT]"
            print(f"  - {variant:10s}: Complexity {complexity:.2f}/100 {status}")

    print("\n" + "=" * 80)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
