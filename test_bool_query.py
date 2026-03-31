#!/usr/bin/env python3
"""
Teste da query EXATA que o builder gera dentro de bool.
"""

import json
import httpx
from core.config import settings

def test_bool_query():
    """Testa query bool com range."""

    api_token = getattr(settings, "lens_api_token", None)
    url = "https://api.lens.org/patent/search"

    client = httpx.Client(timeout=30)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    print("\n" + "="*60)
    print("TESTE: Query BOOL com Range de Data")
    print("="*60)

    # Query EXATA que o builder gera
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "query_string": {
                            "query": 'title:(("artificial intelligence" OR "machine learning")) AND abstract:("neural networks")'
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
        "from": 0,
        "sort": [
            {
                "publication_date": {
                    "order": "desc"
                }
            }
        ],
        "include": [
            "lens_id",
            "title",
            "abstract",
            "publication_date",
            "jurisdiction",
            "doc_key",
            "inventor",
            "applicant",
            "cpc_classifications",
            "ipc_classifications"
        ]
    }

    print("\nPayload completo:")
    print(json.dumps(query, indent=2))

    try:
        response = client.post(url, json=query, headers=headers)
        print(f"\n\nStatus: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            total = data.get('total')
            results = data.get('data', [])
            print(f"Total encontrado: {total}")
            print(f"Documentos retornados: {len(results)}")
            if results:
                first = results[0]
                title = first.get('biblio', {}).get('invention_title', [{}])[0].get('text', 'N/A')
                lens_id = first.get('lens_id', 'N/A')
                date = first.get('date_published', 'N/A')
                print(f"\nPrimeiro documento:")
                print(f"  - Titulo: {title[:100]}...")
                print(f"  - Lens ID: {lens_id}")
                print(f"  - Data: {date}")
            print("\n[SUCESSO] Query VALIDA!")
        else:
            print(f"Erro: {response.status_code}")
            print(f"Resposta: {response.text[:500]}")
            print("\n[FALHA]")

    except Exception as e:
        print(f"[EXCECAO] {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        client.close()


if __name__ == "__main__":
    test_bool_query()
