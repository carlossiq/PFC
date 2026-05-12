# Integração Completa: De Pesquisa para Relatório

## 📋 Visão Geral

Este documento descreve como o sistema de geração de relatórios está integrado com a pesquisa de tecnologias, consolidando dados de duas fontes distintas (OPS para patentes e Scopus para artigos) em um relatório unificado.

## 🔄 Fluxo Completo

```
Pesquisa no BD (Research)
    ↓ (com patent_documents + scholarly_documents)
    │
    ├─→ OPS: Patentes já extraídas
    └─→ Scopus: Artigos já extraídos
         │
         └─→ ReportDataMapper.map_complete_research_data()
             (Consolida OPS + Scopus em formato unificado)
                 │
                 ├─→ Dados de patentes agregados
                 ├─→ Dados de artigos agregados
                 ├─→ Metrics consolidadas
                 └─→ APIs utilizadas
                      │
                      └─→ ReportDataMapper.convert_all_results_to_rag_documents()
                          (Cria documentos indexáveis para RAG)
                              │
                              ├─→ Patent documents (50 máx)
                              └─→ Article documents (50 máx)
                                   │
                                   └─→ ReportService.add_documents_to_rag()
                                       (Indexa em ChromaDB)
                                            │
                                            └─→ ReportService.generate_full_report()
                                                (Gera 10 seções com Ollama)
                                                     │
                                                     └─→ Markdown Report
```

## 🛠️ Componentes Principais

### 1. ReportDataMapper (`services/report_data_mapper.py`)

**Responsabilidade:** Consolidar dados heterogêneos de OPS e Scopus

**Métodos principais:**
- `map_complete_research_data(research)` → dict com dados consolidados
- `convert_all_results_to_rag_documents(research)` → list[dict] para RAG

**Entrada:** Research com patent_documents + scholarly_documents
**Saída:** Formato unificado pronto para relatório

### 2. ReportService (`services/report_service.py`)

**Responsabilidade:** Orquestrar geração de relatório com Ollama + RAG

**Métodos principais:**
- `generate_full_report()` → string Markdown completo
- `generate_section()` → string de uma seção específica
- **`generate_report_from_research()` (NOVO)** → string com workflow completo

**Novo método convenience:**
```python
async def generate_report_from_research(
    research: Research,
    chart_paths: Optional[dict[str, str]] = None,
) -> str:
    """
    Workflow completo em um método:
    1. Consolida OPS + Scopus
    2. Cria documentos RAG
    3. Indexa em ChromaDB
    4. Gera relatório
    """
```

### 3. RAGService (`services/rag_service.py`)

**Responsabilidade:** Indexar e recuperar documentos no ChromaDB

### 4. OllamaService (`services/ollama_service.py`)

**Responsabilidade:** Interface com LLM local para geração de texto

## 📊 Estrutura de Dados

### Input: Research (do banco de dados)

```python
research = Research(
    research_id=1,
    title="Sistemas de Recomendação em E-commerce",
    description="Análise de tecnologias...",
    chosen_candidate={
        "area_of_study": "Inteligência Artificial",
        "keywords": ["recommendation", "personalization"]
    },
    user_input={
        "period_start": 2018,
        "period_end": 2024,
        ...
    },
    patent_documents=[
        PatentDocument(...),  # de OPS
        ...
    ],
    scholarly_documents=[
        ScholarlyDocument(...),  # de Scopus
        ...
    ],
    metrics=ResearchMetrics(
        patent_by_applicant={...},
        article_by_journal={...},
        patent_growth_trend={...},
        ...
    )
)
```

### Output: Dados Consolidados

```python
consolidated = {
    "theme": "Sistemas de Recomendação em E-commerce",
    "description": "Análise de tecnologias...",
    "area_of_study": "Inteligência Artificial",
    "keywords": ["recommendation", "personalization"],
    "period_start": 2018,
    "period_end": 2024,
    
    # Dados de patentes agregados (OPS)
    "patent_data": {
        "patent_count": 1523,
        "patent_by_year": {2018: 45, 2019: 67, ...},
        "top_applicants": [{"name": "Amazon", "count": 156}, ...],
        "top_inventors": [...],
        "top_cpc_codes": ["H04L29", "G06N3", ...],
        "cpc_distribution": {...}
    },
    
    # Dados de artigos agregados (Scopus)
    "scientific_data": {
        "article_count": 245,
        "article_by_year": {2018: 12, 2019: 28, ...},
        "top_journals": [{"journal": "IEEE...", "count": 12}, ...],
        "top_fields": ["Machine Learning", "Information Retrieval", ...],
        "field_distribution": {...},
        "top_authors": [{"author": "John Doe", "count": 5}, ...],
        "citations": {"total": 4521, "average": 18.46}
    },
    
    # Métricas consolidadas
    "metrics": {
        "patent_by_applicant": {...},
        "patent_by_ipc": {...},
        "article_by_journal": {...},
        "top_patent_applicants": [...],
        "top_article_authors": [...]
    },
    
    # Curva-S da tecnologia
    "s_curve_data": {
        "phase": "GROWTH",
        "growth_rate": 0.18,
        "peak_year": 2023,
        "trend": {...}
    },
    
    # Quais APIs retornaram dados
    "apis_used": ["OPS", "Scopus"]
}
```

### RAG Documents

```python
documents = [
    # De patentes (OPS)
    {
        "text": "Título: ...\nResumo: ...\nAplicantes: ...\n...",
        "source": "Patent_OPS_US123456",
        "type": "patent",
        "year": 2023,
        "api": "OPS"
    },
    # De artigos (Scopus)
    {
        "text": "Título: ...\nResumo: ...\nAutores: ...\n...",
        "source": "Article_Scopus_10.1234/...",
        "type": "article",
        "year": 2023,
        "api": "Scopus"
    },
    ...
]
```

