#!/usr/bin/env python3
"""
Teste detalhado da API Lens Patent para diagnosticar o erro 400.
"""

import json
import httpx
from core.config import settings

def test_api_directly():
    """Testa API Lens Patent diretamente com diferentes queries."""

    print("\n" + "="*60)
    print("TESTE DETALHADO: API Lens Patent")
    print("="*60)

    api_token = getattr(settings, "lens_api_token", None)
    url = "https://api.lens.org/patent/search"

    print(f"\nToken API: {api_token[:20]}...{api_token[-5:] if api_token else 'NAO CONFIGURADO'}")
    print(f"URL: {url}")

    # Teste 1: Query minima (apenas titulo)
    print("\n" + "-"*60)
    print("Teste 1: Query MINIMA (apenas titulo)")
    print("-"*60)

    query1 = {
        "query": {
            "bool": {
                "must": [
                    {
                        "query_string": {
                            "query": "title:\"machine learning\""
                        }
                    }
                ]
            }
        },
        "size": 10,
        "from": 0
    }

    print("\nPayload enviado:")
    print(json.dumps(query1, indent=2))

    try:
        client = httpx.Client(timeout=30)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }

        print("\nHeaders HTTP:")
        print(f"  Content-Type: {headers['Content-Type']}")
        print(f"  Authorization: Bearer {api_token[:20]}...")

        response = client.post(url, json=query1, headers=headers)

        print(f"\nStatus Code: {response.status_code}")
        print(f"Razao: {response.reason_phrase}")

        if response.status_code != 200:
            print("\nResposta da API:")
            print(response.text[:500])
        else:
            data = response.json()
            print(f"Total encontrado: {data.get('total_count', 0)}")
            print(f"Documentos retornados: {len(data.get('results', []))}")

    except Exception as e:
        print(f"[ERRO] {str(e)}")

    finally:
        client.close()

    # Teste 2: Query simples sem query_string
    print("\n" + "-"*60)
    print("Teste 2: Query SEM query_string (apenas tamanho)")
    print("-"*60)

    query2 = {
        "size": 10,
        "from": 0
    }

    print("\nPayload enviado:")
    print(json.dumps(query2, indent=2))

    try:
        client = httpx.Client(timeout=30)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }

        response = client.post(url, json=query2, headers=headers)

        print(f"\nStatus Code: {response.status_code}")
        print(f"Razao: {response.reason_phrase}")

        if response.status_code != 200:
            print("\nResposta da API:")
            print(response.text[:500])
        else:
            data = response.json()
            print(f"Total encontrado: {data.get('total_count', 0)}")
            print(f"Documentos retornados: {len(data.get('results', []))}")

    except Exception as e:
        print(f"[ERRO] {str(e)}")

    finally:
        client.close()

    # Teste 3: Teste com match query em vez de query_string
    print("\n" + "-"*60)
    print("Teste 3: Query com MATCH (alternativa a query_string)")
    print("-"*60)

    query3 = {
        "query": {
            "match": {
                "title": "machine learning"
            }
        },
        "size": 10,
        "from": 0
    }

    print("\nPayload enviado:")
    print(json.dumps(query3, indent=2))

    try:
        client = httpx.Client(timeout=30)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }

        response = client.post(url, json=query3, headers=headers)

        print(f"\nStatus Code: {response.status_code}")
        print(f"Razao: {response.reason_phrase}")

        if response.status_code != 200:
            print("\nResposta da API:")
            print(response.text[:500])
        else:
            data = response.json()
            print(f"Total encontrado: {data.get('total_count', 0)}")
            print(f"Documentos retornados: {len(data.get('results', []))}")

    except Exception as e:
        print(f"[ERRO] {str(e)}")

    finally:
        client.close()


if __name__ == "__main__":
    test_api_directly()
