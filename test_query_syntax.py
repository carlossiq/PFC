#!/usr/bin/env python3
"""
Teste de diferentes sintaxes de query para API Lens Patent.
"""

import json
import httpx
from core.config import settings

def test_query_syntax():
    """Testa diferentes sintaxes de query."""

    api_token = getattr(settings, "lens_api_token", None)
    url = "https://api.lens.org/patent/search"

    client = httpx.Client(timeout=30)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    print("\n" + "="*60)
    print("TESTE: Diferentes Sintaxes de Query")
    print("="*60)

    # Teste 1: query_string simples
    queries = [
        {
            "name": "query_string SIMPLES",
            "query": {
                "query_string": {
                    "query": "machine learning"
                }
            }
        },
        {
            "name": "query_string COM CAMPO",
            "query": {
                "query_string": {
                    "query": "title:machine learning"
                }
            }
        },
        {
            "name": "match simples",
            "query": {
                "match": {
                    "title": "machine learning"
                }
            }
        },
        {
            "name": "match_phrase",
            "query": {
                "match_phrase": {
                    "title": "machine learning"
                }
            }
        },
        {
            "name": "bool com must match",
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "title": "machine learning"
                            }
                        }
                    ]
                }
            }
        },
        {
            "name": "bool com must query_string",
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": "machine learning"
                            }
                        }
                    ]
                }
            }
        },
        {
            "name": "bool com must query_string COM CAMPO",
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": "title:machine learning"
                            }
                        }
                    ]
                }
            }
        }
    ]

    for test in queries:
        print(f"\n{'-'*60}")
        print(f"Teste: {test['name']}")
        print(f"{'-'*60}")

        payload = {
            "query": test['query'],
            "size": 5,
            "from": 0
        }

        print(f"\nPayload:")
        print(json.dumps(payload, indent=2))

        try:
            response = client.post(url, json=payload, headers=headers)
            print(f"\nStatus: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                total = data.get('total_count')
                results = data.get('results', [])
                print(f"Total encontrado: {total}")
                print(f"Documentos retornados: {len(results)}")
                if results:
                    print(f"Primeiro documento: {results[0].get('title', 'N/A')[:80]}...")
                print("Status: [SUCESSO]")
            else:
                print(f"Erro: {response.text[:200]}")
                print("Status: [FALHA]")

        except Exception as e:
            print(f"Excecao: {str(e)}")
            print("Status: [ERRO]")

    client.close()


if __name__ == "__main__":
    test_query_syntax()
