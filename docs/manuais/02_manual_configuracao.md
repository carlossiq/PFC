# Manual de Configuração — AGIA (Prospecção Tecnológica)

*Atualizado em 26/10/2026.*

Este manual descreve o que o administrador pode configurar: variáveis do `.env`, provedores
de IA, APIs de busca, parâmetros da tela Configurações e a capa do relatório. Pré-requisito:
o sistema instalado, com o banco migrado e o backend no ar (manual de instalação).

---

## 1. Onde cada valor é definido

| Onde | O que fica ali | Quando vale |
|---|---|---|
| `.env` (raiz do projeto) | Infraestrutura, flags de API e credenciais | Infraestrutura e flags: lidas a cada subida. Credenciais: copiadas para o banco na primeira subida. |
| Banco de dados | Todos os parâmetros editáveis | Fonte da verdade depois da primeira subida. |
| Tela Configurações (ou API `/config/*`) | Interface para editar o banco | Onde alterar valores no dia a dia. |

**Regra:** parâmetros de comportamento (busca, IA, extração de termos, relatório) são
alterados só pela tela Configurações. Editar esses valores no `.env` não tem efeito, porque
eles já foram gravados no banco na primeira subida.

Para voltar um parâmetro ao padrão do código, apague a linha correspondente na tabela
`app_settings`: o backend recria a chave com o padrão na próxima subida.

---

## 2. Arquivo `.env`

Convenção: o nome da variável é o nome do parâmetro em `UPPER_SNAKE_CASE`.

### 2.1 Infraestrutura e aplicação

| Variável | Padrão | Uso |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/pfc_db` | Banco PostgreSQL. |
| `ENVIRONMENT` | `development` | Com `production`, o banco usa pool de conexões. |
| `DEBUG` | `True` | Modo de depuração do FastAPI. Desligue em ambiente compartilhado. |
| `LOG_LEVEL` | `INFO` | Nível de log. |
| `SQL_ECHO` | `False` | Registra todas as queries SQL. Use só para depuração. |
| `API_PREFIX` | `/api/v1` | Prefixo das rotas. Mudar exige ajustar `VITE_API_BASE_URL`. |
| `ALLOWED_ORIGINS` | `["http://localhost:3000","http://localhost:5173","http://localhost:8000"]` | Origens do CORS. **Formato JSON obrigatório.** |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE` | `localhost:9000`, `minioadmin`, `minioadmin`, `session-charts`, `False` | Armazenamento dos gráficos, figuras e capa. O bucket é criado na subida. |
| `CHROMA_HOST`, `CHROMA_PORT` | `localhost`, `8001` | Serviço ChromaDB (RAG do relatório). |
| `LATEX_COMPILER_URL` | `http://localhost:8090` | Compilador de PDF. |
| `LANGUAGETOOL_URL` | `http://localhost:8010` | Revisão de texto. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Servidor compatível com a API da OpenAI (local ou da intranet). Copiado para o banco na primeira subida. |
| `OLLAMA_API_KEY` | vazio | Bearer token, se o servidor exigir. |
| `VITE_API_BASE_URL` (em `frontend/.env`) | `http://localhost:8000/api/v1` | Endereço da API vista pelo navegador. Reinicie o `npm run dev` após mudar. |

Se o MinIO não responder, o backend sobe com aviso (`minio_bucket_ensure_failed`), mas gráficos,
anexos e a capa do relatório não são persistidos.

### 2.2 Flags de API

| Variável | Padrão | Uso |
|---|---|---|
| `LENS_PATENT_ENABLED` | `True` | Lens como fonte de patentes. |
| `LENS_SCHOLARLY_ENABLED` | `True` | Lens como fonte de artigos. |
| `OPS_ENABLED` | `True` | OPS para patentes. Na primeira subida, define a API de patentes ativa. |
| `SCOPUS_ENABLED` | `True` | Scopus para artigos. Na primeira subida, define a API de artigos ativa. |
| `LENS_ENABLED` | `True` | Liga ou desliga as duas APIs Lens de uma vez. |

