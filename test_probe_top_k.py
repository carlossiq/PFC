#!/usr/bin/env python3
"""
Teste para verificar se o probe_top_k está sendo respeitado.
"""

import json
from core.config import settings
from schemas.llm import LLMOutput, TextualFieldQuery, TermGroup
from services.query_builders.lens_patent_query_builder import LensPatentQueryBuilder


def test_probe_top_k():
    """Teste de probe_top_k."""

    print("\n" + "="*60)
    print("TESTE: Verificar probe_top_k vs final_top_k")
    print("="*60)

    print(f"\nConfigurações:")
    print(f"  probe_top_k: {getattr(settings, 'probe_top_k', 10)}")
    print(f"  final_top_k: {getattr(settings, 'final_top_k', 100)}")

    # Criar LLMOutput simples
    llm_output = LLMOutput(
        title=TextualFieldQuery(
            groups=[TermGroup(terms=["machine learning"])]
        ),
    )

    # Teste 1: Probe mode
    print(f"\n{'-'*60}")
    print("Teste 1: search_mode='probe'")
    print(f"{'-'*60}")

    builder_probe = LensPatentQueryBuilder(search_mode="probe")
    query_probe = builder_probe.build_query(
        llm_output=llm_output,
        year_from=2020,
        year_to=2026,
    )

    size_probe = query_probe.get("size")
    print(f"Size na query: {size_probe}")
    print(f"Esperado: {getattr(settings, 'probe_top_k', 10)}")
    print(f"Status: {'[OK]' if size_probe == getattr(settings, 'probe_top_k', 10) else '[ERRO]'}")

    # Teste 2: General mode
    print(f"\n{'-'*60}")
    print("Teste 2: search_mode='general'")
    print(f"{'-'*60}")

    builder_general = LensPatentQueryBuilder(search_mode="general")
    query_general = builder_general.build_query(
        llm_output=llm_output,
        year_from=2020,
        year_to=2026,
    )

    size_general = query_general.get("size")
    print(f"Size na query: {size_general}")
    print(f"Esperado: {getattr(settings, 'final_top_k', 100)}")
    print(f"Status: {'[OK]' if size_general == getattr(settings, 'final_top_k', 100) else '[ERRO]'}")

    # Resumo
    print(f"\n{'-'*60}")
    print("RESUMO")
    print(f"{'-'*60}")
    probe_ok = size_probe == getattr(settings, 'probe_top_k', 10)
    general_ok = size_general == getattr(settings, 'final_top_k', 100)

    print(f"Probe top_k respeitado: {'[OK]' if probe_ok else '[ERRO]'}")
    print(f"Final top_k respeitado: {'[OK]' if general_ok else '[ERRO]'}")
    print(f"Status geral: {'[OK] TUDO CORRETO' if probe_ok and general_ok else '[ERRO] VERIFICAR'}")


if __name__ == "__main__":
    test_probe_top_k()
