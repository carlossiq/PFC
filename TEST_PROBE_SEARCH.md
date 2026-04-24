# Guia Completo: Testando Probe Search

## Fluxo Completo (4 Etapas)

### 1️⃣ Refinar Tema

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/refine-topic" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "machine learning"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "candidates": [
      {
        "theme": "Deep Learning Applications in Technology"
      },
      {
        "theme": "Machine Learning Solutions for Enterprise"
      },
      // ... mais 2
    ]
  }
}
```

---

### 2️⃣ Construir Probe Query

Use um dos temas refinados:

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/probe/query" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Deep Learning Applications in Technology",
    "api": "scopus"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "api": "scopus",
    "query": {
      "query": "TITLE-ABS-KEY(( ... ))",
      "count": 10
    }
  }
}
```

---

### 3️⃣ Executar Probe Search

Use a query retornada da etapa anterior:

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/probe/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "query": "TITLE-ABS-KEY((deep learning OR neural network) AND (application OR implementation))",
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
    "api": "scopus",
    "results_count": 10,
    "total_available": 15234,
    "results": [
      {
        "eid": "2-s2.0-85...",
        "title": "Deep Learning Applications for...",
        "abstract": "This paper presents...",
        "author": "..."
      },
      // ... mais 9
    ]
  }
}
```

---

## Exemplos Simplificados para Testar

### ✅ TESTE 1: Apenas Refine + Probe Query

```bash
# Passo 1: Refine um tema simples
curl -s -X POST "http://localhost:8000/api/v1/chat/refine-topic" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "machine learning"
  }' | python -m json.tool | grep "theme" | head -1

# Copia o primeiro theme refinado e use no próximo comando

# Passo 2: Build probe query
curl -s -X POST "http://localhost:8000/api/v1/chat/probe/query" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Deep Learning Applications in Technology",
    "api": "scopus"
  }' | python -m json.tool | head -50
```

---

### ✅ TESTE 2: Fluxo Completo com Resposta JSON

**Script bash para teste completo:**

```bash
#!/bin/bash

echo "=== 1. Refining topic ==="
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/chat/refine-topic" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "deep learning"
  }')

THEME=$(echo "$RESPONSE" | python -m json.tool | grep '"theme"' | head -1 | sed 's/.*"theme": "\(.*\)".*/\1/')
echo "Refined theme: $THEME"

echo ""
echo "=== 2. Building probe query ==="
QUERY_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/chat/probe/query" \
  -H "Content-Type: application/json" \
  -d "{
    \"theme\": \"$THEME\",
    \"api\": \"scopus\"
  }")

echo "$QUERY_RESPONSE" | python -m json.tool | head -40

echo ""
echo "=== 3. Running probe search ==="
# Salva a query response para usar na busca
QUERY=$(echo "$QUERY_RESPONSE" | python -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data['data']['query']))")
API=$(echo "$QUERY_RESPONSE" | python -c "import sys, json; data=json.load(sys.stdin); print(data['data']['api'])")

curl -s -X POST "http://localhost:8000/api/v1/chat/probe/search" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": $QUERY,
    \"api\": \"$API\"
  }" | python -m json.tool | head -60
```

---

## Estrutura de Dados

### InputIntake (usado em refine-topic e probe/query)
```json
{
  "theme": "string (obrigatório)",
  "description": "string | null (opcional)",
  "area_of_study": "string | null (opcional)",
  "keywords": ["string"] | null (opcional)
}
```

### Query Structure (OPS)
```json
{
  "query": "string com CQL",
  "range": "1-10",
  "format": "json"
}
```

### Query Structure (Scopus)
```json
{
  "query": "string com Scopus syntax",
  "count": 10
}
```

### Query Structure (Lens)
```json
{
  "query": {
    "bool": {
      "must": [...],
      "should": [...]
    }
  },
  "size": 10
}
```

---

## Dicas para Testar

1. **Use temas genéricos:** "machine learning", "blockchain", "renewable energy"
   - Temas muito específicos podem retornar 0 resultados

2. **Experimente diferentes APIs:**
   - `scopus`: Requer API key válida
   - `ops`: Requer OAuth token
   - `lens_patent` / `lens_scholarly`: Requer API key

3. **Monitore a resposta:**
   - Se `results_count` for 0, a query pode estar muito restritiva
   - Se `total_available` for grande, há muito material para refinar

4. **Use extract-terms:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/chat/extract-terms" \
     -H "Content-Type: application/json" \
     -d '{
       "documents": [resultado1, resultado2, ...],
       "top_k": 20
     }'
   ```
   - Extrai termos dos resultados do probe
   - Use esses termos na busca final

---

## Comportamento Esperado

✅ **Sucesso:**
- `refine-topic` retorna 4 candidatos com temas refinados
- `probe/query` retorna query válida para a API
- `probe/search` retorna documentos encontrados (mesmo que 0)

❌ **Erros Possíveis:**
- `HTTP 400` no OPS: Query CQL inválida
- `Result set was empty`: API retorna sem erro, mas sem resultados
- `Unauthorized`: API key/token inválido
- `Invalid JSON`: Formato de entrada incorreto

