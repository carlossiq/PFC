"""
Example of report generation using local Ollama and RAG.

Demonstrates how to:
1. Index documents for RAG
2. Generate complete reports
3. Generate individual sections
"""

import asyncio
import json
from pathlib import Path

from services.ollama_service import OllamaService
from services.rag_service import RAGService
from services.report_service import ReportService


async def example_report_generation():
    """Complete example of report generation workflow."""

    print("\n" + "=" * 100)
    print("EXEMPLO: GERAÇÃO DE RELATÓRIO DE PROSPECÇÃO TECNOLÓGICA COM OLLAMA + RAG")
    print("=" * 100)

    # ========================================================================
    # PASSO 1: Inicializar serviços
    # ========================================================================
    print("\n[1] Inicializando serviços...")

    try:
        ollama_service = OllamaService(
            base_url="http://localhost:11434",
            text_model="qwen2.5:3b-instruct",
            embedding_model="nomic-embed-text",
        )

        # Verificar saúde do Ollama
        is_healthy = await ollama_service.health_check()
        if not is_healthy:
            print("[ERRO] Ollama não está rodando. Inicie com: ollama serve")
            return

        print("[OK] Ollama está saudável")

        # Listar modelos disponíveis
        models = await ollama_service.list_models()
        print(f"[OK] Modelos disponíveis: {', '.join(models)}")

        # Inicializar RAG
        rag_service = RAGService(ollama_service)
        print(f"[OK] RAG inicializado")

        # Inicializar serviço de relatório
        report_service = ReportService(ollama_service, rag_service)
        print(f"[OK] Serviço de relatório inicializado")

    except Exception as exc:
        print(f"[ERRO] Falha na inicialização: {exc}")
        return

    # ========================================================================
    # PASSO 2: Indexar documentos para RAG
    # ========================================================================
    print("\n[2] Indexando documentos para RAG...")

    documents = [
        {
            "text": """
            Sistemas de recomendação são componentes essenciais em plataformas de e-commerce,
            utilizando técnicas de filtragem colaborativa e filtragem baseada em conteúdo.
            A evolução dessas tecnologias passou por três gerações principais: técnicas simples
            de recomendação baseadas em histórico, redes neurais para capturar padrões complexos,
            e mais recentemente, modelos de transformadores que consideram contexto e sequência
            de comportamento do usuário.
            """,
            "source": "Academic_Paper_2024",
            "type": "article",
            "topic": "recommendation systems",
        },
        {
            "text": """
            Patentes recentes em sistemas de e-commerce mostram crescimento significativo
            em dois domínios: (1) personalização em tempo real usando machine learning,
            classificadas em CPC H04L29 (sistemas de processamento de dados),
            G06N3 (redes neurais), e (2) otimização de página de produto, em CPC G06F17
            (processamento de informação). O número de depósitos cresceu de 45 em 2018
            para 120 em 2024, indicando fase de CRESCIMENTO acelerado na curva-S.
            """,
            "source": "Patent_Analysis_OPS",
            "type": "patent",
            "topic": "e-commerce patents",
        },
        {
            "text": """
            Aplicantes líderes incluem grandes varejistas (Amazon, Alibaba) e plataformas
            de software (IBM, Microsoft, Google), que detêm aproximadamente 65% das patentes
            no segmento. Universidades e startups representam 35%, indicando ainda há espaço
            para inovação disruptiva. Distribuição geográfica mostra predominância de EUA (40%),
            Europa (30%) e Ásia (30%).
            """,
            "source": "Patent_Applicants_Analysis",
            "type": "patent",
            "topic": "market leaders",
        },
    ]

    try:
        chunk_count = await report_service.add_documents_to_rag(documents)
        print(f"[OK] {chunk_count} chunks indexados no RAG")
        print(f"    Documentos: {len(documents)}")

        stats = report_service.get_rag_stats()
        print(f"[OK] Stats: {stats['document_count']} documentos no RAG")

    except Exception as exc:
        print(f"[ERRO] Falha ao indexar: {exc}")
        return

    # ========================================================================
    # PASSO 3: Gerar uma única seção (teste rápido)
    # ========================================================================
    print("\n[3] Gerando seção individual: Introdução...")

    try:
        result = await report_service.generate_section_sync(
            section_name="Introdução",
            section_type="introducao",
            theme="Sistemas de Recomendação em E-commerce",
            data={
                "area_of_study": "Inteligência Artificial, E-commerce",
                "keywords": ["recommendation", "personalization", "machine learning"],
            },
        )

        if result["success"]:
            print(f"[OK] Seção gerada com sucesso")
            print(f"\nConteúdo:\n{result['content'][:500]}...")
        else:
            print(f"[ERRO] {result['error']}")

    except Exception as exc:
        print(f"[ERRO] Falha na geração da seção: {exc}")

    # ========================================================================
    # PASSO 4: Gerar relatório completo
    # ========================================================================
    print("\n[4] Gerando relatório completo...")

    try:
        report = await report_service.generate_full_report(
            theme="Sistemas de Recomendação em E-commerce",
            description="Análise de tecnologias para personalização em varejo online",
            data={
                "area_of_study": "Inteligência Artificial, E-commerce",
                "keywords": ["recommendation", "personalization", "machine learning"],
                "period_start": 2018,
                "period_end": 2024,
                "scientific_data": {
                    "article_count": 245,
                    "top_journals": [
                        {"journal": "IEEE Transactions on Knowledge and Data Engineering", "count": 12},
                        {"journal": "ACM Transactions on Recommender Systems", "count": 8},
                    ],
                },
                "patent_data": {
                    "patent_count": 1523,
                    "top_applicants": [
                        {"name": "Amazon", "count": 156},
                        {"name": "Alibaba", "count": 142},
                        {"name": "Google", "count": 89},
                    ],
                    "top_cpc_codes": ["H04L29", "G06N3", "G06F17"],
                },
                "s_curve_data": {
                    "phase": "GROWTH",
                    "growth_rate": 0.18,
                    "peak_year": 2023,
                },
            },
            chart_paths={
                "Histórico de Publicações": "charts/timeline_articles.png",
                "Histórico de Patentes": "charts/timeline_patents.png",
                "Curva-S da Tecnologia": "charts/s_curve.png",
                "Top Depositantes": "charts/top_applicants.png",
            },
        )

        # Salvar relatório
        report_path = Path("generated_report.md")
        report_path.write_text(report, encoding="utf-8")

        print(f"[OK] Relatório gerado com sucesso!")
        print(f"[OK] Salvo em: {report_path.resolve()}")
        print(f"[OK] Tamanho: {len(report)} caracteres")
        print(f"\nPrimeiros 800 caracteres:\n{report[:800]}...")

    except Exception as exc:
        print(f"[ERRO] Falha na geração do relatório: {exc}")

    # ========================================================================
    # PASSO 5: Verificar saúde dos serviços
    # ========================================================================
    print("\n[5] Verificando saúde dos serviços...")

    try:
        health = await report_service.health_check()

        print(f"[OK] Ollama: {health['ollama']['status']}")
        print(f"[OK] RAG: {health['rag']['status']}")
        print(f"     Documentos indexados: {health['rag']['document_count']}")

    except Exception as exc:
        print(f"[ERRO] Health check falhou: {exc}")

    # ========================================================================
    # RESUMO
    # ========================================================================
    print("\n" + "=" * 100)
    print("RESUMO")
    print("=" * 100)

    print("""
Fluxo Completado:
1. ✓ Inicialização de serviços (Ollama + ChromaDB)
2. ✓ Indexação de documentos para RAG
3. ✓ Geração de seção individual
4. ✓ Geração de relatório completo
5. ✓ Health check dos serviços

Próximas Etapas:
- Integrar com FastAPI routes
- Adicionar mais documentos de referência
- Validar qualidade do relatório gerado
- Otimizar prompts por seção
- Implementar caching de seções

Arquivo gerado: generated_report.md
""")

    print("=" * 100 + "\n")


