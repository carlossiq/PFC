# 📊 Fluxo Completo da API de Prospecção Tecnológica

## 🎯 Visão Geral

A API é uma aplicação **FastAPI** que processa requisições de prospecção tecnológica através de um pipeline multi-etapa que busca, filtra, deduplica e normaliza documentos de múltiplas fontes (Lens, OPS, Scopus).

**Entrada:** `{theme, objective, initial_keywords, document_type}`
**Saída:** Documentos persistidos no banco de dados + estatísticas

---

## 📡 ENDPOINTS DISPONÍVEIS

### 1. **GET /api/v1/health**
- **Propósito:** Verificar saúde da aplicação
- **Resposta:** Status, versão, ambiente
- **Localização:** `api/routes/health.py`

### 2. **POST /api/v1/intake** (PRINCIPAL)
- **Propósito:** Processar requisição de prospecção tecnológica
- **Entrada:** `InputIntake` (theme, objective, keywords, document_type)
- **Saída:** `SuccessResponse` com estatísticas e run_id
- **Fluxo:** Executa todo o pipeline (11 estágios)
- **Localização:** `api/routes/intake.py`

### 3. **POST /api/v1/test/llm**
- **Propósito:** Testar LLM e geração de estratégia inicial
- **Entrada:** `InputIntake`
- **Saída:** Detalhes completos do processamento LLM
- **Localização:** `api/routes/test.py`

### 4. **POST /api/v1/test/nlp**
- **Propósito:** Testar extração de keywords e embeddings
- **Entrada:** `InputIntake`
- **Saída:** Keywords extraídos e embeddings
- **Localização:** `api/routes/test.py`

### 5. **POST /api/v1/test/query-builder**
- **Propósito:** Testar geração de queries para uma API
- **Entrada:** `InputIntake` + `api_name` (lens_patent, lens_scholarly, ops, scopus)
- **Saída:** Query construída para a API
- **Localização:** `api/routes/test.py`

### 6. **POST /api/v1/test/field-schema**
- **Propósito:** Testar schema de campos disponíveis
- **Entrada:** `InputIntake` + `api_name`
- **Saída:** Schema dos campos suportados pela API
- **Localização:** `api/routes/test.py`

---

## 🔄 PIPELINE PRINCIPAL (11 ESTÁGIOS)

### **Estágio 1: Validação de Intake** ✅
```
Entrada: InputIntake (via Pydantic)
Validações:
  - theme: obrigatório, 1-500 chars
  - objective: opcional, max 1000 chars
  - initial_keywords: opcional, max 50 items, remove duplicatas
  - document_type: normalizado para "both"
Saída: InputIntake validado
```
**Arquivo:** `schemas/intake.py`

---

### **Estágio 2: Estratégia Inicial via LLM** 🤖
```
Fluxo:
1. Carregar prompt do sistema
   └─> PromptLoader.load_general_system_prompt()
   └─> Arquivo: schemas/prompts/system_general_strategy.txt

2. Enviar intake para LLM
   └─> LLMServiceFactory.get_instance() (Singleton)
   └─> Provider: settings.llm_provider (default: "mock")
   └─> Modelo: settings.llm_gemini_model (default: gemini-2.0-flash-exp)
   └─> API Key: settings.llm_gemini_api_key (do .env)

3. Normalizar saída
   └─> LLMOutputNormalizer.normalize()
   └─> Remove termos vazios/curtos
   └─> Remove duplicatas

Saída: LLMOutput (estrutura JSON com campos de busca)
```
**Arquivos:**
- `services/llm/factory.py` - Factory que cria instância LLM
- `services/llm/gemini_service.py` - Implementação Gemini
- `services/llm/anthropic_service.py` - Implementação Anthropic
- `services/llm/normalizer.py` - Normalização de output

