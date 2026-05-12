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

Use `ReportDataMapper` para consolidar dados de patentes (OPS) e artigos (Scopus):

```python
from services.report_data_mapper import ReportDataMapper
from db.research_models import Research

# Dados para Report com consolidação de OPS + Scopus
research: Research = await get_research(session, research_id)
consolidated_data = ReportDataMapper.map_complete_research_data(research)

# consolidated_data contém:
# - theme: research.title
# - description: research.description
# - area_of_study: de research.chosen_candidate
# - keywords: de research.chosen_candidate
# - period_start/end: de research.user_input
# - patent_data: agregação de OPS (por ano, aplicantes, CPC codes)
# - scientific_data: agregação de Scopus (por ano, journals, fields, autores)
# - metrics: de research.metrics
# - s_curve_data: fase de tecnologia baseada em trend
# - apis_used: ["OPS", "Scopus"] conforme resultados
```

### Converter Documentos para RAG

Use `ReportDataMapper.convert_all_results_to_rag_documents()` para criar documentos indexáveis:

```python
from services.report_data_mapper import ReportDataMapper

research: Research = await get_research(session, research_id)

# Converte tanto patentes (OPS) quanto artigos (Scopus) para formato RAG
rag_documents = ReportDataMapper.convert_all_results_to_rag_documents(
    research,
    max_patents=50,
    max_articles=50,
)

# Cada documento contém:
# {
#   "text": conteúdo formatado em português,
#   "source": "Patent_OPS_{publication_number}" ou "Article_Scopus_{doi}",
#   "type": "patent" ou "article",
#   "year": ano de publicação,
#   "api": "OPS" ou "Scopus"
# }
```

## 🎯 Casos de Uso Práticos

### Caso 1: Relatório Após Pesquisa Completa

```python
from services.report_data_mapper import ReportDataMapper

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
    
    # Consolidar dados de OPS (patentes) + Scopus (artigos)
    consolidated_data = ReportDataMapper.map_complete_research_data(research)
    
    # Converter patentes e artigos para documentos RAG
    rag_documents = ReportDataMapper.convert_all_results_to_rag_documents(research)
    await report_service.add_documents_to_rag(rag_documents)
    
    # Gerar relatório com dados consolidados
    report = await report_service.generate_full_report(
        theme=consolidated_data["theme"],
        description=consolidated_data["description"],
        data=consolidated_data,
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
