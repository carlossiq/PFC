#!/usr/bin/env python3
"""
Teste da rota POST /test/probe-search
"""

import asyncio
import json
from schemas.intake import InputIntake
from fastapi import Request


async def test_route():
    """Testa a rota probe-search."""

    print("\n" + "="*60)
    print("TESTE: Rota POST /test/probe-search")
    print("="*60)

    # Importar a função diretamente do módulo test
    from api.routes.test import test_probe_search

    # Criar requisição mock
    class MockState:
        run_id = None

    class MockRequest:
        state = MockState()

    request = MockRequest()

    # Criar intake
    intake = InputIntake(
        theme="Machine Learning in Healthcare",
        description="Diagnostic AI systems for medical imaging",
        area_of_study="Healthcare",
        keywords=["neural networks", "medical imaging", "deep learning"],
    )

    print(f"\nIntake:")
    print(f"  Theme: {intake.theme}")
    print(f"  Description: {intake.description}")
    print(f"  Area of Study: {intake.area_of_study}")
    print(f"  Keywords: {', '.join(intake.keywords or [])}")

    print(f"\nChamando rota probe-search...")

    try:
        response = await test_probe_search(request, intake)

        print(f"\n[OK] Resposta recebida!")
        print(f"  Success: {response.success}")
        print(f"  Run ID: {response.run_id}")

        # Extrair dados
        data = response.data

        print(f"\nEstrutura da resposta:")
        print(f"  - LLM Strategy:")
        llm = data.get("llm_strategy", {})
        print(f"    Active fields: {llm.get('field_count', 0)}")
        print(f"    Fields: {list(llm.get('active_fields', {}).keys())}")

        print(f"\n  - Query Gerada:")
        query = data.get("query_generated", {})
        print(f"    API: {query.get('api')}")
        print(f"    Size: {query.get('size')}")
        print(f"    Must clauses: {query.get('must_clauses_count')}")

        print(f"\n  - Resultados da API:")
        api_res = data.get("api_results", {})
        print(f"    Success: {api_res.get('success')}")
        print(f"    Total available: {api_res.get('total_available')}")
        print(f"    Results returned: {api_res.get('results_returned')}")
        print(f"    Duration: {api_res.get('duration_seconds')}s")

        print(f"\n  - Documentos Encontrados:")
        docs = data.get("documents", {})
        print(f"    Total retrieved: {docs.get('total_retrieved')}")

        samples = docs.get("samples", [])
        if samples:
            print(f"\n  Primeiros 3 documentos:")
            for i, doc in enumerate(samples[:3], 1):
                print(f"\n    [{i}]")
                print(f"      Title: {doc.get('title', 'N/A')[:80]}...")
                print(f"      Lens ID: {doc.get('lens_id', 'N/A')}")
                print(f"      Date: {doc.get('publication_date', 'N/A')}")
                print(f"      Applicant: {doc.get('applicant', 'N/A')}")
                applicant = doc.get('applicant', 'N/A')
                inventor = doc.get('inventor', 'N/A')
                if applicant != "N/A":
                    print(f"      Applicant: {applicant}")
                if inventor != "N/A":
                    print(f"      Inventor: {inventor}")

        print(f"\n[OK] TESTE COMPLETO COM SUCESSO!")

    except Exception as e:
        print(f"[ERRO] {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_route())