**Configuração (`.env` e `core/config.py`):**
- `LLM_PROVIDER` = "gemini" | "anthropic" | "mock"
- `LLM_GEMINI_API_KEY` - Token de API Gemini
- `LLM_GEMINI_MODEL` - Versão do modelo Gemini
- `LLM_ANTHROPIC_API_KEY` - Token de API Anthropic
- `LLM_ANTHROPIC_MODEL` - Versão do modelo Claude
- `TEST_MODE` = true/false - Força uso de MockLLMService

---

### **Estágio 3: Probe Search** 🔍
```
Fluxo:
1. Determinar API de probe
   └─> settings.probe_api (default: "lens_patent")
   └─> Pode ser: "lens_patent" | "lens_scholarly"

2. Construir query
   └─> QueryBuilderFactory.create(probe_api, search_mode="probe")
   └─> Transforma LLMOutput em query específica da API
   └─> Limita resultados a 50 documentos

3. Executar busca
   └─> LensService.search_patent() ou search_scholarly()
   └─> Busca com API Key: settings.lens_api_token

4. Armazenar para etapa seguinte
   └─> Primeiros 50 documentos salvos em result.details["probe_documents"]

Saída:
  - probe_search_results: {api, success, documents_found, duration}
  - probe_documents: lista de documentos brutos
```
**Arquivos:**
- `services/search/lens_service.py` - Integração Lens
- `services/query_builders/lens_patent_query_builder.py` - Query builder patent
- `services/query_builders/lens_scholarly_query_builder.py` - Query builder scholarly

**Configuração:**
- `PROBE_API` = "lens_patent" | "lens_scholarly"
- `LENS_API_TOKEN` - Token da API Lens
- `LENS_ENABLED` = true/false

---

### **Estágio 4-5: Expansão Semântica** 🧠
```
Fluxo:
1. Extrair keywords dos documentos de probe
   └─> KeywordService.batch_extract(probe_docs, top_k=10)
   └─> Usa KeyBERT para extração
   └─> Retorna keywords por documento

2. Consolidar keywords únicos
   └─> KeywordService.get_unique_keywords()
   └─> Remove duplicatas
   └─> Toma top 20

3. Reranking de documentos (TODO - NÃO IMPLEMENTADO)
   ⚠️ TODO: Implementar lógica sofisticada
   - Calcular embedding do tema
   - Calcular embedding de cada documento
   - Reordenar por similaridade descendente
   - Implementar stratégia de cutoff (top-k)

Saída:
  - extracted_keywords: {total_unique, top_keywords, documents_analyzed}
  - Documentos reordenados (atualmente não usado)
```
**Arquivos:**
- `services/nlp/keyword_service.py` - Extração de keywords
- `services/nlp/embedding_service.py` - Geração de embeddings

**❌ O QUE FALTA:** Implementação completa do reranking

---

### **Estágio 6: Estratégia Final** 📋
```
Fluxo (ATUAL - SIMPLIFICADO):
1. Usar estratégia inicial para ambos patent e scholarly
   └─> result.final_strategy = {
         "patent": result.initial_strategy,
         "scholarly": result.initial_strategy
       }

⚠️ TODO: Refinar com termos expandidos
- Incorporar keywords extraídos na estratégia final
- Gerar strategy separada e otimizada para patent
- Gerar strategy separada e otimizada para scholarly
- Validar herança de campos da estratégia inicial

Saída:
  - final_strategy: {patent: LLMOutput, scholarly: LLMOutput}
```
**Localização:** `pipeline/orchestrator.py` - `_stage_final_strategy()`

**❌ O QUE FALTA:** Refinamento com termos expandidos

---

