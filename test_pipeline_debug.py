#!/usr/bin/env python3
"""Debug pipeline to see where terms are being filtered."""

from services.nlp.term_extraction import TermExtractor

# Realistic abstract and title
title = "Composite ultrafiltration membranes for water desalination"
abstract = """
This paper presents composite ultrafiltration membranes with nanoporous graphene
layers for efficient water desalination. The membranes show improved purification
treatment device efficiency in salt water desalination processes. The composite
membrane structure provides enhanced mechanical strength and dissolution resistance
for seawater treatment applications with brackish water desalination capability.
"""

extractor = TermExtractor()

# Prepare enriched results format expected by the method
enriched_results = [
    {
        "title": title,
        "abstract": abstract,
    }
]

original_params = {}

# Extract with full debugging
result = extractor.extract_and_rank_terms(
    original_params=original_params,
    enriched_results=enriched_results,
    top_k=100,  # Request many to see filtering (deprecated but harmless)
)

print("=" * 90)
print("PIPELINE DEBUG - TERM FILTERING ANALYSIS")
print("=" * 90)

print(f"\nReturned terms: {len(result)}")
print("\nTerms returned:")
print("-" * 90)

for i, term_obj in enumerate(result, 1):
    term = term_obj["term"]
    score = term_obj["score"]
    sources = term_obj.get("sources", [])
    print(f"{i:3}. {term:45} (score: {score:.3f}, sources: {sources})")

print("\n" + "=" * 90)
print(f"Total returned: {len(result)} terms")
print("=" * 90)
