"""
Workflow demonstration with pre-computed data.

Shows the complete flow: Input -> Refined Topics -> Extracted Terms -> 3 Query Variants
"""

import json
from datetime import datetime


def display_workflow_demo():
    """Display complete workflow demonstration."""

    print("\n" + "=" * 100)
    print("TECHNOLOGY PROSPECTING WORKFLOW - DEMONSTRATION")
    print("=" * 100)

    # ============================================================================
    # STEP 1: INPUT
    # ============================================================================
    print("\n[STEP 1] INITIAL INPUT")
    print("-" * 100)

    user_input = {
        "theme": "e-commerce",
        "description": "online retail technologies",
        "area_of_study": "Information Technology",
        "keywords": ["payment", "logistics", "platform"],
    }

    print(f"Theme:           {user_input['theme']}")
    print(f"Description:     {user_input['description']}")
    print(f"Area of Study:   {user_input['area_of_study']}")
    print(f"Keywords:        {', '.join(user_input['keywords'])}")
    print(f"\nInput complexity: Simple, generic keywords")

    # ============================================================================
    # STEP 2: REFINED TOPICS (from LLM)
    # ============================================================================
    print("\n[STEP 2] REFINED TOPICS (from LLM)")
    print("-" * 100)

    refined_candidates = [
        {
            "theme": "AI-driven hyper-personalization engines for dynamic e-commerce recommendations",
            "description": "Development and implementation of advanced artificial intelligence models to deliver highly individualized product recommendations using behavioral analytics and contextual data",
            "area_of_study": "Artificial Intelligence, Machine Learning",
            "keywords": ["recommendation system", "personalization", "AI", "behavioral analytics", "CTR"],
        },
        {
            "theme": "Blockchain-based supply chain transparency and payment settlement for B2B e-commerce",
            "description": "Implementation of distributed ledger technology for automated supplier verification, real-time logistics tracking, and cryptocurrency-based payment systems",
            "area_of_study": "Blockchain, Financial Technology",
            "keywords": ["blockchain", "supply chain", "payment settlement", "smart contracts", "traceability"],
        },
        {
            "theme": "Voice commerce and conversational AI for omnichannel retail experiences",
            "description": "Natural language processing systems enabling voice-activated shopping, customer service, and multimodal shopping experiences across devices",
            "area_of_study": "Natural Language Processing, Voice Technology",
            "keywords": ["voice commerce", "conversational AI", "NLP", "smart speakers", "omnichannel"],
        },
        {
            "theme": "Real-time inventory optimization and demand forecasting using predictive analytics",
            "description": "Machine learning models for stock management, demand prediction, and logistics optimization to reduce costs and improve customer satisfaction",
            "area_of_study": "Predictive Analytics, Operations Research",
            "keywords": ["demand forecasting", "inventory optimization", "predictive analytics", "machine learning"],
        },
    ]

    for i, candidate in enumerate(refined_candidates, 1):
        print(f"\n{i}. {candidate['theme']}")
        print(f"   Description: {candidate['description'][:80]}...")
        print(f"   Area: {candidate['area_of_study']}")
        print(f"   Keywords: {', '.join(candidate['keywords'][:3])}...")

    selected = refined_candidates[0]
    print(f"\n>>> Selected for probe search: Candidate #1")

    # ============================================================================
    # STEP 3: PROBE QUERY (from OPS)
    # ============================================================================
    print("\n[STEP 3] PROBE QUERY (Built via LLM)")
    print("-" * 100)

    probe_query = {
        "query": 'ti = ("personalization" OR "recommendation") AND (ab = "e-commerce" OR ab = "online retail")',
        "range": "1-10",
        "format": "json",
    }

    print(f"CQL Query:")
    print(f"  {probe_query['query']}")
    print(f"Results Range: {probe_query['range']}")

    # ============================================================================
    # STEP 4: PROBE SEARCH RESULTS (Simulated)
    # ============================================================================
    print("\n[STEP 4] PROBE SEARCH RESULTS (10 documents)")
    print("-" * 100)

    probe_results = [
        {
            "title": "Deep Learning for Product Recommendation in E-Commerce",
            "abstract": "This paper presents a neural network approach to personalization in online retail environments...",
            "applicants": ["Amazon"],
            "year": 2023,
        },
        {
            "title": "Real-time Personalization Engine for Online Shopping Platforms",
            "abstract": "A machine learning system for generating real-time product recommendations based on user behavior...",
            "applicants": ["Netflix"],
            "year": 2022,
        },
        {
            "title": "Collaborative Filtering Algorithms for E-Commerce Marketplaces",
            "abstract": "Novel algorithms for collaborative filtering to improve product discovery and recommendation accuracy...",
            "applicants": ["Google"],
            "year": 2023,
        },
        {
            "title": "Customer Behavior Analysis Using Contextual Bandits",
            "abstract": "Application of contextual bandit algorithms to optimize product recommendations in real-time...",
            "applicants": ["Facebook"],
            "year": 2023,
        },
        {
            "title": "Federated Learning for Personalized Product Recommendations",
            "abstract": "Privacy-preserving machine learning approach for personalization without centralizing user data...",
            "applicants": ["Apple"],
            "year": 2023,
        },
    ]

    for i, doc in enumerate(probe_results[:3], 1):
        print(f"\n{i}. {doc['title']}")
        print(f"   {doc['abstract'][:70]}...")
        print(f"   Applicants: {', '.join(doc['applicants'])} | Year: {doc['year']}")

    print(f"\n... and 7 more results")

    # ============================================================================
    # STEP 5: EXTRACTED TERMS
    # ============================================================================
    print("\n[STEP 5] EXTRACTED RELEVANT TERMS (Top 15)")
    print("-" * 100)

    extracted_terms = [
        ("recommendation system", 0.92, 8),
        ("personalization", 0.88, 7),
        ("collaborative filtering", 0.85, 6),
        ("machine learning", 0.82, 5),
        ("neural networks", 0.79, 4),
        ("user behavior", 0.76, 5),
        ("product discovery", 0.74, 3),
        ("real-time systems", 0.72, 3),
        ("deep learning", 0.70, 4),
        ("customer analytics", 0.68, 2),
        ("conversion optimization", 0.66, 2),
        ("contextual bandits", 0.64, 2),
        ("federated learning", 0.62, 1),
        ("privacy-preserving", 0.60, 1),
        ("online learning", 0.58, 2),
    ]

    print(f"{'Term':<30} {'Score':<8} {'Frequency':<10}")
    print("-" * 50)
    for term, score, freq in extracted_terms:
        print(f"{term:<30} {score:>6.2f}    {freq:>6}")

    # ============================================================================
    # STEP 6: FINAL QUERIES (3 VARIANTS)
    # ============================================================================
    print("\n[STEP 6] FINAL QUERY VARIANTS")
    print("=" * 100)

    variants = {
        "SPECIFIC": {
            "description": "High precision (terms scored > 0.4)",
            "query": 'ti = (("recommendation system" OR "personalization" OR "collaborative filtering") AND ("e-commerce" OR "online retail")) AND ab = ("machine learning" OR "neural networks")',
            "complexity": 28.5,
            "rationale": "Uses highest-scoring terms for precise results",
            "focus": ["Recommendation", "AI/ML", "E-commerce"],
        },
        "BALANCED": {
            "description": "Recommended balance (terms scored > 0.3)",
            "query": 'ti = (("recommendation system" OR "personalization" OR "collaborative filtering" OR "machine learning" OR "neural networks") AND ("e-commerce" OR "online retail" OR "shopping")) OR ab = ("user behavior" OR "product discovery")',
            "complexity": 38.2,
            "rationale": "Balanced coverage with strong signal",
            "focus": ["Recommendations", "Personalization", "ML", "E-commerce", "Behavior"],
        },
        "GENERIC": {
            "description": "High coverage (terms scored > 0.2)",
            "query": 'ti = (("recommendation" OR "personalization" OR "collaborative filtering" OR "machine learning" OR "neural networks" OR "user behavior" OR "product discovery" OR "real-time systems" OR "deep learning") AND ("e-commerce" OR "online retail" OR "shopping" OR "platform")) OR ab = ("customer analytics" OR "conversion" OR "learning")',
            "complexity": 52.3,
            "rationale": "Broad coverage including peripheral technologies",
            "focus": ["Broad tech stack", "Multiple domains", "E-commerce ecosystem"],
        },
    }

    for variant_name, variant_data in variants.items():
        print(f"\n{variant_name} VARIANT")
        print("-" * 100)
        print(f"Description:     {variant_data['description']}")
        print(f"Complexity Score: {variant_data['complexity']:.1f}/100")
        print(f"Status:           {'[OK]' if variant_data['complexity'] < 60 else '[OVER LIMIT]'}")
        print(f"Rationale:       {variant_data['rationale']}")
        print(f"Focus Areas:      {', '.join(variant_data['focus'])}")
        print(f"\nCQL Query:")
        print(f"  {variant_data['query']}\n")

    # ============================================================================
    # FINAL COMPARISON
    # ============================================================================
    print("\n" + "=" * 100)
    print("COMPARISON: INPUT vs OUTPUT")
    print("=" * 100)

    print("\n[INPUT]")
    print("-" * 100)
    print(f"Original Theme:  '{user_input['theme']}'")
    print(f"Keywords:        {', '.join(user_input['keywords'])}")
    print(f"Specificity:     Generic/Broad")

    print("\n[PROCESS]")
    print("-" * 100)
    print(f"1. LLM Refined theme to: '{selected['theme']}'")
    print(f"   - Added specificity: AI, personalization, recommendation")
    print(f"   - Generated specialized keywords: {', '.join(selected['keywords'][:5])}")
    print(f"\n2. Probe Search: Explored {len(probe_results)} results")
    print(f"   - Found key patterns: Recommendation systems, ML approaches")
    print(f"\n3. Term Extraction: Identified {len(extracted_terms)} relevant terms")
    print(f"   - Top term: '{extracted_terms[0][0]}' (score: {extracted_terms[0][1]})")
    print(f"\n4. Query Generation: Created 3 variants")
    print(f"   - Specific (28.5/100): High precision")
    print(f"   - Balanced (38.2/100): Recommended - broadest safe coverage")
    print(f"   - Generic (52.3/100): Comprehensive but noisier")

    print("\n[OUTPUT]")
    print("-" * 100)
    print("3 Query Variants Ready for Full Search:")
    print(f"  1. SPECIFIC   - {len([t for t in extracted_terms if t[1] > 0.4])} high-confidence terms")
    print(f"  2. BALANCED   - {len([t for t in extracted_terms if t[1] > 0.3])} medium-confidence terms (RECOMMENDED)")
    print(f"  3. GENERIC    - {len([t for t in extracted_terms if t[1] > 0.2])} all relevant terms")

    print("\n[KEY INSIGHTS]")
    print("-" * 100)
    specificity_gain = "e-commerce" == user_input['theme'] and selected['theme'] != user_input['theme']
    print(f"[OK] Theme Refinement: Generic -> Specific (AI + Personalization focus)")
    print(f"[OK] Term Discovery: {len(extracted_terms)} new relevant terms extracted from probe results")
    print(f"[OK] Query Variants: Each variant balances precision vs recall")
    print(f"[OK] Ready for Scale: All queries < 60/100 complexity (safe for OPS API)")

    print("\n" + "=" * 100)
    print("WORKFLOW COMPLETED - READY FOR FULL SEARCH")
    print("=" * 100 + "\n")

    # Display metrics summary
    print("\nMETRICS SUMMARY")
    print("-" * 100)
    print(f"Initial Keywords:        {len(user_input['keywords'])}")
    print(f"Refined Keywords:        {len(selected['keywords'])}")
    print(f"Probe Results Analyzed:  {len(probe_results)}")
    print(f"Terms Extracted:         {len(extracted_terms)}")
    print(f"Query Variants:          3")
    print(f"Ready for Final Search:  YES (all variants valid)")


if __name__ == "__main__":
    display_workflow_demo()
