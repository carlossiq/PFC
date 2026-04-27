# Setup de Geração de Relatórios com Ollama + RAG

## 📋 Visão Geral

Sistema modular para gerar relatórios de prospecção tecnológica no estilo REPTEC/AGITEC usando:

- **Ollama**: LLM local (qwen2.5:3b-instruct)
- **ChromaDB**: Vector database para RAG
- **FastAPI**: API REST

## 🚀 Instalação

### 1. Instalar Ollama

**Windows:**
- Download: https://ollama.ai/download
- Ou via Winget: `winget install Ollama`

**macOS:**
- Download: https://ollama.ai/download
- Ou via Homebrew: `brew install ollama`

**Linux:**
```bash
curl https://ollama.ai/install.sh | sh
```

### 2. Baixar Modelos

Após instalar Ollama, em um terminal separado execute:

```bash
# Modelo de geração de texto (3B, ~2GB)
ollama pull qwen2.5:3b-instruct

# Modelo de embeddings (274M, ~334MB)
ollama pull nomic-embed-text

# Verificar modelos instalados
ollama list
```

**Tamanho dos modelos:**
- qwen2.5:3b-instruct: ~2GB (rápido, bom para texto)
- nomic-embed-text: ~334MB (embeddings de alta qualidade)
- Total: ~2.3GB

### 3. Dependências Python

```bash
pip install ollama chromadb httpx
```

Ou add ao `requirements.txt`:
```
ollama>=0.1.0
chromadb>=0.3.21
httpx>=0.24.0
```

## 🏃 Executando

### 1. Iniciar Ollama Server

```bash
# Windows / macOS / Linux
ollama serve
```

Saída esperada:
```
2024/04/27 12:00:00 "GET /api/tags HTTP/1.1" 200
listening on 127.0.0.1:11434
```

### 2. Integrar com FastAPI

**Em `app/main.py`:**

```python
from fastapi import FastAPI
from api.routes.reports import router as reports_router, initialize_services

app = FastAPI(title="PFC API")

@app.on_event("startup")
async def startup_event():
    """Initialize report generation services on startup."""
    from api.routes.reports import initialize_services
    success = await initialize_services()
    if not success:
        print("AVISO: Serviço de relatórios não inicializado (Ollama indisponível)")

# Incluir rotas de relatórios
app.include_router(reports_router)

# ... outras rotas
```

### 3. Iniciar FastAPI

```bash
# Desenvolvimento
uvicorn app.main:app --reload

# Produção
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

## 📡 Endpoints da API

### 1. Health Check

```bash
curl http://localhost:8000/reports/health
```

Resposta:
```json
{
  "ollama": {
    "healthy": true,
    "status": "OK"
  },
  "rag": {
    "collection_name": "research_documents",
    "document_count": 42,
    "status": "healthy"
  },
  "timestamp": "2024-04-27T12:00:00Z"
}
```

### 2. Indexar Documentos

```bash
curl -X POST http://localhost:8000/reports/rag/index \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "text": "Sistemas de recomendação baseados em IA...",
        "source": "Article_2024",
        "type": "article"
      }
    ]
  }'
```

### 3. Gerar Relatório Completo

```bash
curl -X POST http://localhost:8000/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Sistemas de Recomendação em E-commerce",
    "description": "Análise de tecnologias para personalização",
    "area_of_study": "Inteligência Artificial",
    "keywords": ["recommendation", "personalization"],
    "period_start": 2018,
    "period_end": 2024,
    "scientific_data": {
      "article_count": 245
    },
    "patent_data": {
      "patent_count": 1523
    },
    "chart_paths": {
      "Histórico": "charts/timeline.png"
    }
  }'
```

### 4. Gerar Seção Individual

```bash
curl -X POST http://localhost:8000/reports/generate-section \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Sistemas de Recomendação em E-commerce",
    "section_name": "Introdução",
    "section_type": "introducao",
    "data": {
      "area_of_study": "Inteligência Artificial",
      "keywords": ["recommendation", "personalization"]
    }
  }'
```

### 5. Obter Stats do RAG

```bash
curl http://localhost:8000/reports/rag/stats
```

### 6. Limpar RAG

```bash
curl -X POST http://localhost:8000/reports/rag/clear
```

### 7. Listar Modelos

```bash
curl -X POST http://localhost:8000/reports/models/list
```

## 🧪 Teste Local

### Exemplo Python

```python
import asyncio
from services.ollama_service import OllamaService
from services.rag_service import RAGService
from services.report_service import ReportService

async def test():
    # Inicializar
    ollama = OllamaService()
    rag = RAGService(ollama)
    report = ReportService(ollama, rag)
    
    # Indexar documentos
    documents = [
        {
            "text": "Sistemas de recomendação usam filtragem colaborativa...",
            "source": "Article_1"
        }
    ]
    await report.add_documents_to_rag(documents)
    
    # Gerar relatório
    result = await report.generate_full_report(
        theme="Recomendação em E-commerce",
        description="Análise de tecnologias",
        data={
            "area_of_study": "IA",
            "keywords": ["recommendation"],
        }
    )
    
    print(result)

