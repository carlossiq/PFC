#!/usr/bin/env python3
"""
Teste SEM range field.
"""

import json
import httpx
from core.config import settings

def test_without_range():
    """Testa query SEM range."""

    api_token = getattr(settings, "lens_api_token", None)
    url = "https://api.lens.org/patent/search"

    client = httpx.Client(timeout=30)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    print("\n" + "="*60)
    print("TESTE: Query SEM Range de Data")
    print("="*60)

    queries = [
        {
            "name": "SEM range",
            "payload": {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "query_string": {
                                    "query": 'title:("artificial intelligence" OR "machine learning") AND abstract:("neural networks")'
                                }
                            }
                        ]
                    }
                },
                "size": 10,
                "from": 0
            }
        },
        {
            "name": "COM range DIFERENTE (date_published)",
            "payload": {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "query_string": {
                                    "query": 'title:("artificial intelligence" OR "machine learning") AND abstract:("neural networks")'
                                }
                            },
                            {
                                "range": {
                                    "date_published": {
                                        "gte": "2020-01-01",
                                        "lte": "2026-12-31"
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": 10,
                "from": 0
            }
        },
        {
            "name": "COM range (biblio.publication_reference.date)",
            "payload": {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "query_string": {
                                    "query": 'title:("artificial intelligence" OR "machine learning") AND abstract:("neural networks")'
                                }
                            },
                            {
                                "range": {
                                    "biblio.publication_reference.date": {
                                        "gte": "2020-01-01",
                                        "lte": "2026-12-31"
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": 10,
                "from": 0
            }
        }
    ]

    for test in queries:
        print(f"\n{'-'*60}")
        print(f"Teste: {test['name']}")
        print(f"{'-'*60}")

        try:
            response = client.post(url, json=test['payload'], headers=headers)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                total = data.get('total')
                results = data.get('data', [])
                print(f"Total encontrado: {total}")
                print(f"Documentos retornados: {len(results)}")
                if results:
                    first = results[0]
                    title = first.get('biblio', {}).get('invention_title', [{}])[0].get('text', 'N/A')
                    print(f"Primeiro: {title[:80]}...")
                print("[SUCESSO]")
            else:
                resp = response.json()
                msg = resp.get('message', '')
                print(f"Erro: {msg[:100]}")

        except Exception as e:
            print(f"Excecao: {str(e)}")

    client.close()


if __name__ == "__main__":
    test_without_range()
