# Plano: Migração de Configuração pro Banco de Dados

Documento de planejamento — nenhuma implementação feita ainda. Objetivo: tirar do `.env`/`core/config.py` praticamente tudo que está catalogado em `VARIAVEIS_DE_CONFIGURACAO.md` e tornar editável em runtime, via tela de Configurações no front, sem depender de redeploy/restart pra maioria dos casos.

---

## 1. Escopo

**Entra nesta migração:**
- As ~35 variáveis escalares de `VARIAVEIS_DE_CONFIGURACAO.md` (seções 4-9 do doc: busca, relevância/complexidade, extração de termos, fuzzy matching, inferência estatística) → tabela genérica `app_settings`.
- As 4 credenciais de API externa (`LENS_API_TOKEN`, `OPS_CONSUMER_KEY`, `OPS_CONSUMER_SECRET`, `SCOPUS_API_KEY`) → também em `app_settings`, marcadas como secretas.
- Os 5 feature flags de API (`ops_enabled`, `scopus_enabled`, `lens_patent_enabled`, `lens_scholarly_enabled`, `lens_enabled`) → **substituídos** por uma tabela de seleção exclusiva por família (`search_api_selection`), não migrados como estão.
- Configuração de IA (seção 1 do doc: `LLM_PROVIDER`, modelos/keys de Gemini/Anthropic/Ollama) → 4 tabelas dedicadas + seleção por call site.

**Fica de fora (infraestrutura fixa, hardcoded ou tratado à parte):**
- `DATABASE_URL`, `SECRET_KEY`/`ALGORITHM`, MinIO (`MINIO_*`), ChromaDB (`CHROMA_HOST`/`CHROMA_PORT`), `LATEX_COMPILER_URL`, `HOST`/`PORT` — problema do ovo-e-galinha (precisam existir antes de qualquer config vinda do banco).
- `VITE_API_BASE_URL` (frontend) — mesmo motivo: o front precisa saber o endereço do backend antes de conseguir ler qualquer config de lá.
- `TEST_MODE` — só usado pela suíte de testes (`tests/conftest.py`), não faz sentido no banco.
- As 5 variáveis já removidas por estarem mortas (`PROBE_API`, `PROBE_API_EXT`, `TERM_EXTRACTION_MMR_LAMBDA`, `TERM_EXTRACTION_MMR_SIMILARITY_THRESHOLD`, `TERM_EXTRACTION_OVERLAP_THRESHOLD`).

---

## 2. As 4 chamadas de IA (call sites)

Confirmado no código — hoje todas as 3 primeiras compartilham uma única instância `self.llm` (`app/core/services/chat_service.py:54`), escolhida uma vez no boot via `LLM_PROVIDER`. Pra virarem seletores independentes, `ChatService` precisa parar de guardar um `self.llm` único e resolver o handle certo por call site.

| Call site | Onde está hoje | Chamada LLM |
|---|---|---|
| `theme_candidates` | `ChatService.generate_candidate_topics` (linha 554) + `specify_topic` (627) | `self.llm.call_raw_json` |
| `probe_query` | `ChatService._build_query_with_retry` (272), usado por `build_probe_queries_multi` | `self.llm.process_intake` |
| `final_query` | `ChatService._build_final_variant_query` (939) | `self.llm.process_intake` |
| `report_writing` | `ReportWriterService` → `OpenAICompatibleAdapter` | HTTP cru pro endpoint compatível com OpenAI |

---

## 3. Schema do banco (6 tabelas novas)

### 3.1 `app_settings` — genérica, chave-valor

```python
class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)       # sempre string, convertido por value_type
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "float" | "int" | "bool" | "str"
    category: Mapped[str] = mapped_column(String(50), nullable=False)    # "term_extraction" | "search" | "statistical_inference" | "external_api" | ...
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)      # mascara no GET se True
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, ...)
```

Uma linha por variável (`key` = nome do campo em `core/config.py`, ex: `term_extraction_score_threshold`). `is_secret=True` pras 4 credenciais de API externa.

### 3.2 `search_api_selection` — seleção exclusiva por família

```python
class SearchApiSelection(Base):
    __tablename__ = "search_api_selection"
    family: Mapped[str] = mapped_column(String(20), primary_key=True)  # 'patent' | 'scholarly'
    active_api: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, ...)
    __table_args__ = (
        CheckConstraint(
            "(family='patent' AND active_api IN ('ops','lens_patent')) OR "
            "(family='scholarly' AND active_api IN ('scopus','lens_scholarly'))"
        ),
    )
```

Exatamente 2 linhas, sempre. Substitui os 5 booleans atuais — impossível por construção ter duas APIs ativas na mesma família ao mesmo tempo (o problema de ambiguidade que a gente discutiu não existe mais nesse desenho).

### 3.3-3.5 Tabelas de provider de IA

