# Variáveis de Configuração

Documento de referência das variáveis de configuração do projeto (`core/config.py`, carregadas via `.env`). Cobre parâmetros que representam **escolhas** do sistema (thresholds, `top_k`, modelos de IA, flags, endereços de serviços externos) — não inclui credenciais/endereços de infraestrutura fixa que devem ficar hardcoded ou tratados à parte (banco de dados, secret key de JWT, credenciais do MinIO, endereço do ChromaDB, endereço do compilador LaTeX, bind de host/porta do servidor).

Todas as variáveis abaixo são lidas de `core/config.py` (classe `Settings`) e podem ser sobrescritas no `.env` usando o nome em `UPPER_SNAKE_CASE` (ex: `llm_provider` → `LLM_PROVIDER`).

---

## 1. Provedor de IA (LLM)

| Variável (.env) | Default | Descrição |
|---|---|---|
| `LLM_PROVIDER` | `mock` | Qual provedor de LLM usar: `gemini`, `anthropic` ou `mock` (respostas falsas, sem custo/rede - usado em testes/dev sem key). Lido por `services/llm/factory.py`. |
| `TEST_MODE` | `False` | Flag geral de modo de teste da aplicação. |
| `LLM_GEMINI_API_KEY` | _(vazio)_ | API key do Google Gemini. |
| `LLM_GEMINI_MODEL` | `gemini-2.0-flash-exp` | Modelo Gemini usado quando `LLM_PROVIDER=gemini`. |
| `LLM_ANTHROPIC_API_KEY` | _(vazio)_ | API key da Anthropic (console.anthropic.com - separada de uma assinatura Claude Pro). |
| `LLM_ANTHROPIC_MODEL` | `claude-haiku-4-5` | Modelo Claude usado quando `LLM_PROVIDER=anthropic`. |
| `LLM_KEYBERT_MODEL` | `distiluse-base-multilingual-cased-v2` | Modelo sentence-transformers usado pelo canal semântico do `TermExtractor` (KeyBERT). Alternativas comentadas no código: `all-mpnet-base-v2` (recomendado para patentes/textos técnicos), `allenai/specter` (papers acadêmicos). |

## 2. Relatório LaTeX / RAG local (Ollama)

| Variável (.env) | Default | Descrição |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endereço do serviço compatível com a API da OpenAI usado pra gerar o relatório (container Ollama local em dev, ou endpoint de intranet em produção - mesmo adapter nos dois casos). |
| `OLLAMA_API_KEY` | _(vazio)_ | Bearer token do endpoint acima (vazio para Ollama local, que não exige auth). |
| `OLLAMA_MODEL` | `qwen2.5:3b-instruct` | Modelo usado na geração do relatório via esse endpoint. |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | `600` | Timeout (segundos) das chamadas a esse endpoint - modelos locais/intranet podem ser bem mais lentos que uma API na nuvem. |
| `RAG_TOP_K_PER_SECTION` | `5` | Quantos trechos o RAG (ChromaDB) recupera por seção do relatório antes de montar o prompt de geração. |

## 3. APIs Externas de Busca

| Variável (.env) | Default | Descrição |
|---|---|---|
| `LENS_API_TOKEN` | _(vazio)_ | Token da API Lens (patentes/artigos - `lens_patent`/`lens_scholarly`). |
| `OPS_CONSUMER_KEY` | _(vazio)_ | Consumer key OAuth2 da API OPS (European Patent Office). |
| `OPS_CONSUMER_SECRET` | _(vazio)_ | Consumer secret OAuth2 da API OPS. |
| `SCOPUS_API_KEY` | _(vazio)_ | API key da Scopus (Elsevier). |

## 4. Configuração de Busca (Probe / Final)

| Variável (.env) | Default | Descrição |
|---|---|---|
| `SEARCH_YEAR_FROM` | `2015` | Ano inicial padrão da janela de busca (probe search / geração de query). Não é usado pela busca final, que sempre recebe `year_from`/`year_to` explícitos na rota. |
| `SEARCH_YEAR_TO` | `2026` | Ano final padrão da mesma janela. |
| `PROBE_TOP_K` | `10` | `top_k` padrão da probe search no backend (distinto do `topK` que o front manda explicitamente em `runProbeSearch` - `frontend/src/services/probeQuery.ts`). |
| `FINAL_TOP_K` | `100` | `top_k` usado na busca final (`run_final_search`), bem maior que o da probe porque é sobre esse volume que os agregados finais (depositantes/instituições/CPC/área) são calculados. |

