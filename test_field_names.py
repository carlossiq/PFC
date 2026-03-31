#!/usr/bin/env python3
"""
Teste para descobrir os nomes corretos dos campos na API Lens.
"""

import json
import httpx
from core.config import settings

def test_field_names():
    """Testa diferentes nomes de campos para date e sort."""

    api_token = getattr(settings, "lens_api_token", None)
    url = "https://api.lens.org/patent/search"

    client = httpx.Client(timeout=30)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    print("\n" + "="*60)
    print("TESTE: Nomes Corretos dos Campos")
    print("="*60)

    # Teste diferentes nomes de campos de data e sort
    date_field_names = [
        "publication_date",
        "date_published",
        "date",
        "biblio.publication_reference.date",
        "published_date"
    ]

    for date_field in date_field_names:
        print(f"\n{'-'*60}")
        print(f"Testando campo de data: {date_field}")
        print(f"{'-'*60}")

        query = {
            "query": {
                "query_string": {
                    "query": "machine learning"
                }
            },
            "size": 2,
            "from": 0,
            "sort": [
                {
                    date_field: {
                        "order": "desc"
                    }
                }
            ]
        }

        try:
            response = client.post(url, json=query, headers=headers)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Total: {data.get('total')}")
                print("[SUCESSO] - Campo de data VALIDO!")
            else:
                resp = response.json()
                msg = resp.get('message', '')
                if "Mismatched input for fields" in msg:
                    print(f"Campo invalido: {date_field}")
                else:
                    print(f"Erro: {msg[:100]}")

        except Exception as e:
            print(f"Excecao: {str(e)}")

    client.close()


if __name__ == "__main__":
    test_field_names()
