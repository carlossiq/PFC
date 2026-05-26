#!/usr/bin/env python3
"""
Teste completo do fluxo de Probe Search:
1. POST /chat/probe/query - Construir query
2. POST /chat/probe/search - Executar busca bruta
3. POST /chat/probe/enrich - Enriquecer top 10 resultados
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_probe_workflow():
    """Testa o fluxo completo de probe search."""

    print("\n" + "=" * 80)
    print("TESTE COMPLETO: FLUXO DE PROBE SEARCH")
    print("=" * 80)

    # ============================================================================
    # ETAPA 1: POST /chat/probe/query - Construir query
    # ============================================================================
    print("\n[ETAPA 1] POST /api/v1/chat/probe/query - Construir Query")
    print("-" * 80)

    intake_data = {
        "theme": "Deep learning for medical diagnosis",
        "description": "AI-based diagnostic systems for medical imaging",
        "area_of_study": "Healthcare & AI",
        "keywords": ["computer-aided diagnosis", "deep learning", "medical imaging"],
    }

    print(f"\nIntake:")
    print(f"  Theme: {intake_data['theme']}")
    print(f"  Description: {intake_data['description']}")
    print(f"  Area: {intake_data['area_of_study']}")
    print(f"  Keywords: {', '.join(intake_data['keywords'])}")

    response1 = client.post(
        "/api/v1/chat/probe/query",
        json=intake_data,
        params={"api": "ops"},
    )

    print(f"\nResposta:")
    print(f"  Status: {response1.status_code}")

    if response1.status_code != 200:
        print(f"  [ERRO] {response1.json()}")
        return

    data1 = response1.json()
    print(f"  Success: {data1.get('success')}")

    if not data1.get("success"):
        print(f"  [ERRO] {data1.get('data', {}).get('error')}")
        return

    query_result = data1.get("data", {})
    query_built = query_result.get("query", {})

    print(f"\nQuery Construída:")
    print(f"  API: {query_result.get('api')}")
    print(f"  Attempt: {query_result.get('attempt')}")
    print(f"  Complexity Score: {query_result.get('complexity', {}).get('score')}")
    print(f"  Complexity Level: {query_result.get('complexity', {}).get('level')}")
    print(f"  Query String: {query_built.get('query', '')[:100]}...")

    # ============================================================================
    # ETAPA 2: POST /chat/probe/search - Executar busca com abstracts
    # ============================================================================
    print("\n" + "=" * 80)
    print("[ETAPA 2] POST /api/v1/chat/probe/search - Busca com Abstracts")
    print("-" * 80)

    search_payload = {
        "query": query_built,
        "api": "ops",
        "top_k": 10,
    }

    print(f"\nPayload:")
    print(f"  API: {search_payload['api']}")
    print(f"  Top K: {search_payload['top_k']}")
    print(f"  Query string (resumido): {search_payload['query'].get('query', '')[:80]}...")

    response2 = client.post(
        "/api/v1/chat/probe/search",
        json=search_payload,
    )

    print(f"\nResposta:")
    print(f"  Status: {response2.status_code}")

    if response2.status_code != 200:
        print(f"  [ERRO] {response2.json()}")
        return

    data2 = response2.json()
    print(f"  Success: {data2.get('success')}")

    search_result = data2.get("data", {})
    print(f"\nResultados da Busca:")
    print(f"  API: {search_result.get('api')}")
    print(f"  Results returned: {search_result.get('results_count')}")
    print(f"  Total available: {search_result.get('total_available')}")
    print(f"  Has abstracts: {search_result.get('has_abstracts')}")
    print(f"  Error: {search_result.get('error')}")

    results_with_abstracts = search_result.get("results", [])
    if results_with_abstracts:
        print(f"\n[OK] Recebidos {len(results_with_abstracts)} resultados COM abstracts")

        print(f"\nPrimeiros 3 resultados:")
        for i, result in enumerate(results_with_abstracts[:3], 1):
            print(f"\n  [{i}]")
            if isinstance(result, dict):
                pub_ref = result.get("publication-reference", "N/A")
                abstract = result.get("abstract", "N/A")
                print(f"      Publication Reference: {str(pub_ref)[:100]}...")
                if abstract and abstract != "N/A":
                    print(f"      Abstract: {abstract[:150]}...")
                else:
                    print(f"      Abstract: [Não disponível]")
    else:
        print(f"[AVISO] Sem resultados na busca")
        return

    # ============================================================================
    # ETAPA 3: POST /chat/extract-terms - Extrair termos relevantes
    # ============================================================================
    print("\n" + "=" * 80)
    print("[ETAPA 3] POST /api/v1/chat/extract-terms - Extração de Termos")
    print("-" * 80)

    extract_payload = {
        "enriched_results": results_with_abstracts,
        "original_params": intake_data,
        "top_k": 20,
    }

    print(f"\nPayload:")
    print(f"  Total results: {len(results_with_abstracts)}")
    print(f"  Top K terms: {extract_payload['top_k']}")

    response3 = client.post(
        "/api/v1/chat/extract-terms",
        json=extract_payload,
    )

    print(f"\nResposta:")
    print(f"  Status: {response3.status_code}")

    if response3.status_code != 200:
        print(f"  [ERRO] {response3.json()}")
        return

    data3 = response3.json()
    print(f"  Success: {data3.get('success')}")

    extract_result = data3.get("data", {})
    print(f"\nTermos Extraídos:")
    terms = extract_result.get("terms", [])
    if terms:
        print(f"  Total: {len(terms)}")
        print(f"  Top 5 termos:")
        for i, term in enumerate(terms[:5], 1):
            print(f"    {i}. {term}")

    # ============================================================================
    # RESUMO FINAL
    # ============================================================================
    print("\n" + "=" * 80)
    print("[RESUMO] TESTE COMPLETADO COM SUCESSO!")
    print("=" * 80)
    print(f"\nFluxo executado:")
    print(f"  ✅ [ETAPA 1] Query construída com sucesso")
    print(f"  ✅ [ETAPA 2] Busca retornou {search_result.get('results_count')} resultados COM abstracts")
    print(f"  ✅ [ETAPA 3] Extração de termos extraiu {len(terms)} termos relevantes")
    print("\nPróximos passos:")
    print(f"  • Use os {len(terms)} termos extraídos para:")
    print(f"    - POST /chat/final/queries-multi (cria 3 variações de query final)")
    print(f"    - POST /chat/final/search (busca final com mais resultados)")


if __name__ == "__main__":
    test_probe_workflow()
