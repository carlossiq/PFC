"""
Analyze token usage in LLM prompts and responses.

Estimates tokens based on character count and actual usage patterns.
"""

from pathlib import Path
import os


def estimate_tokens(text: str, model: str = "gemini") -> int:
    """
    Estimate token count based on character count.

    Rough estimation:
    - Gemini: ~1 token per 4 characters (including spaces)
    - GPT-4: ~1 token per 4 characters
    - Claude: ~1 token per 3.5-4 characters

    More precise: use actual tokenizer, but this gives ballpark
    """
    if not text:
        return 0

    # Rough estimate: 1 token ≈ 4 characters
    return len(text) // 4


def analyze_prompt_file(filepath: str) -> dict:
    """Analyze a single prompt file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        char_count = len(content)
        token_estimate = estimate_tokens(content)
        lines = len(content.split('\n'))

        return {
            "success": True,
            "filename": Path(filepath).name,
            "filepath": filepath,
            "chars": char_count,
            "tokens": token_estimate,
            "lines": lines,
        }
    except Exception as e:
        return {
            "success": False,
            "filename": Path(filepath).name,
            "error": str(e),
        }


def main():
    """Analyze all prompts and estimate token usage."""

    print("\n" + "=" * 100)
    print("LLM TOKEN USAGE ANALYSIS")
    print("=" * 100)

    prompts_dir = Path("c:/Users/carlo/OneDrive/Documentos/GitHub/PFC/prompts")

    # Collect all prompt files
    prompt_files = list(prompts_dir.glob("*.txt")) + list(prompts_dir.glob("*.md"))
    prompt_files = [f for f in prompt_files if f.is_file()]

    if not prompt_files:
        print("[ERROR] No prompt files found")
        return

    # Analyze each file
    results = []
    for filepath in sorted(prompt_files):
        result = analyze_prompt_file(str(filepath))
        if result.get("success"):
            results.append(result)

    # Sort by tokens (descending)
    results.sort(key=lambda x: x.get("tokens", 0), reverse=True)

    # Display results
    print("\n[1] PROMPT FILE SIZES")
    print("-" * 100)
    print(f"{'Filename':<40} {'Chars':<10} {'Tokens':<10} {'Lines':<10}")
    print("-" * 70)

    total_chars = 0
    total_tokens = 0

    for result in results:
        print(f"{result['filename']:<40} {result['chars']:<10} {result['tokens']:<10} {result['lines']:<10}")
        total_chars += result['chars']
        total_tokens += result['tokens']

    print("-" * 70)
    print(f"{'TOTAL':<40} {total_chars:<10} {total_tokens:<10}")

    # ========================================================================
    # ANALYSIS BY WORKFLOW PHASE
    # ========================================================================
    print("\n[2] TOKEN USAGE BY WORKFLOW PHASE")
    print("-" * 100)

    phase_map = {
        "refine_topic": ["refine_topic_system_prompt.txt"],
        "probe_search": ["probe_system_prompt.txt", "probe_system_prompt copy.txt"],
        "final_queries": ["final_system_prompt.md"],
        "general": ["general_system_prompt.txt"],
    }

    for phase_name, filenames in phase_map.items():
        phase_tokens = sum(
            r['tokens'] for r in results
            if r['filename'] in filenames
        )
        phase_chars = sum(
            r['chars'] for r in results
            if r['filename'] in filenames
        )

        print(f"\n{phase_name.upper():<20} Tokens: {phase_tokens:>6}  Chars: {phase_chars:>8}")
        for filename in filenames:
            matching = [r for r in results if r['filename'] == filename]
            if matching:
                r = matching[0]
                print(f"  +- {r['filename']:<35} {r['tokens']:>6} tokens")

    # ========================================================================
    # COST ESTIMATION
    # ========================================================================
    print("\n[3] COST ESTIMATION (USD)")
    print("-" * 100)

    # Pricing (as of 2024)
    gemini_input = 0.075 / 1_000_000  # $0.075 per 1M input tokens
    gemini_output = 0.30 / 1_000_000   # $0.30 per 1M output tokens
    gpt4_input = 3.00 / 1_000_000      # $3.00 per 1M input tokens
    gpt4_output = 6.00 / 1_000_000     # $6.00 per 1M output tokens
    claude_input = 3.00 / 1_000_000    # $3.00 per 1M input tokens
    claude_output = 15.00 / 1_000_000  # $15.00 per 1M output tokens

    # Estimate: 1 call per phase, average output ≈ 2x input
    calls_per_phase = 1
    phases_count = 4
    total_calls = calls_per_phase * phases_count

    avg_input_tokens = total_tokens // phases_count
    avg_output_tokens = avg_input_tokens * 2  # Rough estimate

    print(f"\nAssumptions:")
    print(f"  - {phases_count} workflow phases (refine, probe, extract, final)")
    print(f"  - {calls_per_phase} call per phase")
    print(f"  - Total prompt tokens: {total_tokens}")
    print(f"  - Average input per call: {avg_input_tokens} tokens")
    print(f"  - Average output per call (estimate): {avg_output_tokens} tokens")

    print(f"\nCost per workflow execution:")
    print("-" * 50)

    for provider, input_price, output_price in [
        ("Gemini", gemini_input, gemini_output),
        ("GPT-4", gpt4_input, gpt4_output),
        ("Claude 3", claude_input, claude_output),
    ]:
        total_cost = (total_tokens + avg_output_tokens * phases_count) * input_price
        total_cost += (avg_output_tokens * phases_count) * output_price

        print(f"\n{provider:.<20} ${total_cost:.4f} per workflow")
        print(f"  Input:  {total_tokens + avg_output_tokens} tokens × ${input_price*1_000_000:.3f}/1M")
        print(f"  Output: {avg_output_tokens * phases_count} tokens × ${output_price*1_000_000:.3f}/1M")

    # ========================================================================
    # OPTIMIZATION OPPORTUNITIES
    # ========================================================================
    print("\n[4] OPTIMIZATION OPPORTUNITIES")
    print("-" * 100)

    recommendations = [
        {
            "area": "Probe System Prompt",
            "current": "7408 bytes (~1850 tokens)",
            "issue": "Very detailed with many examples",
            "savings": "Could reduce ~30% (1300 tokens -> 900 tokens)",
            "action": "Move examples to response format instead of prompt",
        },
        {
            "area": "General System Prompt",
            "current": "6568 bytes (~1642 tokens)",
            "issue": "Extensive formatting rules",
            "savings": "Could reduce ~20% (1642 tokens -> 1300 tokens)",
            "action": "Consolidate formatting into JSON schema",
        },
        {
            "area": "Refine Topic Prompt",
            "current": "3407 bytes (~852 tokens)",
            "issue": "Many examples of good/bad variations",
            "savings": "Could reduce ~25% (852 tokens -> 640 tokens)",
            "action": "Use single concise example instead of multiple",
        },
        {
            "area": "Dynamic Field Specification",
            "current": "Included in probe_system_prompt",
            "issue": "Field specs are large and static",
            "savings": "Could extract to client (0 tokens in prompt)",
            "action": "Send field spec only once, cache on client",
        },
        {
            "area": "Final Queries Prompt",
            "current": "4839 bytes (~1210 tokens)",
            "issue": "Detailed complexity rules included",
            "savings": "Could reduce ~15% (1210 tokens -> 1030 tokens)",
            "action": "Validate complexity client-side, simpler prompt",
        },
    ]

    print(f"\n{'Area':<30} {'Current':<20} {'Potential Saving':<15}")
    print("-" * 65)

    total_potential_savings = 0
    for rec in recommendations:
        print(f"{rec['area']:<30} {rec['current']:<20} {rec['savings']:<15}")

        # Extract token numbers from savings
        import re
        match = re.search(r'(\d+)\s*tokens\s*→\s*(\d+)\s*tokens', rec['savings'])
        if match:
            current = int(match.group(1))
            potential = int(match.group(2))
            saving = current - potential
            total_potential_savings += saving

    print(f"\nTotal potential token reduction: {total_potential_savings} tokens (~{total_potential_savings / total_tokens * 100:.1f}%)")

    # ========================================================================
    # DETAILED RECOMMENDATIONS
    # ========================================================================
    print("\n[5] DETAILED OPTIMIZATION PLAN")
    print("-" * 100)

    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['area'].upper()}")
        print(f"   Current: {rec['current']}")
        print(f"   Issue: {rec['issue']}")
        print(f"   Action: {rec['action']}")
        print(f"   Savings: {rec['savings']}")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    print(f"""
Current Situation:
  - Total prompt tokens: {total_tokens} (~${total_tokens * gemini_input:.4f} per workflow in Gemini)
  - 4 main workflow phases
  - Prompts are comprehensive but verbose

Optimization Potential:
  - Could reduce ~30-35% of tokens ({total_potential_savings} tokens)
  - Would save ~${total_potential_savings * gemini_input:.4f} per workflow call
  - With 1000 requests/month: ${total_potential_savings * gemini_input * 1000:.2f}/month saving

Quick Wins (Easy to implement):
  1. Extract field specifications to client-side caching
  2. Reduce redundant examples (keep 1 best example per section)
  3. Move formatting rules to JSON schema validation client-side
  4. Use shorter placeholder names in examples

Top Priority:
  - Probe system prompt (largest, most room for improvement)
  - ~1000 tokens => ~700 tokens possible
""")

    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
