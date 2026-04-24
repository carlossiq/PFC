# Prospecting Workflow - Fluxo Padronizado

## Entrada Padronizada

Todas as rotas que trabalham com contexto de busca usam o seguinte JSON:

```json
{
  "theme": "Machine Learning in Healthcare",
  "description": "Identify emerging trends in diagnostic AI systems, focusing on deep learning applications",
  "area_of_study": "Healthcare",
  "keywords": ["deep learning", "medical imaging", "diagnostic AI"]
}
```

**Obrigatório:** `theme`  
**Opcionais:** `description`, `area_of_study`, `keywords`

---

## Fluxo de Funcionamento

### 1️⃣ **Refinar Tópico** → `POST /chat/refine-topic`

**Entrada:**
```json
{
  "theme": "Machine Learning in Healthcare",
  "description": "...",
  "area_of_study": "Healthcare",
  "keywords": ["deep learning", "medical imaging"]
}
```

**Saída:**
```json
{
  "candidates": [
    {
      "theme": "Deep Learning for Early Cancer Detection in Medical Imaging",
      "description": "...",
      "area_of_study": "Medical Imaging AI & Oncology",
      "keywords": ["deep learning", "cancer detection", ...],
      "user_input": { campos originais do usuário }
    },
    ...
  ]
}
```

**O que faz:**
- LLM gera 4 tópicos refinados a partir do tema genérico
- Cada candidato inclui todos os campos preenchidos
- `user_input` preserva o que o usuário forneceu originalmente

---

### 2️⃣ **Construir Query de Probe** → `POST /chat/probe/query`

**Entrada:**
```json
{
  "theme": "Deep Learning for Early Cancer Detection in Medical Imaging",
  "area_of_study": "Medical Imaging AI & Oncology",
  "keywords": ["deep learning", "cancer detection"],
  "api": "ops"  // opcional, default: "ops"
}
```

**Saída:**
```json
{
  "api": "ops",
  "query": {
    "query": "((ti = (...)) OR ab = (...)) AND (pd within ...)",
    "range": "1-10",
    "format": "json"
  },
  "llm_strategy": { campos ativados },
  "user_input": { campos originais }
}
```

**O que faz:**
- LLM analisa o InputIntake e gera estratégia de busca (quais campos usar)
- QueryBuilder converte a estratégia em query específica da API
- Retorna query pronta para executar em `run_probe_search`

---

### 3️⃣ **Executar Probe Search** → `POST /chat/probe/search`

**Entrada:**
```json
{
  "query": { objeto retornado de /probe/query },
  "api": "ops"
}
```

**Saída:**
```json
{
  "success": true,
  "api": "ops",
  "results_count": 8,
  "total_available": 1250,
  "results": [ documentos encontrados ]
}
```

**O que faz:**
- Executa a query construída na API especificada
- Retorna até 10 documentos (probe_top_k)
- Fornece total disponível para decisão do usuário

---

### 4️⃣ **Extrair Termos Relevantes** → `POST /chat/extract-terms`

**Entrada:**
```json
{
  "documents": [ resultados do probe_search ],
  "top_k": 20
}
```

**Saída:**
```json
{
  "terms": [
    { "term": "convolutional neural networks", "score": 0.95 },
    { "term": "oncology diagnostics", "score": 0.89 },
    ...
  ],
  "count": 20
}
```

**O que faz:**
- NLP extrai termos mais relevantes dos documentos
- Ordena por score de relevância
- Alimenta busca final com keywords expandidas

---

### 5️⃣ **Construir Query Final** → `POST /chat/final/query`

**Entrada:**
```json
{
  "theme": "Deep Learning for Early Cancer Detection in Medical Imaging",
  "area_of_study": "Medical Imaging AI & Oncology",
  "keywords": ["deep learning", "cancer detection", "convolutional neural networks", ...],
  "api": "ops"  // opcional, default: "ops"
}
```

**Saída:**
```json
{
  "api": "ops",
  "query": { query construída },
  "llm_strategy": { campos ativados },
  "user_input": { campos originais }
}
```

**O que faz:**
- Constrói query final usando tema original + termos expandidos
- Similar a probe_query, mas pode usar diferentes campos
- Query retornada é passada para run_final_search

---

### 6️⃣ **Executar Busca Final** → `POST /chat/final/search`

**Entrada:**
```json
{
  "query": { objeto retornado de /final/query },
  "api": "ops",
  "max_results": 500
}
```

**Saída:**
```json
{
  "success": true,
  "api": "ops",
  "results_count": 487,
  "total_available": 3450,
  "results": [ até 500 documentos ]
}
```

**O que faz:**
- Executa busca de produção com query final
- Retorna até max_results documentos (default 500)
- Fornece resultados completos para análise

---

## Fluxo Completo (Exemplo)

```
1. Usuário fornece tema genérico
   ↓
2. /refine-topic → gera 4 candidatos específicos
   ↓
3. Usuário escolhe 1 candidato
   ↓
4. /probe/query → constrói query de teste
   ↓
5. /probe/search → executa probe (10 documentos)
   ↓
6. /extract-terms → extrai keywords dos resultados
   ↓
7. /final/query → constrói query final com keywords expandidas
   ↓
8. /final/search → busca final (até 500 documentos)
```

---

## Características da Implementação

✅ **Entrada Padronizada:** Todas as rotas de query usam InputIntake  
✅ **Propagação de Contexto:** `user_input` preserva o que o usuário forneceu  
✅ **Complementaridade:** Output de uma rota é input da próxima  
✅ **Sem Estado:** Cada ferramenta é independente (stateless)  
✅ **Composição:** Usuário controla o fluxo (pode pular etapas)

