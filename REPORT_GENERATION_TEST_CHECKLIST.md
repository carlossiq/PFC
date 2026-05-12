# Test Checklist: Report Generation System

Complete este checklist para verificar que o sistema está funcionando corretamente.

## 🚀 Phase 1: Setup Inicial

- [ ] Ollama instalado (`ollama --version` retorna versão)
- [ ] Ollama rodando (`ollama serve` em terminal separado)
- [ ] Modelo qwen2.5:3b-instruct baixado (`ollama list` mostra o modelo)
- [ ] Modelo nomic-embed-text baixado (`ollama list` mostra o modelo)
- [ ] Dependencies Python instaladas (`pip list | grep -E "ollama|chromadb|httpx"`)
- [ ] FastAPI rodando (`uvicorn app.main:app --reload`)
- [ ] Base de dados acessível (testes de conexão passam)

## 📋 Phase 2: Health Checks

```bash
# 2.1 Ollama health
curl http://localhost:11434/api/tags
# Esperado: lista de modelos JSON
```
- [ ] Ollama responde a requests
- [ ] Modelos aparecem na lista

```bash
# 2.2 FastAPI health
curl http://localhost:8000/reports/health
# Esperado: {"ollama": {"healthy": true}, "rag": {"status": "healthy"}}
```
- [ ] Endpoint de health retorna 200
- [ ] Ollama health = true
- [ ] RAG health = healthy

```bash
# 2.3 ChromaDB inicializado
ls -la .chroma_db/
```
- [ ] Diretório `.chroma_db` existe
- [ ] Contém arquivos do ChromaDB

## 🔧 Phase 3: Unit Tests

### 3.1 ReportDataMapper

```python
from services.report_data_mapper import ReportDataMapper
from db.research_models import Research

# Carregar Research do BD
research = await session.get(Research, 42)
assert research is not None, "Research não encontrado"

# Teste 1: Consolidação de dados
consolidated = ReportDataMapper.map_complete_research_data(research)
```

- [ ] `consolidated` contém chave "theme"
- [ ] `consolidated["patent_data"]` existe
- [ ] `consolidated["scientific_data"]` existe
- [ ] `consolidated["apis_used"]` é lista não-vazia
- [ ] `consolidated["s_curve_data"]` contém "phase"

```python
# Teste 2: Conversão para RAG documents
documents = ReportDataMapper.convert_all_results_to_rag_documents(research)
```

- [ ] `documents` é lista não-vazia
- [ ] Todos documentos têm `"text"`, `"source"`, `"type"`, `"year"`, `"api"`
- [ ] Metade (aprox) têm `"type" == "patent"`
- [ ] Metade (aprox) têm `"type" == "article"`
- [ ] `"api"` é "OPS" ou "Scopus" conforme tipo

### 3.2 OllamaService

```python
from services.ollama_service import OllamaService

ollama = OllamaService()

# Teste 1: Health check
is_healthy = await ollama.health_check()
```

- [ ] Health check retorna True

```python
# Teste 2: List models
models = await ollama.list_models()
```

- [ ] `models` é lista
- [ ] "qwen2.5:3b-instruct" está em models
- [ ] "nomic-embed-text" está em models

```python
# Teste 3: Generate text
text = await ollama.generate_text(
    prompt="Olá, qual é a capital da França?",
    system="Responda em português.",
    max_tokens=100,
)
```

- [ ] `text` é string não-vazia
- [ ] Comprimento < 100 tokens (~300 chars)
- [ ] Resposta faz sentido (não é erro)

```python
# Teste 4: Generate embedding
embedding = await ollama.generate_embedding("test query")
```

- [ ] `embedding` é lista de floats
- [ ] Comprimento é ~384 (para nomic-embed-text)
- [ ] Valores entre -1 e 1 (aprox)

### 3.3 RAGService

```python
from services.rag_service import RAGService

rag = RAGService(ollama)

# Teste 1: Index documents
documents = [
    {
        "text": "Machine learning é um subcampo da IA",
        "source": "test_doc_1",
        "type": "article"
    },
    {
        "text": "Redes neurais são inspiradas no cérebro",
        "source": "test_doc_2",
        "type": "article"
    }
]
chunk_count = await rag.index_documents(documents)
```

