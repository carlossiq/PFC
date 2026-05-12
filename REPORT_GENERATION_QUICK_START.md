# Quick Start: Geração de Relatórios

Guia rápido para usar o sistema de geração de relatórios. Para detalhes, veja [REPORT_GENERATION_INTEGRATION_SUMMARY.md](REPORT_GENERATION_INTEGRATION_SUMMARY.md).

## ⚡ Setup (5 min)

```bash
# 1. Instalar Ollama
brew install ollama  # macOS
# ou download em https://ollama.ai

# 2. Em terminal separado
ollama serve

# 3. Em outro terminal
ollama pull qwen2.5:3b-instruct
ollama pull nomic-embed-text

# 4. Dependencies Python (já em requirements.txt)
pip install ollama chromadb httpx
```

## 📝 Uso Mais Simples

### Gerar relatório de um Research do BD

```python
import asyncio
from db.research_models import Research
from services.report_service import ReportService
from services.ollama_service import OllamaService
from services.rag_service import RAGService

async def main():
    # 1. Carregar Research do BD
    research = await db_session.get(Research, research_id=42)
    
    # 2. Inicializar serviços (uma vez)
    ollama = OllamaService()
    rag = RAGService(ollama)
    report = ReportService(ollama, rag)
    
    # 3. Gerar relatório (isso cuida de tudo!)
    markdown = await report.generate_report_from_research(research)
    
    # 4. Usar/salvar/enviar para cliente
    Path("report.md").write_text(markdown)
    return markdown

asyncio.run(main())
```

### Em FastAPI endpoint

```python
@router.post("/research/{research_id}/report")
async def generate_report_endpoint(
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
    report_service: ReportService = Depends(get_report_service),
):
    research = await session.get(Research, research_id)
    if not research:
        raise HTTPException(status_code=404)
    
    report = await report_service.generate_report_from_research(research)
    return {"success": True, "report": report}
```

## 🔍 Entender o Fluxo

```
Research (BD)
  └─→ ReportDataMapper
      (consolida OPS + Scopus)
        └─→ RAG indexing
            (ChromaDB)
              └─→ Ollama generation
                  (gera 10 seções)
                    └─→ Markdown Report
```

**ReportDataMapper:** consolida patentes (OPS) + artigos (Scopus)
**RAGService:** indexa documentos para contexto
**OllamaService:** gera texto com LLM local
**ReportService:** orquestra tudo

## 🎯 Casos de Uso Comuns

### 1. Usuário clica "Gerar Relatório"

```python
# Backend
research = await get_research(research_id)
report = await report_service.generate_report_from_research(research)

# Opcional: armazenar
research.latex_content = report
await session.commit()

# Responder ao cliente
return {"report": report, "success": true}
```

### 2. Gerar múltiplos relatórios em batch

```python
for research_id in [1, 2, 3, 4, 5]:
    research = await get_research(research_id)
    report = await report_service.generate_report_from_research(research)
    await save_report_to_db(research_id, report)
```

### 3. Usar dados já consolidados manualmente

```python
# Se você já tem dados agregados (não precisa ReportDataMapper)
data = {
    "theme": "...",
    "patent_data": {...},
    "scientific_data": {...},
    ...
}

report = await report_service.generate_full_report(
    theme=data["theme"],
    data=data,
)
```

### 4. Gerar apenas uma seção (teste rápido)

```python
section = await report_service.generate_section(
    section_name="Introdução",
    section_type="introducao",
    theme="Meu Tema",
    data={
        "area_of_study": "IA",
        "keywords": ["machine learning"],
    }
)
```

## ⚙️ Configuração

### Trocar modelo

```python
# Usar modelo maior (mais lento, melhor qualidade)
ollama = OllamaService(
    text_model="qwen2.5:7b-instruct",
    embedding_model="nomic-embed-text"
)
```

### Ajustar geração

```python
# Em services/report_service.py > generate_section()
section_text = await self.ollama.generate_text(
    prompt=prompt,
    temperature=0.3,    # Menos criatividade
    top_p=0.95,        # Menos diversidade
    max_tokens=1500,    # Mais tokens = texto mais longo
)
```

### Limitar documentos RAG

```python
documents = ReportDataMapper.convert_all_results_to_rag_documents(
    research,
    max_patents=50,    # Máx patentes
    max_articles=50,   # Máx artigos
)
```

## 🔧 Health Check

```python
health = await report_service.health_check()

# Retorna:
# {
#   "ollama": {"healthy": true, "status": "OK"},
#   "rag": {"document_count": 42, "status": "healthy"},
#   "timestamp": "2026-04-27T..."
# }
```

## 📊 Dados Gerados

```python
# ReportDataMapper retorna:
{
    "theme": "...",
    "description": "...",
    "area_of_study": "Inteligência Artificial",
    "keywords": ["recommendation", "personalization"],
    
    # Patentes (OPS)
    "patent_data": {
        "patent_count": 1523,
        "top_applicants": [{"name": "Amazon", "count": 156}],
        "top_cpc_codes": ["H04L29", ...],
    },
    
    # Artigos (Scopus)
    "scientific_data": {
        "article_count": 245,
        "top_journals": [{"journal": "IEEE...", "count": 12}],
        "citations": {"total": 4521, "average": 18.46},
    },
    
    # Curva-S
    "s_curve_data": {
        "phase": "GROWTH",
        "growth_rate": 0.18,
    },
    
    # Quais APIs foram usadas
    "apis_used": ["OPS", "Scopus"]
}
```

## 🚨 Erros Comuns

| Erro | Solução |
|------|---------|
| "Ollama server not running" | `ollama serve` em outro terminal |
| "Model not found" | `ollama pull qwen2.5:3b-instruct` |
| "Research not found" | Verificar se research_id existe no BD |
| "ChromaDB vazio" | Documentos são indexados automaticamente |
| "Relatório muito curto" | Aumentar `max_tokens` em OllamaService |
| "Geração lenta" | Usar modelo 3b em vez de 7b |

## 📚 Documentação Completa

- [Setup Detalhado](OLLAMA_SETUP.md)
- [Arquitetura & Integração](REPORT_GENERATION_INTEGRATION_SUMMARY.md)
- [Guia de Integração](REPORT_INTEGRATION_GUIDE.md)
- [Exemplo Completo](example_research_to_report.py)

## ✅ Verificar se está funcionando

```bash
# 1. Ollama rodando?
curl http://localhost:11434/api/tags

# 2. Modelos baixados?
ollama list

# 3. ChromaDB acessível?
# (Automático, cria em .chroma_db)

# 4. FastAPI report service inicializado?
GET http://localhost:8000/reports/health
```

Response esperada:
```json
{
  "ollama": {"healthy": true, "status": "OK"},
  "rag": {"document_count": 0, "status": "healthy"},
  "timestamp": "2026-04-27T12:00:00Z"
}
```

---

**Dica:** Comece com `example_research_to_report.py 42` para testar end-to-end!