### **Estágio 7: Busca Real em Produção** 🎯
```
Fluxo:
Executa em ordem (continua mesmo se uma falhar):

1. LENS SCHOLARLY
   └─> QueryBuilderFactory.create("lens_scholarly")
   └─> build_query(final_strategy["scholarly"])
   └─> LensService.search_scholarly(query, run_id)
   └─> if settings.lens_enabled

2. LENS PATENT
   └─> QueryBuilderFactory.create("lens_patent")
   └─> build_query(final_strategy["patent"])
   └─> LensService.search_patent(query, run_id)
   └─> if settings.lens_enabled

3. OPS (Patents)
   └─> QueryBuilderFactory.create("ops")
   └─> build_query(final_strategy["patent"])
   └─> OPSService.search(query, run_id)
   └─> if settings.ops_enabled

4. SCOPUS (Scholarly)
   └─> QueryBuilderFactory.create("scopus")
   └─> build_query(final_strategy["scholarly"])
   └─> ScopusService.search(query, run_id)
   └─> if settings.scopus_enabled

Consolidação:
  - results_by_api: {api_name: SearchResult}
  - all_documents: [doc1, doc2, ...]
  - Contadores: documents_found_total, documents_filtered, etc.

Saída:
  - production_search_results: {lens_scholarly, lens_patent, ops, scopus}
  - Todos os documentos coletados em all_documents
```
**Arquivos:**
- `services/search/lens_service.py`
- `services/search/ops_service.py`
- `services/search/scopus_service.py`
- `services/query_builders/*.py` - Um builder por API

**Configuração:**
- `LENS_ENABLED`, `OPS_ENABLED`, `SCOPUS_ENABLED` - true/false
- `LENS_API_TOKEN`, `OPS_CONSUMER_KEY/SECRET`, `SCOPUS_API_KEY`
- `SEARCH_YEAR_FROM` = 2015, `SEARCH_YEAR_TO` = 2026

---

### **Estágio 8: Filtro de Relevância** 📊
```
Fluxo:
1. Calcular embeddings de cada documento
   └─> EmbeddingService.embed()
   └─> Usa SBERT (Sentence Transformer)

2. Calcular embedding do tema
   └─> EmbeddingService.embed(intake.theme)

3. Filtrar documentos por similaridade
   └─> RelevanceService.filter()
   └─> Compara: embedding_tema vs embedding_documento
   └─> Threshold: settings.relevance_threshold (default: 0.5)

Resultado:
  - documentos_relevantes = [documentos com score >= threshold]
  - relevance_filtering: {total_before, total_after, threshold_used}

Saída:
  - all_documents = documentos_relevantes
  - documents_filtered = total_before - total_after
```
**Arquivos:**
- `services/nlp/relevance_service.py`
- `services/nlp/embedding_service.py`

**Configuração:**
- `RELEVANCE_THRESHOLD` = 0.5 (ajustável)

---

### **Estágio 9: Deduplicação** 🔄
```
Fluxo:
1. Detectar documentos duplicados
   └─> DedupService.dedup()
   └─> Para Patents: lens_document_id (primary), título (fallback)
   └─> Para Scholarly: doi (primary), título (fallback)

2. Mesclar documentos duplicados
   └─> Combinar metadados
   └─> ⚠️ TODO: Implementar merge mais sofisticado
     - Agregar campos de lista (authors, keywords, codes)
     - Consolidar information de múltiplas fontes

3. Consolidar
   └─> Manter um documento por grupo de duplicatas
   └─> Preservar informações de todas as fontes

Resultado:
  - dedup_results: {patents_deduped, scholarly_deduped, merged_count}
  - documents_unique = número final de documentos

Saída:
  - all_documents = [documentos únicos]
  - documents_unique contagem
```
**Arquivo:**
- `services/dedup/dedup_service.py`

**❌ O QUE FALTA:** Merge sofisticado com agregação de campos

---

