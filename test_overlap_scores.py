#!/usr/bin/env python3
"""Debug overlap filter to see all scores."""

from services.nlp.term_extraction import TermExtractor

title = "Composite ultrafiltration membranes for water desalination"
abstract = """
This paper presents composite ultrafiltration membranes with nanoporous graphene
layers for efficient water desalination. The membranes show improved purification
treatment device efficiency in salt water desalination processes. The composite
membrane structure provides enhanced mechanical strength and dissolution resistance
for seawater treatment applications with brackish water desalination capability.
"""

extractor = TermExtractor()

enriched_results = [{"title": title, "abstract": abstract}]

# Patch to capture intermediate results
original_method = extractor.extract_and_rank_terms

def patched_extract(original_params, enriched_results, top_k=None):
    result = original_method(original_params, enriched_results, top_k)
    return result

result = extractor.extract_and_rank_terms(
    original_params={},
    enriched_results=enriched_results,
)

print("=" * 90)
print("ALL TERMS AFTER OVERLAP FILTER (before score threshold)")
print("=" * 90)

# Run again to get all terms including those below threshold
import importlib
import services.nlp.term_extraction
importlib.reload(services.nlp.term_extraction)

from services.nlp.term_extraction import TermExtractor

extractor = TermExtractor()

# Access internal state by modifying config threshold temporarily
from core.config import settings
original_threshold = settings.term_extraction_score_threshold
settings.term_extraction_score_threshold = 0.0  # Return all

result_all = extractor.extract_and_rank_terms(
    original_params={},
    enriched_results=enriched_results,
)

settings.term_extraction_score_threshold = original_threshold

print(f"\nAll {len(result_all)} terms (threshold 0.0):\n")
for i, term_obj in enumerate(result_all, 1):
    term = term_obj["term"]
    score = term_obj["score"]
    print(f"{i:2}. {term:45} (score: {score:.3f})")

print("\n" + "=" * 90)
