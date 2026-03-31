#!/usr/bin/env python3
"""
Script de teste para verificar:
1. Validade da query gerada
2. Acesso à API do Lens Patent
"""

import asyncio
import json
from schemas.llm import LLMOutput, TextualFieldQuery, TermGroup, SimpleFieldQuery
from services.query_builders.lens_patent_query_builder import LensPatentQueryBuilder
from services.search.lens_service import LensService


def test_query_generation():
    """Testa geração de query do Lens Patent."""
    print("\n" + "="*60)
    print("TESTE 1: Geracao de Query Lens Patent")
    print("="*60)

    # Criar LLMOutput com exemplo simples
    llm_output = LLMOutput(
        title=TextualFieldQuery(
            groups=[TermGroup(terms=["machine learning", "artificial intelligence"])]
        ),
        abstract=TextualFieldQuery(
            groups=[TermGroup(terms=["neural networks"])]
        ),
    )

    # Construir query
    builder = LensPatentQueryBuilder(search_mode="probe")
    query = builder.build_query(
        llm_output=llm_output,
        year_from=2020,
        year_to=2026,
    )

    print("\n[OK] Query gerada com sucesso!")
    print("\nEstrutura da Query:")
    print(json.dumps(query, indent=2))

    # Validações
    validations = {
        "Tem campo 'query'": "query" in query,
        "Tem campo 'size'": "size" in query,
        "Tem range de data": any("range" in str(c) for c in query.get("query", {}).get("bool", {}).get("must", [])),
        "Query string nao vazia": any("query_string" in str(c) for c in query.get("query", {}).get("bool", {}).get("must", [])),
    }

    print("\nValidacoes da Query:")
    for validation, result in validations.items():
        status = "[OK]" if result else "[ERRO]"
        print(f"  {status} {validation}")

    all_valid = all(validations.values())
    print(f"\nQuery eh valida: {'SIM [OK]' if all_valid else 'NAO [ERRO]'}")

    return query if all_valid else None


async def test_api_connection(query):
    """Testa conexão com API do Lens Patent."""
    print("\n" + "="*60)
    print("TESTE 2: Acesso a API do Lens Patent")
    print("="*60)

    try:
        service = LensService()

        print("\nEnviando query para a API...")
        result = await service.search_patent(query=query)

        print("\n[OK] Resposta recebida da API!")
        print(f"  - Status: {'SUCESSO [OK]' if result.success else 'ERRO [FALHA]'}")
        print(f"  - Documentos encontrados: {result.results_returned}")
        print(f"  - Total disponivel: {result.total_count}")
        print(f"  - Duracao: {result.duration_seconds:.2f}s")

        if not result.success:
            print(f"  - Erro: {result.error_message}")
            print(f"  - Codigo: {result.error_code}")

        # Mostrar exemplo de resultado
        if result.results and len(result.results) > 0:
            print("\nPrimeiro resultado encontrado:")
            first_result = result.results[0]
            print(f"  - Titulo: {first_result.get('title', 'N/A')[:100]}...")
            print(f"  - ID Lens: {first_result.get('lens_id', 'N/A')}")
            print(f"  - Data: {first_result.get('publication_date', 'N/A')}")

        return result.success

    except Exception as e:
        print(f"\n[ERRO] Erro ao conectar a API: {str(e)}")
        return False
    finally:
        service.close()


async def main():
    """Funcao principal."""
    print("\n[INFO] TESTE COMPLETO: QUERY LENS PATENT + API")
    print("="*60)

    # Teste 1: Query
    query = test_query_generation()

    if query is None:
        print("\n[ERRO] Query invalida. Abortando teste de API.")
        return

    # Teste 2: API
    api_ok = await test_api_connection(query)

    # Resumo final
    print("\n" + "="*60)
    print("RESUMO FINAL")
    print("="*60)
    print(f"  Query valida: [OK]")
    print(f"  API acessivel: {'[OK]' if api_ok else '[ERRO]'}")
    print(f"  Status geral: {'[OK] TUDO BEM' if api_ok else '[ERRO] VERIFICAR CREDENCIAIS/CONFIG'}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
