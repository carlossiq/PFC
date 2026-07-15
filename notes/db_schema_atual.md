# Diagrama do Banco de Dados — Prospecção Tecnológica (PFC)

## Como visualizar

### Opção 1 — mermaid.live (sem instalar nada)
1. Acesse **https://mermaid.live**
2. Apague o conteúdo do painel esquerdo
3. Cole o bloco Mermaid abaixo (sem os três backticks)
4. O diagrama aparece ao vivo no painel direito

### Opção 2 — VS Code
Instale a extensão **Markdown Preview Mermaid Support** (`bierner.markdown-mermaid`) e pressione `Ctrl+Shift+V` neste arquivo.

---

```mermaid
erDiagram
	direction TB
	research_session {
		Int id PK ""  
		String public_id UK ""  
		String name  "optional"  
		Boolean completed  ""  
		String patent_source  "optional"  
		String scholarly_source  "optional"  
		Float relevance_threshold  ""  
		DateTime created_at  ""  
		DateTime updated_at  ""  
	}

	session_input {
		Int id PK ""  
		Int session_id FK ""  
		Int parent_id FK "self, optional — refino do input raiz"  
		String theme  ""  
		Text description  "optional"  
		String area_of_study  "optional"  
		JSON keywords  "optional"  
		Int year_from  "optional"  
		Int year_to  "optional"  
		Int iterations  ""  
	}

	session_probe_query {
		Int id PK ""  
		Int session_id FK ""  
		String fonte  "UK com session_id — ops|scopus"  
		Text query_text  ""  
		JSON fields  "optional"  
		Int year_from  "optional"  
		Int year_to  "optional"  
		Float complexity_score  "optional"  
		String complexity_level  "optional"  
		Int result_count  "optional"  
		Int iterations  ""  
		DateTime created_at  ""  
	}

	session_ai_call {
		Int id PK ""  
		Int session_id FK ""  
		String step  ""  
		String provider  ""  
		String model  ""  
		Float duration_ms  ""  
		Int input_tokens  "optional"  
		Int output_tokens  "optional"  
		Int total_tokens  "optional"  
		Int attempts  ""  
		DateTime created_at  ""  
	}

	patent {
		Int id PK ""  
		String dedup_key UK ""  
		String source  ""  
		String source_record_id  "optional"  
		Text title  ""  
		Text abstract  "optional"  
		String publication_number  "optional"  
		String application_number  "optional"  
		String family_id  "optional"  
		JSON applicants  "optional"  
		JSON inventors  "optional"  
		JSON ipc_codes  "optional"  
		JSON cpc_codes  "optional"  
		String filing_date  "optional"  
		String publication_date  "optional"  
		String grant_date  "optional"  
		Int year  "optional"  
		String legal_status  "optional"  
		String country  "optional"  
		DateTime created_at  ""  
	}

	article {
		Int id PK ""  
		String dedup_key UK ""  
		String source  ""  
		String source_record_id  "optional"  
		Text title  ""  
		Text abstract  "optional"  
		String doi  "optional"  
		JSON authors  "optional"  
		JSON affiliations  "optional"  
		JSON affiliation_countries  "optional"  
		String journal_or_source  "optional"  
		String volume  "optional"  
		String issue  "optional"  
		String pages  "optional"  
		String publication_date  "optional"  
		Int year  "optional"  
		JSON keywords  "optional"  
		JSON field_of_study  "optional"  
		Int citations  "optional"  
		DateTime created_at  ""  
	}

	probe_query_patent {
		Int id PK ""  
		Int probe_query_id FK ""  
		Int patent_id FK ""  
		Float relevance_score  "optional"  
		DateTime created_at  ""  
	}

	probe_query_article {
		Int id PK ""  
		Int probe_query_id FK ""  
		Int article_id FK ""  
		Float relevance_score  "optional"  
		DateTime created_at  ""  
	}

	Untitled-Entity {

	}

	research_session||--o{session_input:"define"
	session_input||--o{session_input:"refina"
	research_session||--o{session_probe_query:"executa"
	research_session||--o{session_ai_call:"registra"
	session_probe_query||--o{probe_query_patent:"encontra"
	patent||--o{probe_query_patent:"aparece em"
	session_probe_query||--o{probe_query_article:"encontra"
	article||--o{probe_query_article:"aparece em"
	patent}|--|{Untitled-Entity:"  "
```

---

## Observações importantes

Este banco **não é um esquema único** — são três grupos de tabelas que coexistem hoje no código, sem chave estrangeira alguma ligando um grupo ao outro:

| # | Grupo | Arquivo | Situação |
|---|-------|---------|----------|
| 1 | **Sessão de prospecção** (`research_session` → `session_input`, `session_probe_query`, `session_ai_call`, `patent`, `article`) | `db/research_session_models.py` | **Ativo e em evolução** — gerenciado via Alembic, é o que está sendo construído agora. |
| 2 | **Documentos genéricos** (`scholarly_documents`, `patent_documents`, `*_dedup_registry`) | `db/models.py` | Ainda em uso pelos adapters de persistência (`patent_repository_adapter.py`, `scholarly_repository_adapter.py`), mas independente de sessão — junção feita por convenção via `dedup_key`/`document_id`, sem FK real. |
| 3 | **Research legado** (`research` → `research_patent_documents`, `research_scholarly_documents`, `research_metrics`, `research_phases`, `research_token_usage`) | `db/research_models.py` | Desenho anterior ao modelo session-centric. Ainda montado e usado por `research_router.py`, `report_router.py` e `metrics_aggregator.py` — é de onde vêm métricas e relatório hoje, já que o grupo 1 ainda não tem equivalente pra isso. |

Pontos que valem atenção ao evoluir o schema ativo (grupo 1):
- `session_metrics` e `session_asset` (que existiam num desenho anterior do grupo 1) **não foram implementados** — métricas e assets de sessão não têm tabela própria ainda.
- `llm_candidate` e `search_run` do desenho anterior saíram do modelo: o refino de estratégia virou o auto-relacionamento `session_input.parent_id` (linha raiz = input do usuário, linha filha = versão refinada escolhida), e cada execução de busca por fonte virou uma linha em `session_probe_query` (uma por sessão+fonte, não uma por tentativa).
- `patent`/`article` (grupo 1) são deduplicados globalmente — a mesma patente encontrada por duas probe queries diferentes gera **uma linha** em `patent` e **duas linhas** em `probe_query_patent`.
