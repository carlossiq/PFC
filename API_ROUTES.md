# API Routes - Documentação Completa

## Base URL
```
http://localhost:8000/api/v1
```

---

## 📊 Rotas de Informação

### GET `/chat/current-provider`
Retorna qual LLM provider e model estão sendo utilizados atualmente.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/chat/current-provider"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "success": true,
    "provider": "gemini",
    "model": "gemini-2.5-flash-lite",
    "available": true
  },
  "message": "Current LLM provider: gemini",
  "run_id": "..."
}
```

**Campos:**
- `provider`: Nome do provider (gemini, anthropic, mock)
- `model`: Versão do modelo em uso
- `available`: Se o provider está disponível e funcional

---

### GET `/chat/models`
Lista todos os modelos LLM disponíveis e seu status.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/chat/models"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "gemini": {
      "model": "gemini-2.5-flash-lite",
      "available": true
    },
    "anthropic": {
      "model": "claude-3-5-sonnet-20241022",
      "available": false
    }
  },
  "message": "Available models listed successfully",
  "run_id": "..."
}
```

---

### GET `/chat/apis`
Lista as APIs de busca disponíveis e seu status de habilitação.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/chat/apis"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "ops": true,
    "scopus": true,
    "lens_patent": false,
    "lens_scholarly": false
  },
  "message": "Available APIs listed successfully",
  "run_id": "..."
}
```

---

## 🔄 Rotas de Workflow

### POST `/chat/refine-topic`
Refina um tema genérico em 4 variações específicas.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/refine-topic" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Machine Learning",
    "description": "Optional detailed description",
    "area_of_study": "Optional area",
    "keywords": ["optional", "keywords"]
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "success": true,
    "candidates": [
      {
        "theme": "Deep Learning Applications in Technology",
        "description": "...",
        "area_of_study": "...",
        "keywords": [...],
        "user_input": { ... }
      },
      // ... 3 mais
    ]
  },
  "message": "Topic refined successfully with 4 specific variations",
  "run_id": "..."
}
```

**InputIntake Fields:**
- `theme` (obrigatório): Tema a refinar
- `description` (opcional): Descrição detalhada
- `area_of_study` (opcional): Área de estudo
- `keywords` (opcional): Palavras-chave iniciais

---

### POST `/chat/probe/query`
Constrói query de probe search a partir de um tema.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/probe/query" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Deep Learning Applications in Technology",
    "description": "Optional",
    "area_of_study": "Optional",
    "keywords": ["optional"],
    "api": "scopus"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "success": true,
    "api": "scopus",
    "query": {
      "query": "TITLE-ABS-KEY(...)",
      "count": 10
    },
    "llm_strategy": {
      "title": true,
      "abstract": true,
      "keywords": false,
      ...
    },
    "user_input": { ... }
  },
  "message": "Probe query built successfully",
  "run_id": "..."
}
```

**InputIntake + api (default: "ops")**

---

### POST `/chat/probe/search`
Executa probe search em uma API específica (max 10 resultados).

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/probe/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "query": "TITLE-ABS-KEY((deep learning) AND (application))",
      "count": 10
    },
    "api": "scopus"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "success": true,
    "api": "scopus",
    "results_count": 10,
    "total_available": 5234,
    "results": [
      {
        "eid": "2-s2.0-...",
        "title": "...",
        "abstract": "...",
        ...
      },
      // ... mais
    ],
    "error": null
  },
  "message": "Probe search completed: 10 results",
  "run_id": "..."
}
```

---

### POST `/chat/extract-terms`
Extrai termos relevantes de documentos via NLP.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/extract-terms" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"title": "...", "abstract": "..."},
      {"title": "...", "abstract": "..."}
    ],
    "top_k": 20
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "success": true,
    "terms": [
      {"term": "deep learning", "score": 0.95},
      {"term": "neural networks", "score": 0.89},
      ...
    ],
    "count": 20
  },
  "message": "Extracted 20 terms",
  "run_id": "..."
}
```

---

### POST `/chat/final/query`
Constrói query final usando tema + keywords expandidas.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/final/query" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Deep Learning Applications in Technology",
    "description": "Optional",
    "area_of_study": "Optional",
    "keywords": ["expanded", "keywords", "from", "probe"],
    "api": "scopus"
  }'
```

**Response:**
Mesmo format de `/chat/probe/query`

---

### POST `/chat/final/search`
Executa busca final de produção (max 500 resultados).

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/final/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "query": "...",
      "count": 100
    },
    "api": "scopus",
    "max_results": 500
  }'
```

**Response:**
Mesmo format de `/chat/probe/search` mas com até 500 resultados

---

## 🔑 Configuração

### Variáveis de Ambiente (.env)
```bash
# LLM Provider
LLM_PROVIDER=gemini                          # ou: anthropic, mock
LLM_GEMINI_MODEL=gemini-2.5-flash-lite
LLM_GEMINI_API_KEY=your_api_key
LLM_ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LLM_ANTHROPIC_API_KEY=your_api_key

# Search APIs
OPS_ENABLED=true
SCOPUS_ENABLED=true
LENS_PATENT_ENABLED=false
LENS_SCHOLARLY_ENABLED=false

# Search Settings
PROBE_API=scopus
SEARCH_YEAR_FROM=2015
SEARCH_YEAR_TO=2026
```

---

## 📋 Fluxo Recomendado

```
1. GET /chat/current-provider
   └─ Verificar qual LLM está ativo

2. POST /chat/refine-topic
   └─ Refinar tema genérico em 4 variações

3. POST /chat/probe/query
   └─ Construir query para uma variação

4. POST /chat/probe/search
   └─ Executar busca de prova (10 docs)

5. POST /chat/extract-terms
   └─ Extrair keywords dos resultados

6. POST /chat/final/query
   └─ Construir query final com keywords expandidas

7. POST /chat/final/search
   └─ Busca final de produção (até 500 docs)
```

---

## 🚨 Códigos de Erro

| Status | Significado |
|--------|------------|
| 200 | Sucesso |
| 400 | Requisição inválida (JSON malformado) |
| 422 | Validação falhou (falta campo obrigatório) |
| 500 | Erro interno do servidor |

---

## 📊 Response Format

Todas as respostas seguem este formato:

```json
{
  "success": true,
  "data": { ... },
  "message": "Descrição da operação",
  "run_id": "UUID único por requisição"
}
```

- `success`: boolean
- `data`: Dados retornados (varia por rota)
- `message`: Mensagem amigável
- `run_id`: ID único para rastreamento de logs