async def example_api_integration():
    """Example of how to use the report service with FastAPI."""

    print("\n" + "=" * 100)
    print("EXEMPLO: INTEGRAÇÃO COM FastAPI")
    print("=" * 100)

    print("""
No seu FastAPI app (main.py):

```python
from api.routes.reports import router as reports_router, initialize_services
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Inicializar serviços de relatório
    from api.routes.reports import initialize_services
    await initialize_services()

# Incluir rotas
app.include_router(reports_router)
```

Endpoints disponíveis:

1. POST /reports/generate
   Gera relatório completo

   Body:
   {
       "theme": "Sistemas de Recomendação em E-commerce",
       "description": "...",
       "area_of_study": "Inteligência Artificial",
       "keywords": ["recommendation", "personalization"],
       "period_start": 2018,
       "period_end": 2024,
       "scientific_data": {...},
       "patent_data": {...},
       "chart_paths": {...}
   }

2. POST /reports/generate-section
   Gera uma seção específica

   Body:
   {
       "theme": "...",
       "section_name": "Introdução",
       "section_type": "introducao",
       "data": {...}
   }

3. POST /reports/rag/index
   Indexa documentos para RAG

   Body:
   {
       "documents": [
           {"text": "...", "source": "...", "type": "..."}
       ]
   }

4. GET /reports/health
   Verifica saúde dos serviços

5. GET /reports/rag/stats
   Obtém estatísticas do RAG

6. POST /reports/models/list
   Lista modelos disponíveis no Ollama
""")

    print("=" * 100 + "\n")


if __name__ == "__main__":
    print("""
INSTRUÇÕES:
1. Inicie Ollama:
   ollama serve

2. Em outro terminal, execute este script:
   python example_report_generation.py

3. Ou integre com FastAPI conforme mostrado no segundo exemplo.
""")

    # asyncio.run(example_report_generation())
    # asyncio.run(example_api_integration())

    print("\nDescomente as linhas acima para executar os exemplos.")