## 5. Relevância e Complexidade de Query

| Variável (.env) | Default | Descrição |
|---|---|---|
| `RELEVANCE_THRESHOLD` | `0.4` | Corte mínimo de relevância usado na filtragem de resultados. |
| `LLM_MAX_QUERY_COMPLEXITY` | `0.6` | Teto de complexidade (0-100 na UI, aqui em fração) aceito pra uma query gerada por IA antes de forçar nova tentativa/simplificação (ver mensagens "Query complexity (X/100) exceeds limit" em `chat_service.py`). |

## 6. Extração de Termos (NLP) - `TermExtractor`

| Variável (.env) | Default | Descrição |
|---|---|---|
| `TERM_EXTRACTION_TITLE_WEIGHT` | `3.0` | Peso do título no BM25F (canal lexical) - título pesa mais que abstract por ser mais denso em termos-chave. |
| `TERM_EXTRACTION_ABSTRACT_WEIGHT` | `1.0` | Peso do abstract no BM25F. |
| `TERM_EXTRACTION_SCORE_THRESHOLD` | `0.024` | Corte mínimo de `final_rrf_score` (escala RRF, não 0-1) pra um termo ser retornado. Aumentar → menos termos, só os melhores; diminuir → mais termos. Calibrado empiricamente (~459 termos: min 0.0184, max 0.0325, mediana 0.0244). |
| `TERM_EXTRACTION_MIN_RETURNED_TERMS` | `10` | Piso de termos devolvidos independente do threshold acima - como o `final_rrf_score` é relativo ao rank dentro do próprio lote (não uma escala absoluta), um lote inteiro pode cair abaixo do threshold; nesse caso completa com os próximos melhor-ranqueados em vez de devolver lista vazia. |
| `TERM_EXTRACTION_UNIGRAM_PENALTY` | `-0.4` | Ajuste de ranking (via RRF, não somado ao score) pra termos de 1 palavra - penaliza unigramas, que tendem a ser genéricos. |
| `TERM_EXTRACTION_BIGRAM_BONUS` | `0.0` | Mesma lógica, pra termos de 2 palavras. |
| `TERM_EXTRACTION_TRIGRAM_BONUS` | `0.25` | Mesma lógica, pra termos de 3+ palavras - bonificados por serem tipicamente mais específicos/úteis pra busca. |
| `TERM_EXTRACTION_BAD_BIGRAM_PENALTY` | `-0.8` | Penalidade extra quando um bigrama bate um padrão POS "ruim" (ex: advérbio+verbo, sinal de fragmento não-nominal). |
| `TERM_EXTRACTION_BAD_TRIGRAM_PENALTY` | `-0.8` | Mesma penalidade, pra trigramas. |
| `TERM_EXTRACTION_BM25_K1` | `1.2` | Parâmetro `k1` do BM25F (saturação de frequência de termo) - default padrão do Okapi BM25. |
| `TERM_EXTRACTION_BM25_B` | `0.75` | Parâmetro `b` do BM25F (normalização por tamanho do documento) - default padrão do Okapi BM25. |
| `TERM_EXTRACTION_RRF_K` | `60` | Constante `k` do Reciprocal Rank Fusion (usado nos 2 estágios: BM25F×KeyBERT e salience×qualidade estrutural) - mesmo default usado pelo Elasticsearch. |
| `TERM_EXTRACTION_CVALUE_MIN_FREQUENCY` | `1` | Frequência bruta mínima pra um candidato sobreviver ao filtro de C-value (redundância de termos aninhados). |

## 7. Fuzzy Matching de Entidades

| Variável (.env) | Default | Descrição |
|---|---|---|
| `DEPOSITANT_FUZZY_MATCH_THRESHOLD` | `90.0` | Score mínimo (0-100, RapidFuzz `WRatio`) pra agrupar depositantes de patente / instituições de artigo com nomes parecidos (ex: variações de grafia/sufixo societário) como a mesma entidade antes de contar. Diminuir agrupa mais agressivamente (risco de falso positivo); aumentar agrupa menos. |

