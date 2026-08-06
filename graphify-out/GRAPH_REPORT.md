# Graph Report - .  (2026-08-04)

## Corpus Check
- 266 files · ~117,824 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2318 nodes · 4683 edges · 153 communities (130 shown, 23 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 293 edges (avg confidence: 0.57)
- Token cost: 376,557 input · 0 output

## Community Hubs (Navigation)
- Report Chart Generation & Term Analysis
- Frontend App Shell & Navigation
- LLM Response to Query-Builder Converters
- Candidate Picker & Field Cards
- Query Builder Adapters (Multi-API)
- Hexagonal Architecture & External APIs
- Session Analytics Bar Charts
- Probe Query Hooks & Types
- Chat Router HTTP Endpoints
- Intake & LLM Schema Contracts
- ChatService Core Orchestration
- Dedup Registry Adapter
- BPMN Flow & Design Documentation
- Deduplication Service
- Document & Patent Schemas
- Ollama Embedding Service
- Patent Repository Persistence
- Metadata Normalization Service
- Anthropic LLM Service Base
- OPS Patent Search Service
- Search Adapter Base Classes
- HTTP Middleware & Health Routes
- Vector Store Port & RAG
- Probe/Final Query Frontend State
- Intake Validation Schemas
- DB Initialization & Metrics
- Report Router Endpoints
- Session Persistence Helpers
- Scholarly Repository Persistence
- Search Result Converters
- Scopus Search Adapter
- Prompt Loader Service
- LLM Adapter Converters (Multi-Provider)
- Lens Patent Query Builder
- OPS Query Builder
- Mock LLM Service
- Term Validation Helpers
- Report Section Prompts
- LLM Output Normalization
- Field Schema Service
- Frontend TS App Config
- Lens Scholarly Query Builder
- Chat Service Search Orchestration
- UI Button & Section Components
- Gemini LLM Adapter/Service
- Frontend TS Node Config
- API Route Tests
- Mock LLM Adapter & Container
- Anthropic LLM Adapter/Service
- Frontend Dependencies (package.json)
- Database Session & Docker Compose
- Request Schemas
- Query Builder Base/Factory
- Alembic Env & Migration Config
- LLM Port & Usage Types
- Persistence Service (Scholarly)
- Session Update/Finalize Flow
- Probe Documents Field Mapping
- Relevance Scoring Service
- Report Visualization Functions
- OPS Token Manager
- Frontend Lint Dependencies
- Persistence Service Package
- Research Session HTTP Routes
- LLM Service Tests
- Keyword Extraction Service
- Query Builder Factory Tests
- NLP Services Package
- Query Complexity Analyzer
- Structured Logging
- OPS XML Parsing
- Probe Results Panel & Stat Tiles
- DB Storage Schemas
- Patent Search Port
- OPS OAuth2 Token Handling
- Pytest Fixtures
- DB Architecture Audit Findings
- Embedding Generation (Document)
- OpenAlex Metadata Service
- Frontend Build Scripts
- Lens Search Implementation
- Token Cost Calculator
- Embedding Port Interface
- Configuracoes Tab & Toggle
- Embedding Adapter
- DB Session Dependency Injection
- LLM System Prompts (Search)
- Query Builder Factory
- Config Loading Tests
- Icon Sprite Sheet
- Query Builder Serialization
- Report Graphics Schemas
- Repository Init Methods
- Request Logging Middleware
- Dedup Registry Port
- LLM Output Query Helpers
- Session Input Root Schema
- Health Check Endpoint
- Embedding Model Init
- Prompt Services Package
- Scopus Subject Area Mapping
- Frontend TS Project References
- Normalized Metadata Config
- Query Builder Base build_query
- App Package Init
- Theme Refinement Prompts
- Core Package Init
- DB Package Init
- ESLint Dependency
- Tailwind Dependency
- Tailwind PostCSS Plugin
- React DOM Types
- TypeScript ESLint
- Vite React Plugin
- Schemas Package Init
- Services Package Init
- Relevance Score Serialization
- Tests Package Init
- Favicon Icon Asset
- React Logo Asset
- Vite Logo Asset

## God Nodes (most connected - your core abstractions)
1. `LLMOutput` - 77 edges
2. `ChatService` - 63 edges
3. `InputIntake` - 55 edges
4. `TextualFieldQuery` - 53 edges
5. `SimpleFieldQuery` - 50 edges
6. `get_logger()` - 43 edges
7. `LLMUsage` - 40 edges
8. `TermGroup` - 39 edges
9. `StandardizedPatentMetadata` - 39 edges
10. `StandardizedScholarlyMetadata` - 39 edges

## Surprising Connections (you probably didn't know these)
- `ChatService / chat_router.py (live orchestration: refine-topic, probe, final search, extract-terms)` --references--> `Research`  [AMBIGUOUS]
  ambinte.md → db/research_models.py
- `Finding: init_db() logs models_loaded=10 but 11 tables are actually created (stale/off-by-one log)` --references--> `init_db()`  [EXTRACTED]
  ambinte.md → db/init_db.py
- `init_db()` --references--> `ParamInit model (db/param_init_models.py)`  [EXTRACTED]
  db/init_db.py → ambinte.md
- `metrics_aggregator (app/core/services/metrics_aggregator.py)` --shares_data_with--> `Research`  [EXTRACTED]
  ambinte.md → db/research_models.py
- `postgres service (PostgreSQL 16-alpine, pfc_db)` --references--> `DatabaseSession`  [INFERRED]
  docker-compose.yml → db/session.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Search Query Generation Prompt Family (probe/general/final variants sharing group/OR field schema and boolean-complexity rules)** — config_prompts_final_system_prompt, config_prompts_general_system_prompt, config_prompts_probe_system_prompt_copy, config_prompts_probe_system_prompt [INFERRED 0.85]
- **Documentation set covering the Sidebar/Chevron-Stepper redesign** — frontend_changelog, frontend_design_update, frontend_design_reference, frontend_bpmn_implementation [EXTRACTED 0.90]
- **BPMN 7-step flow orchestration (container, stepper, store, 7 step components)** — frontend_src_components_flow_flowcontainer_flowcontainer, frontend_src_components_flow_flowstepper_flowstepper, frontend_src_store_flowstore_useflowstore, frontend_src_components_flow_steps_initialparamsstep_initialparamsstep, frontend_src_components_flow_steps_specifyparamsstep_specifyparamsstep, frontend_src_components_flow_steps_searchresultsstep_searchresultsstep, frontend_src_components_flow_steps_queryrefinementstep_queryrefinementstep, frontend_src_components_flow_steps_finalsearchstep_finalsearchstep, frontend_src_components_flow_steps_chartsstep_chartsstep, frontend_src_components_flow_steps_reportstep_reportstep [EXTRACTED 0.90]
- **AGIA Frontend v1.0 Design Update Documentation Set** — frontend_release_notes, frontend_visual_changes, frontend_updates_summary [EXTRACTED 1.00]
- **Active Session-Centric Schema Tables (Group 1, db_schema_atual)** — notes_db_schema_atual_research_session, notes_db_schema_atual_session_input, notes_db_schema_atual_session_probe_query, notes_db_schema_atual_session_ai_call, notes_db_schema_atual_patent, notes_db_schema_atual_article, notes_db_schema_atual_probe_query_patent, notes_db_schema_atual_probe_query_article, notes_db_schema_atual_probe_query_term [EXTRACTED 1.00]
- **Session-Centric Legacy Schema Tables (superseded design)** — notes_db_schema_session_centric_research_session, notes_db_schema_session_centric_session_input, notes_db_schema_session_centric_llm_candidate, notes_db_schema_session_centric_search_run, notes_db_schema_session_centric_patent_document, notes_db_schema_session_centric_scholarly_document, notes_db_schema_session_centric_session_metrics, notes_db_schema_session_centric_session_asset, notes_db_schema_session_centric_session_report, notes_db_schema_session_centric_llm_token_usage [EXTRACTED 1.00]

## Communities (153 total, 23 thin omitted)

### Community 0 - "Report Chart Generation & Term Analysis"
Cohesion: 0.05
Nodes (35): Any, ndarray, Contagem por ano, reindexada no range completo (anos sem publicação entram como…, Top-K valores mais frequentes de um campo (lista JSON ou escalar), em ordem…, Gera os PNGs de report (curva S, top entidades, distribuições) para uma sessão., Gera todos os gráficos aplicáveis (pula os que não têm dado o suficiente) e…, ReportService, Path (+27 more)

### Community 1 - "Frontend App Shell & Navigation"
Cohesion: 0.07
Nodes (41): frontend/index.html — App Entry Point, App(), Modal(), ModalInputProps, ModalProps, docTopics, Navbar(), SaveProgressButton() (+33 more)

### Community 2 - "LLM Response to Query-Builder Converters"
Cohesion: 0.07
Nodes (37): Convert domain LLMResponse to schema LLMOutput for legacy query builders., response_to_output(), _to_textual(), Config, LLMOutput, BaseModel, Verifica se a consulta está vazia (sem grupos ou grupos sem termos)., Contrato para campos simples em consultas LLM. Representa consultas sobre… (+29 more)

### Community 3 - "Candidate Picker & Field Cards"
Cohesion: 0.10
Nodes (38): CandidatePickerLayout(), CandidatePickerLayoutProps, parseCsv(), toCsv(), FieldCard(), FieldCardProps, FloatingLabelInput(), FloatingLabelInputProps (+30 more)

### Community 4 - "Query Builder Adapters (Multi-API)"
Cohesion: 0.05
Nodes (28): LensScholarlyQueryBuilderAdapter, Any, OPSQueryBuilderAdapter, Any, Any, ScopusQueryBuilderAdapter, _get_qb_adapter(), Instancia o query builder adapter correto para (api, search_mode). (+20 more)

### Community 5 - "Hexagonal Architecture & External APIs"
Cohesion: 0.07
Nodes (49): LLMPort interface, PatentSourcePort interface, core/services/research_service.py — receives PatentSourcePort & LLMPort by parameter, Lens (patent/scholarly API — schema changes frequently), OPS — EPO Open Patent Services (deprecates endpoints), Scopus API (changes request limits), USPTO API, Clean Architecture (alternative model B, compared to hexagonal) (+41 more)

### Community 6 - "Session Analytics Bar Charts"
Cohesion: 0.09
Nodes (36): Bucket, buildBuckets(), IterationsBarChart(), IterationsBarChartProps, niceStep(), roundedTopBarPath(), roundedTopBarPath(), SessionStatusBarChart() (+28 more)

### Community 7 - "Probe Query Hooks & Types"
Cohesion: 0.10
Nodes (40): ProbeResultsPanelProps, ProbeApi, UseFinalQuerySectionParams, UseProbeQuerySectionParams, UseTermSamplingParams, AiUsage, apiClient, extractAbstract() (+32 more)

### Community 8 - "Chat Router HTTP Endpoints"
Cohesion: 0.16
Nodes (42): analyze_query(), build_final_query_variant(), build_probe_queries_multi(), check_ops_token(), extract_terms(), get_available_apis(), get_available_models(), get_current_provider() (+34 more)

### Community 9 - "Intake & LLM Schema Contracts"
Cohesion: 0.09
Nodes (34): Enum, Input contract schemas for prospecting requests., OperatorEnum, LLM output contract schemas with validation rules., Enumeração de operadores lógicos suportados., Agrupamento de termos com operador lógico. Representa um conjunto de termos…, TermGroup, BaseModel (+26 more)

### Community 10 - "ChatService Core Orchestration"
Cohesion: 0.11
Nodes (14): ChatService, Any, Agrega os ai_usage já calculados de N sub-chamadas independentes (ex: as N…, Achata um LLMResponse (domain, retornado por llm.process_intake) em {campo:…, Reconstrói um schemas.llm.LLMOutput a partir dos campos estruturados…, Chama LLM → QueryBuilder → QueryComplexityAnalyzer em loop de até max_attempts…, Orquestra os steps individuais do workflow de prospecção, chamados um a um pelo…, Recupera candidatos individualmente válidos de uma resposta JSON malformada… (+6 more)

### Community 11 - "Dedup Registry Adapter"
Cohesion: 0.07
Nodes (24): DedupRegistryAdapter, patent_repository_adapter.py, PatentDedupRegistry, PatentDocument, Base, Database models for scholarly documents, patents, and deduplication registries., Modelo de publicação acadêmica no banco de dados. Armazena publicações…, Representação em string. (+16 more)

### Community 12 - "BPMN Flow & Design Documentation"
Cohesion: 0.07
Nodes (39): 7-Step BPMN Flow Pattern (params -> specify -> search -> refine -> final search -> charts -> report), BPMN_IMPLEMENTATION.md — 7-Step BPMN Flow / API Integration Doc, CHANGELOG.md — Design Update v1.0, DESIGN_REFERENCE.md — Quick Design Reference Guide, Design Color Palette (#07345f dark blue sidebar, #0ea5e9 sky blue active, #22c55e green primary, #eab308 yellow secondary), DESIGN_UPDATE.md — Sidebar/Stepper Redesign Summary, Sidebar + Chevron Stepper Redesign (7-circle stepper -> 4-step chevron, centered layout -> sidebar layout), FIGMA_DESIGN_PROMPT.md — Full Figma Design Brief (+31 more)

### Community 13 - "Deduplication Service"
Cohesion: 0.09
Nodes (17): DedupService, Any, Deduplicação de documentos usando chaves primárias com fallback para título…, Inicializa o serviço de normalização., Tests for deduplication service., Verifica normalização de texto para dedup., Verifica deduplicação de patentes., Verifica que primary key é publication_number. (+9 more)

### Community 14 - "Document & Patent Schemas"
Cohesion: 0.12
Nodes (35): Config, DocumentBatch, DocumentMetadata, PatentDocument, PublicationDocument, BaseModel, Document and patent record schemas., Metadados comuns para todos os tipos de documentos. Armazena informações de… (+27 more)

### Community 15 - "Ollama Embedding Service"
Cohesion: 0.06
Nodes (20): OllamaService, Generate text with provided context. Args: prompt: Main prompt context: Context…, Generate embedding for text using Ollama. Args: text: Input text model: Model…, Service for interacting with local Ollama instance., Generate embeddings for multiple texts. Args: texts: List of texts model: Model…, Async context manager entry., Async context manager exit., Initialize Ollama service. Args: base_url: Ollama server URL text_model: Model… (+12 more)

### Community 16 - "Patent Repository Persistence"
Cohesion: 0.10
Nodes (16): patent_doc_to_metadata(), PatentDocument, PatentRepositoryAdapter, PatentRepositoryPort, BaseModel, Estrutura padronizada de metadados de patente. Absorve diferenças entre…, StandardizedPatentMetadata, PatentDocumentRepository (+8 more)

### Community 17 - "Metadata Normalization Service"
Cohesion: 0.10
Nodes (23): NormalizationService, Any, Normaliza metadados genéricos de publicação para formato padrão. Args: data:…, Serviço de normalização de metadados. Absorve diferenças entre APIs,…, Normaliza documento Lens Patent API. Args: data: Resposta da Lens Patent API.…, Normaliza documento Lens Scholarly API. Args: data: Resposta da Lens Scholarly…, Normaliza documento OPS (European Patent Office) API. Mapeia estrutura OPS para…, Normaliza documento Scopus API. Mapeia estrutura Scopus para formato padrão.… (+15 more)

### Community 18 - "Anthropic LLM Service Base"
Cohesion: 0.09
Nodes (20): Anthropic Claude LLM service implementation., BaseLLMService, LLMJSONParseError, ABC, Base abstract class for LLM service providers., Nome do provedor de LLM. Returns: Nome identificador do provedor., JSON malformado retornado pelo LLM (ex: aspa não escapada dentro de um campo de…, Interface abstrata para provedores de serviço LLM. Define contrato que todos os… (+12 more)

### Community 19 - "OPS Patent Search Service"
Cohesion: 0.10
Nodes (19): OPSService, Any, SearchResult, Constrói headers para requisição OPS. OPS espera: Authorization: Bearer <token>…, Fetch bibliographic data for a single patent using /biblio endpoint. Uses OPS…, Extract useful bibliographic information from OPS biblio response. Navigates…, Enrich search results with bibliographic data from OPS. Fetches full…, Fecha clientes httpx (síncrono e assíncrono). (+11 more)

### Community 20 - "Search Adapter Base Classes"
Cohesion: 0.09
Nodes (18): LensScholarlyAdapter, Any, Base class for search services., Resultado de uma busca em API externa. Encapsula dados de sucesso ou erro de…, Converte resultado para dicionário. Returns: Dicionário com dados do resultado., Informações estruturadas sobre erro em busca. Proporciona detalhes padronizados…, Converte erro para dicionário. Returns: Dicionário com informações do erro., SearchError (+10 more)

### Community 21 - "HTTP Middleware & Health Routes"
Cohesion: 0.11
Nodes (21): Health check endpoint for application status verification., Request logging middleware for tracking HTTP requests with structured logging., Endpoint for creating a prospecting session's input parameters. Unlike the old…, Report chart generation for a research session's final-search documents. Pure…, create_app(), lifespan(), Main FastAPI application initialization and startup configuration., BoundLogger (+13 more)

### Community 22 - "Vector Store Port & RAG"
Cohesion: 0.09
Nodes (15): Any, Protocol, VectorStorePort, Any, RAGService, RAG (Retrieval-Augmented Generation) usando VectorStorePort. Responsável por…, asyncio, fixture (+7 more)

### Community 23 - "Probe/Final Query Frontend State"
Cohesion: 0.10
Nodes (29): ProbeQuerySectionViewProps, TermChecklistProps, FinalQueryVariant, FinalQuerySlice, ProbeQuerySlice, TermSamplingSlice, ExtractedTerm, FinalQueryResult (+21 more)

### Community 24 - "Intake Validation Schemas"
Cohesion: 0.08
Nodes (24): Config, InputIntake, BaseModel, field_validator, Contrato de entrada inicial para requisições de prospecção. Define os…, Configuração do Pydantic., Valida e normaliza o tema., Valida e normaliza a descrição. (+16 more)

### Community 25 - "DB Initialization & Metrics"
Cohesion: 0.09
Nodes (21): metrics_aggregator (app/core/services/metrics_aggregator.py), main(), Database initialization utility. Handles table creation for both existing and…, Script principal para inicializar banco de dados. Uso: python -m db.init_db, metrics_aggregator.py (uses legacy research schema), Base, Database models for storing complete research/prospecting data. Stores…, Patente vinculada a uma pesquisa. Armazena documentos de patente encontrados… (+13 more)

### Community 26 - "Report Router Endpoints"
Cohesion: 0.12
Nodes (26): _article_to_dict(), generate_session_graphics(), _patent_to_dict(), Any, AsyncSession, post, Request, Endpoint for generating the technology-prospecting report charts (S-curve, top… (+18 more)

### Community 27 - "Session Persistence Helpers"
Cohesion: 0.15
Nodes (24): apply_generated_fields(), apply_probe_query_fields(), Shared persistence logic for creating or updating a research_session and its…, datetime, Config, BaseModel, Schemas for searching/listing research sessions and their session_input rows., Sessão de pesquisa + todas as suas linhas de session_input (raiz e gerada),… (+16 more)

### Community 28 - "Scholarly Repository Persistence"
Cohesion: 0.15
Nodes (8): scholarly_doc_to_metadata(), ScholarlyRepositoryAdapter, ScholarlyRepositoryPort, Normalized metadata schemas for standardized document representation., Estrutura padronizada de metadados de publicação acadêmica. Absorve diferenças…, StandardizedScholarlyMetadata, Metadata normalization service for standardizing document metadata., Tests for metadata normalization service.

### Community 29 - "Search Result Converters"
Cohesion: 0.13
Nodes (12): SearchResult, to_domain(), LensPatentAdapter, Any, SearchResult, Any, SearchResult, OPSAdapter (+4 more)

### Community 30 - "Scopus Search Adapter"
Cohesion: 0.10
Nodes (14): Any, SearchResult, ScopusAdapter, Any, SearchResult, Serviço de busca na API Scopus com suporte a paginação. Gerencia requisições e…, Executa busca de uma página com retry. Args: query_params: Parâmetros de query.…, Verifica se deve continuar paginação baseado em relevância. Heurística simples:… (+6 more)

### Community 31 - "Prompt Loader Service"
Cohesion: 0.10
Nodes (18): PromptLoader, Limpa cache de prompts. Útil para recarregar prompts atualizados sem reiniciar…, Carrega prompts do sistema de arquivo. Gerencia templates de prompts para…, Obtém dicionário de prompts em cache. Returns: Dicionário com prompts…, Carrega prompt do sistema geral. Lê arquivo general_system_prompt.txt que…, Carrega prompt do sistema para modo probe. Lê arquivo probe_system_prompt.txt…, Carrega prompt do sistema para refinamento de tópicos. Lê arquivo…, Carrega um prompt customizado pelo nome de arquivo. Args: filename: Nome do… (+10 more)

### Community 32 - "LLM Adapter Converters (Multi-Provider)"
Cohesion: 0.21
Nodes (12): output_to_response(), request_to_intake(), _textual(), LLMRequest, LLMResponse, SearchError, TermGroup, TextualQuery (+4 more)

### Community 33 - "Lens Patent Query Builder"
Cohesion: 0.10
Nodes (14): LensPatentQueryBuilderAdapter, Any, LensPatentQueryBuilder, Any, Constrói partes da query_string com sintaxe booleana. Estratégia: - Title e…, Constrói parte de query_string para campo textual. Formato: field:(term1 OR…, Construtor de queries para Lens Patent API. Transforma LLMOutput em query…, Constrói parte de query_string para campo simples. Formato: field:(value1 OR… (+6 more)

### Community 34 - "OPS Query Builder"
Cohesion: 0.10
Nodes (13): OPSQueryBuilder, Any, Constrói cláusula CQL para campo textual. Cada termo vira um predicado…, Construtor de consultas para OPS (European Patent Office) API. Transforma saída…, Constrói cláusula CQL para campo simples. Cada valor vira um predicado…, Constrói cláusula CQL para range de anos. Usa o campo "pd" (publication date)…, Escapa termo para CQL. Se contém espaços ou caracteres especiais, envolve com…, Carrega mapa de campos OPS do arquivo JSON. Espera estrutura: {"field_map":… (+5 more)

### Community 35 - "Mock LLM Service"
Cohesion: 0.10
Nodes (14): MockLLMService, Extract semantic concepts from input. Returns list of concept groups, where…, Extract a single concept from text as a list of synonyms. Extracts meaningful…, Mock LLM service that returns realistic structured outputs. Extracts semantic…, Build a textual field query with groups of terms. Args: concepts: List of…, Build a simple field query as a flat list. Args: concepts: List of concept…, Initialize mock service., Return provider name. (+6 more)

### Community 36 - "Term Validation Helpers"
Cohesion: 0.10
Nodes (16): clean_terms(), is_valid_term(), Cleans a list of terms by: - Removing invalid terms - Removing duplicates -…, Validates a term group structure. Checks: - Has 'operator' field (AND or OR) -…, Validates a single term. Rejects: - Empty or whitespace-only strings - Terms…, validate_group(), Tests for field validation helpers., Test textual field detection. (+8 more)

### Community 37 - "Report Section Prompts"
Cohesion: 0.12
Nodes (23): _conclusao_prompt(), _finalidade_prompt(), get_section_prompt(), _informacoes_cientificas_prompt(), _informacoes_tecnologicas_prompt(), _introducao_prompt(), _metodologia_prompt(), _objetivo_prompt() (+15 more)

### Community 38 - "LLM Output Normalization"
Cohesion: 0.09
Nodes (13): field_validator, Valida que o operador de grupo é um valor permitido., Valida e filtra grupos vazios, convertendo dicts para TermGroup., Normaliza valores removendo duplicatas e vazios., Converte campos textuais para TextualFieldQuery se necessário., Normaliza termos removendo duplicatas, vazios e normalizando espaçamento., Valida que o operador é um valor permitido., Constrói mensagem do usuário para Claude. Args: intake: Entrada do usuário.… (+5 more)

### Community 39 - "Field Schema Service"
Cohesion: 0.11
Nodes (13): FieldSchemaService, Retorna dicionário {field_name: field_type} para busca PROBE. Retorna APENAS…, Retorna lista de campos para busca final/exploratória. Inclui campos de TODAS…, Retorna dicionário {field_name: field_type} para busca FINAL. Returns: Dict com…, Gerencia esquemas de campos para diferentes APIs e modos de busca. Carrega…, Filtra campos que contêm alguma das APIs especificadas. Retorna a lista de…, Filtra campos com seus tipos (textual/simple). Retorna dicionário {field_name:…, Constrói contrato LLM output para uma API específica. DEPRECADO: Use… (+5 more)

### Community 40 - "Frontend TS App Config"
Cohesion: 0.09
Nodes (22): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+14 more)

### Community 41 - "Lens Scholarly Query Builder"
Cohesion: 0.13
Nodes (12): LensScholarlyQueryBuilder, Any, Constrói cláusula booleana para campo textual. Args: field: Campo textual…, Construtor de consultas para Lens Scholarly API. Transforma saída normalizada…, Constrói cláusula booleana para campo simples. Args: field: Campo simples com…, Constrói cláusula de intervalo de anos para publicações. Args: year_from: Ano…, Carrega mapa de campos da Lens Scholarly API. Returns: Dicionário com…, Retorna mapa de campos padrão. Returns: Mapa padrão com campos conhecidos. (+4 more)

### Community 42 - "Chat Service Search Orchestration"
Cohesion: 0.12
Nodes (12): Recorta [year_from, year_to] em faixas com peso decrescente conforme a idade.…, Converte os pesos das faixas em nº de itens, garantindo que a soma bata com…, Substitui a cláusula `(pd within "...")` da CQL original pelo intervalo da…, Substitui a cláusula `(PUBYEAR > X AND PUBYEAR < Y)` da query original pelo…, O OPS não tem nenhum critério de relevância/ordenação na busca (ver…, Mesma ideia de _run_ops_year_diversified_search, mas pro Scopus: a ordenação…, Mesma ideia de diversidade por faixa de ano do run_probe_search (nem OPS nem…, A Scopus Search API não devolve abstract (dc:description) pra essa API key -… (+4 more)

### Community 43 - "UI Button & Section Components"
Cohesion: 0.14
Nodes (16): Button(), ButtonProps, ButtonSize, ButtonVariant, SIZE_CLASSES, VARIANT_CLASSES, SectionHeader(), SectionHeaderProps (+8 more)

### Community 44 - "Gemini LLM Adapter/Service"
Cohesion: 0.12
Nodes (11): GeminiLLMAdapter, GeminiLLMService, Any, Chama Gemini e retorna JSON bruto parseado. Diferente de process_intake que…, Serviço LLM usando Google Gemini API. Integra com Google Gemini para processar…, Faz chamada à API Gemini de forma assíncrona. Args: system_prompt: Prompt do…, Extrai JSON da resposta do Gemini. Procura por bloco JSON delimitado por ``` ou…, Inicializa o serviço Gemini. Args: api_key: Chave de API do Google Gemini.… (+3 more)

### Community 45 - "Frontend TS Node Config"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+12 more)

### Community 46 - "API Route Tests"
Cohesion: 0.10
Nodes (20): client(), fixture, Tests for API routes., Testa rota de teste de field schema., Verifica que responses incluem run_id., Fornece TestClient para testes de rota., Testa rota de health check., Verifica que intake exige tema. (+12 more)

### Community 47 - "Mock LLM Adapter & Container"
Cohesion: 0.13
Nodes (13): MockLLMAdapter, Any, build_container(), _build_llm(), Any, Instancia todos os singletons (app-scoped) e retorna o container. Lê…, shutdown_container(), BaseSettings (+5 more)

### Community 48 - "Anthropic LLM Adapter/Service"
Cohesion: 0.12
Nodes (10): AnthropicLLMAdapter, Any, AnthropicLLMService, Any, Chama Claude e retorna JSON bruto parseado. Diferente de process_intake que…, Serviço LLM usando Anthropic Claude API. Integra com Claude para processar…, Faz chamada à API Claude. Args: system_prompt: Prompt do sistema. user_message:…, Inicializa o serviço Anthropic. Args: api_key: Chave de API do Anthropic… (+2 more)

### Community 49 - "Frontend Dependencies (package.json)"
Cohesion: 0.11
Nodes (19): autoprefixer, axios, dependencies, autoprefixer, axios, lucide-react, @material/web, @monaco-editor/react (+11 more)

### Community 50 - "Database Session & Docker Compose"
Cohesion: 0.13
Nodes (13): DatabaseSession, AsyncSession, Mascara senha na URL para logging. Args: url: URL de banco de dados. Returns:…, Gerenciador de sessão de banco de dados. Configura engine, pool de conexões e…, Inicializa o gerenciador de sessão., Inicializa engine e session factory. Configura pool de conexões baseado em…, Fecha engine e conexões., Fornece sessão de banco de dados como context manager. Yield: AsyncSession para… (+5 more)

### Community 51 - "Request Schemas"
Cohesion: 0.15
Nodes (18): Config, FinalSearchRequest, ProbeEnrichRequest, ProbeSearchRequest, BaseModel, Request schemas for API endpoints. Define estruturas tipadas para request…, Configuração do Pydantic., Request para extração de termos relevantes. Extrai termos de uma lista de items… (+10 more)

### Community 52 - "Query Builder Base/Factory"
Cohesion: 0.15
Nodes (11): BaseQueryBuilder, ABC, Base abstract class for query builders., Interface abstrata para construtores de consultas API. Define contrato que…, Inicializa o construtor de consultas. Args: api_name: Nome da API (lens_patent,…, Identificador único da API. Returns: String com identificação da API., Comprimento máximo de uma consulta para esta API. Returns: Número máximo de…, Factory for creating query builder instances. (+3 more)

### Community 53 - "Alembic Env & Migration Config"
Cohesion: 0.11
Nodes (10): Converte a DATABASE_URL (asyncpg, usada em runtime) pra um driver síncrono, já…, Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online(), _sync_database_url(), Configuration module for application settings management., Field schema service for managing LLM field configurations. Gerencia esquemas… (+2 more)

### Community 54 - "LLM Port & Usage Types"
Cohesion: 0.13
Nodes (10): Any, LLMUsage, Duração e tokens de uma chamada real (ou mock) à LLM, medidos na origem., LLMPort, Any, Protocol, Any, Chama LLM e retorna JSON bruto parseado. Diferente de process_intake que… (+2 more)

### Community 55 - "Persistence Service (Scholarly)"
Cohesion: 0.11
Nodes (10): AsyncSession, Inicializa o serviço de persistência. Args: session: Sessão assíncrona do…, Obtém documento por DOI. Args: doi: Digital Object Identifier. Returns:…, Verifica se dedup_key já existe. Args: dedup_key: Chave de dedup. Returns: True…, Atualiza documento existente. Args: dedup_key: Chave do documento. metadata:…, Obtém documentos por fonte e ano. Args: source: Fonte (scopus, lens_scholarly,…, Repositório para operações de publicações acadêmicas. Fornece interface CRUD…, Cria novo registro de publicação. Args: metadata: Metadados normalizados.… (+2 more)

### Community 56 - "Session Update/Finalize Flow"
Cohesion: 0.14
Nodes (17): Atualiza uma sessão já salva (root/generated/probe_queries em upsert) ao invés…, update_session(), finalize_session(), AsyncSession, post, Cria a research_session e a cadeia de session_input (raiz + gerado) numa…, apply_root_fields(), persist_session_input() (+9 more)

### Community 57 - "Probe Documents Field Mapping"
Cohesion: 0.22
Nodes (17): build_article_fields(), build_patent_fields(), patent_to_raw_item(), Any, AsyncSession, Mapeia os dicts crus de resultado de probe search (OPS/Scopus, como devolvidos…, Inverso de build_patent_fields - reconstrói um dict no formato "cru" (as chaves…, Sincroniza os patentes encontrados por uma probe query - replace completo dos… (+9 more)

### Community 58 - "Relevance Scoring Service"
Cohesion: 0.16
Nodes (11): Any, ndarray, Computa score de relevância entre tema e documento. Usa similaridade de cosseno…, Computa similaridade de cosseno manualmente. Fallback se sklearn não…, Computa scores de relevância para múltiplos documentos. Args: theme: Tema/query…, Filtra documentos por relevância. Separa documentos em aprovados (score >=…, Filtra múltiplos lotes de documentos. Útil para processar resultados de…, Converte resultado para dicionário. Returns: Dicionário com filtragem e… (+3 more)

### Community 59 - "Report Visualization Functions"
Cohesion: 0.14
Nodes (12): _find_year_for_value(), Any, ndarray, Report Visualization Functions for Technology Prospecting. Generates various…, Generates historical deposit/publication timeline. Shows evolution of research…, Generates visualizations for technology prospecting reports., Generates top applicants (patents) or authors (articles). Args: documents: List…, Generates S-curve (technology lifecycle curve) from document data. Shows… (+4 more)

### Community 60 - "OPS Token Manager"
Cohesion: 0.12
Nodes (10): OPSToken, OPSTokenManager, Obtém novo token OAuth2 do OPS. Returns: Tupla (sucesso, mensagem_erro). Se…, Representa um token OAuth2 do OPS com informações de expiração., Inicializa com token de acesso. Args: access_token: Token de acesso OAuth2.…, Verifica se token está expirado com margem de 60 segundos., Retorna dict com informações do token., Gerenciador centralizado de token OAuth2 do OPS. Mantém um token compartilhado… (+2 more)

### Community 61 - "Frontend Lint Dependencies"
Cohesion: 0.12
Nodes (17): eslint, eslint-plugin-react-hooks, eslint-plugin-react-refresh, devDependencies, eslint, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals (+9 more)

### Community 62 - "Persistence Service Package"
Cohesion: 0.16
Nodes (11): Database and persistence services package., PersistenceService, Any, Persistence service for storing normalized and filtered documents. Orchestrates…, Persiste patente normalizada e filtrada. Assume que documento já foi: -…, Persiste lote de publicações. Args: metadata_list: Lista de metadados…, # TODO: Decidir estratégia final de commit:, Serviço de persistência de documentos. Aceita documentos já filtrados,… (+3 more)

### Community 63 - "Research Session HTTP Routes"
Cohesion: 0.17
Nodes (15): delete_session(), get_session(), AsyncSession, get, Endpoint for searching/listing research sessions by their session_input theme., Apaga a research_session e, em cascata (cascade='all, delete-orphan' nas…, Busca sessões pelo tema de qualquer um de seus session_input (raiz ou gerado…, Busca uma sessão específica com todas as suas linhas de session_input e… (+7 more)

### Community 64 - "LLM Service Tests"
Cohesion: 0.16
Nodes (13): Normalizes a simple field to flat list structure. Handles various input shapes…, asyncio, Tests for LLM services and factories., Verifica que factory cria instância de LLM., Verifica que TEST_MODE força uso de MockLLMService., Verifica que mock LLM processa intake corretamente., Verifica que termos com menos de 2 caracteres são removidos., Verifica que normalizador remove duplicatas. (+5 more)

### Community 65 - "Keyword Extraction Service"
Cohesion: 0.18
Nodes (8): KeywordService, Extrai palavras-chave de múltiplos campos de um documento. Processa título,…, Serviço de extração de palavras-chave de documentos. Usa KeyBERT para extrair…, Extrai palavras-chave de múltiplos documentos em batch. Args: documents: Lista…, Obtém lista única de palavras-chave de múltiplos documentos. Útil para…, Inicializa o serviço de keywords. Args: language: Idioma para extração…, Inicializa modelo KeyBERT. Carregando modelo sob demanda para evitar overhead…, Extrai palavras-chave de um texto. Args: text: Texto para extrair palavras-…

### Community 66 - "Query Builder Factory Tests"
Cohesion: 0.14
Nodes (13): Cria instância de construtor de consulta. Args: api_name: Nome da API…, Garante que o Lens Scholarly usa os campos do JSON (não apenas filtro de data)., Verifica criação de builders para diferentes APIs., Verifica construção de query Lens Patent., Verifica construção de query CQL OPS., Verifica que builders respeitam comprimento máximo., Verifica diferenças entre probe e general search modes., test_lens_patent_builder_builds_query() (+5 more)

### Community 67 - "NLP Services Package"
Cohesion: 0.26
Nodes (9): EmbeddingService, Embedding generation service using sentence-transformers., Serviço de geração de embeddings para textos. Usa sentence-transformers para…, NLP services package for keyword extraction and semantic relevance., DocumentRelevanceScore, FilteredDocumentsResult, Relevance scoring and document filtering service., Score de relevância de um documento. Armazena score de similaridade e decisão… (+1 more)

### Community 68 - "Query Complexity Analyzer"
Cohesion: 0.44
Nodes (3): Any, QueryComplexityAnalyzer, Analisa complexidade de queries booleanas (CQL, SQL, etc).

### Community 69 - "Structured Logging"
Cohesion: 0.19
Nodes (8): Any, Log em nível DEBUG com contexto estruturado. Args: message: Mensagem principal…, Wrapper para facilitar logging estruturado com contexto adicional., Inicializa o logger estruturado. Args: name: Nome do módulo., Log em nível INFO com contexto estruturado. Args: message: Mensagem principal…, Log em nível ERROR com contexto estruturado. Args: message: Mensagem principal…, Log em nível WARNING com contexto estruturado. Args: message: Mensagem…, StructuredLogger

### Community 70 - "OPS XML Parsing"
Cohesion: 0.24
Nodes (11): Element, _extract_party_names_xml(), _find_all_by_local_name(), _find_first_by_local_name(), _local_name(), Search service for European Patent Office (OPS) API with OAuth2., Extrai nomes de uma lista de elementos <applicant>/<inventor> da OPS (formato…, Encontra todos elementos descendentes por nome local, ignorando namespace.… (+3 more)

### Community 71 - "Probe Results Panel & Stat Tiles"
Cohesion: 0.22
Nodes (9): selectableCardClass(), formatYearRange(), ProbeResultsPanel(), ProbeResultsStatTiles(), StatTile(), TermChecklist(), Tooltip(), TooltipProps (+1 more)

### Community 72 - "DB Storage Schemas"
Cohesion: 0.21
Nodes (12): Config, DocumentRecord, BaseModel, QueryExecutionLog, Database-related schemas for storage and retrieval., Registro de um documento armazenado em banco de dados. Mapeia dados…, Registro de uma busca armazenado em banco de dados. Permite rastreamento…, Configuração do Pydantic. (+4 more)

### Community 73 - "Patent Search Port"
Cohesion: 0.21
Nodes (5): PatentSearchPort, Any, Protocol, SearchResult, ScholarlySearchPort

### Community 74 - "OPS OAuth2 Token Handling"
Cohesion: 0.17
Nodes (7): OPSToken, Gerencia token OAuth2 do OPS. Armazena token e verifica expiração para auto-…, Inicializa com token de acesso. Args: access_token: Token de acesso OAuth2.…, Obtém novo token OAuth2 do OPS. Usa grant_type=client_credentials com…, Retorna data/hora de expiração. Returns: Datetime de expiração do token., Verifica se token está expirado com buffer. Args: buffer_seconds: Segundos…, Converte token para dicionário. Returns: Dicionário com dados do token.

### Community 75 - "Pytest Fixtures"
Cohesion: 0.23
Nodes (11): async_session_maker(), db_session(), event_loop(), AsyncSession, fixture, Pytest configuration and shared fixtures., Fornece event loop para testes async., Cria session maker para testes com banco em memória. (+3 more)

### Community 76 - "DB Architecture Audit Findings"
Cohesion: 0.20
Nodes (11): ambinte.md — Live DB Analysis Report, Finding: param_init is the only genuinely active DB table (Step1 draft persistence), Finding: research/patent/scholarly schema exists with adapters but is unreachable from any live route, Finding: init_db() logs models_loaded=10 but 11 tables are actually created (stale/off-by-one log), Finding: live wizard flow (chat_router.py/ChatService) is stateless from DB perspective, returns everything to frontend, param_init router (app/adapters/driving/http/param_init.py), research_router (app/adapters/driving/http/research_router.py), build_research_service() (app/container.py) (+3 more)

### Community 77 - "Embedding Generation (Document)"
Cohesion: 0.22
Nodes (6): ndarray, Gera embedding para um documento. Estratégia de fallback: 1. Usar abstract se…, Gera embeddings para múltiplos documentos em batch. Args: documents: Lista de…, Retorna dimensionalidade dos embeddings. Returns: Número de dimensões ou None…, Gera embedding para um texto. Args: text: Texto para embedding. Returns: Array…, Gera embeddings para múltiplos textos em batch. Args: texts: Lista de textos.…

### Community 78 - "OpenAlex Metadata Service"
Cohesion: 0.25
Nodes (5): OpenAlexService, Any, Busca metadados complementares via OpenAlex, usando o DOI que a Scopus Search…, OpenAlex devolve o abstract como índice invertido (palavra -> posições), não…, OpenAlex classifica cada trabalho com uma lista de "concepts" (área/assunto,…

### Community 79 - "Frontend Build Scripts"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, dev, lint, preview, type (+1 more)

### Community 80 - "Lens Search Implementation"
Cohesion: 0.29
Nodes (6): Any, SearchResult, Constrói headers para requisição Lens. Returns: Dicionário com headers HTTP., Busca em Lens Patents. Args: query: Query payload (JSON) para Lens API. run_id:…, Busca em Lens Scholarly. Args: query: Query payload (JSON) para Lens API.…, Executa busca interna com retry logic. Args: api_type: Tipo de API (patent ou…

### Community 81 - "Token Cost Calculator"
Cohesion: 0.22
Nodes (9): calculate_token_cost(), format_cost(), format_tokens(), get_model_pricing(), Token cost calculator for different LLM models. Provides standardized cost…, Format cost as readable string. Args: cost_usd: Cost in USD Returns: Formatted…, Format token count as readable string. Args: token_count: Number of tokens…, Get pricing for a specific model. Args: model: Model name (gemini, gpt-4,… (+1 more)

### Community 82 - "Embedding Port Interface"
Cohesion: 0.31
Nodes (3): EmbeddingPort, Embedding, Protocol

### Community 83 - "Configuracoes Tab & Toggle"
Cohesion: 0.25
Nodes (7): ConfiguracoesTab(), ModelCategory, ModelGroup, modelGroups, ModelItem, Toggle(), ToggleProps

### Community 85 - "DB Session Dependency Injection"
Cohesion: 0.25
Nodes (6): get_db_session(), AsyncSession, FastAPI dependency injection for HTTP adapters., Database session and connection management., # TODO: Suportar outros bancos (MySQL, SQLite para dev), # TODO: Configurar pool_size e max_overflow baseado em load esperado

### Community 86 - "LLM System Prompts (Search)"
Cohesion: 0.36
Nodes (8): Final System Prompt — Comprehensive Final Search Query Builder, Textual field group_operator/groups(OR terms) JSON structure, Query Complexity Constraint (cap score 0.6, target 0.2-0.5), General System Prompt — Exhaustive Recall Search Query Builder, Exhaustive semantic expansion (synonyms, acronyms, adjacent terms) for max recall, Probe System Prompt — Restricted Probe Search, Strict Forbidden-Term Rules, Probe System Prompt (copy) — Restricted Probe Search, Core/Secondary Concepts, CORE vs SECONDARY concept prioritization (CORE=AND mandatory, SECONDARY=OR flexible recall enhancer)

### Community 87 - "Query Builder Factory"
Cohesion: 0.25
Nodes (6): QueryBuilderFactory, Factory para criação de construtores de consulta API. Gerencia a instanciação…, Retorna lista de APIs suportadas. Returns: Lista de nomes de APIs., Registra um novo construtor de consulta customizado. Args: api_name: Nome da…, Verifica lista de APIs suportadas., test_query_builder_factory_supported_apis()

### Community 88 - "Config Loading Tests"
Cohesion: 0.25
Nodes (7): Tests for configuration loading., Verifica campos obrigatórios de config., Verifica valores padrão de configuração., Verifica que configuração carrega corretamente., test_config_defaults(), test_config_has_required_fields(), test_config_loads_from_env()

### Community 89 - "Icon Sprite Sheet"
Cohesion: 0.52
Nodes (7): Bluesky Icon, Discord Icon, Documentation Icon, GitHub Icon, Icons Sprite Sheet (Social & UI Icons), Social (Generic Community/Followers) Icon, X (Twitter) Icon

### Community 90 - "Query Builder Serialization"
Cohesion: 0.29
Nodes (4): Any, Converte output completo para dicionário para serialização., Converte cláusula para dicionário para serialização., Converte cláusula para dicionário para serialização.

### Community 91 - "Report Graphics Schemas"
Cohesion: 0.33
Nodes (6): GeneratedChart, BaseModel, Schemas for the report-graphics generation endpoint (POST…, Manifesto dos gráficos gerados (ou pulados por falta de dado) para uma sessão., Um PNG gerado pelo ReportService., ReportGraphicsResponse

### Community 92 - "Repository Init Methods"
Cohesion: 0.29
Nodes (4): AsyncSession, Inicializa o repositório. Args: session: Sessão assíncrona do SQLAlchemy., Inicializa o repositório. Args: session: Sessão assíncrona do SQLAlchemy., Inicializa o repositório. Args: session: Sessão assíncrona do SQLAlchemy.

### Community 93 - "Request Logging Middleware"
Cohesion: 0.33
Nodes (5): Request, Middleware que adiciona rastreamento de requisições HTTP com run_id único. Cada…, RequestLoggingMiddleware, BaseHTTPMiddleware, Response

### Community 95 - "LLM Output Query Helpers"
Cohesion: 0.33
Nodes (3): Verifica se a consulta está vazia., Retorna dicionário indicando quais campos têm consultas ativas (não vazias)., Verifica se há pelo menos uma consulta ativa em qualquer campo.

### Community 96 - "Session Input Root Schema"
Cohesion: 0.47
Nodes (3): field_validator, Input original do usuário (Step1), raiz da cadeia de session_input., SessionInputRoot

### Community 97 - "Health Check Endpoint"
Cohesion: 0.40
Nodes (5): health_check(), Any, get, Request, Verifica a saúde da aplicação e retorna informações de status. Args: request:…

### Community 100 - "Scopus Subject Area Mapping"
Cohesion: 0.50
Nodes (3): Scopus SUBJAREA field: códigos ASJC (All Science Journal Classification).…, Mapeia um texto livre de área de estudo (gerado pela LLM) pro código ASJC mais…, resolve_asjc_code()

### Community 111 - "Normalized Metadata Config"
Cohesion: 0.67
Nodes (3): Config, Configuração do Pydantic., Configuração do Pydantic.

## Ambiguous Edges - Review These
- `models.py` → `patent_repository_adapter.py`  [AMBIGUOUS]
  notes/db_schema_atual.md · relation: references
- `models.py` → `scholarly_repository_adapter.py`  [AMBIGUOUS]
  notes/db_schema_atual.md · relation: references
- `research_models.py` → `metrics_aggregator.py (uses legacy research schema)`  [AMBIGUOUS]
  notes/db_schema_atual.md · relation: references
- `research_models.py` → `report_router.py (uses legacy research schema)`  [AMBIGUOUS]
  notes/db_schema_atual.md · relation: references
- `research_models.py` → `research_router.py (uses legacy research schema)`  [AMBIGUOUS]
  notes/db_schema_atual.md · relation: references
- `Research` → `ChatService / chat_router.py (live orchestration: refine-topic, probe, final search, extract-terms)`  [AMBIGUOUS]
  ambinte.md · relation: references

## Knowledge Gaps
- **171 isolated node(s):** `SearchError`, `name`, `private`, `version`, `type` (+166 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `models.py` and `patent_repository_adapter.py`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `models.py` and `scholarly_repository_adapter.py`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `research_models.py` and `metrics_aggregator.py (uses legacy research schema)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `research_models.py` and `report_router.py (uses legacy research schema)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `research_models.py` and `research_router.py (uses legacy research schema)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Research` and `ChatService / chat_router.py (live orchestration: refine-topic, probe, final search, extract-terms)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `ChatService` connect `ChatService Core Orchestration` to `LLM Adapter Converters (Multi-Provider)`, `Lens Patent Query Builder`, `LLM Response to Query-Builder Converters`, `OPS Query Builder`, `Query Builder Adapters (Multi-API)`, `Query Complexity Analyzer`, `Chat Router HTTP Endpoints`, `Intake & LLM Schema Contracts`, `Chat Service Search Orchestration`, `Mock LLM Adapter & Container`, `Anthropic LLM Service Base`, `OPS Patent Search Service`, `LLM Port & Usage Types`, `Prompt Loader Service`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._