Depois da primeira subida, a API ativa é escolhida na tela Configurações › Busca.

### 2.3 Credenciais

Copiadas para o banco na primeira subida. Depois, altere-as na tela Configurações › Busca e
reinicie o backend.

| Variável | Uso |
|---|---|
| `LENS_API_TOKEN` | Token Lens (patentes e artigos). |
| `OPS_CONSUMER_KEY`, `OPS_CONSUMER_SECRET` | Chave e segredo OAuth2 da OPS. |
| `SCOPUS_API_KEY` | Chave da Scopus. |
| `LLM_GEMINI_API_KEY` | Chave do Google Gemini. Se preenchida na primeira subida, cadastra o provedor `gemini`. |
| `LLM_ANTHROPIC_API_KEY` | Chave da Anthropic. Se preenchida na primeira subida, cadastra o provedor `anthropic`. |
| `OLLAMA_API_KEY` | Token do servidor Ollama, se houver. |

---

## 3. Provedores de IA

O sistema usa IA em cinco pontos de uso, e cada um pode apontar para um provedor diferente:

| Ponto de uso | Função |
|---|---|
| Geração de temas candidatos | Variações do tema, no refinamento de parâmetros. |
| Geração de query (probe) | Query da busca exploratória. |
| Geração de query final | Query da busca final. |
| Redação do relatório | Texto das seções. |
| Revisão de texto do relatório | Sugestões da revisão com IA. |

### 3.1 Cadastrar um provedor

Em **Configurações › Inteligência Artificial › Provider**, clique em **Adicionar nova
configuração**.

- **Provider**: `gemini`, `anthropic` ou `ollama`. O `ollama` atende qualquer servidor
  compatível com a API da OpenAI, local ou da intranet.
- **Modelo**: nome do modelo no provedor (ex.: `gemini-2.0-flash-exp`, `claude-haiku-4-5`,
  `qwen2.5:3b-instruct`).
- **Base URL**: obrigatória para `ollama`.
- **API key**: obrigatória para `gemini` e `anthropic`. Opcional para `ollama`.

A mesma combinação de provedor, modelo e URL não pode ser cadastrada duas vezes.

Modelos iniciais: `qwen2.5:3b-instruct` (Ollama, sempre cadastrado), `gemini-2.0-flash-exp`
(só se `LLM_GEMINI_API_KEY` estiver preenchida) e `claude-haiku-4-5` (só se
`LLM_ANTHROPIC_API_KEY` estiver preenchida).

### 3.2 Escolher o provedor de cada ponto de uso

Em **Qual IA cada chamada usa**, escolha uma das configurações cadastradas para cada ponto de
uso. A troca vale para a próxima chamada.

Para remover um provedor, use **Remover configuração**. Antes, reaponte os pontos de uso que
o utilizavam.

A chave gravada aparece mascarada nas listagens.

---

## 4. APIs de busca

| Família | Fontes | Padrão na primeira subida |
|---|---|---|
| Patentes | OPS, Lens | OPS |
| Artigos | Scopus, Lens | Scopus |

A OpenAlex também é consultada como complemento para resumos. Ela é pública e não precisa de
configuração.

**Passo a passo:**

1. Obtenha as credenciais (seção 2.3).
2. Preencha-as no `.env` antes da primeira subida, ou depois em Configurações › Busca.
3. Escolha a API ativa de cada família na tela Busca.
4. **Reinicie o backend.** Os adaptadores de busca são montados na subida. Sem o reinício, a
   API configurada não aparece como disponível.

Sem credencial, a família é pulada na montagem (aviso `container_*_api_skipped` com
`missing_credentials`). Com nenhuma API de patentes e nenhuma de artigos configurada, nenhuma
prospecção retorna resultados.

---

## 5. Parâmetros da tela Configurações

A tela tem seis abas: **Inteligência Artificial**, **Busca**, **Extração de Termos**,
**Relevância & Qualidade**, **Inferência Estatística** e **Geral**. Os valores são gravados e
aplicados na hora ao editar, sem botão de salvar, exceto onde indicado como reinício.

