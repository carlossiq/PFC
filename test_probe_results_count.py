#!/usr/bin/env python3
"""
Teste para verificar o numero de resultados retornados pelo probe.
"""

import asyncio
from core.config import settings
from schemas.llm import LLMOutput, TextualFieldQuery, TermGroup
from services.query_builders.lens_patent_query_builder import LensPatentQueryBuilder
from services.search.lens_service import LensService


async def test_probe_results():
    """Teste de quantidade de resultados no probe."""

    print("\n" + "="*60)
    print("TESTE: Quantidade de Resultados do Probe")
    print("="*60)

    probe_top_k = getattr(settings, 'probe_top_k', 10)
    final_top_k = getattr(settings, 'final_top_k', 100)

    print(f"\nConfigurações:")
    print(f"  probe_top_k: {probe_top_k}")
    print(f"  final_top_k: {final_top_k}")

    # Criar LLMOutput
    llm_output = LLMOutput(
        title=TextualFieldQuery(
            groups=[TermGroup(terms=["machine learning"])]
        ),
    )

    service = LensService()

    # Teste 1: Probe search
    print(f"\n{'-'*60}")
    print("Teste 1: Probe Search")
    print(f"{'-'*60}")

    builder_probe = LensPatentQueryBuilder(search_mode="probe")
    query_probe = builder_probe.build_query(
        llm_output=llm_output,
        year_from=2020,
        year_to=2026,
    )

    print(f"Query size: {query_probe.get('size')}")

    try:
        result_probe = await service.search_patent(query=query_probe)

        print(f"\nResultado Probe:")
        print(f"  Success: {result_probe.success}")
        print(f"  Total encontrado: {result_probe.total_count}")
        print(f"  Documentos retornados: {result_probe.results_returned}")
        print(f"  Esperado: {probe_top_k}")
        print(f"  Status: {'[OK]' if result_probe.results_returned == probe_top_k else '[AVISO] Retornou menos que esperado'}")

    except Exception as e:
        print(f"[ERRO] {str(e)}")

    # Teste 2: General/Final search
    print(f"\n{'-'*60}")
    print("Teste 2: General/Final Search")
    print(f"{'-'*60}")

    builder_general = LensPatentQueryBuilder(search_mode="general")
    query_general = builder_general.build_query(
        llm_output=llm_output,
        year_from=2020,
        year_to=2026,
    )

    print(f"Query size: {query_general.get('size')}")

    try:
        result_general = await service.search_patent(query=query_general)

        print(f"\nResultado General:")
        print(f"  Success: {result_general.success}")
        print(f"  Total encontrado: {result_general.total_count}")
        print(f"  Documentos retornados: {result_general.results_returned}")
        print(f"  Esperado: {final_top_k}")
        print(f"  Status: {'[OK]' if result_general.results_returned == final_top_k else '[AVISO] Retornou menos que esperado'}")

    except Exception as e:
        print(f"[ERRO] {str(e)}")

    service.close()

    # Resumo
    print(f"\n{'-'*60}")
    print("RESUMO")
    print(f"{'-'*60}")

    try:
        probe_ok = result_probe.results_returned == probe_top_k
        general_ok = result_general.results_returned == final_top_k

        print(f"Probe retornou top_k documentos: {'[OK]' if probe_ok else '[AVISO]'}")
        print(f"General retornou top_k documentos: {'[OK]' if general_ok else '[AVISO]'}")

        if probe_ok and general_ok:
            print(f"\n[OK] TUDO CONFORME ESPERADO!")
        else:
            print(f"\n[AVISO] Alguns testes não retornaram exatamente top_k")
            print("Nota: Isso é aceitavel se o total disponivel for menor que top_k")
    except Exception as e:
        print(f"[ERRO] Nao foi possivel finalizar os testes: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_probe_results())
