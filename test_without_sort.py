#!/usr/bin/env python3
"""
Teste SEM sort field.
"""

import json
import httpx
from core.config import settings

def test_without_sort():
    """Testa query SEM sort."""

    api_token = getattr(settings, "lens_api_token", None)
    url = "https://api.lens.org/patent/search"

    client = httpx.Client(timeout=30)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    print("\n" + "="*60)
    print("TESTE: Query SEM Sort")
    print("="*60)

    # Query com range de data MAS SEM SORT
    query = {
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
                            "publication_date": {
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

    print("\nPayload (SEM sort, SEM include):")
    print(json.dumps(query, indent=2))

    try:
        response = client.post(url, json=query, headers=headers)
        print(f"\nStatus: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            total = data.get('total')
            results = data.get('data', [])
            print(f"Total encontrado: {total}")
            print(f"Documentos retornados: {len(results)}")
            if results:
                first = results[0]
                title = first.get('biblio', {}).get('invention_title', [{}])[0].get('text', 'N/A')
                print(f"Primeiro documento: {title[:100]}...")
            print("\n[SUCESSO] Query FUNCIONA sem sort e include!")
        else:
            resp = response.json()
            msg = resp.get('message', '')
            print(f"Erro: {msg}")

    except Exception as e:
        print(f"Excecao: {str(e)}")

    finally:
        client.close()


if __name__ == "__main__":
    test_without_sort()