## 8. Inferência Estatística (Chao1 + Bootstrap)

| Variável (.env) | Default | Descrição |
|---|---|---|
| `STATISTICAL_INFERENCE_MAX_DURATION_SECONDS` | `60` | Teto de tempo pra rota de inferência final pedir iterações extras de busca até a amostra "saturar" (Chao1) ou esse tempo acabar - o que vier primeiro. |
| `STATISTICAL_INFERENCE_SATURATION_THRESHOLD` | `0.5` | Cobertura estimada (S_obs/S_chao1) abaixo da qual a amostra é considerada insuficiente. |
| `STATISTICAL_INFERENCE_F1_RATIO_THRESHOLD` | `0.7` | Proporção de singletons (categorias vistas 1x) acima da qual a amostra é considerada insuficiente (sinal de cauda longa não capturada). |
| `STATISTICAL_INFERENCE_F2_MIN` | `5` | Número mínimo de doubletons (categorias vistas 2x) pra uma estimativa Chao1 ser considerada estável. |
| `STATISTICAL_INFERENCE_BOOTSTRAP_RESAMPLES` | `1000` | Número de reamostragens (bootstrap com reposição) usadas pra medir estabilidade do ranking top-10. |
| `STATISTICAL_INFERENCE_MAX_TITLES_FOR_RELEVANCE` | `20` | Teto de títulos amostrados aleatoriamente pra calcular a relevância semântica (SBERT) média com o tema pesquisado. |

## 9. Feature Flags - APIs de Busca Final Habilitadas

| Variável (.env) | Default | Descrição |
|---|---|---|
| `LENS_PATENT_ENABLED` | `True` | Habilita a API Lens Patent na busca final. |
| `LENS_SCHOLARLY_ENABLED` | `True` | Habilita a API Lens Scholarly na busca final. |
| `OPS_ENABLED` | `True` | Habilita a API OPS (patentes) na busca final. |
| `SCOPUS_ENABLED` | `True` | Habilita a API Scopus (artigos) na busca final. |
| `LENS_ENABLED` | `True` | Retrocompatibilidade - liga/desliga as duas APIs Lens de uma vez (sobrepõe os dois flags individuais acima quando presente). |

## 10. Frontend (`frontend/.env`)

| Variável | Default | Descrição |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Endereço base do backend que o front consome (`apiClient` em `frontend/src/services/api.ts`). |

---

## Variáveis de sample size do front (fora do `.env`, hardcoded em código)

Não fazem parte do `Settings`/`.env` - são constantes TypeScript, mas controlam volume de dados de forma parecida às acima:

| Constante | Arquivo | Default | Descrição |
|---|---|---|---|
| `topK` (parâmetro de `runProbeSearch`) | `frontend/src/services/probeQuery.ts` | `20` | Quantos itens a probe search pede à API (backend soma +10 de buffer internamente). |
| `ANALYSIS_SAMPLE_SIZE` | `frontend/src/services/finalQuery.ts` | `30` | Quantos dos itens buscados (com título+abstract) de fato entram no `TermExtractor`. |

---

## Excluído deste documento (propositalmente)

`DATABASE_URL`, `SECRET_KEY`/`ALGORITHM` (JWT), `MINIO_ENDPOINT`/`MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`/`MINIO_BUCKET`/`MINIO_SECURE`, `CHROMA_HOST`/`CHROMA_PORT`, `LATEX_COMPILER_URL`, `HOST`/`PORT` - endereços e credenciais de infraestrutura fixa, tratados à parte por convenção de segurança, não "escolhas" de comportamento do sistema.

## Removidas (2026-09-19)

`PROBE_API`, `PROBE_API_EXT`, `TERM_EXTRACTION_MMR_LAMBDA`, `TERM_EXTRACTION_MMR_SIMILARITY_THRESHOLD`, `TERM_EXTRACTION_OVERLAP_THRESHOLD` - estavam definidas em `core/config.py`/`.env.example` mas nunca eram lidas em nenhum outro lugar do código (confirmado por busca em todo o repo). Removidas de `core/config.py`, `.env.example` e `.env` local.