```python
class LLMGeminiConfig(Base):
    __tablename__ = "llm_gemini_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    api_key: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at, updated_at

class LLMAnthropicConfig(Base):
    __tablename__ = "llm_anthropic_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    api_key: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at, updated_at

class LLMOllamaConfig(Base):
    __tablename__ = "llm_ollama_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[Optional[str]] = mapped_column(String(500))  # opcional, servidor local não exige
    created_at, updated_at
    __table_args__ = (UniqueConstraint("base_url", "model"),)
```

### 3.6 `llm_call_site_bindings` — seleção por call site

```python
class LLMCallSiteBinding(Base):
    __tablename__ = "llm_call_site_bindings"
    call_site: Mapped[str] = mapped_column(String(50), primary_key=True)  # 'theme_candidates' | 'probe_query' | 'final_query' | 'report_writing'
    provider: Mapped[str] = mapped_column(String(20), nullable=False)     # 'gemini' | 'anthropic' | 'ollama'
    gemini_config_id: Mapped[Optional[int]] = mapped_column(ForeignKey("llm_gemini_configs.id"))
    anthropic_config_id: Mapped[Optional[int]] = mapped_column(ForeignKey("llm_anthropic_configs.id"))
    ollama_config_id: Mapped[Optional[int]] = mapped_column(ForeignKey("llm_ollama_configs.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, ...)
    # CHECK constraint: exatamente o FK do `provider` é NOT NULL, os outros dois são NULL
```

4 linhas fixas. FK real pra cada uma das 3 tabelas de provider (não um `config_id` solto sem tipo).

---

## 4. Mudanças de arquitetura no backend

### 4.1 Variáveis "vivas" (`app_settings`, exceto seleção de API) — sem restart

Hoje o código inteiro lê configuração via `settings.x` ou `getattr(settings, "x", default)` — um objeto Pydantic **mutável**, carregado uma vez (`core/config.py:249`, `settings = Settings()`). Em vez de reescrever os ~50 pontos de leitura espalhados (`term_extraction.py`, `chat_service.py`, `statistical_inference_service.py`, `scopus_service.py`, `ops_service.py`, os 4 `query_builders/*`, `relevance_service.py`, `field_schema_service.py`...):

1. No boot, depois de conectar no banco, carregar todas as linhas de `app_settings` e fazer `setattr(settings, row.key, valor_convertido)` no singleton `settings` já existente.
2. Quando o front edita algo via API, o endpoint grava no banco **e** faz o mesmo `setattr` no singleton vivo — efeito imediato, sem restart.
3. **Nenhum dos ~50 pontos de leitura muda** — continuam lendo `settings.x` exatamente como hoje.

**Limitação conhecida**: só funciona porque o backend roda como processo único hoje (confirmado nos logs: `Uvicorn running on http://127.0.0.1:8000`, um worker). Com múltiplos workers, cada processo teria seu próprio `settings` em memória — precisaria de um mecanismo de invalidação entre processos (ex: Postgres `LISTEN`/`NOTIFY`, ou polling) se um dia escalar.

### 4.2 Variáveis de boot (`search_api_selection`, credenciais de API externa) — restart necessário

`container.py` lê `search_api_selection` (não mais os 5 booleans) e monta `patent_pairs`/`scholarly_pairs` com **um único** adapter por família — nunca mais os dois simultâneos como hoje é tecnicamente possível. Aceito ficar como boot-time: editar no front grava no banco, só aplica depois de reiniciar o backend.

### 4.3 IA — resolver com cache + invalidação

- **`LLMServiceFactory`**: ganha `create_from_config(provider, model, api_key, base_url=None) -> BaseLLMService`, recebendo dados já resolvidos em vez de ler `settings.llm_*` direto.
- **`LLMConfigResolver`** (novo): dado um `call_site`, busca `LLMCallSiteBinding` + a tabela de provider certa, devolve uma instância pronta de `BaseLLMService`. Roda com cache em memória por `call_site` (não uma vez só no boot como hoje) — invalidado no momento em que o binding daquele call site é atualizado via API. Isso é o que permite editar IA no front **sem restart**, diferente da seleção de API de busca.
- **`ChatService`**: troca `self.llm` único por `self.llm_resolver`, chamado com o `call_site` certo em cada um dos 3 métodos.
- **`ReportWriterService`**: mesma ideia, `call_site="report_writing"` — hoje só Ollama está implementado como provider real pra esse call site, mas o resolver já fica pronto pra aceitar Gemini/Anthropic ali no futuro (chat simples).

### 4.4 `container.py`

Para de instanciar os serviços de IA e os adapters de busca como singletons fixos calculados uma vez; passa a:
- Instanciar `LLMConfigResolver` (recebe sessão do banco) e injetar em `ChatService`/`ReportWriterService`.
- Ler `search_api_selection` pra decidir qual único adapter registrar por família (patent/scholarly).

---

## 5. Endpoints novos