- [ ] `chunk_count` > 0
- [ ] Não há erro de indexação

```python
# Teste 2: Query documents
results = await rag.query("machine learning neural networks")
```

- [ ] `results` é lista de dicts
- [ ] Cada result tem `"text"`, `"distance"` (similarity score)
- [ ] Primeiro result é mais similar (menor distance)
- [ ] `distance` entre 0 e 2 (aprox)

```python
# Teste 3: Get stats
stats = rag.get_stats()
```

- [ ] `stats["document_count"]` >= 2
- [ ] `stats["status"]` = "healthy"
- [ ] `stats["collection_name"]` = "research_documents"

### 3.4 ReportService

```python
from services.report_service import ReportService

report = ReportService(ollama, rag)

# Teste 1: Generate section
section = await report.generate_section(
    section_name="Introdução",
    section_type="introducao",
    theme="Machine Learning",
    data={
        "area_of_study": "Inteligência Artificial",
        "keywords": ["machine learning", "neural networks"],
    }
)
```

- [ ] `section` é string não-vazia
- [ ] `section` contém "## Introdução"
- [ ] Comprimento > 200 chars
- [ ] Não contém "[Seção não gerada]"

```python
# Teste 2: Health check
health = await report.health_check()
```

- [ ] `health["ollama"]["healthy"]` = true
- [ ] `health["rag"]["status"]` = "healthy"

## 🧪 Phase 4: Integration Tests

### 4.1 Gerar relatório completo com dados mockados

```python
from services.report_service import ReportService

report = ReportService(ollama, rag)

data = {
    "theme": "Teste de Relatório",
    "description": "Relatório de teste",
    "area_of_study": "Tecnologia",
    "keywords": ["teste"],
    "period_start": 2020,
    "period_end": 2024,
    "patent_data": {
        "patent_count": 100,
        "top_applicants": [{"name": "Test Corp", "count": 10}],
        "top_cpc_codes": ["A01B"],
    },
    "scientific_data": {
        "article_count": 50,
        "top_journals": [{"journal": "Test Journal", "count": 5}],
        "citations": {"total": 500, "average": 10.0},
    },
    "s_curve_data": {
        "phase": "GROWTH",
        "growth_rate": 0.15,
    },
    "apis_used": ["OPS", "Scopus"],
}

full_report = await report.generate_full_report(
    theme=data["theme"],
    description=data["description"],
    data=data,
)
```

- [ ] `full_report` é string não-vazia
- [ ] Contém "# Relatório de Prospecção Tecnológica"
- [ ] Contém "## Finalidade"
- [ ] Contém "## Introdução"
- [ ] Contém "## Conclusão"
- [ ] Tamanho > 1000 chars
- [ ] Não contém "[Seção não gerada]" (exceto possíveis falhas esperadas)

### 4.2 Gerar relatório de Research real

```python
from db.research_models import Research

# Carregar Research com dados
research = await session.get(Research, 42)
assert research.patent_documents, "Research não tem patentes"
assert research.scholarly_documents, "Research não tem artigos"

# Usar novo método convenience
report_md = await report.generate_report_from_research(research)
```

- [ ] Método retorna sem erro
- [ ] `report_md` é string com tamanho > 2000 chars
- [ ] Contém todas as 10 seções esperadas
- [ ] Formatação Markdown válida (pode testar em Markdown viewer)

## 📊 Phase 5: API Endpoints

### 5.1 Health endpoint

```bash
curl -X GET http://localhost:8000/reports/health
```

Response esperado:
```json
{
  "ollama": {"healthy": true, "status": "OK"},
  "rag": {"collection_name": "research_documents", "document_count": 0, "status": "healthy"},
  "timestamp": "2026-04-27T..."
}
```

- [ ] Status 200
- [ ] Ollama healthy = true
- [ ] RAG status = healthy

### 5.2 RAG stats endpoint

```bash
curl -X GET http://localhost:8000/reports/rag/stats
```

- [ ] Status 200
- [ ] Retorna `collection_name`, `document_count`, `status`

### 5.3 Index documents endpoint

```bash
curl -X POST http://localhost:8000/reports/rag/index \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "text": "Test document for indexing",
        "source": "test_source",
        "type": "article"
      }
    ]
  }'
```