### **Estágio 10: Normalização de Metadados** 📝
```
Fluxo:
1. Detectar tipo de documento (Patent vs Scholarly)
   └─> Analisar campos presentes
   └─> Se tem patent_id, ipc, cpc → Patent
   └─> Se tem doi, journal, authors → Scholarly

2. Normalizar para cada tipo

   A. Se PATENT:
      └─> NormalizationService.normalize_patent()
      └─> Campos esperados:
          - lens_id (dedup key)
          - title
          - abstract
          - filing_date, publication_date
          - inventors, applicants
          - ipc_codes, cpc_codes
          - claims, description
      └─> Normaliza: tipos, formatos de data, listas

   B. Se SCHOLARLY:
      └─> NormalizationService.normalize_scholarly()
      └─> Campos esperados:
          - doi (dedup key)
          - title
          - abstract
          - publication_date
          - authors, affiliations
          - keywords
          - source_title, journal
      └─> Normaliza: tipos, formatos de data, listas

3. Consolidar
   └─> Mapeamento para DocumentModel (banco de dados)

Resultado:
  - normalized_documents: {patents_normalized, scholarly_normalized}
  - Documentos prontos para persistência

Saída:
  - all_documents = [documentos normalizados e validados]
```
**Arquivo:**
- `services/db/normalization_service.py`
- `db/models.py` - Modelos SQLAlchemy

**⚠️ O QUE PODE MELHORAR:** Detecção automática baseada em campos (TODO implementado)

---

### **Estágio 11: Persistência no Banco de Dados** 💾
```
Fluxo:
1. Conectar ao banco
   └─> AsyncSession (SQLAlchemy com aiosqlite)
   └─> DATABASE_URL: settings.database_url
   └─> (default: sqlite+aiosqlite:///./app.db)

2. Inserir cada documento
   └─> PersistenceService.persist()
   └─> INSERT INTO documents (...)
   └─> ON CONFLICT: Atualiza se já existe

3. Commit
   └─> ⚠️ TODO: Decidir estratégia final
     - Por documento (transação isolada - lentos)
     - Batch commit (mais rápido - menos granular)
     - Sem commit (transação única - mais rápido)

Resultado:
  - documents_persisted = quantidade inserida/atualizada
  - persistence_results: {success, count, duration}

Saída:
  - run_id, success, statistics
```
**Arquivo:**
- `services/db/persistence_service.py`
- `db/session.py` - Configuração de banco
- `db/models.py` - Modelos

**Configuração:**
- `DATABASE_URL` = "sqlite+aiosqlite:///./app.db" (padrão)

**❌ O QUE FALTA:** Otimização de estratégia de commit

---

## 📦 ESTRUTURA DE DADOS

### InputIntake (Entrada)
```python
{
  "theme": str,                    # Obrigatório (1-500 chars)
  "description": str | None,       # Opcional (0-2000 chars)
  "area_of_study": str | None,     # Opcional (0-500 chars)
  "keywords": [str] | None         # Opcional (max 50, sem duplicatas)
}
```
**Arquivo:** `schemas/intake.py`

**Todos os campos são passados para a LLM como contexto da pesquisa.**

### LLMOutput (Estratégia)
```python
{
  # Campos textuais (busca por termos)
  "title": TextualFieldQuery,
  "abstract": TextualFieldQuery,
  "claims": TextualFieldQuery,
  "description": TextualFieldQuery,
  "full_text": TextualFieldQuery,

  # Campos simples (busca exata)
  "ipc": SimpleFieldQuery,
  "cpc": SimpleFieldQuery,
  "authors": SimpleFieldQuery,
  "affiliation": SimpleFieldQuery,
  "applicant": SimpleFieldQuery,
  "inventor": SimpleFieldQuery,
  "field_of_study": SimpleFieldQuery,
  "keywords": SimpleFieldQuery,
  "source_title": SimpleFieldQuery,
  "year": SimpleFieldQuery
}
```
**Arquivo:** `schemas/llm.py`

