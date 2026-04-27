"""
Example of token tracking integration with ResearchWorkflow.

Demonstrates how to record LLM token usage for each phase of research.
"""

import asyncio
import time
from datetime import datetime

from services.research_service import ResearchService
from services.token_cost_calculator import calculate_token_cost, format_cost, format_tokens


async def example_research_with_token_tracking(session):
    """
    Example of complete research workflow with token tracking.
    """

    print("\n" + "=" * 100)
    print("EXAMPLE: RESEARCH WITH TOKEN TRACKING")
    print("=" * 100)

    # ========================================================================
    # STEP 1: CREATE RESEARCH
    # ========================================================================
    print("\n[1] Creating research...")

    research = await ResearchService.create_research(
        session=session,
        title="E-commerce Recommendation Systems",
        description="Technology prospecting for recommendation systems in e-commerce",
        user_input={
            "theme": "recommendation systems",
            "description": "AI-powered personalization for online retail",
            "area_of_study": "e-commerce, artificial intelligence",
            "keywords": ["recommendation", "personalization", "collaborative filtering"],
        },
    )

    research_id = research.id
    print(f"[OK] Research created: {research_id}")

    # ========================================================================
    # STEP 2: REFINE TOPIC (with token tracking)
    # ========================================================================
    print("\n[2] Refining topic (1st attempt)...")

    start_time = time.time()

    # Simulate LLM response
    input_tokens_refine_1 = 1200
    output_tokens_refine_1 = 800

    # Calculate cost
    input_cost, output_cost, total_cost = calculate_token_cost(
        model="gemini",
        input_tokens=input_tokens_refine_1,
        output_tokens=output_tokens_refine_1,
        variant="gemini-1.5-pro",
    )

    # Register token usage
    await ResearchService.add_token_usage(
        session=session,
        research_id=research_id,
        phase_name="refine",
        llm_call_type="generate_candidate_topics",
        model="gemini",
        model_variant="gemini-1.5-pro",
        input_tokens=input_tokens_refine_1,
        output_tokens=output_tokens_refine_1,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        api_latency_ms=int((time.time() - start_time) * 1000),
        call_number=1,
        status="success",
        metadata={
            "prompt_size": 1200,
            "response_size": 800,
            "temperature": 0.7,
        },
    )

    print(f"[OK] Refine phase 1 - Tokens: {input_tokens_refine_1 + output_tokens_refine_1}, Cost: {format_cost(total_cost)}")

    # ========================================================================
    # STEP 3: REFINE TOPIC AGAIN (client wants to refine 2x)
    # ========================================================================
    print("\n[3] Refining topic (2nd attempt)...")

    start_time = time.time()

    input_tokens_refine_2 = 1150
    output_tokens_refine_2 = 850

    input_cost, output_cost, total_cost = calculate_token_cost(
        model="gemini",
        input_tokens=input_tokens_refine_2,
        output_tokens=output_tokens_refine_2,
        variant="gemini-1.5-pro",
    )

    await ResearchService.add_token_usage(
        session=session,
        research_id=research_id,
        phase_name="refine",
        llm_call_type="generate_candidate_topics",
        model="gemini",
        model_variant="gemini-1.5-pro",
        input_tokens=input_tokens_refine_2,
        output_tokens=output_tokens_refine_2,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        api_latency_ms=int((time.time() - start_time) * 1000),
        call_number=2,
        status="success",
    )

    print(f"[OK] Refine phase 2 - Tokens: {input_tokens_refine_2 + output_tokens_refine_2}, Cost: {format_cost(total_cost)}")

    # ========================================================================
    # STEP 4: PROBE SEARCH
    # ========================================================================
    print("\n[4] Probe search...")

    start_time = time.time()

    input_tokens_probe = 3500
    output_tokens_probe = 2500

    input_cost, output_cost, total_cost = calculate_token_cost(
        model="gemini",
        input_tokens=input_tokens_probe,
        output_tokens=output_tokens_probe,
        variant="gemini-1.5-pro",
    )

    await ResearchService.add_token_usage(
        session=session,
        research_id=research_id,
        phase_name="probe",
        llm_call_type="probe_search",
        model="gemini",
        model_variant="gemini-1.5-pro",
        input_tokens=input_tokens_probe,
        output_tokens=output_tokens_probe,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        api_latency_ms=int((time.time() - start_time) * 1000),
        call_number=1,
        status="success",
    )

    print(f"[OK] Probe search - Tokens: {input_tokens_probe + output_tokens_probe}, Cost: {format_cost(total_cost)}")

    # ========================================================================
    # STEP 5: EXTRACT TERMS
    # ========================================================================
    print("\n[5] Extracting terms...")

    start_time = time.time()

    input_tokens_extract = 2800
    output_tokens_extract = 1200

    input_cost, output_cost, total_cost = calculate_token_cost(
        model="gemini",
        input_tokens=input_tokens_extract,
        output_tokens=output_tokens_extract,
        variant="gemini-1.5-pro",
    )

    await ResearchService.add_token_usage(
        session=session,
        research_id=research_id,
        phase_name="extract",
        llm_call_type="extract_terms",
        model="gemini",
        model_variant="gemini-1.5-pro",
        input_tokens=input_tokens_extract,
        output_tokens=output_tokens_extract,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        api_latency_ms=int((time.time() - start_time) * 1000),
        call_number=1,
        status="success",
    )

    print(f"[OK] Extract terms - Tokens: {input_tokens_extract + output_tokens_extract}, Cost: {format_cost(total_cost)}")

    # ========================================================================
    # STEP 6: GENERATE FINAL QUERIES
    # ========================================================================
    print("\n[6] Generating final queries...")

    start_time = time.time()

    input_tokens_final = 2200
    output_tokens_final = 900

    input_cost, output_cost, total_cost = calculate_token_cost(
        model="gemini",
        input_tokens=input_tokens_final,
        output_tokens=output_tokens_final,
        variant="gemini-1.5-pro",
    )

    await ResearchService.add_token_usage(
        session=session,
        research_id=research_id,
        phase_name="final",
        llm_call_type="generate_final_queries",
        model="gemini",
        model_variant="gemini-1.5-pro",
        input_tokens=input_tokens_final,
        output_tokens=output_tokens_final,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        api_latency_ms=int((time.time() - start_time) * 1000),
        call_number=1,
        status="success",
    )

    print(f"[OK] Final queries - Tokens: {input_tokens_final + output_tokens_final}, Cost: {format_cost(total_cost)}")

    # ========================================================================
    # STEP 7: RETRIEVE TOKEN USAGE SUMMARY
    # ========================================================================
    print("\n[7] Token Usage Summary")
    print("-" * 100)

    summary = await ResearchService.get_token_summary(session, research_id)

    print(f"\nTotal Tokens Used: {format_tokens(summary['total_tokens'])}")
    print(f"Total Cost: {format_cost(summary['total_cost_usd'])}")
    print(f"Total API Calls: {len(summary['call_history'])}")

    print("\n[By Phase]")
    for phase_name, phase_data in summary["by_phase"].items():
        print(
            f"  {phase_name.upper():<15} {phase_data['calls']:>2} calls, {format_tokens(phase_data['tokens']):>8} tokens, {format_cost(phase_data['cost_usd']):>10}"
        )

    print("\n[By Model]")
    for model_name, model_data in summary["by_model"].items():
        print(
            f"  {model_name:<25} {model_data['calls']:>2} calls, {format_tokens(model_data['tokens']):>8} tokens, {format_cost(model_data['cost_usd']):>10}"
        )

    print("\n[Call History]")
    print(f"{'Timestamp':<25} {'Phase':<10} {'Tokens':<10} {'Cost':<10}")
    print("-" * 55)
    for call in summary["call_history"]:
        print(
            f"{call['timestamp'][:19]:<25} {call['phase']:<10} {format_tokens(call['tokens']):<10} {format_cost(call['total_cost_usd']):<10}"
        )

    # ========================================================================
    # STEP 8: RETRIEVE DETAILED USAGE
    # ========================================================================
    print("\n[8] Detailed Token Usage")
    print("-" * 100)

    usage_records = await ResearchService.get_token_usage(session, research_id)

    print(f"\n{'#':<3} {'Phase':<10} {'Call':<6} {'Model':<25} {'Input':<8} {'Output':<8} {'Total':<8} {'Cost':<10} {'Status':<10}")
    print("-" * 100)

    for i, record in enumerate(usage_records, 1):
        model_str = f"{record.model}"
        if record.model_variant:
            model_str = f"{record.model} ({record.model_variant})"

        print(
            f"{i:<3} {record.phase_name:<10} {record.call_number:<6} {model_str:<25} "
            f"{format_tokens(record.input_tokens):<8} {format_tokens(record.output_tokens):<8} "
            f"{format_tokens(record.total_tokens):<8} {format_cost(record.total_cost_usd):<10} {record.status:<10}"
        )

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    total_phases = len(summary["by_phase"])
    total_calls = len(summary["call_history"])
    refine_calls = summary["by_phase"].get("refine", {}).get("calls", 0)

    print(f"""
Research: {research.title}
Status: {research.status}

Token Usage:
  - Total tokens: {format_tokens(summary['total_tokens'])}
  - Total cost: {format_cost(summary['total_cost_usd'])} USD
  - API calls: {total_calls}
  - Phases: {total_phases}

Key Insight:
  - Refine phase called {refine_calls}x (user explored multiple options)
  - Most expensive phase: {max(summary["by_phase"], key=lambda x: summary["by_phase"][x]["cost_usd"])}
  - Model used: Gemini (most cost-effective)

Cost Breakdown:
  - Per call average: {format_cost(summary['total_cost_usd'] / total_calls)} USD
  - Estimated monthly cost (1000 searches): {format_cost((summary['total_cost_usd'] / total_calls) * 1000)} USD
""")

    print("=" * 100 + "\n")


if __name__ == "__main__":
    print("\n" + "=" * 100)
    print("NOTE: This example requires a database session to run")
    print("Use it within your FastAPI app or async context with proper database setup")
    print("=" * 100)

    print("""
Example usage in ResearchWorkflow:

    from services.research_service import ResearchService
    from services.token_cost_calculator import calculate_token_cost

    # After calling LLM
    input_tokens = 1200
    output_tokens = 800

    input_cost, output_cost, total_cost = calculate_token_cost(
        model="gemini",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        variant="gemini-1.5-pro",
    )

    await ResearchService.add_token_usage(
        session=session,
        research_id=research_id,
        phase_name="refine",
        llm_call_type="generate_candidate_topics",
        model="gemini",
        model_variant="gemini-1.5-pro",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        api_latency_ms=1250,
        call_number=1,
    )
""")