`app/adapters/driving/http/config_router.py` (ou dividido em 2-3 routers):

- `GET/PUT /api/v1/config/settings` — lista/atualiza os escalares de `app_settings` (agrupados por `category` pro front)
- `GET/PUT /api/v1/config/search-apis` — lê/troca `search_api_selection` (2 famílias)
- `GET/POST/PUT/DELETE /api/v1/config/llm/gemini`
- `GET/POST/PUT/DELETE /api/v1/config/llm/anthropic`
- `GET/POST/PUT/DELETE /api/v1/config/llm/ollama`
- `GET /api/v1/config/llm/call-sites` — lista os 4 bindings + configs disponíveis (pros dropdowns)
- `PUT /api/v1/config/llm/call-sites/{call_site}` — troca a config de um call site (invalida cache do resolver)

Todo `GET` que devolve algo com `is_secret=True` (credenciais de API externa, `api_key` de IA) mascara o valor (ex: só últimos 4 caracteres). **Sem autenticação nos endpoints por enquanto** — combinado que fica como risco documentado, resolvido depois como projeto à parte.

---

## 6. Frontend

`ConfiguracoesTab.tsx` (hoje mock estático com array hardcoded) vira real:
- Seções pra escalares de `app_settings`, agrupadas por categoria (mesmas 6 seções do `VARIAVEIS_DE_CONFIGURACAO.md`).
- Seletor exclusivo (tipo radio button, não toggle independente) por família de API de busca — ativar um desativa o outro automaticamente, refletindo a constraint do banco.
- 3 listas CRUD (Gemini/Anthropic/Ollama) + 4 dropdowns de call site (um por call site, listando todas as configs das 3 tabelas juntas).
- `Step3.tsx` (hoje hardcoded `'ops'`/`'scopus'` literal) passa a consultar qual API está ativa por família em vez do literal fixo — resolve de vez a pergunta de "como o front escolhe a API" de mais cedo nesta conversa.

---

## 7. Migração/seed dos dados existentes

Migration Alembic única que:
1. Cria as 6 tabelas.
2. Semeia `app_settings` com os valores atuais de `core/config.py` (um `INSERT` por campo migrado, com `value_type`/`category`/`is_secret` corretos).
3. Semeia `search_api_selection`: `family='patent'` → `'ops'` se `OPS_ENABLED` true (ou `'lens_patent'` caso só esse esteja true); mesma lógica pra `scholarly`/Scopus/Lens Scholarly. Se ambos vierem `True` no `.env` atual (caso real hoje), **OPS/Scopus vencem** por padrão na semente (mantém o comportamento atual, que já usa só essas duas).
4. Semeia as 3 tabelas de IA a partir de `LLM_GEMINI_API_KEY`/`LLM_ANTHROPIC_API_KEY`/`OLLAMA_*` (só cria linha se a key/token existir).
5. Semeia os 4 `llm_call_site_bindings`: os 3 de query → o que `LLM_PROVIDER` apontava hoje; `report_writing` → a config Ollama criada.
6. `core/config.py` mantém os campos migrados só como fallback de leitura da migration (não lidos mais em runtime depois do boot) — remover de vez numa limpeza futura, mesmo espírito da limpeza das 5 variáveis mortas já feita.

---

## 8. Riscos/limitações documentados (aceitos por ora)

- **Sem autenticação** nos endpoints de configuração — qualquer um com acesso à API pode ler (mascarado) ou trocar credenciais/modelos. Mitigado parcialmente pelo mascaramento no `GET`; escrita fica sem proteção. Resolver auth é projeto à parte.
- **Restart necessário** pra `search_api_selection` e pras credenciais de API externa em `app_settings` — só os demais escalares e a seleção de IA são editáveis sem restart.
- **Single-process**: o mecanismo de `setattr` no singleton `settings` não propaga entre múltiplos workers uvicorn, se um dia o backend escalar horizontalmente.
- **Lens sem paridade de agregação**: se `lens_patent`/`lens_scholarly` virar a API ativa de uma família, a busca final roda sem `depositants`/`cpc`/`institutions`/`area_of_study` (só essas duas rotas OPS/Scopus têm essa agregação hoje) — aceito, fora de escopo desta migração.

---

## 9. Ordem sugerida de implementação

1. Modelos SQLAlchemy das 6 tabelas + migration Alembic (schema + seed)
2. Mecanismo de sync `app_settings` ↔ singleton `settings` (boot + endpoint de update)
3. `search_api_selection` + `container.py` lendo de lá (só no boot)
4. `LLMConfigResolver` + `LLMServiceFactory.create_from_config` + cache/invalidação
5. Refatorar `ChatService` (4 call sites) e `ReportWriterService` pra usar o resolver
6. Endpoints CRUD (settings genéricos, search-apis, IA)
7. Front: `ConfiguracoesTab.tsx` real + `Step3.tsx` consumindo a API ativa dinamicamente
