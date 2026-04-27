# Guia de Integração: Sistema de Geração de Relatórios

## 📋 Visão Geral da Integração

Este guia mostra como integrar o sistema de geração de relatórios com Ollama/RAG ao seu backend FastAPI existente, mantendo a modularidade e sem quebrar funcionalidades atuais.

## 🔗 Arquitetura de Integração

```
┌─────────────────────────────────────────────────────────────┐
│                      Cliente (Frontend)                     │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (main.py)                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Research Routes  │  │ Reports Routes   │               │
│  │ (Existentes)     │  │ (Novo com Ollama)│               │
│  └────────┬─────────┘  └────────┬─────────┘               │
│           │                      │                          │
│  ┌────────▼──────────────────────▼──────────────┐          │
│  │    Pipeline de Pesquisa                      │          │
│  │  (refine_topic, probe, extract, final)      │          │
│  └────────┬───────────────────────────────────┘           │
│           │                                                 │
│  ┌────────▼──────────────────────────────────────┐         │
│  │ Aggregação de Dados                          │         │
│  │ (ResearchService, MetricsAggregator)        │         │
│  └────────┬──────────────────────────────────┬──┘         │
│           │                                  │              │
│  ┌────────▼──┐                    ┌─────────▼────────┐    │
│  │  Banco de │                    │ Serviço Ollama   │    │
│  │  Dados    │                    │ + RAG (LOCAL)    │    │
│  │ (Postgres)│                    │ (ChromaDB)       │    │
│  └───────────┘                    └──────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│              Ollama Server (http://localhost:11434)         │
│  - qwen2.5:3b-instruct (geração)                          │
│  - nomic-embed-text (embeddings)                          │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Implementação Passo a Passo

### Passo 1: Adicionar Inicialização ao FastAPI

**Arquivo: `app/main.py`**

```python
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

# Importar rotas existentes
from api.routes.research import router as research_router
from api.routes.reports import router as reports_router, initialize_services