- [ ] Status 200
- [ ] Response: `{"success": true, "chunks_indexed": ...}`
- [ ] `chunks_indexed` > 0

### 5.4 Generate section endpoint

```bash
curl -X POST http://localhost:8000/reports/generate-section \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Machine Learning",
    "section_name": "Introdução",
    "section_type": "introducao",
    "data": {
      "area_of_study": "IA",
      "keywords": ["ml"]
    }
  }'
```

- [ ] Status 200
- [ ] Response: `{"success": true, "section": "Introdução", "content": "...", "generated_at": "..."}`
- [ ] Content é string não-vazia

### 5.5 Generate full report endpoint

```bash
curl -X POST http://localhost:8000/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Machine Learning",
    "description": "Study of ML technologies",
    "area_of_study": "Inteligência Artificial",
    "keywords": ["machine learning"],
    "period_start": 2020,
    "period_end": 2024,
    "scientific_data": {"article_count": 100},
    "patent_data": {"patent_count": 500},
    "chart_paths": {}
  }'
```

- [ ] Status 200
- [ ] Response: `{"success": true, "report": "...", "metadata": {...}}`
- [ ] `report` contém Markdown válido
- [ ] Tamanho > 2000 chars

### 5.6 List models endpoint

```bash
curl -X POST http://localhost:8000/reports/models/list
```

- [ ] Status 200
- [ ] Response: `{"success": true, "models": ["qwen2.5:3b-instruct", "nomic-embed-text"], "count": 2}`

## 🎯 Phase 6: End-to-End Workflow

### 6.1 Complete flow from Research

```bash
python example_research_to_report.py 42
```

- [ ] Script executa sem erro
- [ ] Exibe "Pesquisa carregada: ..."
- [ ] Exibe "Dados consolidados: ..."
- [ ] Exibe "Documentos criados: ..."
- [ ] Exibe "Relatório gerado com sucesso!"
- [ ] Arquivo `report_42.md` criado
- [ ] Arquivo contém Markdown válido (verificar em editor)

### 6.2 FastAPI endpoint flow

```bash
# Se implementou endpoint /workflow/research/{id}/generate-report
curl -X POST http://localhost:8000/workflow/research/42/generate-report
```

- [ ] Status 200
- [ ] Response: `{"success": true, "report": "..."}`
- [ ] Report é válido Markdown

## 📈 Phase 7: Performance & Quality

```python
import time

# Medir tempo de geração
start = time.time()
report = await report_service.generate_report_from_research(research)
duration = time.time() - start
```

- [ ] Tempo de geração < 5 minutos (para 50 docs)
- [ ] Tempo total de endpoint < 10 minutos
- [ ] Relatório tem > 3000 chars
- [ ] Relatório contém referências aos documentos do RAG

```python
# Verificar qualidade do português
# (Manual: ler o markdown e verificar se está em português formal)
```

- [ ] Linguagem é português (não inglês)
- [ ] Estilo é formal (não coloquial)
- [ ] Não há alucinações óbvias
- [ ] Estrutura de seções faz sentido

## ✅ Final Checklist

- [ ] Todas as fases passaram
- [ ] Não há erros em logs
- [ ] Performance é aceitável
- [ ] Relatórios gerados fazem sentido
- [ ] Dados de OPS e Scopus aparecem no relatório
- [ ] Sistema está pronto para produção

## 🐛 Se algo falhar...

| Sintoma | Diagnóstico | Solução |
|---------|-------------|---------|
| Ollama connection refused | Ollama não está rodando | `ollama serve` |
| Model not found | Modelos não foram baixados | `ollama pull qwen2.5:3b-instruct` |
| Empty ChromaDB | Documentos não foram indexados | Chamar `add_documents_to_rag()` |
| Seção não gerada | Prompt ou LLM erro | Verificar logs, aumentar timeout |
| Relatório muito curto | LLM gerou pouco | Aumentar `max_tokens` |
| Muito lento | Modelo ou docs demais | Usar 3b em vez de 7b, reduzir docs |
| Erro de BD | Research não encontrado | Verificar research_id existe |
| Erro de tipo | Schema mismatch | Verificar tipos em schemas/report.py |

---

**Tempo estimado:** 1-2 horas para completar todo o checklist

**Quando reportar issue:** Se mais de uma fase falhar após troubleshooting