Os padrões são os do código. O valor vigente é o que aparece na tela.

### 5.1 Geral

| Parâmetro | Chave | Padrão | Observação |
|---|---|---|---|
| Modelo de teste | `test_mode` | `false` | Com `true`, todas as chamadas de IA devolvem respostas falsas. Não ligar em uso normal. |
| Modelo do KeyBERT | `llm_keybert_model` | `distiluse-base-multilingual-cased-v2` | **Reinício obrigatório.** Modelo de embeddings da extração de termos e do RAG. |
| Timeout do Ollama (s) | `ollama_request_timeout_seconds` | `600` | Espera máxima por resposta do servidor Ollama. |
| Corte relativo do RAG | `rag_relative_min_relevance` | `0.75` | Descarta trechos muito abaixo do melhor para o prompt de cada seção. |
| Top-K do RAG por seção | `rag_top_k_per_section` | `5` | Trechos recuperados por seção. |
| Idioma da revisão de texto | `languagetool_language` | `pt-BR` | Idioma da revisão ortográfica. |

### 5.2 Busca

| Parâmetro | Chave | Padrão | Observação |
|---|---|---|---|
| Ano inicial padrão | `search_year_from` | `2015` | Início da janela da busca. |
| Ano final padrão | `search_year_to` | `2026` | Não pode ser maior que o ano atual. |
| Top-K da probe | `probe_top_k` | `10` | Resultados da busca exploratória. |
| Top-K da busca final | `final_top_k` | `100` | Resultados da busca final. |
| Credenciais | `lens_api_token`, `ops_consumer_key`, `ops_consumer_secret`, `scopus_api_key` | vazio | Seção 4. |

### 5.3 Relevância & Qualidade

| Parâmetro | Chave | Padrão | Observação |
|---|---|---|---|
| Threshold de relevância | `relevance_threshold` | `0.4` | Corte mínimo para um resultado ser considerado válido. |
| Complexidade máxima de query | `llm_max_query_complexity` | `0.6` | Teto de complexidade de query gerada por IA. |
| Threshold de fuzzy match | `depositant_fuzzy_match_threshold` | `90.0` | Similaridade (0 a 100) para tratar nomes parecidos como a mesma entidade. Valores baixos agrupam entidades diferentes. |

### 5.4 Extração de Termos

| Parâmetro | Chave | Padrão |
|---|---|---|
| Peso do título | `term_extraction_title_weight` | `3.0` |
| Peso do abstract | `term_extraction_abstract_weight` | `1.0` |
| Threshold de score | `term_extraction_score_threshold` | `0.024` |
| Piso de termos devolvidos | `term_extraction_min_returned_terms` | `10` |
| Penalidade de unigrama | `term_extraction_unigram_penalty` | `-0.4` |
| Bônus de bigrama | `term_extraction_bigram_bonus` | `0.0` |
| Bônus de trigrama | `term_extraction_trigram_bonus` | `0.25` |
| Penalidade de bigrama ruim | `term_extraction_bad_bigram_penalty` | `-0.8` |
| Penalidade de trigrama ruim | `term_extraction_bad_trigram_penalty` | `-0.8` |
| BM25 k1 | `term_extraction_bm25_k1` | `1.2` |
| BM25 b | `term_extraction_bm25_b` | `0.75` |
| RRF k | `term_extraction_rrf_k` | `60` |
| Frequência mínima (C-value) | `term_extraction_cvalue_min_frequency` | `1` |

O peso do título define quanto os termos encontrados no título pesam em relação aos do resumo.
O threshold de score define quantos termos passam; se o lote inteiro ficar abaixo dele, entra o
piso de termos.

### 5.5 Inferência Estatística

| Parâmetro | Chave | Padrão |
|---|---|---|
| Duração máxima (s) | `statistical_inference_max_duration_seconds` | `60` |
| Threshold de saturação | `statistical_inference_saturation_threshold` | `0.5` |
| Threshold de singletons | `statistical_inference_f1_ratio_threshold` | `0.7` |
| Mínimo de doubletons | `statistical_inference_f2_min` | `5` |
| Reamostragens (bootstrap) | `statistical_inference_bootstrap_resamples` | `1000` |
| Máximo de títulos (relevância) | `statistical_inference_max_titles_for_relevance` | `20` |