## 💻 Exemplos de Uso

### Opção 1: Script Simples (sem FastAPI)

```python
import asyncio
from db.research_models import Research
from services.report_service import ReportService
from services.ollama_service import OllamaService
from services.rag_service import RAGService

async def main():
    # Carregar Research do BD (omitido aqui)
    research = await load_research(42)
    
    # Inicializar serviços
    ollama = OllamaService()
    rag = RAGService(ollama)
    report = ReportService(ollama, rag)
    
    # Gerar relatório com um método!
    markdown = await report.generate_report_from_research(research)
    
    # Salvar
    Path("report.md").write_text(markdown)

asyncio.run(main())
```

### Opção 2: Endpoint FastAPI

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.reports import get_report_service
from services.research_service import ResearchService
from services.report_service import ReportService

router = APIRouter(prefix="/workflow", tags=["workflow"])

@router.post("/research/{research_id}/generate-report")
async def generate_report(
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
    report_service: ReportService = Depends(get_report_service),
):
    """Gerar relatório para pesquisa existente."""
    
    # Buscar Research
    research = await ResearchService.get_research(session, research_id)
    if not research:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Gerar relatório (consolida + RAG + geração automaticamente)
    try:
        report = await report_service.generate_report_from_research(
            research=research,
            chart_paths={
                "Histórico": "charts/timeline.png",
                "Curva-S": "charts/s_curve.png",
            }
        )
        
        # Opcional: armazenar no BD
        research.latex_content = report
        await session.commit()
        
        return {"success": True, "report": report}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

### Opção 3: Usar dados já consolidados

Se você já tem dados consolidados manualmente:

```python
# Seus dados consolidados (não via ReportDataMapper)
data = {
    "theme": "...",
    "patent_data": {...},
    "scientific_data": {...},
    ...
}

# Criar documentos RAG manualmente
documents = [
    {"text": "...", "source": "Patent_...", "type": "patent"},
    {"text": "...", "source": "Article_...", "type": "article"},
]

# Gerar relatório
report = await report_service.generate_full_report(
    theme=data["theme"],
    description=data.get("description", ""),
    data=data,
)
```

## 🚀 Como Usar

### Pré-requisitos

```bash
# 1. Ollama rodando
ollama serve

# 2. Em outro terminal
ollama pull qwen2.5:3b-instruct
ollama pull nomic-embed-text

# 3. Python dependencies
pip install ollama chromadb httpx
```

### Execução

**Script simples:**
```bash
python example_research_to_report.py 42
```

**Integrado no FastAPI:**
```bash
# 1. Iniciar Ollama
ollama serve

# 2. Iniciar FastAPI
uvicorn app.main:app --reload

# 3. POST para gerar relatório
curl -X POST http://localhost:8000/workflow/research/42/generate-report
```

## 📁 Arquivos Envolvidos

```
services/
├── report_data_mapper.py       ← Consolidação OPS + Scopus
├── report_service.py            ← Orquestração + novo método
├── ollama_service.py            ← LLM local
├── rag_service.py               ← RAG com ChromaDB
└── query_builders/
    ├── ops_query_builder.py     ← Queries para patentes
    └── scopus_query_builder.py  ← Queries para artigos

api/routes/
└── reports.py                   ← Endpoints da API

prompts/
└── report_prompts.py            ← Prompts para cada seção

db/
└── research_models.py           ← Research + relacionamentos

example_research_to_report.py    ← Exemplo completo
REPORT_INTEGRATION_GUIDE.md      ← Guia com exemplos
OLLAMA_SETUP.md                  ← Setup do Ollama
```

## ✅ Checklist de Implementação

- [x] ReportDataMapper criado e testado
- [x] ReportService.generate_report_from_research() implementado
- [x] Documentação atualizada com ReportDataMapper
- [x] Exemplo completo criado (example_research_to_report.py)
- [x] Endpoints da API documentados
- [ ] Testes unitários para ReportDataMapper
- [ ] Testes de integração end-to-end
- [ ] Integração final em production

## 🐛 Troubleshooting

### "Ollama server not running"
```bash
ollama serve
```

### "Model not found"
```bash
ollama pull qwen2.5:3b-instruct
ollama pull nomic-embed-text
```

### "ChromaDB vazio"
Os documentos são indexados automaticamente pelo método `add_documents_to_rag()`, que é chamado pelo novo `generate_report_from_research()`.

### "Relatório muito curto"
- Aumentar `max_tokens` em OllamaService
- Melhorar qualidade dos documentos RAG
- Revisar prompts em `prompts/report_prompts.py`

### "Geração muito lenta"
- Usar modelo menor (qwen2.5:3b vs 7b)
- Reduzir `max_articles` / `max_patents` em ReportDataMapper
- Limitar `top_k` em RAG queries

## 📚 Referências

- [Guia de Setup Ollama](OLLAMA_SETUP.md)
- [Guia de Integração](REPORT_INTEGRATION_GUIDE.md)
- [Exemplo Simples](example_report_generation.py)
- [Exemplo Completo com Research](example_research_to_report.py)

## 🎯 Próximas Etapas

1. **Testes:** Executar exemplo com Research real do BD
2. **Integração:** Plugar endpoint FastAPI em production
3. **PDF Export:** Adicionar suporte para converter Markdown → PDF
4. **Caching:** Implementar cache de seções geradas
5. **Métricas:** Rastrear tempo de geração e qualidade
6. **Feedback:** Coletar feedback dos usuários sobre relatórios

---

**Última atualização:** 2026-04-27
**Status:** Pronto para testes e integração