### Document (Banco de Dados)
```python
{
  "id": UUID (primary key),
  "run_id": UUID (grupo de docs),
  "document_type": "patent" | "scholarly",
  "title": str,
  "abstract": str,

  # Para Patents
  "patent_id": str,
  "filing_date": date,
  "publication_date": date,
  "inventors": list,
  "applicants": list,
  "ipc_codes": list,
  "cpc_codes": list,

  # Para Scholarly
  "doi": str,
  "authors": list,
  "keywords": list,
  "source_title": str,

  # Metadados
  "source_api": "lens" | "ops" | "scopus",
  "relevance_score": float,
  "raw_data": dict (JSON),

  "created_at": datetime,
  "updated_at": datetime
}
```
**Arquivo:** `db/models.py`

---

## 🔧 CONFIGURAÇÃO (core/config.py)

### Seção: Application
```
app_name = "Technology Prospecting API"
app_version = "0.1.0"
environment = "development"
debug = True
log_level = "INFO"
```

### Seção: Server
```
host = "0.0.0.0"
port = 8000
```

### Seção: API
```
api_prefix = "/api/v1"
allowed_origins = ["http://localhost:3000", "http://localhost:8000", "http://localhost:5173"]
```

### Seção: Database
```
database_url = "sqlite+aiosqlite:///./app.db"
```

### Seção: Security
```
secret_key = "65E3ifwj_6WAL3FBVmOIpg4axw656GNbEOqYTJdx-cg" (JWT)
algorithm = "HS256"
```

### Seção: LLM Configuration
```
llm_provider = "mock" | "gemini" | "anthropic"
test_mode = false (força uso de mock)
llm_gemini_api_key = "..." (do .env)
llm_gemini_model = "gemini-2.0-flash-exp"
llm_anthropic_api_key = "..." (do .env)
llm_anthropic_model = "claude-3-5-sonnet-20241022"
```

### Seção: External APIs
```
lens_api_token = "..." (do .env)
ops_consumer_key = "..." (do .env)
ops_consumer_secret = "..." (do .env)
scopus_api_key = "..." (do .env)
```

### Seção: Search Configuration
```
search_year_from = 2015
search_year_to = 2026
probe_api = "lens_patent" | "lens_scholarly"
probe_api_ext = "lens_scholarly"
```

### Seção: Relevance
```
relevance_threshold = 0.5 (0.0-1.0)
```

### Seção: Feature Flags
```
lens_enabled = true
ops_enabled = true
scopus_enabled = true
```

---

## ❌ LISTA DE TAREFAS (TODO)

### 🔴 CRÍTICAS (Bloqueia funcionalidade)

1. **Reranking de documentos** (Estágio 5)
   - Arquivo: `pipeline/orchestrator.py:454`
   - Tarefa: Implementar lógica de reranking sofisticada
     - [ ] Calcular embedding do tema
     - [ ] Calcular embedding de cada documento
     - [ ] Reordenar por similaridade descendente
     - [ ] Implementar estratégia de cutoff (top-k)
   - Impacto: Qualidade dos documentos iniciais

2. **Refinamento de estratégia final** (Estágio 6)
   - Arquivo: `pipeline/orchestrator.py:507`
   - Tarefa: Incorporar keywords expandidos na estratégia final
     - [ ] Gerar strategy separada para patent (otimizada)
     - [ ] Gerar strategy separada para scholarly (otimizada)
     - [ ] Validar herança de campos da inicial
   - Impacto: Qualidade dos resultados de busca

3. **Merge sofisticado de dedup** (Estágio 9)
   - Arquivo: `services/dedup/dedup_service.py:283`
   - Tarefa: Implementar agregação de campos ao mesclar
     - [ ] Agregar authors, keywords, codes
     - [ ] Consolidar informações de múltiplas fontes
     - [ ] Definir estratégia de prioridade (qual fonte usar)
   - Impacto: Qualidade de dados consolidados

### 🟡 IMPORTANTES (Afeta performance)