Esses parâmetros controlam quando a busca final é repetida para cobrir melhor o campo: a
inferência pede mais resultados até a amostra saturar ou até o tempo máximo.

---

## 6. Capa do relatório

Em **Configurações › Geral › Imagem de capa do relatório**:

- **Trocar imagem** envia uma capa própria. Ela nunca é sobrescrita pelo sistema.
- **Restaurar imagem padrão** volta ao brasão do sistema.

A capa padrão é enviada ao MinIO na subida, se ainda não houver capa.

API: `GET`, `POST` e `DELETE /config/report-cover-image` (o `DELETE` restaura a capa padrão).

---

## 7. Compilador de PDF

O PDF é gerado pelo serviço `latex-compiler`, sem acesso à internet. Ele usa `pdflatex`, com
limite de 120 segundos por compilação, e não suporta `fontspec`, XeLaTeX nem LuaLaTeX.

Para adicionar um pacote LaTeX ao compilador, inclua-o na lista de instalação do Dockerfile
de `latex-compiler/` e reconstrua o serviço (`docker compose up -d --build latex-compiler`).
Isso exige internet no momento do build.

---

## 8. Configuração pela API

Todas as rotas estão sob `/api/v1`. Documentação interativa: <http://localhost:8000/docs>.

| Método e rota | Função |
|---|---|
| `GET /config/settings` | Lista as configurações editáveis, com valor, tipo, categoria e limites. |
| `PUT /config/settings/{key}` | Altera uma configuração. Corpo: `{"value": "..."}`. O valor é sempre texto, mesmo para números e booleanos (ex.: `"2015"`, `"false"`). |
| `GET /config/search-apis` | Opções de API por família e a ativa. |
| `PUT /config/search-apis/{family}` | Troca a API ativa. Família: `patent` ou `scholarly`. Corpo: `{"active_provider_code": "ops"}`. Reinício obrigatório. |
| `GET /config/llm/providers` | Provedores suportados. |
| `GET /config/llm/configs` | Configurações de IA cadastradas (chave mascarada). |
| `POST /config/llm/configs` | Cadastra uma configuração de IA. |
| `PUT /config/llm/configs/{id}` | Altera uma configuração de IA. |
| `DELETE /config/llm/configs/{id}` | Remove uma configuração de IA. |
| `GET /config/llm/call-sites` | Mostra qual configuração atende cada ponto de uso. |
| `PUT /config/llm/call-sites/{call_site}` | Aponta um ponto de uso para outra configuração. |
| `GET`, `POST`, `DELETE /config/report-cover-image` | Capa do relatório. |

---

## 9. Quando reiniciar o backend

A maioria das alterações vale na hora. **Reinicie o backend** após:

- Trocar ou adicionar credenciais de OPS, Scopus ou Lens.
- Trocar a API ativa de patentes ou de artigos.
- Trocar o modelo do KeyBERT (`llm_keybert_model`).
- Alterar `.env`: credenciais, flags, `ALLOWED_ORIGINS`, `DATABASE_URL` e `API_PREFIX`.

Para reiniciar, interrompa o processo (`Ctrl+C`) e suba de novo.

---

## 10. Segurança

- **Troque as senhas padrão** de PostgreSQL, MinIO e pgAdmin antes de usar o sistema em rede
  compartilhada.
- **Chaves ficam no banco.** Restrinja o acesso ao PostgreSQL e não faça backup em local aberto.
- **Não envie o `.env` a repositórios.** Ele contém credenciais.
- **Modo de teste desligado** (`test_mode = false`) em uso real.
- **Limite `ALLOWED_ORIGINS`** às origens que de fato acessam a API.
- **Limite as portas publicadas** à máquina local, por exemplo `127.0.0.1:5432:5432` na configuração do serviço.
