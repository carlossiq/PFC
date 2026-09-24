# Graph Report - C:\Users\carlo\OneDrive\Documentos\GitHub\PFC  (2026-09-23)

## Corpus Check
- 241 files · ~521,091 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3989 nodes · 8353 edges · 239 communities (212 shown, 27 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 511 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- LLM Output Schema
- Probe/Final Query Frontend
- Report Text Quality & Writer
- Legacy LLM Services
- ChatService Orchestration
- LLM Output Validators
- UI Components & Steps
- Report Chart Routes
- Settings UI
- LLM Adapters & Domain Types
- LaTeX Editor Frontend
- Report Document Router
- Logging & Health
- Dashboard Charts
- Report Assembly
- CPC Titles & Citations
- Wizard Steps & Session Services
- App Shell & Modals
- LaTeX Static Sections
- Chart Rendering Service
- Input Intake Schema
- Research Session Persistence
- Legacy Schema & Alembic
- Term Extraction Pipeline
- Session Input Persistence
- LLM JSON Repair & Group Limits
- Legacy BPMN Frontend Docs
- Query Builder Base
- RAG Service & Vector Port
- Deduplication
- Legacy Ollama RAG
- Query Field Extractor
- Legacy Document Repositories
- Metadata Normalization
- Config Router
- Candidate Picker UI
- Config Models & Seeds
- Scopus Query Builder
- Session Chart Model
- Statistical Inference API
- Report Generation Form
- OPS Query Builder
- Lens Patent Query Builder
- Query Prompt Rules
- Legacy N-gram Term Pipeline
- Scopus Final Search Tests
- Lens Scholarly Query Builder
- Patent Repository Adapter
- Technical Report Overview
- Document & Search Schemas
- Inference Service Tests
- LLM Config Repository
- Chat Router
- Prompt Loader
- Gemini Service
- ChromaDB Adapter
- Scopus Final Aggregation
- Report Figure Catalog
- Chao1 & Bootstrap
- Hexagonal Architecture Diagram
- Field Schema Service
- Report Service Tests
- Settings Sync
- MinIO Storage
- TS App Config
- Scopus Search Service
- LaTeX Review (pure)
- OpenAI-compatible Text Generation
- Scholarly Repository Adapter
- Legacy Repositories
- Report Lifecycle Stage
- TS Node Config
- Config-in-DB Migration Plan
- App Settings Repository
- OPS Search Adapter
- Storage Port
- AI Review Parsing
- Inference Enrichment Loop
- Frontend Dependencies
- add2 cluster
- lens service cluster
- research session cluster
- chart labels cluster
- relevance service cluster
- report visualizations cluster
- ops token manager cluster
- repositories cluster
- base cluster
- test report review cluster
- s curve cluster
- docker-compose cluster
- package cluster
- response cluster
- persistence service cluster
- test chat service ops final search cluster
- test chat service depositants cluster
- SessionCard cluster
- ops service cluster
- session cluster
- VARIAVEIS DE CONFIGURACAO cluster
- request cluster
- query complexity cluster
- report review service cluster
- modelo dados der cluster
- ollama service cluster
- keyword service cluster
- relevance service cluster 2
- report document router cluster
- TESTE EXTRACAO TERMOS BM25F RRF cluster
- kucharavy cluster
- logging cluster
- drawio cluster
- generate db schema docs cluster
- ops service cluster 2
- test scopus service cluster
- search port cluster
- report prompts cluster
- conftest cluster
- report service cluster
- general system prompt copy cluster
- add1 cluster
- ops service cluster 3
- db schema atual cluster
- db cluster
- embedding service cluster
- openalex service cluster
- ollama adapter cluster
- scopus adapter cluster
- llm config resolver cluster
- report review cluster
- package cluster 2
- test ops party names cluster
- token cost calculator cluster
- test report service cluster
- embedding port cluster
- app cluster
- main cluster
- promptIA cluster
- pipeline rag local cluster
- test routes cluster
- test openai compatible adapter cluster
- provider registry cluster
- embedding adapter cluster
- pipeline rag local cluster 2
- build cpc titles cluster
- ops service cluster 4
- test config cluster
- lens patent adapter cluster
- lens scholarly adapter cluster
- session input cluster
- report review cluster 2
- icons cluster
- db schema atual cluster 2
- pipeline cinco fases cluster
- README cluster
- request logging cluster
- repository port cluster
- DocUserGuide cluster
- db schema atual cluster 3
- fluxograma cluster
- health router cluster
- report review cluster 3
- drawio cluster 2
- base cluster 2
- dependencies cluster
- research session cluster 2
- embedding service cluster 2
- ops service cluster 5
- provider registry cluster 2
- tsconfig cluster
-   init   cluster
- refine topic system prompt cluster
-   init   cluster 2
-   init   cluster 3
- package cluster 3
- package cluster 4
- package cluster 5
- package cluster 6
- package cluster 7
- package cluster 8
-   init   cluster 4
-   init   cluster 5
- relevance service cluster 3
-   init   cluster 6
- Misc cluster
- Misc cluster 2
- favicon cluster
- react cluster
- vite cluster
- db schema atual cluster 4
- Misc cluster 3
- promptIA cluster 2
- Misc cluster 4

## God Nodes (most connected - your core abstractions)
1. `ChatService` - 95 edges
2. `LLMOutput` - 80 edges
3. `get_logger()` - 63 edges
4. `TextualFieldQuery` - 53 edges
5. `SimpleFieldQuery` - 50 edges
6. `Settings` - 46 edges
7. `InputIntake` - 41 edges
8. `TermGroup` - 40 edges
9. `Documentacao Tecnica do Sistema (Relatorio PFC)` - 40 edges
10. `StandardizedPatentMetadata` - 39 edges

## Surprising Connections (you probably didn't know these)
- `Combine keywords with CPC/IPC classification` --semantically_similar_to--> `Lens.org search strategy (trunked AND tetra AND radio, CPC h04w*)`  [INFERRED] [semantically similar]
  promptIA.md → notes/REPTEC_001_2023_TETRA.pdf
- `ChatService / chat_router.py (live orchestration: refine-topic, probe, final search, extract-terms)` --references--> `Research`  [AMBIGUOUS]
  ambinte.md → db/research_models.py
- `Finding: init_db() logs models_loaded=10 but 11 tables are actually created (stale/off-by-one log)` --references--> `init_db()`  [EXTRACTED]
  ambinte.md → db/init_db.py
- `init_db()` --references--> `ParamInit model (db/param_init_models.py)`  [EXTRACTED]
  db/init_db.py → ambinte.md
- `Old Pipeline: spaCy noun_chunks + TF-IDF + KeyBERT` --semantically_similar_to--> `TermExtractor.extract_and_rank_terms (legacy pipeline)`  [INFERRED] [semantically similar]
  TESTE_EXTRACAO_TERMOS_BM25F_RRF.md → EXTRACAO_TERMOS_NGRAMAS.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Current Term Extraction Pipeline (PatternRank + BM25F + KeyBERT + RRF + C-value)** — teste_extracao_termos_bm25f_rrf_patternrank, teste_extracao_termos_bm25f_rrf_bm25f, teste_extracao_termos_bm25f_rrf_rrf, teste_extracao_termos_bm25f_rrf_c_value, relatorio_tecnico_sistema_term_extraction_current, variaveis_de_configuracao_term_extraction_settings [EXTRACTED 1.00]
- **Query Complexity Guardrail (prompt constraint + analyzer + retry)** — config_prompts_probe_system_prompt_complexity_constraint, config_prompts_final_system_prompt_complexity_constraint, relatorio_tecnico_sistema_query_complexity_analyzer, relatorio_tecnico_sistema_complexity_retry_loop, variaveis_de_configuracao_relevance_complexity_settings [INFERRED 0.85]
- **Runtime Configuration in Database** — plano_migracao_config_banco_app_settings, plano_migracao_config_banco_search_api_selection, plano_migracao_config_banco_llm_call_site_bindings, plano_migracao_config_banco_llmconfigresolver, plano_migracao_config_banco_settings_setattr_sync, relatorio_tecnico_sistema_config_tables [INFERRED 0.85]
- **Report generation infrastructure (RAG, storage, LaTeX, review)** — docker_compose_ollama, docker_compose_chromadb, docker_compose_minio, docker_compose_latex_compiler, docker_compose_languagetool, notes_db_schema_atual_session_report [INFERRED 0.85]
- **Probe query results and extracted terms** — notes_db_schema_atual_session_probe_query, notes_db_schema_atual_probe_query_patent, notes_db_schema_atual_probe_query_article, notes_db_schema_atual_probe_query_term, notes_db_schema_atual_session_chart [EXTRACTED 1.00]
- **Editable LLM/search configuration** — notes_db_schema_atual_app_settings, notes_db_schema_atual_llm_provider_configs, notes_db_schema_atual_llm_call_site_bindings, notes_db_schema_atual_search_api_selection, notes_db_schema_atual_config_seed [EXTRACTED 1.00]
- **S-curve technology maturity analysis (GP/MP/SP)** — pfc_img_s_curve_madeo_technology_life_cycle, pfc_img_relatorio_2_gp_mp_sp_points, pfc_img_relatorio_2_extrapolacao_informacoes_cientificas, pfc_img_curva_s_sintetica_gpmpsp_logistic_fit [INFERRED 0.85]
- **Hexagonal architecture layers** — pfc_img_arquitetura_hexagonal_camadas_driving_adapters, pfc_img_arquitetura_hexagonal_camadas_servicos_nucleo, pfc_img_arquitetura_hexagonal_camadas_ports, pfc_img_arquitetura_hexagonal_camadas_dominio, pfc_img_arquitetura_hexagonal_camadas_driven_adapters [EXTRACTED 1.00]
- **Search module querying external APIs** — pfc_img_drawio_modulo_busca, pfc_img_drawio_ops_api, pfc_img_drawio_scopus_api, pfc_img_drawio_lens_api [EXTRACTED 1.00]
- **BPMN research-to-report pipeline** — pfc_img_fluxograma_geracao_parametros, pfc_img_fluxograma_busca_inicial, pfc_img_fluxograma_escolhe_termos, pfc_img_fluxograma_busca_final, pfc_img_fluxograma_gera_graficos, pfc_img_fluxograma_sintese_relatorio, pfc_img_fluxograma_edita_valida_relatorio [EXTRACTED 1.00]
- **Probe query to deduplicated results linkage** — pfc_img_modelo_dados_der_session_probe_query, pfc_img_modelo_dados_der_probe_query_article, pfc_img_modelo_dados_der_probe_query_patent, pfc_img_modelo_dados_der_article, pfc_img_modelo_dados_der_patent [EXTRACTED 1.00]
- **5-phase technology prospection pipeline with user validation** — pfc_img_pipeline_cinco_fases_fase1_refinamento_tema, pfc_img_pipeline_cinco_fases_fase2_busca_exploratoria, pfc_img_pipeline_cinco_fases_fase3_extracao_termos, pfc_img_pipeline_cinco_fases_fase4_busca_final, pfc_img_pipeline_cinco_fases_fase5_geracao_relatorio, pfc_img_pipeline_cinco_fases_validacao_usuario [EXTRACTED 1.00]
- **Local RAG: chunk, embed, store, retrieve, generate** — pfc_img_pipeline_rag_local_chunking, pfc_img_pipeline_rag_local_nomic_embed_text, pfc_img_pipeline_rag_local_recuperacao_top_k, pfc_img_pipeline_rag_local_qwen_2_5_ollama, pfc_img_pipeline_rag_local_secao_relatorio_gerada [EXTRACTED 1.00]
- **Session 1 Patent Report Figures** — gerados_session_1_patent_s_curve_patent_s_curve_chart, gerados_session_1_patent_top10_heatmap_top10_cpc_heatmap, gerados_session_1_patent_yearly_volume_patents_per_year_chart [INFERRED 0.85]
- **S-Curve Theory Applied to Patent Data** — config_report_assets_kucharavy_logistic_s_curve_model, config_report_assets_madeo_technology_life_cycle_s_curve, gerados_session_1_patent_s_curve_patent_s_curve_chart [INFERRED 0.85]
- **Documentation set covering the Sidebar/Chevron-Stepper redesign** — frontend_changelog, frontend_design_update, frontend_design_reference, frontend_bpmn_implementation [EXTRACTED 0.90]
- **BPMN 7-step flow orchestration (container, stepper, store, 7 step components)** — frontend_src_components_flow_flowcontainer_flowcontainer, frontend_src_components_flow_flowstepper_flowstepper, frontend_src_store_flowstore_useflowstore, frontend_src_components_flow_steps_initialparamsstep_initialparamsstep, frontend_src_components_flow_steps_specifyparamsstep_specifyparamsstep, frontend_src_components_flow_steps_searchresultsstep_searchresultsstep, frontend_src_components_flow_steps_queryrefinementstep_queryrefinementstep, frontend_src_components_flow_steps_finalsearchstep_finalsearchstep, frontend_src_components_flow_steps_chartsstep_chartsstep, frontend_src_components_flow_steps_reportstep_reportstep [EXTRACTED 0.90]
- **AGIA Frontend v1.0 Design Update Documentation Set** — frontend_release_notes, frontend_visual_changes, frontend_updates_summary [EXTRACTED 1.00]
- **Session-Centric Legacy Schema Tables (superseded design)** — notes_db_schema_session_centric_research_session, notes_db_schema_session_centric_session_input, notes_db_schema_session_centric_llm_candidate, notes_db_schema_session_centric_search_run, notes_db_schema_session_centric_patent_document, notes_db_schema_session_centric_scholarly_document, notes_db_schema_session_centric_session_metrics, notes_db_schema_session_centric_session_asset, notes_db_schema_session_centric_llm_token_usage [EXTRACTED 1.00]

## Communities (239 total, 27 thin omitted)

### Community 0 - "LLM Output Schema"
Cohesion: 0.05
Nodes (62): Config, LLMOutput, BaseModel, field_validator, Valida e filtra grupos vazios, convertendo dicts para TermGroup., Verifica se a consulta está vazia (sem grupos ou grupos sem termos)., Contrato para campos simples em consultas LLM. Representa consultas sobre…, Normaliza valores removendo duplicatas e vazios. (+54 more)

### Community 1 - "Probe/Final Query Frontend"
Cohesion: 0.06
Nodes (72): ProbeQuerySectionViewProps, formatYearRange(), ProbeResultsPanel(), ProbeResultsPanelProps, ProbeResultsStatTiles(), TermChecklistProps, ProbeApi, PANEL_ACCENT (+64 more)

### Community 2 - "Report Text Quality & Writer"
Cohesion: 0.05
Nodes (61): find_text_issues(), _fix_decimal(), fix_number_formatting(), _format_thousands(), Pós-processamento/validação do texto gerado pelo LLM pras seções do relatório -…, _convert_markdown_bold(), escape_latex(), _is_latin_renderable() (+53 more)

### Community 3 - "Legacy LLM Services"
Cohesion: 0.04
Nodes (45): Input contract schemas for prospecting requests., AnthropicLLMService, Any, Anthropic Claude LLM service implementation., Chama Claude e retorna JSON bruto parseado. Diferente de process_intake que…, Serviço LLM usando Anthropic Claude API. Integra com Claude para processar…, Constrói mensagem do usuário para Claude. Args: intake: Entrada do usuário.…, Faz chamada à API Claude. Args: system_prompt: Prompt do sistema. user_message:… (+37 more)

### Community 4 - "ChatService Orchestration"
Cohesion: 0.06
Nodes (28): ChatService, _get_qb_adapter(), Any, LLMRequest, LLMUsage, Agrega os ai_usage já calculados de N sub-chamadas independentes (ex: as N…, Uma requisição por ano cobrindo todo o intervalo pedido - usado quando o volume…, Pagina a query inteira em janelas sequenciais de 100 - 1-100, 101-200, ... -… (+20 more)

### Community 5 - "LLM Output Validators"
Cohesion: 0.05
Nodes (49): Enum, OperatorEnum, LLM output contract schemas with validation rules., Enumeração de operadores lógicos suportados., Config, Any, BaseModel, QueryBuilderOutput (+41 more)

### Community 6 - "UI Components & Steps"
Cohesion: 0.07
Nodes (48): Button(), ButtonProps, ButtonSize, ButtonVariant, SIZE_CLASSES, VARIANT_CLASSES, DocFaq(), FaqItem (+40 more)

### Community 7 - "Report Chart Routes"
Cohesion: 0.08
Nodes (60): generate_article_s_curve(), generate_patent_yearly_volume(), generate_session_graphics(), generate_top10_heatmap(), generate_top_entities(), generate_yearly_volume(), get_existing_chart(), Any (+52 more)

### Community 8 - "Settings UI"
Cohesion: 0.06
Nodes (50): ConfiguracoesTab(), TabId, TABS, ConfirmButton(), ConfirmButtonProps, InfoTooltip(), InfoTooltipProps, RangeSliderInput() (+42 more)

### Community 9 - "LLM Adapters & Domain Types"
Cohesion: 0.08
Nodes (28): AnthropicLLMAdapter, Any, output_to_response(), request_to_intake(), _textual(), GeminiLLMAdapter, Any, MockLLMAdapter (+20 more)

### Community 10 - "LaTeX Editor Frontend"
Cohesion: 0.06
Nodes (52): chartFigureSnippet(), errorMessage(), escapeLatex(), LATEX_ESCAPE_MAP, ReportDocumentEditor(), ReportDocumentEditorProps, ReviewIssueItem, ReviewPanel() (+44 more)

### Community 11 - "Report Document Router"
Cohesion: 0.07
Nodes (51): _bundle_filename(), _collect_image_keys(), _cover_image_exists(), _is_report_chart(), Endpoints do relatório de prospecção em LaTeX (padrão REPTEC/AGITEC - ver…, Só os gráficos do catálogo do relatório (FIGURE_SPECS) - ver report_figures.py…, Revisão do .tex do editor: problemas de LaTeX (documento todo) e sugestões de…, REPTEC_001_2026.zip" quando a capa já foi montada (número/ano em… (+43 more)

### Community 12 - "Logging & Health"
Cohesion: 0.07
Nodes (32): Health check endpoint for application status verification., Request logging middleware for tracking HTTP requests with structured logging., Endpoint for creating a prospecting session's input parameters. Unlike the old…, shutdown_container(), Validação de códigos IPC/CPC gerados pela IA - rede de segurança contra…, Montagem do .tex do relatório e compilação de PDF sob demanda. Duas…, ensure_static_figures_uploaded(), Figuras fixas da Metodologia do relatório REPTEC/AGITEC (5.3 - estágios do… (+24 more)

### Community 13 - "Dashboard Charts"
Cohesion: 0.09
Nodes (41): ChartAxisGrid(), ChartAxisGridProps, ChartCard(), ChartCardProps, buildNiceTicks(), niceStep(), roundedTopBarPath(), ChartTooltip() (+33 more)

### Community 14 - "Report Assembly"
Cohesion: 0.11
Nodes (48): _assemble_document(), assemble_report_tex(), _attachments_prefix(), build_static_sections(), compile_report_pdf(), compute_section_rag_context(), delete_report_attachment(), _detect_databases_used() (+40 more)

### Community 15 - "CPC Titles & Citations"
Cohesion: 0.08
Nodes (42): describe_code(), describe_codes(), Significado oficial das classificações CPC/IPC usadas no relatório -…, Título oficial de um código de subclasse (ex.: "H02S"). Subclasses extintas nas…, _titles(), _abnt_author(), build_citation(), build_reference() (+34 more)

### Community 16 - "Wizard Steps & Session Services"
Cohesion: 0.07
Nodes (40): steps, StepsBar(), stepsData, Fonte, withExistingCheck(), SCurveKind, mapResult(), mapTop10Block() (+32 more)

### Community 17 - "App Shell & Modals"
Cohesion: 0.08
Nodes (29): frontend/index.html — App Entry Point, App(), Modal(), ModalInputProps, ModalProps, docTopics, Navbar(), ReportImagesToggleButton() (+21 more)

### Community 18 - "LaTeX Static Sections"
Cohesion: 0.07
Nodes (38): _attachment_filename(), _format_count_pt(), _quadro_busca_cell(), Nome seguro pro \\includegraphics: "anexo-<slug>.<ext>" (só [a-z0-9-], sem…, 1800 -> "1.800" (separador de milhar pt-BR)., Conteúdo (já escapado) de uma célula do Quadro de estratégias de busca -…, Any, Template LaTeX do relatório REPTEC/AGITEC (ver notes/REPTEC_001_2023_TETRA.pdf… (+30 more)

### Community 19 - "Chart Rendering Service"
Cohesion: 0.08
Nodes (24): Any, Gera os PNGs de report (curva S, top entidades, distribuições) para uma sessão., Baixa os bytes de um PNG já persistido no storage (ver SessionChart.object_key)…, Codifica `png_bytes` em base64 e tenta subir pro storage numa chave…, Gera todos os gráficos aplicáveis (pula os que não têm dado o suficiente) e…, Contagem por ano, reindexada no range completo (anos sem publicação entram como…, Implementação compartilhada de generate_patent_s_curve e…, Ajusta e desenha a curva S (Fisher-Pry) de patentes a partir de uma contagem… (+16 more)

### Community 20 - "Input Intake Schema"
Cohesion: 0.06
Nodes (30): Config, InputIntake, BaseModel, field_validator, Contrato de entrada inicial para requisições de prospecção. Define os…, Configuração do Pydantic., Valida e normaliza o tema., Valida e normaliza a descrição. (+22 more)

### Community 21 - "Research Session Persistence"
Cohesion: 0.10
Nodes (39): Endpoint for searching/listing research sessions by their session_input theme., article_to_raw_item(), build_article_fields(), build_patent_fields(), patent_to_raw_item(), Any, AsyncSession, Mapeia os dicts crus de resultado de probe search (OPS/Scopus, como devolvidos… (+31 more)

### Community 22 - "Legacy Schema & Alembic"
Cohesion: 0.06
Nodes (32): Converte a DATABASE_URL (asyncpg, usada em runtime) pra um driver síncrono, já…, Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online(), _sync_database_url(), ambinte.md — Live DB Analysis Report, Finding: param_init is the only genuinely active DB table (Step1 draft persistence) (+24 more)

### Community 23 - "Term Extraction Pipeline"
Cohesion: 0.08
Nodes (22): get_term_extractor(), Any, Extract and rank relevant terms from enriched search results. Uses spaCy +…, Devolve uma instância compartilhada de TermExtractor, criada na primeira…, Load spaCy model + PatternRank keyphrase vectorizer., Load POS patterns (bad bigrams/trigrams) from config., Load string quality filter rules (boundary stopwords, structural words)., Clean text: lowercase, remove URLs, normalize hyphens, extra spaces. Args:… (+14 more)

### Community 24 - "Session Input Persistence"
Cohesion: 0.11
Nodes (36): apply_generated_fields(), apply_probe_query_fields(), apply_root_fields(), _get_or_create_probe_query(), persist_session_input(), AsyncSession, Shared persistence logic for creating or updating a research_session and its…, Upsert de root/generated/probe_queries em `research_session` (nova ou… (+28 more)

### Community 25 - "LLM JSON Repair & Group Limits"
Cohesion: 0.07
Nodes (27): enforce_final_query_group_limits(), enforce_group_limit(), LLMResponse, Achata o número de grupos de conceito em TITLE/ABSTRACT para o teto permitido…, Funde grupos excedentes de `field` num único grupo OR final, até respeitar…, Aplica enforce_group_limit em TITLE/ABSTRACT de `llm_response` in-place,…, LLMJSONParseError, parse_llm_json() (+19 more)

### Community 26 - "Legacy BPMN Frontend Docs"
Cohesion: 0.07
Nodes (39): 7-Step BPMN Flow Pattern (params -> specify -> search -> refine -> final search -> charts -> report), BPMN_IMPLEMENTATION.md — 7-Step BPMN Flow / API Integration Doc, CHANGELOG.md — Design Update v1.0, DESIGN_REFERENCE.md — Quick Design Reference Guide, Design Color Palette (#07345f dark blue sidebar, #0ea5e9 sky blue active, #22c55e green primary, #eab308 yellow secondary), DESIGN_UPDATE.md — Sidebar/Stepper Redesign Summary, Sidebar + Chevron Stepper Redesign (7-circle stepper -> 4-step chevron, centered layout -> sidebar layout), FIGMA_DESIGN_PROMPT.md — Full Figma Design Brief (+31 more)

### Community 27 - "Query Builder Base"
Cohesion: 0.07
Nodes (25): BaseQueryBuilder, ABC, Any, Base abstract class for query builders., Interface abstrata para construtores de consultas API. Define contrato que…, Inicializa o construtor de consultas. Args: api_name: Nome da API (lens_patent,…, TITLE e ABSTRACT são combinados com OR em todo modo/variante, MENOS na variante…, Constrói consulta específica da API a partir de saída LLM. Args: llm_output:… (+17 more)

### Community 28 - "RAG Service & Vector Port"
Cohesion: 0.08
Nodes (19): Any, Protocol, VectorStorePort, Any, RAGService, Remove só os chunks que casam com `filter_metadata` (ex.: de uma `session_id`…, RAG (Retrieval-Augmented Generation) usando VectorStorePort. Responsável por…, asyncio (+11 more)

### Community 29 - "Deduplication"
Cohesion: 0.09
Nodes (17): DedupService, Any, Deduplicação de documentos usando chaves primárias com fallback para título…, Inicializa o serviço de normalização., Tests for deduplication service., Verifica normalização de texto para dedup., Verifica deduplicação de patentes., Verifica que primary key é publication_number. (+9 more)

### Community 30 - "Legacy Ollama RAG"
Cohesion: 0.06
Nodes (20): OllamaService, Generate text with provided context. Args: prompt: Main prompt context: Context…, Generate embedding for text using Ollama. Args: text: Input text model: Model…, Service for interacting with local Ollama instance., Generate embeddings for multiple texts. Args: texts: List of texts model: Model…, Async context manager entry., Async context manager exit., Initialize Ollama service. Args: base_url: Ollama server URL text_model: Model… (+12 more)

### Community 31 - "Query Field Extractor"
Cohesion: 0.10
Nodes (32): Reconstrói um schemas.llm.LLMOutput a partir dos campos estruturados…, Dá o query builder "cru" (não o adapter) pra reconstrução síncrona (sem LLM) -…, _append(), extract_fields_from_query(), _extract_ops(), _extract_scopus(), _matching_paren(), Extração dos campos estruturados (title/abstract/ipc/field_of_study) de volta a… (+24 more)

### Community 32 - "Legacy Document Repositories"
Cohesion: 0.09
Nodes (19): DedupRegistryAdapter, PatentDedupRegistry, PatentDocument, Base, Database models for scholarly documents, patents, and deduplication registries., Modelo de publicação acadêmica no banco de dados. Armazena publicações…, Registro de deduplicação para publicações acadêmicas. Rastreia dedup_keys e…, Registro de deduplicação para patentes. Rastreia dedup_keys e fontes para… (+11 more)

### Community 33 - "Metadata Normalization"
Cohesion: 0.11
Nodes (22): NormalizationService, Any, Serviço de normalização de metadados. Absorve diferenças entre APIs,…, Normaliza documento Lens Patent API. Args: data: Resposta da Lens Patent API.…, Normaliza documento Lens Scholarly API. Args: data: Resposta da Lens Scholarly…, Normaliza documento OPS (European Patent Office) API. Mapeia estrutura OPS para…, Normaliza documento Scopus API. Mapeia estrutura Scopus para formato padrão.…, Normaliza metadados genéricos de patente para formato padrão. Args: data: Dados… (+14 more)

### Community 34 - "Config Router"
Cohesion: 0.18
Nodes (31): _cover_image_response(), create_llm_config(), delete_llm_config(), delete_report_cover_image(), get_report_cover_image(), list_call_sites(), list_llm_configs(), list_llm_providers() (+23 more)

### Community 35 - "Candidate Picker UI"
Cohesion: 0.10
Nodes (24): CandidatePickerLayout(), CandidatePickerLayoutProps, parseCsv(), selectableCardClass(), toCsv(), FieldCard(), FieldCardProps, FloatingLabelInput() (+16 more)

### Community 36 - "Config Models & Seeds"
Cohesion: 0.14
Nodes (28): AppSetting, LLMCallSiteBinding, LLMProviderConfig, Base, datetime, Modelos de configuração editável em runtime (settings genéricos, seleção de API…, Qual LLMProviderConfig cada chamada de IA do programa usa hoje. `call_site` é…, Um escalar configurável (threshold, top_k, peso, flag booleana...) - espelha os… (+20 more)

### Community 37 - "Scopus Query Builder"
Cohesion: 0.08
Nodes (17): Any, LLMResponse, ScopusQueryBuilderAdapter, Any, Constrói parte textual de query Scopus. Args: field: Campo textual estruturado.…, Constrói parte simples de query Scopus. Args: field: Campo simples com lista de…, Construtor de consultas para Scopus API. Transforma saída normalizada do LLM em…, Constrói a cláusula SUBJAREA a partir do field_of_study gerado pela LLM.… (+9 more)

### Community 38 - "Session Chart Model"
Cohesion: 0.12
Nodes (22): PNG de report (curva S, e futuramente top entidades/distribuições) gerado a…, SessionChart, field_validator, Input original do usuário (Step1), raiz da cadeia de session_input., Payload enviado ao salvar/atualizar uma sessão: nome + input raiz + gerado…, SessionInputRoot, SessionInputSaveRequest, _create_empty_session() (+14 more)

### Community 39 - "Statistical Inference API"
Cohesion: 0.09
Nodes (24): infer_final_search(), post, Request, SuccessResponse, Endpoint de inferência estatística: enriquece o compilado de uma busca final…, _svc(), Any, Loop principal: pede iterações extras de run_final_search (iteration 1, 2,… (+16 more)

### Community 40 - "Report Generation Form"
Cohesion: 0.11
Nodes (26): AiSectionState, EMPTY_SIGNATURE_LIST, ReportGeneration(), ReportGenerationProps, SectionRunStatus, SignatureListEditor(), StaticSectionState, STATUS_CLASSES (+18 more)

### Community 41 - "OPS Query Builder"
Cohesion: 0.09
Nodes (16): OPSQueryBuilderAdapter, Any, LLMResponse, OPSQueryBuilder, Any, Constrói cláusula CQL para campo textual. Cada termo vira um predicado…, Construtor de consultas para OPS (European Patent Office) API. Transforma saída…, Constrói cláusula CQL para campo simples. Cada valor vira um predicado… (+8 more)

### Community 42 - "Lens Patent Query Builder"
Cohesion: 0.08
Nodes (17): LensPatentQueryBuilderAdapter, Any, LLMResponse, LensPatentQueryBuilder, Any, Query builder para Lens Patent API com sintaxe query_string. Gera queries…, Constrói partes da query_string com sintaxe booleana. Estratégia: - Title e…, Constrói parte de query_string para campo textual. Formato: field:(term1 OR… (+9 more)

### Community 43 - "Query Prompt Rules"
Cohesion: 0.09
Nodes (29): Ambiguity Check, Query Complexity Constraint (<= 0.6), Final System Prompt, Document Type Guidance (PATENT / SCHOLARLY mode), Field Guidelines: Group Count Drives AND Count, Probe-discovered Classification Codes Only, Reasoning Step Before JSON, Search Variant Guidance (SPECIFIC/BALANCED/GENERIC) (+21 more)

### Community 44 - "Legacy N-gram Term Pipeline"
Cohesion: 0.08
Nodes (29): Boundary Token/POS Segmentation (_split_by_boundaries), ChatService.extract_terms, _clean_text Normalization, Dead config: term_extraction_mmr_lambda/similarity_threshold, Pipeline de Extracao e Pontuacao de Termos (N-gramas), KeyBERT Scoring (restricted + fallback pass), KeywordService (keyword_service.py, unconnected), Language Filter (language_filter.py) (+21 more)

### Community 45 - "Scopus Final Search Tests"
Cohesion: 0.17
Nodes (21): _base_query(), FakeGenericAdapter, FakeScopusAdapter, _FlakyYearAdapter, _item(), asyncio, SearchResult, Adapter fake pro Scopus - simula count()/fetch_results_page() sem rede,… (+13 more)

### Community 46 - "Lens Scholarly Query Builder"
Cohesion: 0.10
Nodes (15): LensScholarlyQueryBuilderAdapter, Any, LLMResponse, LensScholarlyQueryBuilder, Any, Constrói cláusula booleana para campo textual. Args: field: Campo textual…, Construtor de consultas para Lens Scholarly API. Transforma saída normalizada…, Constrói cláusula booleana para campo simples. Args: field: Campo simples com… (+7 more)

### Community 47 - "Patent Repository Adapter"
Cohesion: 0.15
Nodes (9): patent_doc_to_metadata(), PatentDocument, PatentRepositoryAdapter, PatentRepositoryPort, Normalized metadata schemas for standardized document representation., Estrutura padronizada de metadados de patente. Absorve diferenças entre…, StandardizedPatentMetadata, Metadata normalization service for standardizing document metadata. (+1 more)

### Community 48 - "Technical Report Overview"
Cohesion: 0.12
Nodes (27): Docker Compose Services (postgres, pgadmin, minio, ollama, chromadb, latex-compiler), API Routes (/chat, /research-session, /report, /inference, /config), Chao1 + Bootstrap Statistical Inference, ChatService (flow orchestration), ChromaDB RAG (VectorStorePort, HttpClient), Explicit Confirmations as Audit Mechanism, Documentacao Tecnica do Sistema (Relatorio PFC), End-to-end Data Flow (+19 more)

### Community 49 - "Document & Search Schemas"
Cohesion: 0.16
Nodes (25): Config, DocumentBatch, DocumentMetadata, PatentDocument, PublicationDocument, BaseModel, Document and patent record schemas., Metadados comuns para todos os tipos de documentos. Armazena informações de… (+17 more)

### Community 50 - "Inference Service Tests"
Cohesion: 0.21
Nodes (21): FakeChatService, FakeEmbeddingAdapter, _ops_result(), Any, asyncio, Fila de respostas de run_final_search, uma por chamada (iteration 1, 2, ...)., Vetores constantes - qualquer texto vira o mesmo vetor, cosseno sempre 1.0., _scopus_result() (+13 more)

### Community 51 - "LLM Config Repository"
Cohesion: 0.16
Nodes (6): _llm_config_to_domain(), LLMConfigRepositoryAdapter, LLMCallSiteBindingData, LLMProviderConfigData, LLMConfigRepositoryPort, LLMProviderConfig

### Community 52 - "Chat Router"
Cohesion: 0.44
Nodes (24): analyze_query(), build_final_query_variant(), build_probe_queries_multi(), check_ops_token(), extract_terms(), get_available_apis(), get_available_models(), get_current_provider() (+16 more)

### Community 53 - "Prompt Loader"
Cohesion: 0.10
Nodes (18): Prompt services package for managing LLM prompts., PromptLoader, Limpa cache de prompts. Útil para recarregar prompts atualizados sem reiniciar…, Obtém dicionário de prompts em cache. Returns: Dicionário com prompts…, Carrega prompts do sistema de arquivo. Gerencia templates de prompts para…, Carrega prompt do sistema para modo probe. Lê arquivo probe_system_prompt.txt…, Carrega prompt do sistema para refinamento de tópicos. Lê arquivo…, Carrega um prompt customizado pelo nome de arquivo. Args: filename: Nome do… (+10 more)

### Community 54 - "Gemini Service"
Cohesion: 0.12
Nodes (14): GeminiLLMService, Any, InputIntake, LLMUsage, Chama Gemini e retorna JSON bruto parseado. Diferente de process_intake que…, Serviço LLM usando Google Gemini API. Integra com Google Gemini para processar…, Constrói mensagem do usuário para Gemini. Args: intake: Entrada do usuário.…, Faz chamada à API Gemini de forma assíncrona. Args: system_prompt: Prompt do… (+6 more)

### Community 55 - "ChromaDB Adapter"
Cohesion: 0.12
Nodes (10): ChromaVectorStoreAdapter, _EmbeddingPortFunction, Any, Adapta EmbeddingPort (sentence-transformers, já usado pelo KeyBERT) pro…, Implementa VectorStorePort contra um container ChromaDB (HttpClient) - não…, EmbeddingFunction, EmbeddingPort, FakeEmbeddingPort (+2 more)

### Community 56 - "Scopus Final Aggregation"
Cohesion: 0.10
Nodes (12): A Scopus Search API não devolve abstract (dc:description) pra essa API key -…, Recorta [year_from, year_to] em faixas com peso decrescente conforme a idade.…, Converte os pesos das faixas em nº de itens, garantindo que a soma bata com…, Substitui a cláusula `(pd within "...")` da CQL original pelo intervalo da…, Substitui a cláusula `(PUBYEAR > X AND PUBYEAR < Y)` da query original pelo…, O OPS não tem nenhum critério de relevância/ordenação na busca (ver…, Mesma ideia de _run_ops_year_diversified_search, mas pro Scopus: a ordenação…, Agrega os itens BRUTOS da Scopus (dc:title/affiliation/... - ver docstring de… (+4 more)

### Community 57 - "Report Figure Catalog"
Cohesion: 0.18
Nodes (19): CatalogEntry, figure_latex(), FigureSpec, _fix_figure_word(), place_figures(), Figuras/quadros dos Resultados do relatório REPTEC (6.1-6.3) - catálogo e…, O LLM às vezes chama um Quadro de "Figura" (e vice-versa): a palavra antes do…, Troca `[[REF:id]]` por `\\ref{...}` e `[[FIG:id]]` pelo bloco LaTeX da figura;… (+11 more)

### Community 58 - "Chao1 & Bootstrap"
Cohesion: 0.16
Nodes (22): bootstrap_topk_stability(), chao1_diagnostics(), chao1_estimate(), is_sample_insufficient(), Any, Estimador Chao1 (riqueza de espécies) e bootstrap de estabilidade de ranking -…, Estabilidade do ranking top-`top_k`: reamostra a distribuição observada (com…, Riqueza estimada (S_chao1) - fórmula bias-corrected de Chao1 (Chao, 1987; a… (+14 more)

### Community 59 - "Hexagonal Architecture Diagram"
Cohesion: 0.09
Nodes (24): Arquitetura Hexagonal (Ports & Adapters) diagram, Dependency Inversion Principle, Dominio (pure data types, no I/O), Adaptadores Driven (Anthropic, Gemini, OPS, Scopus clients), Adaptadores Driving (Rotas HTTP FastAPI), Ports (LLM, patent search, article search, repository), Servicos (nucleo): orquestracao, geracao de graficos, analise de complexidade, Cronograma (project Gantt schedule) (+16 more)

### Community 60 - "Field Schema Service"
Cohesion: 0.11
Nodes (13): FieldSchemaService, Retorna dicionário {field_name: field_type} para busca PROBE. Retorna APENAS…, Retorna lista de campos para busca final/exploratória. Inclui campos de TODAS…, Retorna dicionário {field_name: field_type} para busca FINAL. Returns: Dict com…, Gerencia esquemas de campos para diferentes APIs e modos de busca. Carrega…, Filtra campos que contêm alguma das APIs especificadas. Retorna a lista de…, Filtra campos com seus tipos (textual/simple). Retorna dicionário {field_name:…, Constrói contrato LLM output para uma API específica. DEPRECADO: Use… (+5 more)

### Community 61 - "Report Service Tests"
Cohesion: 0.19
Nodes (23): _articles(), _patents(), _patents_by_year_from(), asyncio, Fonte ausente de `probe_query_ids` (ex.: sessão sem query final de artigo) não…, test_article_s_curve_requires_at_least_two_distinct_years(), test_download_chart_returns_uploaded_bytes(), test_generate_patent_s_curve_from_yearly_counts() (+15 more)

### Community 62 - "Settings Sync"
Cohesion: 0.18
Nodes (7): AppSettingValue, SearchApiSelectionData, AppSettingsRepositoryPort, Protocol, SearchApiSelectionRepositoryPort, Sincroniza app_settings (banco) com o singleton `core.config.settings`…, SettingsSyncService

### Community 63 - "MinIO Storage"
Cohesion: 0.11
Nodes (8): MinioStorageAdapter, build_container(), Any, Instancia todos os singletons (app-scoped) e retorna o container. Lê…, Object storage services package for external storage integrations., MinioService, Storage service for MinIO (S3-compatible object storage) - wraps the…, Cliente síncrono do MinIO - upload/download/delete de objetos e garantia de…

### Community 64 - "TS App Config"
Cohesion: 0.09
Nodes (22): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+14 more)

### Community 65 - "Scopus Search Service"
Cohesion: 0.14
Nodes (13): Any, SearchResult, Executa busca de uma página com retry. Args: query_params: Parâmetros de query.…, Requisição leve (count=1) só pra ler opensearch:totalResults, sem paginar -…, Busca UMA página de até _FINAL_SEARCH_PAGE_SIZE resultados da busca final -…, Verifica se deve continuar paginação baseado em relevância. Heurística simples:…, Constrói headers para requisição Scopus. Returns: Dicionário com headers HTTP., Serviço de busca na API Scopus com suporte a paginação. Gerencia requisições e… (+5 more)

### Community 66 - "LaTeX Review (pure)"
Cohesion: 0.19
Nodes (21): _body_start(), _brace_group_end(), _check_braces(), _check_environments(), _check_special_chars(), _figure_calls(), _iter_lines(), LatexIssue (+13 more)

### Community 67 - "OpenAI-compatible Text Generation"
Cohesion: 0.15
Nodes (10): OpenAICompatibleAdapter, Implementa TextGenerationPort contra qualquer endpoint compatível com a API de…, _AnthropicTextGenerationAdapter, build_text_generation_port(), _GeminiTextGenerationAdapter, Registry equivalente a provider_registry.py, mas pro call site "report_writing"…, Protocol, Geração de texto livre a partir de um prompt - usado pelo ReportWriterService… (+2 more)

### Community 68 - "Scholarly Repository Adapter"
Cohesion: 0.17
Nodes (8): scholarly_doc_to_metadata(), ScholarlyRepositoryAdapter, ScholarlyRepositoryPort, Config, BaseModel, Configuração do Pydantic., Estrutura padronizada de metadados de publicação acadêmica. Absorve diferenças…, StandardizedScholarlyMetadata

### Community 69 - "Legacy Repositories"
Cohesion: 0.10
Nodes (10): AsyncSession, Obtém documento por DOI. Args: doi: Digital Object Identifier. Returns:…, Verifica se dedup_key já existe. Args: dedup_key: Chave de dedup. Returns: True…, Atualiza documento existente. Args: dedup_key: Chave do documento. metadata:…, Obtém documentos por fonte e ano. Args: source: Fonte (scopus, lens_scholarly,…, Repositório para operações de publicações acadêmicas. Fornece interface CRUD…, Inicializa o repositório. Args: session: Sessão assíncrona do SQLAlchemy., Cria novo registro de publicação. Args: metadata: Metadados normalizados.… (+2 more)

### Community 70 - "Report Lifecycle Stage"
Cohesion: 0.16
Nodes (20): build_lifecycle(), complete_years_only(), last_complete_year(), lifecycle_stage(), _pt(), Any, Resumos numéricos dos gráficos do relatório e estágio do ciclo de vida da…, Resumo em pt-BR pro prompt (números já no formato brasileiro). (+12 more)

### Community 71 - "TS Node Config"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+12 more)

### Community 72 - "Config-in-DB Migration Plan"
Cohesion: 0.14
Nodes (21): Alembic Migration + Seed, app_settings Table (key-value), Chicken-and-egg Infra Exclusion (DATABASE_URL, MinIO, Chroma...), /api/v1/config Endpoints, ConfiguracoesTab.tsx / Step3.tsx, container.py (build_container), Plano: Migracao de Configuracao pro Banco, llm_call_site_bindings Table (+13 more)

### Community 73 - "App Settings Repository"
Cohesion: 0.18
Nodes (14): AppSettingsRepositoryAdapter, AsyncSession, SearchApiSelectionRepositoryAdapter, _setting_to_domain(), LLMConfigRequest, BaseModel, ReportCoverImageResponse, UpdateCallSiteRequest (+6 more)

### Community 74 - "OPS Search Adapter"
Cohesion: 0.14
Nodes (9): OPSAdapter, Any, SearchResult, OPSService, Fecha clientes httpx (síncrono e assíncrono)., Context manager entry., Context manager exit., Serviço de busca na API European Patent Office (OPS). Gerencia autenticação… (+1 more)

### Community 75 - "Storage Port"
Cohesion: 0.15
Nodes (6): Protocol, StoragePort, Any, Baixa só os PNGs que já existem no MinIO (`chart_object_keys`, resolvidos pelo…, Só chamado por POST /report/{session_id}/compile-pdf, nunca automaticamente.…, ReportLatexService

### Community 76 - "AI Review Parsing"
Cohesion: 0.16
Nodes (13): _parse_corrections(), Any, JSON da IA, tolerante a texto em volta e a pequenos erros de formato., _FakeGenerator, _FakeResolver, _languagetool_transport(), asyncio, LanguageTool fake: marca cada palavra de `matches_for` (palavra ->… (+5 more)

### Community 77 - "Inference Enrichment Loop"
Cohesion: 0.15
Nodes (15): _merge_counts(), Enriquece iterativamente a amostra de uma busca final (OPS ou Scopus) até ela…, Soma duas contagens por chave exata (Counter-style), sem depender de…, fuzzy_group_names(), Agrupamento fuzzy de nomes de entidade (depositantes de patente, instituições…, Funde nomes de entidade que provavelmente são a mesma (variação de…, filter_english_abstracts(), is_non_english_abstract() (+7 more)

### Community 78 - "Frontend Dependencies"
Cohesion: 0.11
Nodes (19): autoprefixer, axios, dependencies, autoprefixer, axios, lucide-react, @material/web, @monaco-editor/react (+11 more)

### Community 79 - "add2 cluster"
Cohesion: 0.15
Nodes (19): llm_candidate rationale — stores each LLM-generated search strategy, is_chosen flag, llm_token_usage rationale — granular per-call LLM token/cost/latency log, separated from llm_candidate, patent_document rationale — denormalized patent results, passed_filter via embedding relevance, research_session rationale — central object of a prospecção session, scholarly_document rationale — same role as patent_document for articles, search_run rationale — each external API search execution, linked to llm_candidate_id, session_asset rationale — references to generated files (charts, figures, embedding indices), session_input rationale — snapshot of user parameters, kept separate to preserve initial state (+11 more)

### Community 80 - "lens service cluster"
Cohesion: 0.15
Nodes (11): LensService, Any, SearchResult, Serviço de busca na API Google Lens. Gerencia requisições para Lens Patents e…, Constrói headers para requisição Lens. Returns: Dicionário com headers HTTP., Context manager entry., Context manager exit., Inicializa o serviço Lens. Args: api_token: Token de API do Lens (se None,… (+3 more)

### Community 81 - "research session cluster"
Cohesion: 0.16
Nodes (18): delete_session(), get_session(), AsyncSession, delete, get, put, Request, SuccessResponse (+10 more)

### Community 82 - "chart labels cluster"
Cohesion: 0.20
Nodes (16): abbreviate_label(), abbreviate_labels(), _abbreviate_words(), _drop_stopwords(), _match_case(), Rótulos dos gráficos de ranking (top depositantes/instituições) - nomes muito…, Nomes da OPS vêm em MAIÚSCULAS - a abreviação acompanha., Nome com até `max_length` caracteres - intacto se já couber. (+8 more)

### Community 83 - "relevance service cluster"
Cohesion: 0.16
Nodes (11): Any, ndarray, Computa score de relevância entre tema e documento. Usa similaridade de cosseno…, Computa similaridade de cosseno manualmente. Fallback se sklearn não…, Computa scores de relevância para múltiplos documentos. Args: theme: Tema/query…, Filtra documentos por relevância. Separa documentos em aprovados (score >=…, Converte para dicionário. Returns: Dicionário com dados do score., Filtra múltiplos lotes de documentos. Útil para processar resultados de… (+3 more)

### Community 84 - "report visualizations cluster"
Cohesion: 0.14
Nodes (12): _find_year_for_value(), Any, ndarray, Report Visualization Functions for Technology Prospecting. Generates various…, Generates historical deposit/publication timeline. Shows evolution of research…, Generates visualizations for technology prospecting reports., Generates top applicants (patents) or authors (articles). Args: documents: List…, Generates S-curve (technology lifecycle curve) from document data. Shows… (+4 more)

### Community 85 - "ops token manager cluster"
Cohesion: 0.12
Nodes (10): OPSToken, OPSTokenManager, Gerenciador centralizado de token OAuth2 do OPS. Mantém um token compartilhado…, Obtém novo token OAuth2 do OPS. Returns: Tupla (sucesso, mensagem_erro). Se…, Representa um token OAuth2 do OPS com informações de expiração., Inicializa com token de acesso. Args: access_token: Token de acesso OAuth2.…, Verifica se token está expirado com margem de 60 segundos., Retorna dict com informações do token. (+2 more)

### Community 86 - "repositories cluster"
Cohesion: 0.15
Nodes (10): AsyncSession, Inicializa o serviço de persistência. Args: session: Sessão assíncrona do…, PatentDocumentRepository, PatentDocument, Repositório para operações de patentes. Fornece interface CRUD para…, Cria novo registro de patente. Args: metadata: Metadados normalizados. Returns:…, Obtém patente por chave de deduplicação. Args: dedup_key: Chave de dedup.…, Obtém patente por número de publicação. Args: publication_number: Número de… (+2 more)

### Community 87 - "base cluster"
Cohesion: 0.21
Nodes (11): SearchResult, to_domain(), SearchResult, _ServiceResult, Base class for search services., Resultado de uma busca em API externa. Encapsula dados de sucesso ou erro de…, Informações estruturadas sobre erro em busca. Proporciona detalhes padronizados…, SearchError (+3 more)

### Community 88 - "test report review cluster"
Cohesion: 0.24
Nodes (16): _protected_tokens(), Posição de `original` em `fragment` se a correção for aceitável; None se não…, validate_ai_suggestion(), _doc(), _messages(), _report(), _scoped_text(), test_ai_suggestion_must_only_change_words() (+8 more)

### Community 89 - "s curve cluster"
Cohesion: 0.18
Nodes (15): Report chart generation for a research session's final-search documents. Pure…, fit_s_curve(), logistic(), project_s_curve(), Any, RuntimeError, Ajuste do modelo de crescimento logístico de Fisher-Pry sobre a série temporal…, Ajusta o modelo logístico de Fisher-Pry a uma série de contagens anuais (NÃO… (+7 more)

### Community 90 - "docker-compose cluster"
Cohesion: 0.16
Nodes (17): ChromaDB vector store service, LanguageTool review service, LaTeX compiler service (TeX Live minimal), MinIO object storage service, Ollama local LLM service, pfc_network bridge network, pgAdmin service, PostgreSQL service (pfc_postgres) (+9 more)

### Community 91 - "package cluster"
Cohesion: 0.12
Nodes (17): eslint, eslint-plugin-react-hooks, eslint-plugin-react-refresh, devDependencies, eslint, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals (+9 more)

### Community 92 - "response cluster"
Cohesion: 0.19
Nodes (16): Config, ErrorDetail, ErrorResponse, HealthCheckResponse, PaginatedResponse, PaginationInfo, BaseModel, Standard API response schemas for consistent response formatting. (+8 more)

### Community 93 - "persistence service cluster"
Cohesion: 0.16
Nodes (11): Database and persistence services package., PersistenceService, Any, Persistence service for storing normalized and filtered documents. Orchestrates…, Persiste patente normalizada e filtrada. Assume que documento já foi: -…, Persiste lote de publicações. Args: metadata_list: Lista de metadados…, # TODO: Decidir estratégia final de commit:, Serviço de persistência de documentos. Aceita documentos já filtrados,… (+3 more)

### Community 94 - "test chat service ops final search cluster"
Cohesion: 0.32
Nodes (13): _base_query(), FakeOpsAdapter, _item(), asyncio, SearchResult, Adapter fake pra OPS - simula search()/fetch_biblio_page() sem rede.…, _svc(), test_run_final_search_ops_returns_aggregated_shape_with_strategy() (+5 more)

### Community 95 - "test chat service depositants cluster"
Cohesion: 0.17
Nodes (12): BaseSettings, field_validator, Aplicação de configurações usando Pydantic Settings. Carrega variáveis de…, Parse allowed_origins from comma-separated string or list. Args: v: Environment…, Retorna a URL completa do servidor., Settings, _svc(), test_aggregate_ops_final_items_groups_depositants_and_cpc() (+4 more)

### Community 96 - "SessionCard cluster"
Cohesion: 0.17
Nodes (11): SCurveFitLegend(), SCurveReliabilityWarning(), formatDate(), InputBlockType, SCurveChartBlock(), SessionCard(), SCurveSection(), useFinalSCurve() (+3 more)

### Community 97 - "ops service cluster"
Cohesion: 0.21
Nodes (9): Any, SearchResult, Executa busca de UMA página no endpoint /search/biblio com retry logic. Este…, Executa busca em OPS com CQL. Args: query: Query dict com 'query' (CQL string)…, Executa busca em OPS usando endpoint /search/biblio que já retorna dados…, Substitui (ou adiciona) a cláusula `(pd within "...")` da CQL pelo intervalo de…, Busca UMA página no endpoint /search/biblio, opcionalmente restrita a um…, Garante que token OAuth2 válido está disponível. Usa token manager centralizado… (+1 more)

### Community 98 - "session cluster"
Cohesion: 0.16
Nodes (9): DatabaseSession, AsyncSession, Mascara senha na URL para logging. Args: url: URL de banco de dados. Returns:…, Gerenciador de sessão de banco de dados. Configura engine, pool de conexões e…, Inicializa o gerenciador de sessão., Inicializa engine e session factory. Configura pool de conexões baseado em…, Fecha engine e conexões., Fornece sessão de banco de dados como context manager. Yield: AsyncSession para… (+1 more)

### Community 99 - "VARIAVEIS DE CONFIGURACAO cluster"
Cohesion: 0.15
Nodes (15): TF-IDF Scoring (TfidfVectorizer), BM25F (Robertson/Zaragoza, pure Python), Decision: No Real Elasticsearch, Reciprocal Rank Fusion (2 stages, k=60), Unigram Noise Trade-off (rank-based fusion), DEPOSITANT_FUZZY_MATCH_THRESHOLD (RapidFuzz WRatio), Variaveis de Configuracao, Frontend Sample Constants (topK, ANALYSIS_SAMPLE_SIZE) (+7 more)

### Community 100 - "request cluster"
Cohesion: 0.21
Nodes (14): Config, FinalSearchRequest, ProbeEnrichRequest, ProbeSearchRequest, BaseModel, Request schemas for API endpoints. Define estruturas tipadas para request…, Request para extração de termos relevantes. Extrai termos de uma lista de items…, Query estruturada para busca em APIs de patentes/artigos. (+6 more)

### Community 101 - "query complexity cluster"
Cohesion: 0.38
Nodes (3): Any, QueryComplexityAnalyzer, Analisa complexidade de queries booleanas (CQL, SQL, etc).

### Community 102 - "report review service cluster"
Cohesion: 0.27
Nodes (8): overlaps(), ReviewResult, ScopeRange, Orquestra a revisão do .tex no editor (POST /report/{session_id}/review):…, ReportReviewService, Suggestion, ReviewResult, test_overlap_detection_for_dedup()

### Community 103 - "modelo dados der cluster"
Cohesion: 0.16
Nodes (14): Loop de Retentativa por Complexidade (placeholder image), article table, patent table, probe_query_article table, probe_query_patent table, probe_query_term table, research_session table, session_ai_call table (+6 more)

### Community 104 - "ollama service cluster"
Cohesion: 0.25
Nodes (6): OllamaLLMService, Any, InputIntake, LLMUsage, Serviço LLM genérico via endpoint `{base_url}/v1/chat/completions` (formato…, test_ollama_extracts_and_repairs_fenced_json_after_reasoning_text()

### Community 105 - "keyword service cluster"
Cohesion: 0.18
Nodes (8): KeywordService, Extrai palavras-chave de múltiplos campos de um documento. Processa título,…, Serviço de extração de palavras-chave de documentos. Usa KeyBERT para extrair…, Extrai palavras-chave de múltiplos documentos em batch. Args: documents: Lista…, Obtém lista única de palavras-chave de múltiplos documentos. Útil para…, Inicializa o serviço de keywords. Args: language: Idioma para extração…, Inicializa modelo KeyBERT. Carregando modelo sob demanda para evitar overhead…, Extrai palavras-chave de um texto. Args: text: Texto para extrair palavras-…

### Community 106 - "relevance service cluster 2"
Cohesion: 0.26
Nodes (9): EmbeddingService, Embedding generation service using sentence-transformers., Serviço de geração de embeddings para textos. Usa sentence-transformers para…, NLP services package for keyword extraction and semantic relevance., DocumentRelevanceScore, FilteredDocumentsResult, Relevance scoring and document filtering service., Score de relevância de um documento. Armazena score de similaridade e decisão… (+1 more)

### Community 107 - "report document router cluster"
Cohesion: 0.15
Nodes (13): _article_to_rag_dict(), _build_section_data(), _figure_facts(), _merge_signatures(), _patent_to_rag_dict(), _pt_int(), Any, Fatos passados ao prompt da seção (ver formato em report_prompts.py) - tudo… (+5 more)

### Community 108 - "TESTE EXTRACAO TERMOS BM25F RRF cluster"
Cohesion: 0.21
Nodes (13): Use of Extracted Terms (prioritized over original), Returned score != adjusted ranking score, Current Term Extraction: PatternRank + BM25F + KeyBERT + RRF + C-value, Teste Comparativo: Pipeline Antigo vs BM25F+RRF, keyphrase-vectorizers dependency, Candidate Word Cap 5 (instead of 3), New Pipeline: PatternRank + BM25F + RRF + C-value, Old Pipeline: spaCy noun_chunks + TF-IDF + KeyBERT (+5 more)

### Community 109 - "kucharavy cluster"
Cohesion: 0.18
Nodes (13): Growth Rate Function, Growth Time (10%-90% of K), Logistic S-Curve Model (Kucharavy), Midpoint t0 (Inflection Point), Saturation Limit K, S-Curve Phases (Iniciacao, Crescimento, Maturidade, Saturacao), Technology Life Cycle S-Curve (Madeo), S-Curve Milestones GP 2008 / MP 2017 / SP 2026 (+5 more)

### Community 110 - "logging cluster"
Cohesion: 0.19
Nodes (8): Any, Log em nível INFO com contexto estruturado. Args: message: Mensagem principal…, Log em nível ERROR com contexto estruturado. Args: message: Mensagem principal…, Log em nível WARNING com contexto estruturado. Args: message: Mensagem…, Log em nível DEBUG com contexto estruturado. Args: message: Mensagem principal…, Wrapper para facilitar logging estruturado com contexto adicional., Inicializa o logger estruturado. Args: name: Nome do módulo., StructuredLogger

### Community 111 - "drawio cluster"
Cohesion: 0.18
Nodes (13): Arquitetura da Solucao Proposta (diagram), Extracao de Termos (PLN local), Interface do Usuario (Web), Lens API, Modulo de Busca (QueryBuilders + SearchServices), Modulo de IA (LLM Remota), Modulo de Orquestracao (Chat Service), OPS (Worldwide Patent Search) (+5 more)

### Community 112 - "generate db schema docs cluster"
Cohesion: 0.33
Nodes (12): build_dbml(), build_html(), build_md(), build_mermaid(), _composite_uniques(), _foreign_keys(), main(), _mermaid_type() (+4 more)

### Community 113 - "ops service cluster 2"
Cohesion: 0.15
Nodes (8): OPSToken, datetime, Gerencia token OAuth2 do OPS. Armazena token e verifica expiração para auto-…, Inicializa com token de acesso. Args: access_token: Token de acesso OAuth2.…, Retorna data/hora de expiração. Returns: Datetime de expiração do token., Obtém novo token OAuth2 do OPS. Usa grant_type=client_credentials com…, Verifica se token está expirado com buffer. Args: buffer_seconds: Segundos…, Converte token para dicionário. Returns: Dicionário com dados do token.

### Community 114 - "test scopus service cluster"
Cohesion: 0.23
Nodes (11): extract_scopus_final_fields(), Search service for Scopus API with pagination., Deriva title/institutions/year de um entry BRUTO da Scopus - usada por…, # TODO: Implementar análise de relevância baseada em:, asyncio, test_extract_scopus_final_fields_ignores_affiliation_without_affilname(), test_extract_scopus_final_fields_missing_affiliation_and_date(), test_extract_scopus_final_fields_multiple_affiliations_as_list() (+3 more)

### Community 115 - "search port cluster"
Cohesion: 0.21
Nodes (5): PatentSearchPort, Any, Protocol, SearchResult, ScholarlySearchPort

### Community 116 - "report prompts cluster"
Cohesion: 0.39
Nodes (11): _conclusao_prompt(), _documents_block(), _figures_block(), get_section_prompt(), _informacoes_cientificas_prompt(), _informacoes_tecnologicas_prompt(), _introducao_prompt(), _lifecycle_lines() (+3 more)

### Community 117 - "conftest cluster"
Cohesion: 0.23
Nodes (11): async_session_maker(), db_session(), event_loop(), AsyncSession, fixture, Pytest configuration and shared fixtures., Fornece event loop para testes async., Cria session maker para testes com banco em memória. (+3 more)

### Community 118 - "report service cluster"
Cohesion: 0.22
Nodes (7): top_summary(), _font_for_label(), Top-K valores mais frequentes de um campo (lista JSON ou escalar), em ordem…, Desenha o gráfico de barra horizontal (ranking top-K já pronto em `counts`,…, Gera o gráfico de barra horizontal top-K a partir de uma distribuição…, Detecta se `text` contém Hangul ou Han (chinês/a maioria dos kanjis japoneses)…, Series

### Community 119 - "general system prompt copy cluster"
Cohesion: 0.18
Nodes (11): Concept Extraction CORRECT/INCORRECT Examples, General System Prompt (copy), Exhaustive Semantic Expansion, Sentence Filter & Term Quality Rules, Diversity Requirement (4 distinct variations), Refine Topic System Prompt (copy), Field Preservation (area_of_study, keywords copied exactly), JSON String Safety Rules (+3 more)

### Community 120 - "add1 cluster"
Cohesion: 0.18
Nodes (11): LLMPort interface, PatentSourcePort interface, core/services/research_service.py — receives PatentSourcePort & LLMPort by parameter, Lens (patent/scholarly API — schema changes frequently), OPS — EPO Open Patent Services (deprecates endpoints), Scopus API (changes request limits), USPTO API, Clean Architecture (alternative model B, compared to hexagonal) (+3 more)

### Community 121 - "ops service cluster 3"
Cohesion: 0.25
Nodes (10): Element, _extract_party_names_xml(), _find_all_by_local_name(), _find_first_by_local_name(), _local_name(), Extrai nomes de uma lista de elementos <applicant>/<inventor> da OPS (formato…, Encontra todos elementos descendentes por nome local, ignorando namespace.…, Extrai campos bibliográficos estruturados de um elemento XML exchange-document.… (+2 more)

### Community 122 - "db schema atual cluster"
Cohesion: 0.18
Nodes (11): article table, patent table, probe_query_article table, probe_query_patent table, probe_query_term table, session_probe_query table, Engenharia de Prompt, Funcao de Complexidade de Consulta (+3 more)

### Community 123 - "db cluster"
Cohesion: 0.25
Nodes (10): Config, DocumentRecord, BaseModel, QueryExecutionLog, Database-related schemas for storage and retrieval., Registro de um documento armazenado em banco de dados. Mapeia dados…, Registro de uma busca armazenado em banco de dados. Permite rastreamento…, Log de execução de uma consulta contra base de dados. Rastreia performance e… (+2 more)

### Community 124 - "embedding service cluster"
Cohesion: 0.22
Nodes (6): ndarray, Gera embedding para um documento. Estratégia de fallback: 1. Usar abstract se…, Gera embeddings para múltiplos documentos em batch. Args: documents: Lista de…, Retorna dimensionalidade dos embeddings. Returns: Número de dimensões ou None…, Gera embedding para um texto. Args: text: Texto para embedding. Returns: Array…, Gera embeddings para múltiplos textos em batch. Args: texts: Lista de textos.…

### Community 125 - "openalex service cluster"
Cohesion: 0.25
Nodes (5): OpenAlexService, Any, Busca metadados complementares via OpenAlex, usando o DOI que a Scopus Search…, OpenAlex devolve o abstract como índice invertido (palavra -> posições), não…, OpenAlex classifica cada trabalho com uma lista de "concepts" (área/assunto,…

### Community 126 - "ollama adapter cluster"
Cohesion: 0.22
Nodes (5): OllamaLLMAdapter, Any, LLMRequest, LLMResponse, LLMUsage

### Community 127 - "scopus adapter cluster"
Cohesion: 0.29
Nodes (3): Any, SearchResult, ScopusAdapter

### Community 128 - "llm config resolver cluster"
Cohesion: 0.24
Nodes (4): LLMConfigResolver, AsyncSession, LLMPort, `resolve` serve os 3 call sites de query estruturada (LLMPort:…

### Community 129 - "report review cluster"
Cohesion: 0.24
Nodes (8): _category_label(), filter_languagetool_matches(), languagetool_suggestions(), _protected_spans(), Any, _match(), test_false_positives_are_filtered_but_real_errors_kept(), test_uppercase_word_still_flagged_for_agreement_rules()

### Community 130 - "package cluster 2"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, dev, lint, preview, type (+1 more)

### Community 131 - "test ops party names cluster"
Cohesion: 0.31
Nodes (7): Extrai nomes de uma lista de applicant/inventor da OPS (formato JSON). Cada…, Extrai campos bibliográficos estruturados do exchange-document. Retorna apenas…, _json_party(), test_latin_original_name_is_kept_even_with_accents(), test_non_latin_name_without_epodoc_pair_is_kept(), test_non_latin_original_name_falls_back_to_epodoc_without_country_suffix(), test_xml_variant_uses_same_fallback()

### Community 132 - "token cost calculator cluster"
Cohesion: 0.22
Nodes (9): calculate_token_cost(), format_cost(), format_tokens(), get_model_pricing(), Token cost calculator for different LLM models. Provides standardized cost…, Format cost as readable string. Args: cost_usd: Cost in USD Returns: Formatted…, Format token count as readable string. Args: token_count: Number of tokens…, Get pricing for a specific model. Args: model: Model name (gemini, gpt-4,… (+1 more)

### Community 133 - "test report service cluster"
Cohesion: 0.20
Nodes (5): FakeStoragePort, fixture, StoragePort fake em memória - substitui o MinIO real nos testes., storage(), svc()

### Community 134 - "embedding port cluster"
Cohesion: 0.31
Nodes (3): EmbeddingPort, Embedding, Protocol

### Community 135 - "app cluster"
Cohesion: 0.22
Nodes (8): compile_latex(), health(), get, post, Response, UploadFile, Serviço HTTP dedicado de compilação de LaTeX (POST /compile). Só é chamado sob…, `main_tex`: o arquivo .tex principal (campo obrigatório). `assets`: 0+ arquivos…

### Community 136 - "main cluster"
Cohesion: 0.25
Nodes (9): research_session table, session_ai_call table, session_input table, session_report_section table, Modelagem do Banco de Dados (sec 3.6), Filtragem de documentos por idioma e relevancia ao tema, Pipeline de processamento (5 fases: refinamento, busca exploratoria, extracao de termos, busca final, relatorio), Retrieval-Augmented Generation (RAG) (+1 more)

### Community 137 - "promptIA cluster"
Cohesion: 0.25
Nodes (9): IMBEL / Rohill partnership (report requester), Lens.org search strategy (trunked AND tetra AND radio, CPC h04w*), REPTEC 001/2023 AGITEC - Terrestrial Trunked Radio prospection report, TETRA (Terrestrial Trunked Radio) technology, Combine keywords with CPC/IPC classification, LLM query expansion anchored on CPC, Precision/recall measurement by sampling, Suggested query pipeline (Block A theme / B context / C CPC) (+1 more)

### Community 138 - "pipeline rag local cluster"
Cohesion: 0.25
Nodes (9): ChromaDB, Fase 4 - Busca Final, Fase 5 - Geracao do Relatorio, Amostra de temas da busca final, Chunking, Pipeline do RAG Local (diagram), nomic-embed-text (local embeddings), Relatorios de referencia AGITEC (+1 more)

### Community 139 - "test routes cluster"
Cohesion: 0.22
Nodes (8): client(), fixture, Tests for API routes., Fornece TestClient para testes de rota., Testa rota de health check., Verifica que responses incluem run_id., test_health_check_route(), test_response_includes_run_id()

### Community 140 - "test openai compatible adapter cluster"
Cohesion: 0.39
Nodes (8): adapter(), _fake_response(), asyncio, fixture, test_generate_connect_error_raises_runtime_error(), test_generate_posts_to_chat_completions_and_strips_response(), test_generate_sends_bearer_token_when_api_key_set(), test_generate_without_system_prompt_omits_system_message()

### Community 141 - "provider registry cluster"
Cohesion: 0.36
Nodes (7): _build_anthropic(), _build_gemini(), build_llm_port(), _build_ollama(), LLMProviderSpec, LLMPort, Registry de providers de IA suportados pelo código - o ponto de extensão da…

### Community 143 - "pipeline rag local cluster 2"
Cohesion: 0.25
Nodes (8): Colecao: estilo/estrutura REPTEC/AGITEC, Colecao: temas factuais, Qwen 2.5 (via Ollama) modelo local, Recuperacao top-k por secao do relatorio, Secao do relatorio gerada, Self-Attention (Query, Key, Value) figure, Self-Attention mechanism softmax(QK^T/sqrt(d_k))V, Vaswani et al., 2017 (Attention Is All You Need)

### Community 144 - "build cpc titles cluster"
Cohesion: 0.36
Nodes (7): build(), main(), Gera config/cpc_titles.json (código -> título oficial) a partir das listas…, Remove blocos "(...)" (com aninhamento) e chaves "{...}" do título., Aceita os dois formatos: CPC ("código<TAB>nível<TAB>título") e IPC…, _read(), _strip_references()

### Community 145 - "ops service cluster 4"
Cohesion: 0.25
Nodes (4): Constrói headers para requisição OPS. OPS espera: Authorization: Bearer <token>…, Fetch bibliographic data for a single patent using /biblio endpoint. Uses OPS…, Extract useful bibliographic information from OPS biblio response. Navigates…, Enrich search results with bibliographic data from OPS. Fetches full…

### Community 146 - "test config cluster"
Cohesion: 0.25
Nodes (7): Tests for configuration loading., Verifica campos obrigatórios de config., Verifica valores padrão de configuração., Verifica que configuração carrega corretamente., test_config_defaults(), test_config_has_required_fields(), test_config_loads_from_env()

### Community 147 - "lens patent adapter cluster"
Cohesion: 0.29
Nodes (3): LensPatentAdapter, Any, SearchResult

### Community 148 - "lens scholarly adapter cluster"
Cohesion: 0.29
Nodes (3): LensScholarlyAdapter, Any, SearchResult

### Community 149 - "session input cluster"
Cohesion: 0.33
Nodes (7): finalize_session(), AsyncSession, post, Request, SuccessResponse, Cria a research_session e a cadeia de session_input (raiz + gerado) numa…, _storage()

### Community 150 - "report review cluster 2"
Cohesion: 0.29
Nodes (7): _edited_ranges(), _mask_commands(), (início do conteúdo, fim, título, seção-pai) de cada \\section/\\subsection., Faixas (offsets no texto ATUAL) das linhas inseridas/alteradas., review_scope(), _sections(), _subtract()

### Community 151 - "icons cluster"
Cohesion: 0.52
Nodes (7): Bluesky Icon, Discord Icon, Documentation Icon, GitHub Icon, Icons Sprite Sheet (Social & UI Icons), Social (Generic Community/Followers) Icon, X (Twitter) Icon

### Community 152 - "db schema atual cluster 2"
Cohesion: 0.29
Nodes (7): app_settings table, db/config_models.py (editable config), db/config_seed.py (idempotent seed), llm_call_site_bindings table, llm_provider_configs table, search_api_selection table, APIs utilizadas (OPS, Scopus, Lens)

### Community 153 - "pipeline cinco fases cluster"
Cohesion: 0.33
Nodes (7): Pipeline de Prospeccao Tecnologica - 5 Fases (diagram), Fase 1 - Refinamento do Tema, Fase 2 - Busca Exploratoria, Fase 3 - Extracao de Termos, Validacao do Usuario (human-in-the-loop: aprovar/ajustar/refazer), pipeline_extracao_termos.png (placeholder stock image, no diagram content), wizard_interface_web.png (placeholder stock image, no screenshot content)

### Community 154 - "README cluster"
Cohesion: 0.29
Nodes (7): Alembic Migrations (research_session_models), README - AGIA Prospeccao Tecnologica, Ollama GPU Passthrough, Pre-existing Test Failures, qwen2.5:3b-instruct default model, notes/REPTEC_001_2023_TETRA.pdf, Ollama / RAG Settings (OLLAMA_*, RAG_TOP_K_PER_SECTION)

### Community 155 - "request logging cluster"
Cohesion: 0.33
Nodes (5): Request, Middleware que adiciona rastreamento de requisições HTTP com run_id único. Cada…, RequestLoggingMiddleware, BaseHTTPMiddleware, Response

### Community 157 - "DocUserGuide cluster"
Cohesion: 0.33
Nodes (5): DocUserGuide(), GuideNote, GuideSection, GuideSubsection, sections

### Community 158 - "db schema atual cluster 3"
Cohesion: 0.40
Nodes (6): scripts/generate_db_schema_docs.py (generator), Session-centric ERD (Mermaid HTML render), db/research_session_models.py (active schema, Alembic), session_chart table, S-curve extrapolation via LogLetLab4 logistic model, Curva S de maturidade tecnologica (GP, MP, SP)

### Community 159 - "fluxograma cluster"
Cohesion: 0.33
Nodes (6): Geracao Textual do Relatorio, RAGService, Busca Final, Edita e Valida Relatorio, Gera graficos / Seleciona graficos, Sintese de dados e Gera relatorio

### Community 160 - "health router cluster"
Cohesion: 0.40
Nodes (5): health_check(), Any, get, Request, Verifica a saúde da aplicação e retorna informações de status. Args: request:…

### Community 161 - "report review cluster 3"
Cohesion: 0.40
Nodes (4): AnnotatedSegment, Segmentos texto/markup cuja concatenação é EXATAMENTE `fragment` - assim os…, to_annotated_text(), test_annotated_text_concatenates_back_to_the_original()

### Community 162 - "drawio cluster 2"
Cohesion: 0.40
Nodes (5): Consolidacao e Visualizacao, MinIO Remoto/Local, Modulo de Persistencia (SQLAlchemy + SQLite/PostgreSQL), Modelo de Dados (DER), Patentes por Ano (chart)

### Community 163 - "base cluster 2"
Cohesion: 0.40
Nodes (3): Any, Converte resultado para dicionário. Returns: Dicionário com dados do resultado., Converte erro para dicionário. Returns: Dicionário com informações do erro.

### Community 164 - "dependencies cluster"
Cohesion: 0.50
Nodes (3): get_db_session(), AsyncSession, FastAPI dependency injection for HTTP adapters.

### Community 165 - "research session cluster 2"
Cohesion: 0.50
Nodes (3): Any, field_validator, `ResearchSession.report` (SQLAlchemy relationship, ver…

### Community 167 - "ops service cluster 5"
Cohesion: 0.50
Nodes (4): _is_latin_name(), _pick_party_names(), True se todas as letras do nome são do alfabeto latino (com ou sem acento). O…, Escolhe UM nome por parte a partir de (data-format, sequence, nome): o…

### Community 168 - "provider registry cluster 2"
Cohesion: 0.67
Nodes (3): list_providers_for_family(), Registry de providers de busca suportados por família (patent/scholarly) -…, SearchProviderSpec

## Ambiguous Edges - Review These
- `Research` → `ChatService / chat_router.py (live orchestration: refine-topic, probe, final search, extract-terms)`  [AMBIGUOUS]
  ambinte.md · relation: references
- `REPTEC 001/2023 - Terrestrial Trunked Radio (TETRA) report` → `Geracao de Relatorio (RAG)`  [AMBIGUOUS]
  PFC/img/Relatorio_1.png · relation: conceptually_related_to
- `Modulo de Orquestracao (Chat Service)` → `Loop de Retentativa por Complexidade (placeholder image)`  [AMBIGUOUS]
  PFC/img/loop_retentativa_complexidade.png · relation: conceptually_related_to
- `ChromaDB` → `plano_persistencia_minio.png (placeholder stock image, no diagram content)`  [AMBIGUOUS]
  PFC/img/plano_persistencia_minio.png · relation: conceptually_related_to
- `Pipeline de Prospeccao Tecnologica - 5 Fases (diagram)` → `wizard_interface_web.png (placeholder stock image, no screenshot content)`  [AMBIGUOUS]
  PFC/img/wizard_interface_web.png · relation: conceptually_related_to
- `Fase 3 - Extracao de Termos` → `pipeline_extracao_termos.png (placeholder stock image, no diagram content)`  [AMBIGUOUS]
  PFC/img/pipeline_extracao_termos.png · relation: references
- `Curva S e Evolucao Temporal - Patentes` → `Placeholder Image Icon (iStock)`  [AMBIGUOUS]
  img.jpg · relation: conceptually_related_to

## Knowledge Gaps
- **282 isolated node(s):** `SearchError`, `name`, `private`, `version`, `type` (+277 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Research` and `ChatService / chat_router.py (live orchestration: refine-topic, probe, final search, extract-terms)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `REPTEC 001/2023 - Terrestrial Trunked Radio (TETRA) report` and `Geracao de Relatorio (RAG)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Modulo de Orquestracao (Chat Service)` and `Loop de Retentativa por Complexidade (placeholder image)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `ChromaDB` and `plano_persistencia_minio.png (placeholder stock image, no diagram content)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Pipeline de Prospeccao Tecnologica - 5 Fases (diagram)` and `wizard_interface_web.png (placeholder stock image, no screenshot content)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Fase 3 - Extracao de Termos` and `pipeline_extracao_termos.png (placeholder stock image, no diagram content)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Curva S e Evolucao Temporal - Patentes` and `Placeholder Image Icon (iStock)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._