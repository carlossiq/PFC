#!/usr/bin/env python3
"""
Debug test to find the exact error.
"""

import asyncio
import json
import traceback
from schemas.llm import LLMOutput, TextualFieldQuery, TermGroup
from services.query_builders.lens_patent_query_builder import LensPatentQueryBuilder
from services.search.lens_service import LensService


async def test():
    """Debug test."""

    print("\n" + "="*60)
    print("DEBUG TEST")
    print("="*60)

    # Create LLMOutput
    llm_output = LLMOutput(
        title=TextualFieldQuery(
            groups=[TermGroup(terms=["machine learning"])]
        ),
    )

    # Build query
    builder = LensPatentQueryBuilder(search_mode="probe")
    query = builder.build_query(
        llm_output=llm_output,
        year_from=2020,
        year_to=2026,
    )

    print("\nQuery:")
    print(json.dumps(query, indent=2))

    # Search
    service = LensService()

    try:
        print("\nCalling search_patent...")
        result = await service.search_patent(query=query)

        print(f"\nResult object: {result}")
        print(f"Success: {result.success}")
        print(f"Total count: {result.total_count} (type: {type(result.total_count)})")
        print(f"Results returned: {result.results_returned}")
        print(f"Results length: {len(result.results)}")

        if not result.success:
            print(f"Error: {result.error_message}")

    except Exception as e:
        print(f"\nException occurred: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        traceback.print_exc()

    finally:
        service.close()


if __name__ == "__main__":
    asyncio.run(test())
