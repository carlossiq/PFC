#!/usr/bin/env python3
"""
Teste de sintaxe query_string complexa.
"""

import json
import httpx
from core.config import settings

def test_query_string_variations():
    """Testa variações de sintaxe query_string."""

    api_token = getattr(settings, "lens_api_token", None)
    url = "https://api.lens.org/patent/search"

    client = httpx.Client(timeout=30)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    print("\n" + "="*60)
    print("TESTE: Variações de Sintaxe query_string")
    print("="*60)

    queries = [
        {
            "name": "query_string SIMPLES",
            "query_str": "machine learning"
        },
        {
            "name": "query_string COM FIELD",
            "query_str": "title:machine learning"
        },
        {
            "name": "query_string COM QUOTES",
            "query_str": 'title:"machine learning"'
        },
        {
            "name": "query_string COM OR",
            "query_str": "title:(machine OR learning)"
        },
        {
            "name": "query_string COM OR QUOTES",
            "query_str": 'title:("machine learning" OR "artificial intelligence")'
        },
        {
            "name": "query_string COM AND OPERATOR",
            "query_str": 'title:("machine learning") AND abstract:("neural networks")'
        },
        {
            "name": "query_string DO PAYLOAD GERADO (ORIGINAL)",
            "query_str": 'title:(("artificial intelligence" OR "machine learning")) AND abstract:("neural networks")'
        },
        {
            "name": "query_string SIMPLIFICADO (SEM PARENTESES DUPLOS)",
            "query_str": 'title:("artificial intelligence" OR "machine learning") AND abstract:("neural networks")'
        }
    ]

    for test in queries:
        print(f"\n{'-'*60}")
        print(f"Teste: {test['name']}")
        print(f"Query string: {test['query_str']}")
        print(f"{'-'*60}")

        payload = {
            "query": {
                "query_string": {
                    "query": test['query_str']
                }
            },
            "size": 2,
            "from": 0
        }

        try:
            response = client.post(url, json=payload, headers=headers)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                total = data.get('total')
                results = data.get('data', [])
                print(f"Total encontrado: {total}")
                print(f"Documentos retornados: {len(results)}")
                if results:
                    title = results[0].get('biblio', {}).get('invention_title', [{}])[0].get('text', 'N/A')
                    print(f"Primeiro documento: {title[:80]}...")
                print("[SUCESSO]")
            else:
                resp_text = response.text[:200]
                print(f"Resposta: {resp_text}")
                print("[FALHA]")

        except Exception as e:
            print(f"Excecao: {str(e)}")

    client.close()


if __name__ == "__main__":
    test_query_string_variations()
