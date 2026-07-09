1. Live database initialization code
c:\Users\joaop\OneDrive\Documentos\PFC\db\init_db.py is the live equivalent of the old db/init_db.py — it did not move during the refactor, and it is still imported directly by the FastAPI entrypoint:

app\main.py:21 — from db.init_db import init_db
app\main.py:50 — await init_db() inside the lifespan() startup handler (after db_session.initialize() at line 35)
db/init_db.py:20-80 (async def init_db()) imports three model modules and calls Base.metadata.create_all three times, once per Base instance:

db.models → Base as ModelsBase (imports PatentDedupRegistry, PatentDocument, ScholarlyDedupRegistry, ScholarlyDocument by name, but since importing the module registers all classes in that file with the shared Base.metadata, all 4 classes get their tables created)
db.research_models → Base as ResearchBase (imports Research, ResearchMetrics, ResearchPatentDocument, ResearchPhase, ResearchScholarlyDocument by name — note ResearchTokenUsage isn't in the import list but its table still gets created because importing the module registers it with ResearchBase.metadata too)
db.param_init_models → Base as ParamInitBase (ParamInit)
So init_db() creates 11 tables total at startup (the logger.info(..., models_loaded=10) log at line 42 is a stale/inaccurate hardcoded count — off by one, doesn't reflect ResearchTokenUsage).

db/session.py (DatabaseSession, global instance db_session) is the live session/engine manager, imported by app/main.py:22 and app/adapters/driving/http/dependencies.py:9. Configured DATABASE_URL (.env:3) points to postgresql+asyncpg://postgres:postgres@localhost:5432/pfc_db.

2. Live model files — none moved, all still at the old db/ paths
Contrary to the rest of the codebase, the db/ directory itself is NOT dead code — only api/routes/ and services/tools/ are dead (both contain only __pycache__, their .py sources are gone). db/*.py files are live and unchanged in location:

Old expected path	Live status	File path
db/models.py	Still live, same path	c:\Users\joaop\OneDrive\Documentos\PFC\db\models.py
db/research_models.py	Still live, same path	c:\Users\joaop\OneDrive\Documentos\PFC\db\research_models.py
db/param_init_models.py	Still live, same path	c:\Users\joaop\OneDrive\Documentos\PFC\db\param_init_models.py
db/init_db.py	Still live, same path	c:\Users\joaop\OneDrive\Documentos\PFC\db\init_db.py
db/session.py	Still live, same path	c:\Users\joaop\OneDrive\Documentos\PFC\db\session.py
Each file uses its own Base = declarative_base() — there are three separate Base instances (models.py, research_models.py, param_init_models.py), not one shared metadata object.

3. Table-by-table detail
db/models.py (Base #1)
scholarly_documents (ScholarlyDocument, models.py:15-90)

id PK int, source str(50) idx, source_record_id str(255), dedup_key str(500) unique idx, title str(1000) idx, abstract Text, doi str(255) unique idx, authors JSON, affiliations JSON, journal_or_source str(500) idx, volume/issue/pages str(50), publication_date str(10), year int idx, keywords JSON, field_of_study JSON, citations int, relevance_score float, created_at/updated_at DateTime, raw_payload JSON
Indexes: (source, source_record_id), (year, relevance_score), (source, year)
No FKs/relationships
patent_documents (PatentDocument, models.py:93-166)

id PK int, source str(50) idx, source_record_id str(255), dedup_key str(500) unique idx, title str(1000) idx, abstract Text, publication_number str(255) unique idx, application_number str(255) idx, family_id str(255) idx, applicants JSON, inventors JSON, ipc_codes JSON, cpc_codes JSON, filing/publication/grant_date str(10), year int idx, legal_status str(255) idx, relevance_score float, created_at/updated_at DateTime, raw_payload JSON
Indexes: (source, source_record_id), (year, relevance_score), (source, year)
No FKs/relationships
scholarly_dedup_registry (ScholarlyDedupRegistry, models.py:169-208)

id PK int, dedup_key str(500) unique idx, document_id int idx, source str(50) idx, source_record_ids JSON, created_at DateTime idx
Index (source, dedup_key). No FKs.
patent_dedup_registry (PatentDedupRegistry, models.py:211-250)

Same shape as above for patents. Index (source, dedup_key). No FKs.
db/research_models.py (Base #2)
research (Research, research_models.py:18-128)

id PK int, research_id str(36) unique idx (UUID), title str(500), description Text, status str(50) idx default "ongoing", user_input JSON, refined_candidates JSON, chosen_candidate JSON, probe_query JSON, probe_api str(50), extracted_terms JSON, extracted_terms_count int, final_query_specific/balanced/generic JSON, chosen_final_query str(50), patent_results_count/scholarly_results_count/total_results_count int, latex_content Text, latex_generated_at DateTime, report_url str(500), timing JSON, total_tokens_used int, total_cost_usd float, created_at/updated_at DateTime idx
Relationships: patent_documents → ResearchPatentDocument (cascade delete-orphan), scholarly_documents → ResearchScholarlyDocument (cascade), metrics → ResearchMetrics (one-to-one, cascade), token_usage → ResearchTokenUsage (cascade)
Indexes: created_at, status, probe_api
research_patent_documents (ResearchPatentDocument, research_models.py:131-190)

id PK, research_id FK → research.id (indexed), plus publication_number, source, source_record_id, title, abstract, applicants/inventors JSON, ipc_codes/cpc_codes JSON, filing/publication/grant_date, year idx, legal_status, relevance_score, query_variant, raw_payload JSON, created_at
Indexes: (research_id, publication_number), (research_id, year)
research_scholarly_documents (ResearchScholarlyDocument, research_models.py:193-255)

id PK, research_id FK → research.id, doi unique idx, source, source_record_id, title, abstract, authors/affiliations JSON, journal_or_source, volume/issue/pages, publication_date, year idx, keywords/field_of_study JSON, citations, relevance_score, query_variant, raw_payload JSON, created_at
Indexes: (research_id, doi), (research_id, year)
research_metrics (ResearchMetrics, research_models.py:258-307)

id PK, research_id FK → research.id (unique — one-to-one), a large set of JSON aggregate columns (patent_by_year/applicant/ipc/legal_status/query_variant, article_by_year/journal/field/citations/query_variant, top_patent_applicants/inventors, top_article_authors/journals, patent_growth_trend, article_growth_trend, query_variant_comparison, patent_vs_article_ratio), calculated_at DateTime
research_phases (ResearchPhase, research_models.py:310-348)

id PK, research_id FK → research.id (indexed, no back-populated relationship declared on Research), phase_name str(100), description str(500), started_at/completed_at DateTime, duration_seconds float, status str(50), error_message Text, phase_metadata JSON
Index (research_id, phase_name)
research_token_usage (ResearchTokenUsage, research_models.py:351-404)

id PK, research_id FK → research.id (indexed; referenced from Research.token_usage relationship via explicit foreign_keys=), phase_name idx, llm_call_type, call_number, model, model_variant, input_tokens/output_tokens/total_tokens, input_cost_usd/output_cost_usd/total_cost_usd, api_latency_ms, status, created_at idx, call_metadata JSON
Indexes: (research_id, phase_name), (research_id, llm_call_type), (research_id, created_at)
db/param_init_models.py (Base #3)
param_init (ParamInit, param_init_models.py:14-24)

id PK int, tema str(500) not null, descricao Text, keywords JSON, area_estudo str(500). No FKs, no relationships.
4. Which tables are actually wired into a working live feature vs. dead schema
This is the key finding — almost the entire "research" persistence layer exists as schema and even has repository/service code, but is not reachable from any live HTTP route today.

param_init — ACTIVE, fully wired end-to-end.

app/adapters/driving/http/param_init.py (registered in app/main.py:95) does session.add(row) (create, line 31), session.get(ParamInit, ...) (update line 47, delete line 65), session.delete(row) (line 67) — full CRUD.
Frontend confirmed calling it: frontend/src/services/paramInit.ts, frontend/src/components/Workflow.tsx, frontend/src/stores/useFormStore.ts all reference param-init/ParamInit.
This is Step1 draft persistence (theme/description/keywords/area) — genuinely live.
patent_documents, scholarly_documents, patent_dedup_registry, scholarly_dedup_registry — schema created, full adapter stack exists, but NOT reachable from any live route.

services/db/repositories.py (PatentDocumentRepository, ScholarlyDocumentRepository, DedupRegistry) does real session.add/select(...) work and is imported live by app/adapters/driven/persistence/{patent_repository_adapter,scholarly_repository_adapter,dedup_registry_adapter}.py.
Those adapters are wired into ResearchService (app/core/services/research_service.py), whose persist_batch() method (line 267) is the only code that would actually create rows in these tables.
ResearchService is only ever instantiated inside app/container.py:123 (build_research_service) — and build_research_service is never called anywhere (grep for the name across the whole repo returns only its own definition).
chat_router.py / ChatService (the actual live orchestration the frontend drives — refine-topic, probe/query, probe/search, final/query, final/search, extract-terms) never touches the database at all; it just returns JSON to the frontend, which holds state client-side.
Conclusion: these 4 tables exist and have working repository code, but currently nothing in the live request path calls it — no route creates a patent/scholarly document row.
research, research_patent_documents, research_scholarly_documents, research_metrics, research_token_usage — schema created, READ-ONLY routes exist, but nothing ever WRITES a row.

Read paths are live and real: app/adapters/driving/http/research_router.py (GET /research/{id}, /patents, /articles, /token-usage, /token-summary, POST /calculate-metrics, POST /generate-report) and app/adapters/driving/http/report_router.py (POST /reports/generate-latex) both do genuine select(Research)/select(ResearchPatentDocument)/etc. app/core/services/metrics_aggregator.py does real aggregation queries and session.add(metrics) for ResearchMetrics (line 42) — but only if a research_id already exists.
I grepped the entire app/ tree for Research(, ResearchPatentDocument(, ResearchScholarlyDocument(, session.add(Research — the only session.add calls in the whole app are in metrics_aggregator.py (for ResearchMetrics, conditional on a Research already existing) and param_init.py. No code anywhere creates a Research row.
Confirmed from the frontend side too: grep for /research/, calculate-metrics, generate-report in frontend/src returns nothing — the frontend never calls these endpoints.
Conclusion: these routes are dead in practice — they can only ever return "not found" today, since nothing populates a research_id to look up.
research_phases — fully dead, not even read.

Grep across the whole repo for ResearchPhase only turns up the class definition in research_models.py and its mention in init_db.py's import list. No route, service, or adapter reads or writes it anywhere.
research_token_usage — read-only, same as the other research tables (dead in practice, no writer).

5. param_init (Step1 draft persistence) — confirmed still wired the same way
param_init did move in file location terms only in the sense that the router moved from the old dead api/routes/ structure into the hexagonal layer at app/adapters/driving/http/param_init.py, but the feature itself works exactly as before: POST /param-init, PUT /param-init/{id}, DELETE /param-init/{id}, POST /param-init/{id}/discard (sendBeacon-friendly alias for delete), all doing direct CRUD against the single ParamInit model in db/param_init_models.py. Registered in app/main.py:95 (app.include_router(param_init.router, prefix=settings.api_prefix)), and actively called by the frontend wizard (frontend/src/services/paramInit.ts).

Summary table for plain-language explanation
Table	Purpose (plain terms)	Status
param_init	Saves the Step1 wizard draft (theme/description/keywords/area) so it's not lost on refresh; deleted when the user cancels/closes	Active — real feature in use today
patent_documents / scholarly_documents / patent_dedup_registry / scholarly_dedup_registry	Meant to be a global cache/store of every patent & article ever fetched, with dedup tracking	Schema + working repository code exist, but no live route calls it. Nothing currently writes to these tables.
research	Meant to represent one saved "research project" (theme → candidates → queries → results → report)	Schema + read-only endpoints exist, but nothing ever creates a research row. Endpoints are effectively unreachable (always "not found") today.
research_patent_documents / research_scholarly_documents	Meant to hold the patents/articles found for a specific saved research	Same as above — read endpoints exist, no writer
research_metrics	Meant to hold precomputed chart data (by year, by applicant, growth trends, etc.) for a research's report	Only written if a research row already exists (which never happens today), so effectively dead too
research_token_usage	Meant to track LLM token/cost usage per research, per phase	Read-only endpoints exist; nothing writes it
research_phases	Meant to track how long each pipeline phase took	Completely dead — not read or written anywhere in live code
The overall picture: the actual live wizard flow (theme refinement → query building → probe/final search → term extraction, all in chat_router.py/ChatService) is stateless from the database's perspective — it returns everything to the frontend and never persists results. The only genuinely active table is param_init. All patent/article/research/metrics/token-usage tables are created at startup and have varying amounts of supporting code (from full repository+adapter stacks down to nothing at all), but none of them currently participate in a request that a user can actually trigger through the frontend.