# Variável global para controlar inicialização
ollama_initialized = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar ciclo de vida da aplicação."""
    global ollama_initialized
    
    # Startup
    print("Inicializando serviços...")
    ollama_initialized = await initialize_services()
    
    if not ollama_initialized:
        print("⚠️  AVISO: Ollama não disponível. Relatórios desabilitados.")
    else:
        print("✅ Serviço de relatórios inicializado com sucesso")
    
    yield
    
    # Shutdown
    print("Encerrando serviços...")
    # Cleanup aqui se necessário

app = FastAPI(
    title="PFC - Technology Prospecting API",
    version="1.0.0",
    lifespan=lifespan,
)

# Incluir rotas
app.include_router(research_router)
app.include_router(reports_router)

@app.get("/")
async def root():
    return {
        "message": "PFC API",
        "research_api": "/research",
        "reports_api": "/reports",
        "ollama_status": "enabled" if ollama_initialized else "disabled",
    }
```

### Passo 2: Workflow Completo da Pesquisa

**Exemplo: Pesquisa → Índice → Relatório**

```python
from fastapi import APIRouter, Depends
from services.research_service import ResearchService
from services.report_service import ReportService

router = APIRouter(prefix="/workflow", tags=["workflow"])

@router.post("/research-to-report")
async def research_to_report(
    user_input: dict,
    research_service: ResearchService = Depends(),
    report_service: ReportService = Depends(),
):
    """
    Fluxo completo: pesquisa → agregação → índice → relatório
    """
    
    # 1. Executar pesquisa (usa pipeline existente)
    research = await research_service.create_research(
        session=session,
        title=user_input["theme"],
        description=user_input.get("description"),
        user_input=user_input,
    )
    
    # 2. Executar pipeline de pesquisa
    # (refine_topic, probe, extract, final) ...
    # [código existente do workflow]
    
    # 3. Agregar dados
    metrics = await MetricsAggregator.calculate_and_store_metrics(research.id)
    
    # 4. Preparar documentos para RAG
    documents = [
        {
            "text": f"Abstract: {patent.abstract}\nApplicants: {patent.applicants}",
            "source": f"Patent_{patent.publication_number}",
            "type": "patent",
        }
        for patent in research.patent_documents
    ] + [
        {
            "text": f"Title: {article.title}\nAbstract: {article.abstract}",
            "source": f"Article_{article.doi}",
            "type": "article",
        }
        for article in research.scholarly_documents
    ]
    
    # 5. Indexar no RAG
    await report_service.add_documents_to_rag(documents)
    
    # 6. Gerar relatório
    report = await report_service.generate_full_report(
        theme=user_input["theme"],
        description=user_input.get("description"),
        data={
            "area_of_study": user_input.get("area_of_study"),
            "keywords": user_input.get("keywords", []),
            "period_start": user_input.get("period_start"),
            "period_end": user_input.get("period_end"),
            "scientific_data": metrics.article_by_year,
            "patent_data": metrics.patent_by_year,
            "s_curve_data": metrics.patent_growth_trend,
        },
        chart_paths={
            "Histórico de Publicações": "charts/timeline_articles.png",
            "Histórico de Patentes": "charts/timeline_patents.png",
            "Curva-S": "charts/s_curve.png",
        },
    )
    
    # 7. Armazenar relatório no banco de dados
    await research_service.update_report(
        session=session,
        research_id=research.id,
        latex_content=report,  # Ou converter para LaTeX se necessário
    )
    
    return {
        "success": True,
        "research_id": research.id,
        "report": report,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

## 🔄 Fluxo de Dados

### Cenário 1: Usar Dados Existentes da Pesquisa

```
Pesquisa Salva no BD
      ↓
ResearchPatentDocument[] + ResearchScholarlyDocument[]
      ↓
Converter para documentos RAG
      ↓
RAGService.index_documents()
      ↓
ReportService.generate_full_report()
      ↓
Relatório Markdown
      ↓
Armazenar em Research.latex_content
```

### Cenário 2: Usar Dados Externos

```
Dados Externos (API, arquivo)
      ↓
Converter para formato padrão
      ↓
RAGService.index_documents()
      ↓
ReportService.generate_full_report()
      ↓
Relatório Markdown
```

### Cenário 3: Gerar Seção Por Seção

```
Para cada seção (Introdução, Metodologia, ...):
      ↓
ReportService.generate_section()
      ↓
Coletar seções
      ↓
Montar documento final
```

## 📊 Integração com Dados Existentes

### Mapear Dados do Research para Report

```python
def map_research_to_report_data(research: Research) -> dict:
    """
    Mapeia Research record para dados que o report espera.
    """
    
    # Dados científicos
    scientific_data = {
        "article_count": research.scholarly_results_count,
        "top_journals": [
            {"journal": j, "count": c}
            for j, c in research.metrics.article_by_journal.items()
        ][:5] if research.metrics else [],
        "top_fields": list(
            research.metrics.article_by_field.keys()
        )[:5] if research.metrics else [],
    }
    
    # Dados de patentes
    patent_data = {
        "patent_count": research.patent_results_count,
        "top_applicants": [
            {"name": a, "count": c}
            for a, c in research.metrics.patent_by_applicant.items()
        ][:5] if research.metrics else [],
        "top_cpc_codes": list(
            research.metrics.patent_by_ipc.keys()
        )[:5] if research.metrics else [],
    }
    
    # S-Curve
    s_curve_data = {
        "phase": "GROWTH",  # Extrair de research.metrics.patent_growth_trend
        "growth_rate": 0.18,
        "peak_year": 2023,
    }
    
    return {
        "area_of_study": research.chosen_candidate.get("area_of_study") if research.chosen_candidate else "",
        "keywords": research.chosen_candidate.get("keywords", []) if research.chosen_candidate else [],
        "period_start": research.user_input.get("period_start"),
        "period_end": research.user_input.get("period_end"),
        "scientific_data": scientific_data,
        "patent_data": patent_data,
        "s_curve_data": s_curve_data,
    }
```

### Converter Documentos para RAG

```python
def convert_results_to_rag_documents(research: Research) -> list[dict]:
    """
    Converte resultados de patentes e artigos para documentos RAG.
    """
    
    documents = []
    
    # Documentos de patentes
    for patent in research.patent_documents[:50]:  # Limitar para não sobrecarregar
        doc_text = f"""
Patente: {patent.title}
Aplicantes: {', '.join(patent.applicants or [])}
Inventores: {', '.join(patent.inventors or [])}
Resumo: {patent.abstract or 'N/A'}
Classificação CPC: {', '.join(patent.cpc_codes or [])}
Ano: {patent.year}
Status: {patent.legal_status}
"""
        documents.append({
            "text": doc_text.strip(),
            "source": f"Patent_{patent.publication_number}",
            "type": "patent",
            "year": patent.year,
        })
    
    # Documentos de artigos
    for article in research.scholarly_documents[:50]:
        doc_text = f"""
