"""
Example: Complete workflow from Research to Report generation.

This example demonstrates how to:
1. Load a Research object from the database
2. Consolidate OPS (patents) and Scopus (articles) data
3. Index documents for RAG
4. Generate complete technology prospecting report
"""

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from db.research_models import Research
from services.ollama_service import OllamaService
from services.rag_service import RAGService
from services.report_service import ReportService
from services.report_data_mapper import ReportDataMapper


async def example_research_to_report(research_id: int):
    """
    Complete example: Load Research → Consolidate → RAG → Generate Report.

    This is the typical production workflow.
    """

    print("\n" + "=" * 100)
    print("EXEMPLO: PESQUISA → CONSOLIDAÇÃO → RAG → RELATÓRIO")
    print("=" * 100)

    # ========================================================================
    # PASSO 1: Conectar ao banco de dados e buscar Research
    # ========================================================================
    print(f"\n[1] Carregando pesquisa {research_id} do banco de dados...")

    try:
        # Assumindo que você tem configurado DATABASE_URL
        DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/pfc"
        engine = create_async_engine(DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Buscar Research com relacionamentos carregados
            research = await session.get(Research, research_id)
            if not research:
                print(f"[ERRO] Pesquisa {research_id} não encontrada")
                return

            print(f"[OK] Pesquisa carregada: {research.title}")
            print(f"     Patentes: {len(research.patent_documents or [])}")
            print(f"     Artigos: {len(research.scholarly_documents or [])}")

            # ================================================================
            # PASSO 2: Consolidar dados de OPS + Scopus
            # ================================================================
            print("\n[2] Consolidando dados de patentes (OPS) e artigos (Scopus)...")

            consolidated = ReportDataMapper.map_complete_research_data(research)

            print(f"[OK] Dados consolidados:")
            print(f"     Tema: {consolidated['theme']}")
            print(f"     Área de Estudo: {consolidated['area_of_study']}")
            print(f"     APIs utilizadas: {', '.join(consolidated['apis_used'])}")
            print(f"     Patentes: {consolidated['patent_data'].get('patent_count', 0)}")
            print(f"     Artigos: {consolidated['scientific_data'].get('article_count', 0)}")

            # ================================================================
            # PASSO 3: Criar documentos para RAG de ambas as fontes
            # ================================================================
            print("\n[3] Criando documentos RAG de patentes e artigos...")

            rag_documents = (
                ReportDataMapper.convert_all_results_to_rag_documents(
                    research, max_patents=50, max_articles=50
                )
            )

            patent_docs = [d for d in rag_documents if d["type"] == "patent"]
            article_docs = [d for d in rag_documents if d["type"] == "article"]

            print(f"[OK] Documentos criados:")
            print(f"     Patentes para RAG: {len(patent_docs)}")
            print(f"     Artigos para RAG: {len(article_docs)}")

            # ================================================================
            # PASSO 4: Inicializar serviços de Report
            # ================================================================
            print("\n[4] Inicializando serviços de relatório...")

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

                # Inicializar RAG e Report
                rag_service = RAGService(ollama_service)
                report_service = ReportService(ollama_service, rag_service)

                print("[OK] Serviço de relatório inicializado")

            except Exception as exc:
                print(f"[ERRO] Falha na inicialização: {exc}")
                return

            # ================================================================
            # PASSO 5: Gerar relatório completo (usando novo método!)
            # ================================================================
            print("\n[5] Gerando relatório completo com dados consolidados...")

            try:
                # Usar novo método que cuida de tudo automaticamente
                report = await report_service.generate_report_from_research(
                    research=research,
                    chart_paths={
                        "Histórico de Publicações": "charts/timeline_articles.png",
                        "Histórico de Patentes": "charts/timeline_patents.png",
                        "Curva-S da Tecnologia": "charts/s_curve.png",
                    },
                )

                # Salvar relatório
                report_path = Path(f"report_{research_id}.md")
                report_path.write_text(report, encoding="utf-8")

                print(f"[OK] Relatório gerado com sucesso!")
                print(f"[OK] Salvo em: {report_path.resolve()}")
                print(f"[OK] Tamanho: {len(report)} caracteres")

            except Exception as exc:
                print(f"[ERRO] Falha na geração do relatório: {exc}")
                return

            # ================================================================
            # PASSO 6: Verificar saúde dos serviços
            # ================================================================
            print("\n[6] Verificando saúde dos serviços...")

            try:
                health = await report_service.health_check()

                print(f"[OK] Ollama: {health['ollama']['status']}")
                print(f"[OK] RAG: {health['rag']['status']}")
                print(f"     Documentos indexados: {health['rag']['document_count']}")

            except Exception as exc:
                print(f"[ERRO] Health check falhou: {exc}")

            # ================================================================
            # RESUMO
            # ================================================================
            print("\n" + "=" * 100)
            print("RESUMO")
            print("=" * 100)

            print(f"""
Fluxo Completado para Pesquisa {research_id}:
1. ✓ Carregamento do Research do banco de dados
2. ✓ Consolidação de dados (OPS + Scopus)
3. ✓ Criação de documentos RAG
4. ✓ Inicialização de serviços (Ollama + ChromaDB)
5. ✓ Geração de relatório completo
6. ✓ Health check dos serviços

Dados da Pesquisa:
- Título: {research.title}
- Área: {consolidated['area_of_study']}
- Período: {consolidated['period_start']} a {consolidated['period_end']}
- Patentes indexadas: {len(patent_docs)}
- Artigos indexados: {len(article_docs)}
- APIs utilizadas: {', '.join(consolidated['apis_used'])}

Relatório gerado: report_{research_id}.md
Tamanho: {len(report)} caracteres

Próximas Etapas:
- Converter Markdown para PDF (pandoc)
- Armazenar relatório no banco de dados (Research.latex_content)
- Entregar para usuário
""")

            print("=" * 100 + "\n")

        await engine.dispose()

    except Exception as exc:
        print(f"[ERRO] Falha geral: {exc}")
        import traceback
        traceback.print_exc()


async def example_usage_with_research_service():
    """
    Example: How to integrate with ResearchService for end-to-end pipeline.
    """

    print("\n" + "=" * 100)
    print("EXEMPLO: INTEGRAÇÃO COM ResearchService (PIPELINE COMPLETO)")
    print("=" * 100)

    print("""
Integração em endpoint FastAPI:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.research import get_db_session
from services.research_service import ResearchService
from services.report_service import ReportService
from api.routes.reports import get_report_service

router = APIRouter(prefix="/workflow", tags=["workflow"])

@router.post("/research/{research_id}/generate-report")
async def generate_report_for_research(
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
    report_service: ReportService = Depends(get_report_service),
):
    \"\"\"Gerar relatório para pesquisa existente.\"\"\"

    # Buscar Research do banco
    research = await ResearchService.get_research(session, research_id)
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")

    # Gerar relatório (cuida de consolidação + RAG + geração automaticamente)
    try:
        report = await report_service.generate_report_from_research(
            research=research,
            chart_paths={
                "Histórico de Publicações": "charts/timeline.png",
                "Histórico de Patentes": "charts/patents.png",
                "Curva-S": "charts/s_curve.png",
            }
        )

        # Armazenar no banco
        research.latex_content = report
        await session.commit()

        return {
            "success": True,
            "research_id": research_id,
            "report_size": len(report),
        }

    except Exception as exc:
        logger.error("report_generation_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
```

Fluxo:
1. Cliente POST /workflow/research/{research_id}/generate-report
2. Buscar Research do BD (com patentes e artigos)
3. Consolidar dados OPS + Scopus
4. Criar documentos RAG
5. Indexar no ChromaDB
6. Gerar relatório com Ollama
7. Armazenar relatório no BD
8. Retornar para cliente

Todos esses passos são feitos automaticamente por:
    report_service.generate_report_from_research()
""")

    print("=" * 100 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        research_id = int(sys.argv[1])
        print(f"\nGerando relatório para pesquisa {research_id}...")
        print("Certifique-se de que:")
        print("1. Ollama está rodando: ollama serve")
        print("2. Base de dados está acessível")
        print("3. DATABASE_URL está configurada\n")

        asyncio.run(example_research_to_report(research_id))
    else:
        print("USO:")
        print("  python example_research_to_report.py <research_id>")
        print("\nExemplo:")
        print("  python example_research_to_report.py 42")
        print("\nMostrando exemplo de integração com FastAPI...\n")

        asyncio.run(example_usage_with_research_service())