4. **Otimização de persistência** (Estágio 11)
   - Arquivo: `services/db/persistence_service.py:298`
   - Tarefa: Decidir estratégia final de commit
     - [ ] Por documento (lentos, transações isoladas)
     - [ ] Batch commit (mais rápido)
     - [ ] Transação única (muito rápido, sem rollback)
   - Impacto: Velocidade de persistência

5. **Configuração de pool de conexões DB**
   - Arquivo: `db/session.py:44`
   - Tarefa: Ajustar pool_size e max_overflow baseado em load
     - [ ] Testar com carga esperada
     - [ ] Dimensionar pool
   - Impacto: Concorrência

### 🟢 ENHANCEMENTS (Nice to have)

6. **Suporte a múltiplos bancos de dados**
   - Arquivo: `db/session.py:105`
   - Tarefa: Adicionar suporte MySQL, PostgreSQL (além SQLite)

7. **Configurabilidade de Query Builders**
   - Arquivo: `services/query_builders/ops_query_builder.py:126`
   - Tarefa: Fazer configuráveis parâmetros hardcoded
     - [ ] OPS: 'range', 'inputs'
     - [ ] Scopus: 'sort', 'count', 'view'
     - [ ] Lens: verificar campos de data

8. **Detecção automática de tipo de documento**
   - Arquivo: `pipeline/orchestrator.py:773`
   - Tarefa: Implementar detecção baseada em campos presentes
     - [ ] Se tem patent_id, IPC, CPC → Patent
     - [ ] Se tem DOI, journal, authors → Scholarly

---

## 🏗️ ARQUITETURA

```
requests (HTTP)
    ↓
[FastAPI Middlewares]
  - CORS
  - Request Logging
    ↓
[api/routes/intake.py::create_intake]
    ↓
[PipelineOrchestrator.execute()]
    ├─→ Estágio 2: LLMServiceFactory → LLM Service (Gemini/Anthropic/Mock)
    ├─→ Estágio 3: QueryBuilder → LensService.search_patent/scholarly()
    ├─→ Estágio 4-5: KeywordService → EmbeddingService
    ├─→ Estágio 7: QueryBuilder → {LensService, OPSService, ScopusService}
    ├─→ Estágio 8: RelevanceService (com EmbeddingService)
    ├─→ Estágio 9: DedupService
    ├─→ Estágio 10: NormalizationService
    └─→ Estágio 11: PersistenceService → Database
        ↓
[AsyncSession com SQLAlchemy]
    ↓
[SQLite/Database]
```

---

## 🚀 FLUXO DE UMA REQUISIÇÃO (Exemplo)

```
ENTRADA:
POST /api/v1/intake
{
  "theme": "Machine Learning in Healthcare",
  "description": "Identify emerging trends in diagnostic AI systems, focusing on deep learning applications",
  "area_of_study": "Healthcare",
  "keywords": ["deep learning", "medical imaging", "diagnostic AI"]
}

PROCESSAMENTO:
1. Validate → InputIntake validado
2. LLM → "Estratégia com fields: {title, abstract, keywords, ipc, authors}"
3. Probe → 50 documentos do Lens Scholarly
4. Keywords → Extrai 100+ keywords dos 50 docs
5. Final Strategy → Usa strategy inicial para patent e scholarly
6. Search →
   - Lens Scholarly: 500 docs
   - Lens Patent: 300 docs
   - OPS: 200 docs
   - Scopus: 400 docs
   Total: 1400 docs
7. Filter → Relevância > 0.5: 800 docs
8. Dedup → Remove duplicatas: 650 docs únicos
9. Normalize → Mapeia para modelos DB
10. Persist → Insere 650 documentos
11. Return

SAÍDA:
{
  "success": true,
  "data": {
    "run_id": "uuid-12345",
    "statistics": {
      "documents_found_total": 1400,
      "documents_filtered": 600,
      "documents_unique": 650,
      "documents_persisted": 650
    },
    "api_failures": {},
    "stages_completed": 10,
    "total_stages": 11
  }
}
```