Artigo: {article.title}
Autores: {', '.join(article.authors or [])}
Resumo: {article.abstract or 'N/A'}
Campos de Estudo: {', '.join(article.field_of_study or [])}
Ano: {article.year}
Citações: {article.citations or 0}
"""
        documents.append({
            "text": doc_text.strip(),
            "source": f"Article_{article.doi}",
            "type": "article",
            "year": article.year,
        })
    
    return documents
```

## 🎯 Casos de Uso Práticos

### Caso 1: Relatório Após Pesquisa Completa

```python
@app.post("/research/{research_id}/generate-report")
async def generate_report_for_research(
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
    report_service: ReportService = Depends(get_report_service),
):
    # Buscar pesquisa
    research = await ResearchService.get_research(session, research_id)
    
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    
    # Indexar documentos
    documents = convert_results_to_rag_documents(research)
    await report_service.add_documents_to_rag(documents)
    
    # Gerar relatório
    report_data = map_research_to_report_data(research)
    report = await report_service.generate_full_report(
        theme=research.title,
        description=research.description,
        data=report_data,
    )
    
    return {"success": True, "report": report}
```

### Caso 2: Regenerar Seção Específica

```python
@app.post("/research/{research_id}/regenerate-section/{section}")
async def regenerate_section(
    research_id: int,
    section: str,  # "introducao", "metodologia", etc
    session: AsyncSession = Depends(get_db_session),
    report_service: ReportService = Depends(get_report_service),
):
    research = await ResearchService.get_research(session, research_id)
    
    # Mapear nome para tipo
    section_map = {
        "introducao": ("Introdução", "introducao"),
        "metodologia": ("Metodologia", "metodologia"),
        # ... outros
    }
    
    section_name, section_type = section_map[section]
    report_data = map_research_to_report_data(research)
    
    result = await report_service.generate_section_sync(
        section_name=section_name,
        section_type=section_type,
        theme=research.title,
        data=report_data,
    )
    
    return result
```

### Caso 3: Converter para PDF

```python
import subprocess
import tempfile
from pathlib import Path

@app.post("/reports/{research_id}/export-pdf")
async def export_report_as_pdf(
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    # Buscar pesquisa com relatório
    research = await session.get(Research, research_id)
    
    if not research or not research.latex_content:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Salvar como arquivo Markdown temporário
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.md',
        delete=False,
        encoding='utf-8'
    ) as tmp_md:
        tmp_md.write(research.latex_content)
        tmp_path = tmp_md.name
    
    # Converter com pandoc
    output_pdf = f"reports/report_{research_id}.pdf"
    
    try:
        subprocess.run([
            "pandoc",
            tmp_path,
            "-o", output_pdf,
            "--pdf-engine=xelatex",
            "-V", "lang=pt-BR",
        ], check=True)
        
        return {
            "success": True,
            "pdf_path": output_pdf,
            "file_size": Path(output_pdf).stat().st_size,
        }
    finally:
        Path(tmp_path).unlink()
```

## ⚙️ Configuração de Produção

### Docker Compose

```yaml
version: '3.8'

services:
  # FastAPI Backend
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - OLLAMA_URL=http://ollama:11434
    depends_on:
      - ollama
      - postgres

  # Ollama LLM Server
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_NUM_GPU=1  # Se tiver GPU

  # PostgreSQL
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=...
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  ollama_data:
  postgres_data:
```

### requirements.txt

```
fastapi==0.104.0
uvicorn==0.24.0
sqlalchemy==2.0.0
asyncpg==0.29.0

# Ollama + RAG
ollama==0.1.0
chromadb==0.3.21
httpx==0.24.0

# Outros
pydantic==2.0.0
python-dotenv==1.0.0
```

## 🧪 Teste de Integração

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_full_workflow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Criar pesquisa
        response = await client.post("/research", json={
            "title": "Test",
            "theme": "Recommendation Systems",
        })
        assert response.status_code == 200
        research_id = response.json()["research_id"]
        
        # 2. Gerar relatório
        response = await client.post(
            f"/research/{research_id}/generate-report"
        )
        assert response.status_code == 200
        assert "report" in response.json()
        assert len(response.json()["report"]) > 0
        
        # 3. Verificar seção
        assert "# Introdução" in response.json()["report"] or \
               "## Introdução" in response.json()["report"]
```

## 📋 Checklist de Integração

- [ ] Ollama rodando (ollama serve)
- [ ] Modelos instalados (ollama list)
- [ ] Initialize_services() no startup
- [ ] Reports router incluído
- [ ] Endpoint /reports/health retorna OK
- [ ] Dados mapeados corretamente
- [ ] RAG indexando documentos
- [ ] Seção individual gerando
- [ ] Relatório completo gerando
- [ ] Dados de pesquisa integrados
- [ ] Testes passando
- [ ] Logging funcionando

## 🚀 Deploy

```bash
# 1. Build
docker-compose build

# 2. Start
docker-compose up -d

# 3. Check health
curl http://localhost:8000/reports/health

# 4. Test report generation
curl -X POST http://localhost:8000/reports/generate \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

## 📞 Suporte

Se encontrar problemas:

1. Verificar logs: `docker-compose logs backend`
2. Health check: `GET /reports/health`
3. RAG stats: `GET /reports/rag/stats`
4. Ollama logs: `docker-compose logs ollama`
5. Ver OLLAMA_SETUP.md para troubleshooting