asyncio.run(test())
```

### Exemplo com cURL

Ver seção "Endpoints" acima.

## 📁 Estrutura de Arquivos

```
services/
├── ollama_service.py       # Interface com Ollama
├── rag_service.py          # ChromaDB + RAG
└── report_service.py       # Orquestração

schemas/
└── report.py               # Pydantic schemas

prompts/
└── report_prompts.py       # Prompts por seção

api/routes/
└── reports.py              # Endpoints FastAPI

example_report_generation.py # Exemplo completo
```

## ⚙️ Configuração Avançada

### Mudar Modelo de Texto

Em `services/ollama_service.py`:

```python
ollama_service = OllamaService(
    text_model="qwen2.5:7b-instruct",  # Modelo maior, mais lento
    embedding_model="nomic-embed-text"
)
```

Modelos suportados:
- `qwen2.5:3b-instruct` (rápido, 3B)
- `qwen2.5:7b-instruct` (melhor qualidade, 7B)
- `mistral:latest` (equilibrado)
- `neural-chat:latest` (otimizado para chat)

### Ajustar Parâmetros de Geração

Em `services/report_service.py` > `generate_section()`:

```python
section_text = await self.ollama.generate_text(
    prompt=prompt,
    system=REPORT_SYSTEM_PROMPT,
    temperature=0.3,      # Menos criatividade, mais acurácia
    top_p=0.95,          # Menos diversidade
    max_tokens=1500      # Mais caracteres por seção
)
```

### Mudar Diretório ChromaDB

Em `api/routes/reports.py` > `initialize_services()`:

```python
_rag_service = RAGService(
    ollama_service=_ollama_service,
    db_path="/path/to/chroma_db",  # Caminho customizado
    collection_name="research_documents"
)
```

## 🐛 Troubleshooting

### "Ollama server not running"

```bash
# Verifique se Ollama está rodando
ollama serve

# Em outro terminal, teste conexão
curl http://localhost:11434/api/tags
```

### "Model not found"

```bash
# Baixe o modelo
ollama pull qwen2.5:3b-instruct
ollama pull nomic-embed-text

# Verifique
ollama list
```

### ChromaDB vazio

```bash
# Use o endpoint para indexar documentos
POST /reports/rag/index

# Ou use RAG clear + re-index
POST /reports/rag/clear
```

### Relatório muito curto ou com erros

- Aumentar `max_tokens` na chamada ao Ollama
- Reduzir `temperature` para mais acurácia
- Melhorar contexto via RAG (indexar mais documentos)
- Revisar prompts em `prompts/report_prompts.py`

### Geração muito lenta

- Usar modelo menor (qwen2.5:3b-instruct vs 7b)
- Reduzir `top_k` na busca RAG (de 5 para 3)
- Limitar `max_tokens` (de 2000 para 1000)
- Usar GPU (se disponível)

## 🚨 Limitações

- **Modelo 3B**: Melhor para textos pequenos/médios
- **Sem contexto prolongado**: Máx ~2000 tokens por seção
- **Local**: Sem acesso a internet para validação
- **Uma seção por vez**: Para economizar memória

## 💡 Dicas de Uso

1. **Indexe contexto bom**: Quanto melhor os documentos, melhor o RAG
2. **Teste seções individuais**: Antes de gerar relatório completo
3. **Use dados reais**: Não deixe campos vazios na requisição
4. **Cache de seções**: Implemente caching se gerar múltiplas vezes
5. **Validação**: Post-processe texto para garantir formatação Markdown

## 📚 Referências

- Ollama: https://ollama.ai
- ChromaDB: https://www.trychroma.com/
- Qwen: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct
- REPTEC: Relatórios de Prospecção Tecnológica (ABNT)

## 📝 Exemplo Completo

Ver `example_report_generation.py`

```bash
python example_report_generation.py
```

Gera: `generated_report.md`

## 🔄 Workflow Recomendado

1. ✅ Instalar Ollama
2. ✅ Baixar modelos
3. ✅ Iniciar `ollama serve`
4. ✅ Integrar em FastAPI
5. ✅ Indexar documentos via `/reports/rag/index`
6. ✅ Gerar seção via `/reports/generate-section`
7. ✅ Gerar relatório completo via `/reports/generate`
8. ✅ Validar saída (Markdown bem formatado)
9. ✅ Converter para PDF (pandoc ou similar)

## ✅ Checklist de Setup

- [ ] Ollama instalado
- [ ] Modelos baixados (`ollama list`)
- [ ] Ollama rodando (`ollama serve`)
- [ ] Dependências Python instaladas
- [ ] FastAPI com rotas de reports
- [ ] `initialize_services()` no startup
- [ ] `/reports/health` retorna OK
- [ ] Documentos indexados
- [ ] Primeira seção gerada
- [ ] Relatório completo gerado

Pronto para produção! 🎉
