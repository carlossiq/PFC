#!/usr/bin/env python3
"""
Teste para ver a resposta completa da API.
"""

import json
import httpx
from core.config import settings

def test_api_response():
    """Testa resposta da API."""

    api_token = getattr(settings, "lens_api_token", None)
    url = "https://api.lens.org/patent/search"

    client = httpx.Client(timeout=30)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    print("\n" + "="*60)
    print("RESPOSTA COMPLETA DA API")
    print("="*60)

    payload = {
        "query": {
            "match": {
                "title": "machine"
            }
        },
        "size": 5,
        "from": 0
    }

    print(f"\nPayload enviado:")
    print(json.dumps(payload, indent=2))

    try:
        response = client.post(url, json=payload, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")

        print(f"\nResposta (primeiros 2000 caracteres):")
        print(response.text[:2000])

        print("\n\nJSON estruturado:")
        data = response.json()
        print(json.dumps(data, indent=2)[:2000])

    except Exception as e:
        print(f"[ERRO] {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        client.close()


if __name__ == "__main__":
    test_api_response()