---

## 📊 DIAGRAMA DO PIPELINE

```
InputIntake
    ↓
┌─→ [2] LLM Strategy
│   └─→ PromptLoader.load_general_system_prompt()
│   └─→ LLMService.process_intake()
│   └─→ LLMOutputNormalizer.normalize()
│   ↓ LLMOutput (estratégia inicial)
│
├─→ [3] Probe Search (Lens)
│   └─→ QueryBuilder.build_query()
│   └─→ LensService.search_*()
│   ↓ 50 documentos
│
├─→ [4-5] Semantic Expansion
│   ├─→ KeywordService.batch_extract()
│   └─→ 🔴 TODO: RelevanceService.rerank()
│   ↓ Keywords + Documentos reordenados
│
├─→ [6] Final Strategy
│   └─→ 🔴 TODO: Refinar com keywords expandidos
│   ↓ LLMOutput refinado {patent, scholarly}
│
├─→ [7] Production Search (Multi-API)
│   ├─→ [Lens Scholarly] + [Lens Patent] + [OPS] + [Scopus]
│   └─→ Consolidar todos os documentos
│   ↓ Todos os documentos brutos
│
├─→ [8] Relevance Filtering
│   ├─→ EmbeddingService.embed()
│   └─→ RelevanceService.filter()
│   ↓ Documentos com score >= threshold
│
├─→ [9] Deduplication
│   ├─→ DedupService.dedup()
│   └─→ 🔴 TODO: Merge sofisticado
│   ↓ Documentos únicos
│
├─→ [10] Normalization
│   ├─→ 🟡 TODO: Detecção automática de tipo
│   ├─→ NormalizationService.normalize_patent()
│   ├─→ NormalizationService.normalize_scholarly()
│   └─→ Mapeamento para DocumentModel
│   ↓ Documentos normalizados
│
└─→ [11] Persistence
    ├─→ PersistenceService.persist()
    └─→ 🟡 TODO: Otimização de commit
    ↓ Documentos persistidos

PipelineResult
  ├─→ run_id
  ├─→ success
  ├─→ documents_found_total
  ├─→ documents_filtered
  ├─→ documents_unique
  ├─→ documents_persisted
  └─→ stages[] com detalhes
```

---

## 🔐 SEGURANÇA & CONFIGURAÇÃO

### Variáveis Sensíveis (em `.env`)
- `SECRET_KEY` - JWT secret (gerado)
- `LLM_GEMINI_API_KEY` - Token Gemini
- `LLM_ANTHROPIC_API_KEY` - Token Anthropic
- `LENS_API_TOKEN` - Token Lens
- `OPS_CONSUMER_KEY` / `OPS_CONSUMER_SECRET` - OAuth OPS
- `SCOPUS_API_KEY` - Token Scopus

### Middleware de Segurança
- CORS: Whitelist de origins em `allowed_origins`
- Request Logging: Todos os requests logados
- Error Handling: Não expõe stack traces em production

---

## 📝 RESUMO DE AJUSTES RECOMENDADOS

| Prioridade | Tarefa | Impacto | Esforço |
|-----------|--------|---------|---------|
| 🔴 CRÍTICA | Implementar reranking de documentos | Qualidade | Alto |
| 🔴 CRÍTICA | Refinar estratégia com keywords | Qualidade | Médio |
| 🔴 CRÍTICA | Merge sofisticado de dedup | Qualidade | Médio |
| 🟡 IMPORTANTE | Otimizar commit de persistência | Performance | Médio |
| 🟡 IMPORTANTE | Configurar pool DB | Escalabilidade | Baixo |
| 🟢 ENHANCEMENT | Multi-DB support | Flexibilidade | Alto |
| 🟢 ENHANCEMENT | Detectar tipo automático | Robustez | Baixo |
| 🟢 ENHANCEMENT | Configurabilidade QB | Flexibilidade | Baixo |

