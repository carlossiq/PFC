# Documentação Técnica do Sistema — Base para o Relatório do PFC

> **Como usar este documento**: este `.md` é uma fonte de verdade técnica, extraída diretamente do código-fonte atual (não de documentação antiga, que em vários pontos está desatualizada — ver §16). Ele deve ser usado como insumo para redigir/atualizar as seções do relatório do PFC. Cada seção indica explicitamente se o recurso está **✅ Implementado** ou **🔜 Planejado (ainda não implementado)** — essa distinção é crítica e não deve ser perdida na redação do relatório.

---

## 0. Visão Geral do Sistema

O sistema é uma ferramenta de **prospecção tecnológica** (technology foresight): a partir de um tema de pesquisa informado pelo usuário, ele (1) refina o tema com apoio de LLM, (2) constrói e executa buscas exploratórias ("probe") em bases de patentes (EPO/OPS — Espacenet) e de artigos científicos (Scopus, com enriquecimento via OpenAlex), (3) extrai termos-chave relevantes dos resultados via NLP local, (4) usa esses termos para gerar uma query final (em três níveis de abrangência: específica, balanceada, ampla), (5) executa a busca final em maior volume, e (6) gera gráficos analíticos (curva S, distribuições, rankings) a partir dos documentos recuperados e (7) compila tudo isso em um relatório de prospecção tecnológica no padrão AGITEC/REPTEC (`.tex` editável no navegador + PDF), redigido por um LLM local via RAG, com revisão de texto assistida (LanguageTool + IA opcional) — ✅ implementado de ponta a ponta (§13).

**Stack atual**: backend Python (FastAPI, async, SQLAlchemy 2.0 async), frontend React + TypeScript (Vite, Zustand, Tailwind), PostgreSQL como banco relacional, MinIO (objetos: PNGs, `.tex`, PDF, anexos), ChromaDB (RAG), LLMs configuráveis **por ponto de uso** (`theme_candidates`, `probe_query`, `final_query`, `report_writing`, `report_review` — `LLMConfigResolver`, editável na tela de Configurações; provedores Anthropic, Gemini ou OpenAI-compatible/Ollama, hoje apontados para Ollama `gemma3:4b` local), um pipeline NLP local (spaCy/PatternRank + BM25F + KeyBERT + RRF + C-value, §5) para extração de termos, e containers auxiliares `latex-compiler` (TeX Live) e `languagetool` (revisão ortográfica/gramatical).

---

## 1. Arquitetura Geral do Backend: Hexagonal (Ports & Adapters)

O backend segue **Arquitetura Hexagonal** (Ports & Adapters), documentada explicitamente em `notes/add1.txt`. A justificativa central, citada diretamente da nota de projeto:

> "Prospecção tecnológica tem uma característica rara: você depende pesadamente de fontes externas que mudam com frequência e que você não controla. A Lens muda seu esquema de resposta, a OPS depreca endpoints, a Scopus altera limites de requisição, a Anthropic lança novos modelos... No hexagonal, essas mudanças ficam contidas nos driven/adapters — o core/ não sabe que aconteceu nada."

> "O core recebe uma porta (`Port`) de busca e uma porta de LLM por parâmetro. Isso significa que nos testes você instancia o serviço com um Mock — sem subir ChromaDB, sem chamar a API da USPTO, sem gastar tokens."

Ou seja, a escolha arquitetural foi feita para dar **escalabilidade de manutenção**: cada integração externa (busca ou LLM) é isolada em um adaptador substituível, e o núcleo de regras de negócio nunca importa bibliotecas de terceiros diretamente — apenas contratos (`Protocol`/interfaces) definidos pelo próprio domínio. Isso permite trocar/adicionar provedores (nova API de busca, novo provedor de LLM) sem alterar a lógica de negócio, e testar essa lógica sem depender de rede ou de custos de API.

### 1.1 As camadas, com exemplos concretos do repositório

| Camada | Diretório | Responsabilidade | Exemplos |
|---|---|---|---|
| **Domain** | `app/core/domain/` | Tipos de dados puros, sem I/O | `types.py`: `SearchResult`, `SearchError`, `LLMRequest`, `LLMResponse`, `TermGroup`, `TextualQuery`, `Embedding` |
| **Ports** | `app/core/ports/outbound/` | Contratos (`Protocol`) que o núcleo depende, mas não implementa | `LLMPort`, `EmbeddingPort`, `PatentSearchPort`/`ScholarlySearchPort`, `PatentQueryBuilderPort`/`ScholarlyQueryBuilderPort`, `*RepositoryPort`, `VectorStorePort` |
| **Services (core)** | `app/core/services/` | Regras de negócio puras, sem framework | `chat_service.py` (orquestração do fluxo), `query_complexity.py` (`QueryComplexityAnalyzer`), `dedup_service.py`, `report_service.py` (gráficos), `rag_service.py` |
| **Driven Adapters** | `app/adapters/driven/` | Implementam os *ports*, conectando a integrações reais | `llm/anthropic_adapter.py`, `llm/gemini_adapter.py`, `llm/mock_adapter.py`, `search/*_adapter.py`, `query_builders/*_adapter.py`, `persistence/*_adapter.py`, `nlp/embedding_adapter.py` |
| **Driving Adapters** | `app/adapters/driving/` | Chamam o núcleo a partir do mundo externo | `http/chat_router.py`, `http/research_session.py`, `http/session_input.py`, `http/report_router.py`, `http/health_router.py`, middleware de logging |

### 1.2 Composição (Dependency Injection manual)

Não há framework de DI: `app/container.py::build_container(settings)` é uma função que monta um `dict` de serviços prontos (armazenado em `app.state.container`), lido depois pelas rotas. O padrão de seleção de adaptador é sempre o mesmo — por *feature flag* + presença de credencial:

```python
if provider == "anthropic" and settings.llm_anthropic_api_key:
    service = AnthropicLLMService(api_key=..., model=settings.llm_anthropic_model)
    return AnthropicLLMAdapter(service)
```

Cada fonte de busca (Lens Patente, Lens Scholarly, OPS, Scopus) só é instanciada `if settings.<fonte>_enabled and settings.<fonte>_api_key`, sendo empacotada em pares `(SearchAdapter, QueryBuilderAdapter)` — adicionar/remover uma fonte de busca é uma mudança **apenas no container**, nunca no núcleo (`ChatService`). Esse é o mecanismo concreto que sustenta o argumento de escalabilidade: uma nova API de busca no futuro (ex.: USPTO, Derwent) exige apenas um novo par adaptador+query builder, registrado no container — o `ChatService` já está escrito para operar sobre uma lista de pares, sem saber quantas nem quais fontes existem.

Se as credenciais de LLM não estão configuradas, o container faz *fallback* silencioso para `MockLLMAdapter`, "para que o servidor suba sem erro em qualquer ambiente" — uma decisão deliberada de robustez de deploy.

### 1.3 Princípios SOLID Aplicados na Arquitetura

A aplicação dos princípios SOLID no backend não foi um exercício isolado, mas uma consequência direta da escolha pela Arquitetura Hexagonal descrita acima: separar núcleo de regras de negócio, contratos (*ports*) e integrações externas (*adapters*) já força boa parte da disciplina que o SOLID formaliza. A seguir, cada princípio é analisado com evidência concreta do código, incluindo um exemplo local (módulo de geração de relatórios, `app/core/services/report_service.py`, §10) que ilustra os princípios em escala menor.

**Princípio da Responsabilidade Única (SRP)**

O módulo de geração de gráficos de report foi dividido em três arquivos, cada um com uma única razão para mudar:

| Arquivo | Responsabilidade única |
|---|---|
| `app/adapters/driving/http/report_router.py` | Tradução HTTP: validação de sessão, montagem de queries SQL, conversão ORM→dict |
| `app/core/services/report_service.py` | Orquestração e renderização (matplotlib) dos PNGs |
| `app/core/services/s_curve.py` | Ajuste estatístico puro (Fisher-Pry/scipy), sem I/O e sem dependência de matplotlib |

Essa separação evita que uma mudança na fórmula de ajuste da curva logística exija tocar em código de desenho de gráfico, e vice-versa — cada módulo muda por um motivo diferente. O mesmo padrão se repete em escala de sistema: `ChatService` orquestra o fluxo de negócio, mas nunca implementa uma chamada HTTP a uma API externa — isso é responsabilidade exclusiva dos *driven adapters* (`app/adapters/driven/search/*.py`, `app/adapters/driven/llm/*.py`).

**Princípio Aberto/Fechado (OCP)**

A geração dos gráficos de report (`ReportService.generate_session_report`) é guiada por uma lista declarativa de especificações de gráfico, iterada em laço, em vez de uma sequência de chamadas manuais a cada tipo de gráfico. Adicionar um novo gráfico (por exemplo, distribuição por *assignee*) passa a ser uma questão de **acrescentar um item à lista de especificações**, sem alterar a lógica de orquestração existente — o método está fechado para modificação, mas aberto para extensão.

O mesmo princípio orienta o ajuste da curva S: os limiares que definem os pontos de Crescimento e Saturação (`growth_threshold`, `saturation_threshold`) são parâmetros de `fit_s_curve`, nunca valores fixos na fórmula — o que permite calibrar o critério de "início do crescimento real" por área tecnológica sem alterar `s_curve.py`.

Em escala de sistema, o mesmo padrão está no `app/container.py`: adicionar uma nova fonte de busca (ex.: USPTO) é uma mudança **apenas no container** — registrar um novo par `(Adapter, QueryBuilderAdapter)` — sem tocar em `ChatService`, que já opera genericamente sobre uma lista de pares de fontes.

**Princípio da Substituição de Liskov (LSP)**

Não avaliável no módulo de report, que não define hierarquias de herança. Em escala de sistema, porém, o LSP é o princípio que sustenta a camada de *driven adapters*: `AnthropicLLMAdapter`, `GeminiLLMAdapter` e `MockLLMAdapter` implementam o mesmo contrato (`LLMPort`) e são intercambiáveis sem que `ChatService` precise saber qual está em uso — o comportamento observável pelo consumidor da porta é preservado por qualquer implementação. O *fallback* silencioso para `MockLLMAdapter` quando não há credenciais configuradas (§1.2) só é seguro porque essa substituição respeita LSP: nenhum código que depende de `LLMPort` quebra ao trocar a implementação concreta.

**Princípio da Segregação de Interfaces (ISP)**

Os schemas Pydantic de `schemas/report.py` são deliberadamente estreitos: `GeneratedChart`, `PatentSCurveRequest`, `SCurveFitQuality`, `SCurveFit` e `ReportGraphicsResponse` expõem apenas os campos que seu consumidor específico precisa, em vez de um schema único genérico para "dados de report". O mesmo princípio aparece nas *ports* do núcleo (`app/core/ports/outbound/`): `LLMPort` e `EmbeddingPort` são contratos distintos e mínimos — um serviço que só precisa gerar embeddings depende exclusivamente de `EmbeddingPort`, sem carregar métodos de chat/LLM que nunca usaria.

**Princípio da Inversão de Dependência (DIP)**

Este é o princípio mais visivelmente ligado à escolha arquitetural do projeto: `ChatService` depende de `LLMPort` e `PatentSearchPort`/`ScholarlySearchPort` — abstrações (`Protocol`) definidas pelo próprio domínio — nunca de bibliotecas concretas como o SDK da Anthropic ou o cliente HTTP da OPS. A implementação concreta é decidida e injetada em `build_container()`, mantendo o núcleo de negócio livre de dependências de infraestrutura (justificativa citada acima: mudanças em APIs externas "ficam contidas nos driven/adapters — o core/ não sabe que aconteceu nada").

O módulo de report segue uma versão mais modesta do mesmo princípio: `report_router.py` obtém `ReportService` via o container (`request.app.state.container["services"]["report"]`) em vez de instanciá-lo diretamente, invertendo o controle de construção. A diferença é que, ao contrário de `ChatService`, não há uma `Port`/`Protocol` formal para `ReportService` — o router depende da classe concreta. Isso é aceitável porque existe apenas uma implementação (não há necessidade real de múltiplos "provedores de relatório"), mas vale registrar como uma aplicação parcial do DIP: a inversão de dependência é mais forte na camada de integrações externas do que na camada de geração de relatórios.

**Síntese**

| Princípio | Nível sistema (hexagonal) | Nível módulo (report) |
|---|---|---|
| SRP | ✅ core/ports/adapters separados | ✅ router / service / s_curve separados |
| OCP | ✅ novas fontes de busca só no container | ✅ novos gráficos só na lista de specs |
| LSP | ✅ adapters de LLM/busca intercambiáveis via Port | — não aplicável (sem herança) |
| ISP | ✅ ports estreitos (`LLMPort`, `EmbeddingPort`, ...) | ✅ schemas Pydantic estreitos |
| DIP | ✅ core depende de `Protocol`, não de SDKs concretos | ⚠️ parcial — injeção via container, mas sem `Protocol` formal |

---

## 2. Inventário de Módulos e Serviços do Backend

| Módulo | Arquivo | Função |
|---|---|---|
| Orquestração do fluxo | `app/core/services/chat_service.py` | Orquestra refinamento de tema, geração de queries (probe/final), busca, extração de termos |
| Análise de complexidade | `app/core/services/query_complexity.py` | `QueryComplexityAnalyzer` — pontua a complexidade estrutural de uma query booleana (§6) |
| Deduplicação | `app/core/services/dedup_service.py` | Gera `dedup_key` a partir de identificadores primários ou título+ano normalizado |
| Geração de relatórios/gráficos | `app/core/services/report_service.py` | Curva S, top entidades, distribuições (§10) — implementação ativa, conectada à rota |
| RAG do relatório | `app/core/services/rag_service.py`, `report_writer_service.py` | Chunking/RAG contra `VectorStorePort` (adapter ChromaDB, §13) + orquestração das 6 seções de IA |
| Extração de termos (NLP) | `services/nlp/term_extraction.py` | Pipeline completo de extração/pontuação de termos (§5) |
| Embeddings | `services/nlp/embedding_service.py` | Geração de embeddings (`all-MiniLM-L6-v2`) para relevância de documentos |
| Relevância documento-tema | `services/nlp/relevance_service.py` | Similaridade de cosseno entre embedding do tema e do documento |
| Filtro de idioma | `services/nlp/language_filter.py` | Descarta resumos que não estão em inglês (`langdetect`) |
| Relatório: figuras | `app/core/services/report_figures.py` | Catálogo/whitelist de figuras e quadros REPTEC, marcadores `[[REF:id]]`/`[[FIG:id]]` → LaTeX (`place_figures`), concordância "a Figura"/"o Quadro" (§13.6) |
| Relatório: ciclo de vida | `app/core/services/report_lifecycle.py` | Só anos completos, resumos numéricos dos gráficos, estágio do ciclo de vida a partir de GP/MP/SP (§13.6) |
| Relatório: citações | `app/core/services/report_citations.py` | Citação "(SOBRENOME et al., ano)" e referência ABNT gerados a partir dos metadados do RAG; remove citações inventadas (§13.6) |
| Relatório: qualidade do texto | `app/core/services/report_text_quality.py` | Números em pt-BR, detecção de vazamentos do pipeline ("N/A", "Relevância: 18%"...), 1 regeneração (§13.6) |
| Relatório: formulário | `app/core/services/report_form_validation.py` | Validação de referências administrativas, bibliografia ABNT e assinaturas (nome/posto/função) |
| Relatório: CPC | `app/core/services/cpc_titles.py` + `config/cpc_titles.json` | Títulos oficiais CPC/IPC (827 códigos, gerados por `scripts/build_cpc_titles.py`) |
| Relatório: rótulos | `app/core/services/chart_labels.py` | Abrevia nomes > 45 caracteres nos gráficos (ISO 4/ABNT, remoção de stopwords, truncamento com "…", rótulos únicos) |
| Relatório: revisão | `app/core/services/report_review.py` (puro) + `report_review_service.py` (I/O) | Lint de LaTeX, escopo (seções de IA + linhas editadas), LanguageTool, segunda opinião por IA (§13.7) |
| Relatório: figuras fixas | `app/core/services/report_static_figures.py` | Sobe as figuras fixas da Metodologia (Madeo, Kucharavy) ao MinIO na inicialização |
| Inferência estatística | `app/core/services/sample_statistics.py`, `statistical_inference_service.py` | Chao1 + bootstrap de estabilidade top-10 + relevância SBERT (§11) |
| Extração de campos da query | `app/core/services/query_field_extractor.py` | Recupera título/resumo/CPC/área a partir de uma query editada em texto livre (OPS e Scopus) |
| Config em banco | `app/core/services/llm_config_resolver.py`, `settings_sync_service.py`, `db/config_seed.py` | LLM por ponto de uso, `app_settings` editáveis em tempo de execução, seeds idempotentes (§9.1) |
| LLM (Anthropic) | `services/llm/anthropic_service.py` | Cliente do Claude |
| LLM (Gemini) | `services/llm/gemini_service.py` | Cliente do Gemini, com JSON mode nativo |
| Normalização de saída LLM | `services/llm/normalizer.py`, `validators.py` | Camadas de defesa da saída estruturada (§8.5) |
| Carregamento de prompts | `services/prompt/prompt_loader.py` | Cache + leitura dos arquivos de prompt em `config/prompts/` |
| Construtores de query | `services/query_builders/*.py` | Um builder por API externa (§7.1) |
| Busca externa | `services/search/*.py` | Clientes HTTP para Lens, OPS/Espacenet, Scopus, OpenAlex |
| Repositórios | `services/db/repositories.py` | Padrão *Repository* sobre as tabelas genéricas de documentos |
| Persistência orquestrada | `services/db/persistence_service.py` | Relevância → dedup → normalização → persistência |
| Normalização de metadados | `services/db/normalization_service.py` | Unifica payloads heterogêneos (OPS/Scopus/Lens) em schemas padronizados |
| LLM do relatório (local/intranet) | `app/adapters/driven/llm/openai_compatible_adapter.py` | `TextGenerationPort` compatível com OpenAI - serve Ollama local e o LLM da intranet, só trocando config (§13.3) |
| Custo de tokens (código morto) | `services/token_cost_calculator.py` | Tabela de preços por modelo; **não é importado em nenhum lugar do app** |

---

## 3. Frontend: Fluxo de Trabalho e Modularidade

O frontend (`frontend/src`) implementa um **wizard de 4 etapas** (Input → Exploração Inicial → Exploração Final → Geração do Relatório), orquestrado por `Workflow.tsx` e por dois stores Zustand: um de navegação (passo/sub-passo atual) e `useFormStore.ts`, que concentra todo o estado do formulário/sessão em memória.

### 3.1 Fluxo passo a passo

1. **Etapa 0 — Input Inicial** (`Step1.tsx`): usuário preenche Tema (obrigatório), Descrição, Palavras-chave, Área de Estudo.
2. **Sub-etapa — Refinamento de Parâmetros** (`Step2.tsx`): a LLM gera 4 variações temáticas (persona pattern, few-shot); usuário escolhe uma, pode editá-la manualmente, "Especificar" (a LLM a torna ainda mais estreita, encadeável) ou pedir novas variações.
3. **Etapa 1 — Exploração Inicial** (`Step3.tsx`): geração de N tentativas independentes de query "probe" por fonte (OPS para patentes, Scopus para artigos); usuário escolhe uma por fonte, pode editar os campos estruturados (título/resumo/IPC ou área de estudo/ano — reconstrói a query sem custo de LLM) ou pedir novas tentativas. "Próximo" dispara a busca real (paralela, nas duas fontes).
4. **Sub-etapa — Resultados Iniciais** (`InitialResults.tsx`): exibe resultados reais; permite salvar progresso ou "Finalizar Sessão".
5. **Sub-etapa — Amostragem de Termos** (`TermSampling.tsx`): mostra os termos extraídos via NLP local (não é chamada de LLM) com score de relevância; usuário marca quais manter e escolhe, por fonte, o tipo de query final (Específica/Balanceada/Ampla).
6. **Etapa 2 — Exploração Final** (`FinalExploration.tsx`): revisão/edição da query final gerada por fonte; "Confirmar e buscar" dispara a busca final real (maior volume).
7. **Sub-etapa — Análise de Resultados** (`FinalResults.tsx`): estatísticas agregadas (OPS) e lista bruta de itens (Scopus); exibe o **total real** de documentos da base (`total_count`) separado da "amostra analisada", e avisa quando não há contagem por ano (curva S indisponível).
8. **Etapa 3 — Geração do Relatório** (`ReportStep.tsx` → `ReportGeneration.tsx` + `ReportDocumentEditor.tsx`): formulário do relatório (número/ano, destinatário, objetivo, local, referências administrativas, bibliografia, assinaturas com Nome / Posto-Graduação / Função — validados em `utils/reportFormValidation.ts`), geração seção a seção (RAG → LLM), montagem do `.tex` e editor LaTeX no navegador com painel de imagens, revisão, compilação de PDF e download `.zip` (§13.8).

### 3.2 Tudo o que o usuário pode editar/configurar

- **Etapa 0**: Tema, Descrição, Palavras-chave, Área de Estudo.
- **Refinamento**: seleção entre 5 cartões de tema (entrada bruta + 4 gerados por IA); edição livre de qualquer campo do cartão selecionado; "Especificar" (afunilamento por IA, encadeável); regeneração das 4 variações.
- **Queries probe (por fonte, OPS e Scopus independentemente)**: seleção de 1 dentre N tentativas geradas; edição dos campos estruturados (Título, Resumo, IPC/Área de Estudo, Ano — aceita intervalo); regeneração de novo lote.
- **Amostragem de Termos**: checklist por termo (nenhuma seleção padrão); seletor do tipo de query final (específica/balanceada/ampla) por fonte.
- **Exploração Final**: edição dos campos estruturados da query final por fonte; edição livre da query inteira (os campos Título/Resumo/CPC/Área continuam preenchidos, extraídos da query editada por `query_field_extractor.py` conforme a sintaxe de cada API); regeneração da variante escolhida.
- **Geração do Relatório**: todos os campos do formulário (§3.1, item 8); texto de cada seção de IA (regenerável); o `.tex` inteiro, no editor; imagens anexadas pelo usuário; aplicação/rejeição individual de cada sugestão da revisão.
- **Configurações**: modelo de LLM por ponto de uso, `app_settings` (ex.: `rag_relative_min_relevance`, `languagetool_language`), APIs de busca ativas e imagem de capa do relatório.
- **Gerenciamento de sessão**: nome da sessão; salvar progresso a qualquer momento; finalizar sessão explicitamente; excluir sessão (com confirmação); retomar sessão incompleta (reidrata o formulário, mas reabre sempre na Etapa 0 preenchida — os resultados de busca não são persistidos e precisam ser reexecutados).
- **Listagem de sessões**: busca textual (debounce 300ms) e filtro por status (Todas/Pendentes/Concluídas).

Não existe, hoje, controle na interface para escolher **quais** APIs de busca consultar — OPS (patentes) e Scopus (artigos) estão fixos em todo o fluxo; o Lens e o OpenAlex não aparecem como opções de UI (OpenAlex é usado apenas no backend, para enriquecer resumos do Scopus).

### 3.3 Confirmações como mecanismo de auditoria

Toda ação que custa tokens de LLM ou dispara uma busca real em API externa exige um clique explícito e distinto do clique de "gerar" — nunca é disparada automaticamente:

- A transição Etapa 0→Refinamento só reprocessa via LLM se a entrada realmente mudou desde a última chamada (comparação de assinatura), evitando chamadas redundantes.
- "Próximo" na Exploração Inicial compara a assinatura da query selecionada com a última pesquisada e **pula a chamada de API real se nada mudou** — deduplicação consciente de custo/auditoria, não apenas UX.
- "Confirmar e buscar" na Exploração Final é um botão deliberadamente separado da geração da query — nunca implícito.
- "Finalizar Sessão" é separado de "Salvar Progresso" — persistir com `completed=true` nunca é implícito.
- Exclusão de sessão passa por um modal de confirmação explícita.
- Um contador de chamadas de IA em andamento (`aiCallsInFlight`) desabilita os botões de salvar/finalizar enquanto qualquer chamada está pendente, evitando salvar uma sessão que omitiria o registro de uso de uma chamada ainda em voo.
- Todo uso de LLM é acumulado em um log client-side (`aiCallLog`) e só é limpo após um salvamento bem-sucedido — esse log é a trilha de auditoria depois exibida em `SessionCard.tsx` ("Consumo de tokens na sessão", "Modelo(s) Utilizado(s)", número de iterações).
- Contadores de iteração por etapa (`step2Iterations`, `step3Iterations`, etc.) são incrementados a cada regeneração/especificação e persistidos ao finalizar — dão um registro durável de quantas tentativas de IA a sessão consumiu.

### 3.4 Modularidade para futura integração de novas APIs de busca

O frontend já é parcialmente parametrizado por um tipo `ProbeApi` (`'ops' | 'scopus'`) e um registro `PROBE_FIELDS_BY_API` que mapeia cada API para a ordem/rótulos de seus campos. Todas as funções de geração de query e busca (`generateProbeQueriesMulti`, `rebuildProbeQuery`, `runProbeSearch`, `generateFinalQuery`, `runFinalSearch`) recebem `api` como parâmetro, e os *hooks* (`useProbeQuerySection`, `useFinalQuerySection`) já são agnósticos à fonte (recebem `api`, ordem de campos e um *slice* do store). Adicionar uma terceira fonte (ex.: Lens) exigiria: estender o tipo `ProbeApi` e o registro de campos; adicionar ramos de extração no `probeQuery.ts`; adicionar um terceiro *slice* no `useFormStore.ts` (hoje os campos de cada fonte são duplicados manualmente, não organizados como array/mapa); e instanciar um terceiro par de hooks nos componentes de etapa. Ou seja: a camada de hooks/registro de campos já é de baixo atrito para extensão, mas o *store* Zustand ainda nomeia "Patente"/"Artigo" (OPS/Scopus) como slices fixos em vez de um registro genérico por API — esse é o ponto de atrito remanescente para escalar para mais fontes.

O padrão de registro mais limpo do código hoje é `FINAL_QUERY_VARIANTS`/`FINAL_QUERY_VARIANT_LABELS` (array + mapa de rótulos, iterado diretamente em JSX) — um modelo a seguir ao generalizar o restante do store.

---

## 4. Rotas da API (documentação detalhada)

Todas as rotas ficam sob o prefixo `settings.api_prefix = "/api/v1"`. Um middleware (`RequestLoggingMiddleware`) gera um `run_id` (UUID4) por requisição, logado e devolvido no header `X-Run-Id` e frequentemente ecoado no corpo da resposta.

### 4.1 `chat_router.py` (prefixo `/chat`)

Camada fina sobre `ChatService`, expondo o fluxo passo a passo chamado incrementalmente pelo frontend. A maioria das rotas usa corpos/respostas `dict[str, Any]` não tipados (não há `schemas/chat.py`); erros de negócio retornam `SuccessResponse(success=False, data={"error": ...})` com HTTP 200, em vez de exceções HTTP — os erros ficam "dentro" do envelope de resposta.

| Rota | Entrada | Saída | O que faz |
|---|---|---|---|
| `GET /chat/apis` | — | `{apis: {ops, lens_patent, scopus, lens_scholarly}: bool}` | Quais fontes de busca estão habilitadas/configuradas |
| `GET /chat/models` | — | `{models: {anthropic, gemini}: {model, available}}` | Quais provedores de LLM estão configurados |
| `GET /chat/current-provider` | — | `{provider, available}` | Provedor de LLM ativo no momento |
| `GET /chat/system-prompt` | — | `{prompt: str}` | Expõe o prompt geral (endpoint de debug/inspeção) |
| `GET /chat/ops-token-status` | — | `{is_valid, is_expired, access_token(truncado), expiration_time, ...}` | Status do token OAuth do EPO/OPS |
| `POST /chat/refine-topic` | `InputIntake` (tema, descrição, área, keywords) | `{candidates: [...], ai_usage, warning?}` | LLM gera 4 variações diversas do tema |
| `POST /chat/specify-topic` | `InputIntake` | `{theme, description?, area_of_study?, keywords?, ai_usage}` | LLM estreita um tema já escolhido em UM eixo |
| `POST /chat/analyze-query` | `{query: str}` | `{score, level, operators, nesting_depth, term_count, warnings, recommendations}` | Utilitário síncrono: roda só o `QueryComplexityAnalyzer` (§6), sem LLM/DB |
| `POST /chat/probe/queries-multi` | `InputIntake`, query param `api` | `{queries: [...], ai_usage}` | Gera N tentativas de query probe em paralelo (`asyncio.gather`), com *retry* por complexidade (§6.3) |
| `POST /chat/probe/rebuild-query` | `{fields: dict}`, query param `api` | `{query, fields, complexity, year_range}` | Reconstrói a query probe deterministicamente a partir de campos editados (sem LLM) |
| `POST /chat/final/rebuild-query` | idem, `search_mode="final"` | idem | Igual ao acima, para a query final |
| `POST /chat/final/query-variant` | `{intake, extracted_terms}`, query params `variant`, `api` | `{query, complexity, fields, year_range, ai_usage, warning?}` | Gera a variante final (específica/balanceada/ampla) usando termos extraídos (§7.2) |
| `POST /chat/probe/search` | `{query: dict}`, query params `api`, `top_k` | `{results_count, total_available, results}` | Busca exploratória pequena (~10-20 itens), diversificada por ano para evitar viés de recência |
| `POST /chat/final/search` | `{query: dict}`, query params `year_from`, `year_to`, `api`, `max_results` | Varia por API: OPS retorna estatísticas agregadas (`depositants`, `cpc`, `title`, `patents_by_year`); Scopus retorna lista de itens | Busca final exaustiva, com paginação/estratégia adaptada por volume de resultados |
| `POST /chat/extract-terms` | `{items, original_params}`, query param `top_k` | `{terms: [...], count, ai_usage}` | Extração de termos via NLP local (§5) — **não** é chamada de LLM |

### 4.2 `research_session.py` (prefixo `/research-session`)

CRUD de sessões salvas, com reidratação completa para retomada:

- `GET /research-session?theme&limit` → lista/busca sessões (mais recentes primeiro); não reidrata documentos/termos.
- `GET /research-session/{id}` → sessão única, com documentos e termos completamente reconstruídos (para o wizard retomar sem re-consultar OPS/Scopus).
- `PUT /research-session/{id}` → upsert de input raiz/gerado + queries probe, via lógica compartilhada `persist_session_input`.
- `DELETE /research-session/{id}` → exclui sessão, com *cascade* ORM para todas as tabelas filhas.

### 4.3 `session_input.py` (prefixo `/session-input`)

- `POST /session-input` → cria uma sessão nova (input raiz + gerado + queries probe) em uma única transação — usado tanto para "salvar progresso" (`completed=false`) quanto para finalização completa (`completed=true`). Compartilha a mesma lógica de persistência (`persist_session_input`) usada pelo `PUT /research-session/{id}`.

### 4.4 `report_router.py` (prefixo `/report`)

Gráficos (`report_router.py`) — todos a partir dos dados **já persistidos/compilados** da busca final; nenhum dispara busca nova. Cada PNG é enviado ao MinIO e registrado em `session_chart` (upsert por `(probe_query_id, chart_type)`) junto com um **resumo numérico** (`summary`, JSON) usado depois pelo prompt do relatório:

| Rota | O que faz |
|---|---|
| `POST /report/{id}/graphics` | Curva S de **patentes** (Fisher-Pry, GP/MP/SP, §10) |
| `POST /report/{id}/article-s-curve` | Curva S de artigos |
| `POST /report/{id}/patents-yearly-volume`, `/yearly-volume` | Volume anual (só anos completos) |
| `POST /report/{id}/top-entities` | Top depositantes/instituições (rótulos > 45 caracteres abreviados) |
| `POST /report/{id}/top10-heatmap` | Quadro top-10 (classificações CPC / áreas de estudo) |
| `GET /report/{id}/existing-chart?require_summary=` | Reaproveita um gráfico já gerado (com `require_summary=true`, só se já tiver resumo) |

Documento do relatório (`report_document_router.py`, detalhes em §13):

| Rota | O que faz |
|---|---|
| `POST /report/{id}/sections/{key}/rag` | Recupera e persiste o contexto RAG (+ `sources` citáveis) da seção |
| `POST /report/{id}/sections/{key}/generate` | Chama o LLM, valida o texto (1 nova tentativa), persiste |
| `POST /report/{id}/sections/static` | Seções fixas: Finalidade, Objetivo, Metodologia, Bibliografia |
| `POST /report/{id}/assemble`, `/reassemble` | Renderiza o `.tex` (template Jinja2) e sobe ao MinIO, com baseline para a revisão |
| `POST /report/{id}/compile-pdf`, `GET /{id}/pdf` | Compila via `latex-compiler` e devolve o PDF |
| `GET /report/{id}/document` | `.tex` atual para o editor |
| `GET /report/{id}/charts` | Imagens disponíveis (`origin`: gerada/fixa/anexo) |
| `POST /report/{id}/attachments`, `DELETE /{id}/attachments/{filename}` | Anexos de imagem do usuário |
| `POST /report/{id}/review` | Revisão: lint LaTeX + LanguageTool + IA opcional (§13.7) |
| `POST /report/{id}/bundle` | `.zip` com o `.tex` e as imagens referenciadas (`REPTEC_num_ano.zip`) |

### 4.4.1 `inference_router.py` (prefixo `/inference`) e `config_router.py` (prefixo `/config`)

- `POST /inference/final-search` → inferência estatística sobre a busca final (Chao1 + bootstrap, §11). Não persiste.
- `/config/settings`, `/config/search-apis`, `/config/llm/{providers,configs,call-sites}`, `/config/report-cover-image` → tela de Configurações: `app_settings`, APIs ativas, configurações de LLM e o vínculo de cada ponto de uso, imagem de capa.

### 4.5 `health_router.py`

- `GET /health` → liveness check simples, sem dependência de DB/serviço: `{status, message, run_id}`.

### 4.6 Observação importante sobre testes obsoletos

`tests/test_routes.py` testa rotas que **não existem mais** na árvore atual (`/intake`, `/test/llm`, `/test/nlp`, `/test/query-builder`, `/test/field-schema`) — resquícios de uma versão anterior à refatoração hexagonal (comentário em `main.py`: `# Rotas v2 (hexágono)`). Apenas os testes de `/health` ainda são válidos. Isso não deve ser citado no relatório como comportamento real do sistema.

---

## 5. Extração de Termos (Pipeline NLP)

Este é o módulo local (não-LLM) que extrai e pontua termos candidatos a partir de título+resumo dos documentos recuperados na busca probe, alimentando a etapa de Amostragem de Termos.

### 5.0 Pipeline atual: PatternRank + BM25F + KeyBERT + RRF + C-value

> **Atualização**: o pipeline descrito em §5.1–§5.4 (noun chunks + TF-IDF + KeyBERT combinados linearmente 0,6/0,4) foi **substituído**. A comparação entre os dois está em `TESTE_EXTRACAO_TERMOS_BM25F_RRF.md`. §5.1–§5.4 ficam como registro histórico; filtros de qualidade (§5.2) e penalidades de POS/n-grama (§5.5) continuam em uso, agora como canal de "qualidade estrutural".

`services/nlp/term_extraction.py::extract_and_rank_terms`, hoje:

1. **Candidatos — PatternRank** (`KeyphraseCountVectorizer`, padrão gramatical adjetivo* + substantivo+): frases nominais maximais sobre todo o corpus, no lugar de noun chunks + janelas de 1 a 3 palavras.
2. **Filtros**: remove unigramas idênticos aos termos originais do usuário (n-gramas com 2+ palavras são mantidos); filtros de qualidade de string (§5.2) aplicados **antes** da contagem de frequência.
3. **Canal léxico — BM25F**: BM25 ponderado por campo (título peso 3,0; resumo 1,0 — `term_extraction_title_weight`/`abstract_weight`), `k1 = 1,2`, `b = 0,75`, com título e resumo alinhados por documento.
4. **Canal semântico — KeyBERT**: similaridade de cosseno do candidato com o texto do corpus (mesmo modelo de antes).
5. **1º estágio RRF** (*Reciprocal Rank Fusion*): `RRF(t) = Σ 1/(k + rank_i(t))`, `k = 60` (`term_extraction_rrf_k`), fundindo BM25F × KeyBERT → `salience_score`. Fundir **postos**, e não scores, elimina o problema de escalas diferentes entre os canais.
6. **Qualidade estrutural**: preferência por tamanho de n-grama + penalidade por padrão POS ruim (§5.5).
7. **2º estágio RRF**: saliência × qualidade estrutural → `final_rrf_score`.
8. **C-value**: sinal de redundância entre termos aninhados (substitui o filtro de sobreposição de palavras de §5.4); em seguida, um termo contido de forma contígua em outro de posto maior é descartado ("ultrafiltration membrane" some quando "composite ultrafiltration membrane" já está na lista).
9. **Limiar e corte**: `final_rrf_score ≥ 0,024` (`term_extraction_score_threshold`, recalibrado para a escala do RRF), mínimo de 10 termos retornados, teto de 60.

### 5.1 Pipeline anterior (histórico) (`services/nlp/term_extraction.py::extract_and_rank_terms`)

1. **Normalização dos parâmetros originais**: tema/descrição do usuário viram um conjunto de palavras, usado depois para excluir termos que o usuário já buscou.
2. **Filtro de idioma** (aplicado a montante, antes desta etapa): `language_filter.py` descarta resumos não confiáveis como inglês.
3. **Separação de texto**: título e resumo de cada documento são limpos (`_clean_text`: minúsculas, remoção de URLs, hífens→espaços, colapso de espaços) e mantidos em duas listas **separadas** (nunca misturadas na pontuação).
4. **Geração de candidatos**: `spaCy en_core_web_sm` extrai *noun chunks*; cada chunk é quebrado em sub-n-gramas de 1 a 3 palavras, respeitando tokens/POS de fronteira (§5.2).
5. **Pontuação**: KeyBERT e TF-IDF são calculados **separadamente para títulos e para resumos** (4 dicionários de score).
6. **Normalização**: scores do KeyBERT divididos pelo próprio máximo do grupo (0–1); TF-IDF já normalizado na extração.
7. **Combinação**: 60% TF-IDF + 40% KeyBERT por fonte, depois título/resumo combinados por média ponderada (peso 3:1 — §5.4).
8. **Ajustes de score**: bônus/penalidade por tamanho de n-grama e por padrão POS ruim (§5.5).
9. **Filtro de termos originais**: remove n-gramas idênticos aos termos de busca originais.
10. **Filtro de qualidade** (§5.2): stopwords de fronteira, palavras estruturais de patente, palavras estruturais acadêmicas.
11. **Ranking** pelo score combinado puro (desc).
12. **Filtro de subsunção/sobreposição** (§5.4): remove termos com sobreposição de palavras ≥ 0.66 contra um termo já selecionado de score maior.
13. **Re-ranking** pelo score ajustado (score + bônus + penalidade), desc.
14. **Filtro por limiar**: mantém apenas termos com score ajustado ≥ 0.35.
15. **Corte rígido**: no máximo 60 termos retornados.
16. **Montagem do resultado**: cada termo devolvido com score, `n_words`, scores por fonte, frequência, `sources` (título/resumo), bônus, penalidade e pesos usados.

> **Nota histórica**: o código documenta que uma etapa de **MMR (Maximal Marginal Relevance)** foi removida por ser O(N³) em loop guloso, substituída pelo filtro de sobreposição/subsunção de passagem única (O(N × |selecionados|)). Configurações `term_extraction_mmr_lambda`/`term_extraction_mmr_similarity_threshold` ainda existem em `core/config.py` mas estão mortas em relação ao pipeline atual.

### 5.2 Filtros e dicionários

- **`config/ngram_boundary_tokens.json`** (~90 tokens): usado para cortar a sequência de tokens do noun-chunk *antes* de gerar sub-n-gramas, para que nenhum n-grama atravesse essas fronteiras. Categorias: pronomes relativos/conjunções (`wherein, whereby, which, that, who…`), conjunções coordenativas/subordinativas (`and, or, if, because…`), verbos de "boilerplate" de patente (`comprising, including, having, configured, disposed, coupled…`), preposições (`using, based, via, from, into, between, during…`), advérbios (`respectively, particularly, substantially, approximately`).
- **`config/pos_patterns.json`**: `ngram_boundary_pos = ["ADP","CCONJ","SCONJ","PUNCT","SPACE","NUM"]` (também cortam segmentos); `bad_bigrams = [[VERB,VERB],[ADV,VERB],[VERB,ADJ],[ADJ,VERB]]`; `bad_trigrams = [[VERB,VERB,NOUN],[ADV,VERB,NOUN],[ADV,ADJ,NOUN],[VERB,NOUN,VERB]]` — usados para penalizar n-gramas com sequência POS "ruim" (§5.5).
- **Limpeza de bordas POS**: remove tokens iniciais/finais com POS em `{DET, ADP, CCONJ, SCONJ, PART, PUNCT, SPACE, SYM}`.
- **`config/string_quality_filter.json`**: três listas — `boundary_stopwords` (~55 palavras; termo descartado se a **primeira ou última** palavra estiver na lista: `a, an, the, of, is, are, this, that, high, low, new, such, about…`); `patent_structural_words` (termo descartado se **qualquer** palavra bater: `wherein, comprising, said, first, second, opposing, planar, configured, plurality, substantially, device…`); `scholarly_structural_words` (mesmo critério, para boilerplate acadêmico: `proposed, novel, improved, significant, method, technique, framework, model, system, based, compared…`).

### 5.3 Algoritmos: KeyBERT + TF-IDF (histórico)

Os dois métodos de pontuação combinados são **KeyBERT** e **TF-IDF** (scikit-learn `TfidfVectorizer`) — spaCy é apenas o gerador de candidatos (noun chunks), não um método de pontuação.

- **KeyBERT** (modelo `distiluse-base-multilingual-cased-v2`, configurável via `llm_keybert_model`): chamado com `candidates=ngramas` (extração restrita à lista de candidatos) e `top_n=min(len(ngramas), 50)`. Se a cobertura for menor que 50% dos candidatos, roda um segundo passe irrestrito e pontua os n-gramas não cobertos por proporção de sobreposição de palavras com as keywords encontradas: `score_escalado = score_keyword × (|palavras_comuns| / |palavras_do_ngrama|)`, tomando o máximo entre os candidatos do segundo passe.
- **TF-IDF**: se o n-grama está diretamente no vocabulário ajustado, o score é a média da coluna TF-IDF entre documentos; se é multi-palavra e todos os tokens componentes estão no vocabulário, o score é a **média aritmética** dos scores TF-IDF dos tokens componentes (n-gramas com qualquer token ausente não recebem score parcial).
- **Nota**: existe um `services/nlp/keyword_service.py` (`KeywordService`) separado, usando o modelo `all-MiniLM-L6-v2` — parece ser um utilitário independente/legado, **não conectado** ao pipeline principal de `extract_and_rank_terms` (que instancia seu próprio KeyBERT).

### 5.4 Fórmulas de score e normalização (histórico; cosseno de §5.6 continua em uso)

- **Similaridade de cosseno** (usada em `relevance_service.py`, filtro de documentos, não de termos): `cosine_similarity(embedding_tema, embedding_documento)`, com faixa teórica **[-1, 1]** — na prática, com embeddings de sentence-transformers, tende a valores não-negativos, mas o código não recorta/reescala essa faixa.
- **Score bruto do KeyBERT**: já é um valor tipo similaridade-de-cosseno em **[0,1]**, renormalizado por grupo: `normalize(d) = {t: s / max(d.values()) para t,s em d}`.
- **Combinação por fonte** (título ou resumo): `combinado = 0.6 × tfidf_norm + 0.4 × keybert_norm` (pesos fixos no código).
- **Agregação título/resumo**: se o termo aparece em ambos com score>0: `base_score = (título_comb × peso_título + resumo_comb × peso_resumo) / (peso_título + peso_resumo)`, com `peso_título = 3.0` e `peso_resumo = 1.0` (i.e., título pesa 3× mais que resumo). Se só aparece em um, usa o score desse.
- **Não há chunking de embeddings** dentro do `TermExtractor` — o KeyBERT é chamado uma vez sobre o texto combinado por grupo (`" ".join(textos)`), não por documento/chunk com agregação posterior. `EmbeddingService.embed_document` (usado por `RelevanceService`, módulo separado) usa uma estratégia de *fallback* por campo (resumo se >50 chars → título+resumo → título → `full_text` truncado a 200 palavras), não um verdadeiro *mean-pooling* multi-chunk.
- **Filtro de sobreposição/subsunção**: `overlap_ratio(a,b) = |palavras(a) ∩ palavras(b)| / min(|palavras(a)|, |palavras(b)|)`; candidato descartado se essa razão ≥ 0.66 contra qualquer termo já selecionado de score maior. Exemplos documentados no código: `"salt water"` vs `"water desalination"` → 0.50 (mantém ambos); `"ultrafiltration membrane"` vs `"composite ultrafiltration membranes"` → 1.0 (remove); `"desalination"` vs `"water desalination"` → 1.0 (remove).
- **Score final**: `final = max(0, base_score + bônus + penalidade)`.

### 5.5 Penalidades e bônus de n-grama (`_get_score_adjustments`)

```
unigram_penalty      = -0.4
bigram_bonus         =  0.0
trigram_bonus        =  0.25   (fallback no código: 0.3)
bad_bigram_penalty   = -0.8    (aplicado se o par de POS bater com bad_bigrams)
bad_trigram_penalty  = -0.8    (aplicado se o trio de POS bater com bad_trigrams)
```

Ou seja: unigramas são ativamente desincentivados (-0.4); trigramas são recompensados (+0.25); bigramas são neutros; qualquer bigrama/trigrama cuja sequência POS bata com um "padrão ruim" (§5.2) sofre penalidade adicional de -0.8 (suficiente, na prática, para empurrar o termo abaixo do limiar de 0.35). O score final é sempre não-negativo.

### 5.6 Re-ranking por relevância documento-tema (`relevance_service.py`)

Este é um filtro **em nível de documento**, separado da pontuação de termos — não altera scores de termos. `RelevanceService` embeda o tema do usuário e cada documento (mesma estratégia de fallback de campo citada em §5.4), calcula similaridade de cosseno entre os dois, e marca `is_approved = score >= threshold` (`relevance_threshold = 0.4`, padrão de configuração). Documentos aprovados/rejeitados são ordenados separadamente por score. Esse filtro governa **quais documentos chegam** à etapa de extração de termos — é um portão a montante, não um re-ranking dos termos já extraídos.

---

## 6. Função de Complexidade de Query

### 6.1 Motivação — evidência de erro/zero-resultado em APIs remotas

Múltiplos comentários no código confirmam que queries booleanas complexas/verbosas quebram ou zeram nas APIs externas:

- **Scopus**: *"Termos SEMPRE entre aspas: sem aspas... OR'ar duas ou mais dessas frases sem aspas quebra o parser e zera os resultados (confirmado testando direto na API)."*
- **Scopus SUBJAREA**: com aspas e nome livre, "0 resultados sempre, mesmo em queries amplas"; com o código correto, resultados normais.
- **Scopus service**: a contagem por requisição é limitada porque a API "devolve 400 'Exceeds the maximum number allowed for the service level'"; uma resposta sem matches retorna um item-placeholder de erro que precisa ser filtrado manualmente da paginação.
- **OPS builder**: códigos IPC/CPC com espaços causam "erro 500 (SERVER.DomainAccess)" — os espaços precisam ser removidos antes do envio.
- **Limites de tamanho são reforçados no código**: OPS `max_query_length=10000`, Scopus `10000`, Lens `50000`, cada um logando aviso quando excedido.

Ou seja: o problema real não era "poucos resultados por query pouco abrangente" — era o **oposto** do esperado intuitivamente: queries mais "abrangentes" (muitos termos, muitos operadores OR/AND aninhados) tendiam a **quebrar o parser da API remota ou retornar zero resultados/erro HTTP**, em vez de trazer mais resultados. A função de complexidade existe como *guardrail* preventivo contra esse comportamento, calculada e verificada **antes** de qualquer query ser enviada a uma API externa.

### 6.2 Fórmula (`app/core/services/query_complexity.py::QueryComplexityAnalyzer`)

Quatro sub-scores normalizados (cada um limitado a 100), combinados com pesos fixos:

```python
def _calculate_complexity_score(self) -> float:
    operator_score = min(100, (operators["total"] / 10) * 100)
    nesting_score  = min(100, (nesting["max_depth"] / 5) * 100)
    term_score     = min(100, (terms["total_terms"] / 20) * 100)
    length_score   = min(100, (length / 1000) * 100)

    return round(
        operator_score * 0.2
        + nesting_score * 0.3
        + term_score * 0.3
        + length_score * 0.2,
        2,
    )
```

- **operator_score (peso 20%)**: contagem de `AND`/`OR`/`NOT` (regex, case-insensitive), normalizada contra uma base de 10 operadores.
- **nesting_score (peso 30%)**: profundidade máxima de aninhamento de parênteses, normalizada contra uma base de 5. O cálculo (`_calculate_nesting_depth`) **não** conta um `(` como novo nível se o caractere não-espaço anterior também for `(` — porque os *query builders* embrulham mecanicamente cada cláusula em seus próprios parênteses (ex.: `" AND ".join(f"({parte})" for parte in partes)`), o que empilha parênteses sem aninhamento lógico real.
- **term_score (peso 30%)**: contagem de termos entre aspas, normalizada contra uma base de 20 termos.
- **length_score (peso 20%)**: contagem bruta de caracteres da string de query, normalizada contra uma base de 1000 caracteres.

**Níveis de complexidade** (`_get_complexity_level`):
```
score <  25 → "Simples"
score <  50 → "Moderado"
score <  75 → "Complexo"
score >= 75 → "Muito Complexo"
```

Também são emitidos avisos (ex.: >15 operadores totais, aninhamento >4, parênteses desbalanceados, >5 termos repetidos, comprimento >2000 caracteres, contagem de OR > 2× contagem de AND) e recomendações textuais (reduzir termos para ~5-8, limitar aninhamento, remover duplicatas).

### 6.3 Uso no fluxo (loop de retry e auto-correção)

`ChatService` usa o `QueryComplexityAnalyzer` como *guardrail* antes de enviar qualquer query a uma API externa, tanto nas queries probe (`_build_query_with_retry`) quanto nas variantes finais (`_build_final_variant_query`): até `max_attempts=3` tentativas; após cada query gerada pela LLM, calcula a complexidade e compara contra `settings.llm_max_query_complexity` (padrão `0.6` → limiar de score 60/100). Se ultrapassar, o prompt é reenviado com um **sufixo de simplificação** que literalmente cita de volta a decomposição da tentativa anterior (operadores/aninhamento/termos) e instrui:

```python
def _simplification_suffix(self, complexity, attempt):
    max_score = getattr(self.settings, "llm_max_query_complexity", 0.6) * 100
    return (
        f"\n\n[CRITICAL RETRY #{attempt}] "
        f"Previous query was TOO COMPLEX (score: {complexity['score']:.1f}/100, max: {max_score:.0f}). "
        f"\nMUST simplify by:\n"
        f"- Use ONLY 1-2 most important concepts (reduce terms)\n..."
    )
```

Se todas as tentativas ainda excederem o limiar, o código **não falha** — retorna a tentativa menos complexa das três, com um aviso (`warning`) explícito no payload de resposta, exibido ao usuário no frontend. Esse design (melhor-de-3, escolher a menos complexa, avisar se ainda ultrapassar) lida na prática com o fato de que a LLM nem sempre converge para o alvo pedido — mas essa premissa não está documentada explicitamente em nenhum comentário/docstring do código; o mecanismo é apresentado de forma puramente mecânica.

---

## 7. Geração de Queries por API e por Nível de Abrangência

### 7.1 Query Builders (`services/query_builders/*.py`)

Todos implementam o contrato `BaseQueryBuilder.build_query(llm_output, year_from, year_to)`, com estratégia comum: campos de **título OU resumo** combinados com OR (qualquer um pode bater), demais campos preenchidos combinados com AND, mais uma cláusula de intervalo de anos.

| Builder | API alvo | Sintaxe | Limite de tamanho |
|---|---|---|---|
| `LensPatentQueryBuilder` | Lens.org (patentes) | `query_string` do Elasticsearch (`campo:(t1 OR t2) AND (t3 OR t4)`), em `bool.must` + filtro `range` de data | 50.000 chars |
| `LensScholarlyQueryBuilder` | Lens.org (acadêmico) | JSON nativo de bool-query do Elasticsearch (título/resumo em `should` com `minimum_should_match:1`; demais campos em `must`) | 50.000 chars |
| `OPSQueryBuilder` | EPO/Espacenet | CQL — cada termo vira `campo = "termo"`, agrupado e unido por AND/OR, cada cláusula embrulhada em parênteses | 10.000 chars |
| `ScopusQueryBuilder` | Scopus/Elsevier | Sintaxe de prefixo de campo (`TITLE(("t1" OR "t2"))`, `ABS(...)`, `AUTH(...)`, etc.), termos sempre entre aspas; `SUBJAREA(CÓDIGO)` via tabela de 27 códigos ASJC; `DOCTYPE(ar)` fixo | 10.000 chars |

`QueryBuilderFactory` é um registro simples (`api_name` → classe do builder), com ponto de extensão (`register_builder`) para novas fontes.

### 7.2 Geração das variantes Específica / Balanceada / Ampla

Isso acontece em `app/core/services/chat_service.py`, não nos *query builders* — o builder só traduz uma estrutura de campos já decidida em sintaxe de API; quem decide **quais** termos e com que operadores é a camada de orquestração, via prompt para a LLM.

- **Etapa probe**: gera N tentativas independentes a partir do mesmo prompt, confiando na variância natural da LLM — "não faz sentido variar precisão/cobertura nesta etapa" (comentário no código), já que o probe é por natureza estreito/de alta precisão.
- **Etapa final**: gera explicitamente três variantes nomeadas, via um dicionário de instruções injetado no prompt:

```python
_VARIANT_INSTRUCTIONS = {
    "specific": "Build a FOCUSED, HIGH-PRECISION query. Use only the highest-scoring "
                "extracted terms. Combine core concepts with AND. Limit OR groups to 3-4 terms.",
    "balanced": "Build a BALANCED query with good recall and precision. Use mid-range "
                "scoring extracted terms. Allow broader OR groups (4-6 terms). "
                "Limit AND combinations to 1-2.",
    "generic":  "Build a BROAD, HIGH-RECALL query. Include all extracted terms above "
                "the score threshold. Minimize AND operators. Maximize coverage.",
}
```

Além disso, o conjunto de termos extraídos (§5) que é oferecido à LLM como contexto varia por variante, via limiar de score mínimo: **específica: 0.4, balanceada: 0.3, ampla (genérica): 0.2** — a variante específica só recebe os termos de score mais alto; a genérica recebe mais termos com barra mais baixa. Cada variante passa pelo mesmo loop de retry por complexidade descrito em §6.3.

### 7.3 Robustez da busca final (totais reais e contagem por ano)

- **Total real × amostra**: `ChatService.run_final_search` devolve `total_count` — o total que a base informa para a query (ou, quando o Scopus não informa, a soma da contagem por ano), separado do número de documentos efetivamente baixados e analisados. O relatório usa o total real no quadro de busca ("Patentes (1.800) = …") e a amostra só nas análises; o frontend mostra ambos.
- **Scopus, contagem por ano** (base da curva S de artigos): falhas de rede em um ano são repetidas sequencialmente numa segunda passada e **nunca registradas como 0** — um ano que falha de vez é omitido da série, em vez de criar um "vale" falso que distorceria o ajuste logístico. `services/search/scopus_service.py` repete `httpx.TransportError` (erro de rede) até 4 vezes (`_MAX_RETRIES = 4`).
- **OPS, nomes de depositantes em escrita não latina** (chinês, japonês, coreano): `ops_service.py::_pick_party_names` usa a forma `epodoc` (latinizada) quando o nome original não é latino — antes, esses depositantes apareciam em branco nos gráficos, porque o LaTeX descarta CJK.

---

## 8. Engenharia de Prompts para a LLM Remota

Todos os prompts de sistema ficam em `config/prompts/`, carregados (sem interpolação de template — apenas leitura de arquivo com cache) por `services/prompt/prompt_loader.py::PromptLoader`. A montagem final (concatenação de prompt-base + dicas dinâmicas de campo + sufixo de retry) acontece em tempo de chamada, em `chat_service.py`.

### 8.1 Persona Pattern

Todos os prompts de sistema abrem atribuindo um papel de especialista à LLM, por exemplo:

> "You are a specialist in technology foresight and in building structured search queries for patent and scholarly databases." (`general_system_prompt.txt`, `probe_system_prompt.txt`)

> "You are a specialist in technology foresight and thematic refinement." (`refine_topic_system_prompt.txt`)

> "Você é um especialista em redação de relatórios de prospecção tecnológica no estilo REPTEC/AGITEC." (`report_prompts.py`)

### 8.2 Raciocínio passo a passo (Chain-of-Thought estruturado)

O `probe_system_prompt.txt` contém uma seção de lógica numerada explícita:

> "## CORE LOGIC (CRITICAL)\n1. Identify 2 to 4 semantic concepts\n2. Select 2 CORE concepts\n3. Remaining concepts become SECONDARY\n4. Create ONE group per concept..."

O `final_system_prompt.md` usa uma variante de CoT por **ramificação condicional de cenário**: para cada variante (específica/balanceada/ampla), descreve uma lógica de restrição diferente:

> "### SPECIFIC\n- Most restrictive: use only the highest-scoring extracted terms\n- More AND operators to narrow scope (maximum 3-4 ANDs)..."

### 8.3 Few-shot examples

`refine_topic_system_prompt.txt` e `specify_topic_system_prompt.txt` usam exemplos contrastantes BOM/RUIM para forçar diversidade/especificidade real, em vez de paráfrases superficiais:

> "BAD EXAMPLE:\n- \"AI for drones\"\n- \"Artificial intelligence in drones\"...\nGOOD EXAMPLE:\n- \"Autonomous swarm coordination for military drones in contested environments\"..."

`general_system_prompt.txt` usa exemplos CORRETO/INCORRETO para extração de conceitos.

### 8.4 Injeção da restrição de complexidade e auto-correção

A restrição de complexidade é injetada em **dois pontos**:

**(a) Estática, no texto do prompt** — tanto `probe_system_prompt.txt` quanto `final_system_prompt.md` fixam um alvo numérico e passos de mitigação diretamente no prompt de sistema:

> "The generated query must NOT exceed a complexity score of 0.6 (on a 0-1 scale)... Target: Complexity score between 0.2-0.5 (simple to moderate queries)."
>
> "If your generated query would exceed 0.6 complexity:\n1. Reduce the number of terms per group\n2. Remove secondary concepts\n3. Use only the most essential terms\n4. Combine similar terms into single broader expressions"

**(b) Dinâmica, injetada após uma falha real** — como detalhado em §6.3, o *breakdown* exato de complexidade da tentativa anterior é recolocado no prompt da próxima tentativa via `_simplification_suffix`. É um padrão de auto-correção por *feedback loop*: a saída da LLM é medida deterministicamente pelo código (não a própria LLM se autoavaliando), e a métrica concreta é reinjetada como novo contexto.

**Sobre a tendência da LLM a gerar complexidade alta**: nem o código nem o texto dos prompts afirmam explicitamente que modelos de LLM têm viés para gerar saídas mais complexas do que o pedido, ou que "empacam" num piso de complexidade mínima dependendo do modelo. Essa premissa fica implícita apenas no *design* do mecanismo (3 tentativas, escolher a menos complexa, avisar se ainda estiver acima do limite) — o comentário no código descreve o retry apenas como cobrindo "tanto complexidade excessiva quanto falhas transitórias da LLM", sem justificar a causa raiz. Na prática observada pela equipe, modelos de LLM tendem a manter um piso de complexidade — raramente geram os níveis mais baixos possíveis mesmo quando instruídos a simplificar — o que motivou o desenho de "melhor-de-3 tentativas com aviso ao usuário" em vez de um limite rígido que travaria o fluxo.

### 8.5 Enforcement de saída estruturada — defesa em camadas

1. **JSON mode nativo (só Gemini)**: `generation_config = genai.types.GenerationConfig(response_mime_type="application/json")` — reduz bastante erros de parsing (comentário no código). O Anthropic **não** usa JSON mode/function-calling — depende só de instrução textual ("Return ONLY valid JSON") e extração pós-hoc de blocos ```` ```json ```` ou parse bruto, levantando `LLMJSONParseError` em falha.
2. **Reparo de JSON malformado**: `services/llm/base.py::parse_llm_json` (usado por Gemini e Ollama) remove vírgulas finais e **insere vírgulas faltantes** entre membros antes de re-parsear — erro típico de modelos locais pequenos ("Expecting ',' delimiter"). O laço de geração da query final também refaz a chamada ao LLM quando a resposta vem malformada (guardando `last_error`), em vez de falhar na primeira tentativa; no fluxo de `refine-topic`, há ainda uma recuperação tolerante a candidato individual corrompido (`_salvage_candidates`), que extrai cada objeto `{...}` do array por contagem de profundidade de chaves, descartando apenas o candidato malformado em vez de falhar a chamada inteira.
3. **Validação de schema Pydantic**: `LLMOutput(**json_normalizado)` — primeira camada de validação de tipos/formato.
4. **`validators.py`**: funções puras de checagem pós-geração — `is_valid_term()` rejeita stopwords/palavras genéricas isoladas; `validate_group()` checa a forma `{operator, terms}` e força `operator ∈ {"AND","OR"}`; `filter_to_enabled_fields()` remove qualquer campo que a LLM tenha produzido mas que não esteja na lista de campos habilitados.
5. **`normalizer.py::LLMOutputNormalizer.normalize()`**: re-molda o objeto conforme os campos habilitados por configuração/feature-flag, zerando campos não habilitados.
6. **`field_schema_service.py`**: monta a lista dinâmica de campos permitidos (`get_fields_for_probe()`/`get_fields_for_final()`) a partir de `config/dict/llm.fields.json`, de acordo com quais APIs externas estão habilitadas — é essa lista que os prompts referenciam como "especificação dinâmica de campos".

### 8.6 Anthropic vs. Gemini

Ambos implementam a mesma interface abstrata (`services/llm/base.py::BaseLLMService`, exigindo `process_intake`, `call_raw_json`, `is_available`, `provider_name`), selecionada por `LLMServiceFactory.create()` de acordo com `settings.llm_provider` (com `TEST_MODE` forçando `MockLLMService`, e *fallback* automático para mock se a chave de API estiver ausente ou a inicialização do cliente falhar — garantindo que o app nunca trava por falta de credencial). Diferença de implementação: Anthropic chama `client.messages.create(system=..., messages=[...])`; Gemini concatena sistema+usuário em um único prompt (`f"{system_prompt}\n\n{user_message}"`, já que sua API não separa um campo de sistema do mesmo jeito) e usa `generate_content_async` com JSON mode.

---

## 9. Banco de Dados

### 9.1 Schema ativo (session-centric), `db/research_session_models.py`

Este é o schema **hoje efetivamente usado por toda a aplicação em produção** — gerenciado por Alembic (não por `create_all`). Tabela central: `research_session`.

| Tabela | Papel |
|---|---|
| `research_session` | Uma execução do wizard (id, public_id/UUID, nome, `completed`, `completed_at`, `current_step`/`current_substep` para retomar no ponto certo, timestamps) |
| `session_input` | Input do usuário (tema/descrição/keywords/área/anos); auto-referenciada por `parent_id` — a linha raiz (`parent_id=NULL`) é a entrada bruta, a linha filha é a variação escolhida/refinada por IA |
| `session_probe_query` | Uma query gerada (probe ou final) por fonte; `fonte ∈ {ops, scopus}`; `tipo ∈ {NULL, specific, balanced, generic}` — ver §9.2 |
| `session_ai_call` | Log append-only de toda chamada de LLM da sessão (etapa, provedor, modelo, tokens, tentativas, duração) — a base do log de auditoria exibido no frontend |
| `patent` / `article` | Documentos deduplicados globalmente por `dedup_key`, reutilizados entre sessões e entre estágio probe/final |
| `probe_query_patent` / `probe_query_article` | Tabelas de associação N:N entre `session_probe_query` e `patent`/`article`, carregando `relevance_score` |
| `probe_query_term` | Termos extraídos (§5), com `score`, `frequency`, `selected` — só populada para linhas de `tipo IS NULL` (extração de termos é etapa exclusiva do estágio probe) |
| `session_chart` | Um PNG de report gerado (§10), com `object_key` (chave MinIO) e `summary` (JSON: resumo numérico do gráfico — total, pico, top-N, GP/MP/SP — que alimenta o prompt da seção de resultados) — FK pra `session_probe_query`, unique `(probe_query_id, chart_type)` |
| `session_report_section` | Texto de uma seção do relatório LaTeX (§13.1/13.2) — `rag_context`/`generated_text`/`status` e `sources` (JSON: citação + referência ABNT de cada documento recuperado pelo RAG, §13.6), FK pra `research_session`, unique `(session_id, section_key)` |
| `session_report` | Manifesto do `.tex`/PDF montado (§13.2) — `tex_object_key`/`pdf_object_key` (chaves MinIO; ao lado do `.tex` editável fica no MinIO a cópia `main.assembled.tex`, baseline usado pela revisão para detectar linhas editadas), `assemble_payload`, FK única pra `research_session` |

**Tabelas de configuração** (`db/config_models.py`, semeadas por `db/config_seed.py`): `app_settings` (parâmetros editáveis em tempo de execução, com tipo/faixa/descrição — ex.: `rag_top_k_per_section`, `rag_relative_min_relevance`, `languagetool_language`), `llm_provider_configs` e `llm_call_site_bindings` (vínculo de cada ponto de uso de LLM (`theme_candidates`, `probe_query`, `final_query`, `report_writing`, `report_review`), e `search_api_selection`. O seed é **idempotente**: `seed_missing_app_settings` e `seed_missing_call_site_bindings` inserem só chaves/pontos de uso ausentes, sem sobrescrever valores já editados pelo usuário — assim um banco existente recebe as configurações novas sem perder as antigas.

Documentação gerada do schema: `notes/db_schema_atual.{dbml,md,html}`, regenerada a partir dos metadados SQLAlchemy por `scripts/generate_db_schema_docs.py` (16 tabelas).

### 9.2 Reuso das tabelas "probe" para os dados "final" (via `tipo`/`parent_id`)

A migração `b1c4f0a9d2e7_add_tipo_and_parent_id_to_session_probe_query` adicionou `tipo` (String nulável) e `parent_id` (auto-FK, `ondelete=CASCADE`) à `session_probe_query`, e trocou a restrição de unicidade de `(session_id, fonte)` para `(session_id, fonte, tipo)`. A semântica:

- **`tipo IS NULL`** → linha do estágio probe ("Exploração Inicial").
- **`tipo ∈ {specific, balanced, generic}`** → linha do estágio final, auto-referenciada por `parent_id` à sua irmã probe da mesma `fonte`.

As tabelas `patent`, `article`, `probe_query_patent`, `probe_query_article` **não são duplicadas** entre probe e final — são entidades genéricas chaveadas por `dedup_key` de documento, reutilizadas seja qual for o `session_probe_query` (probe ou final) que as encontrou, distinguidas apenas por qual `probe_query_id` a linha de associação aponta. `probe_query_term` é a única exceção: só é populada para `tipo=NULL`, já que a extração de termos é uma sub-etapa exclusiva do estágio probe.

Ou seja: não existe um banco separado ou um prefixo de nome de tabela chamado literalmente "probe" versus "final" — o mecanismo de reuso é o par de colunas `tipo`/`parent_id` dentro da mesma tabela `session_probe_query`, e as tabelas de documentos/associação/deduplicação são inteiramente compartilhadas entre os dois estágios.

### 9.3 Estatísticas da busca final: sem tabela dedicada

> **Atualização**: os gráficos agora são persistidos (PNG no MinIO + `session_chart.summary`), então o texto abaixo vale só para os agregados brutos — ainda não há uma tabela `session_metrics`.

Não existe uma tabela dedicada de estatísticas (ex.: `session_metrics`) — os dados para a curva S, top depositantes/instituições, top temas, top CPC/áreas de estudo são hoje **computados sob demanda, não persistidos**, pela rota `POST /report/{session_id}/graphics` (§4.4, §10), que consulta `patent`/`article` via `probe_query_patent`/`probe_query_article` filtrando `session_probe_query.tipo IS NOT NULL` (documentos do estágio final), e devolve arquivos PNG — nenhuma linha nova é criada no banco. Esta é exatamente a peça mencionada como "só foi feita pro OPS": a agregação de estatísticas (depositantes, CPC, contagem por ano) hoje só acontece de fato para a fonte OPS dentro de `run_final_search` (`/chat/final/search`), que já devolve dados agregados prontos (`depositants`, `cpc`, `title`, `patents_by_year`) em vez de lista bruta — diferente do Scopus, que devolve lista de itens crus.

### 9.4 Aviso: schemas legados/órfãos (não citar como funcionais)

Existem **dois outros grupos de tabelas** no banco, criados por `db/init_db.py` via `create_all` (não por Alembic), mas **não usados pelo fluxo real hoje**:

- **`db/models.py`** (schema genérico de documentos: `scholarly_documents`, `patent_documents`, `*_dedup_registry`): tem código de repositório funcional (`services/db/repositories.py`) e adaptadores hexagonais conectados a um `ResearchService`, mas esse `ResearchService`/`build_research_service` nunca é efetivamente chamado por nenhuma rota ativa — é infraestrutura pronta, mas desconectada do caminho de execução real.
- **`db/research_models.py`** (schema legado `research`, `research_metrics`, `research_token_usage`, `research_phases` etc.): versões antigas de `notes/db_schema_atual.md` afirmavam que rotas como `research_router.py`/`metrics_aggregator.py` ainda usam este schema (o arquivo foi regenerado e hoje documenta só o schema ativo) — essas rotas **não existem mais** na árvore atual do projeto (confirmado por busca no repositório). O `report_router.py` real usa exclusivamente o schema session-centric (§9.1).

Essa distinção é importante para o relatório: o sistema tem "peças fantasma" no banco (schema criado, mas sem escritor ativo) que não devem ser descritas como funcionalidade em uso.

---

## 10. Geração de Relatórios: Gráficos e Curva S — ✅ Implementado

### 10.1 Módulos ativos

O cálculo estatístico e a renderização foram separados em dois módulos (ver também §1.3, SRP):

- **`app/core/services/s_curve.py`** — ajuste do modelo logístico (Fisher-Pry), puro (`numpy`/`scipy`, sem I/O, sem matplotlib).
- **`app/core/services/report_service.py::ReportService`** — orquestração e renderização dos PNGs (`matplotlib`/`numpy`/`pandas`), conectado à rota `POST /report/{session_id}/graphics` (§4.4). Computação pura sobre dicts já extraídos pela rota (sem acesso a banco), salvando os PNGs em `output_dir/session_{id}/`.

Gráficos que entram no relatório. Uma lista fechada, a whitelist `FIGURE_SPECS` em `report_figures.py`, cada um gerado por uma rota própria (§4.4):

- Curva S (Fisher-Pry, com GP/MP/SP) de patentes e de artigos
- Volume anual de patentes e de artigos ("Artigos por Ano")
- Top depositantes (patentes) e top instituições (artigos)
- Quadros top-10 (heatmap): 10 classificações CPC mais encontradas (patentes; códigos IPC são tratados como CPC em todo o relatório, com títulos oficiais de `config/cpc_titles.json`) e áreas de estudo relacionadas (artigos)

Top inventores, top autores, distribuição geográfica e o gráfico de distribuição por área de estudo saíram do relatório por pedido do usuário. Não aparecem no padrão REPTEC.

Regras de renderização adotadas:

- **Sem título dentro do PNG.** O título vai na legenda LaTeX (`\caption`), seguida de "Fonte: O autor.", no padrão REPTEC.
- **Só anos completos.** O ano corrente é descartado das séries (`report_lifecycle.complete_years_only`), porque um ano parcial parece queda e distorce o ajuste.
- **Nomes longos abreviados.** Nomes de depositantes ou instituições com mais de 45 caracteres passam por `chart_labels.abbreviate_labels` para não achatar o gráfico.
- **Resumo numérico.** Cada gráfico devolve um resumo (total, pico, top-N, GP/MP/SP), persistido em `session_chart.summary` e usado pelo prompt para descrever a figura com números reais.

> **Nota**: existe também um módulo mais antigo, `services/report_visualizations.py::TechProspectingVisualizations`, com lógica semelhante mas **não conectado a nenhuma rota** — seu ajuste de curva S usa parâmetros fixos (`k=2`, `x0=len(anos)/2`), sem regressão real. O módulo realmente ativo é o descrito acima.

### 10.2 Modelo matemático: curva logística de Fisher-Pry

O ajuste é feito sobre a contagem **cumulativa** por ano (`np.cumsum` das contagens anuais; em `report_service.py`, os anos sem publicação são reindexados como zero antes de acumular):

$$N(t) = \frac{K}{1 + e^{-r \cdot (t - t_0)}}$$

```python
def logistic(t, K, r, t0):
    return K / (1 + np.exp(-r * (np.asarray(t, dtype=float) - t0)))
```

Onde:
- **N(t)** — quantidade acumulada de documentos até o ano *t*.
- **K** — capacidade máxima / platô de saturação (assíntota superior; total estimado de documentos quando a tecnologia amadurecer).
- **r** — taxa de crescimento (inclinação da subida; quanto maior, mais rápida/concentrada a adoção).
- **t₀** — ponto de inflexão: ano de crescimento máximo, onde N(t) = K/2.

**Ajuste (`scipy.optimize.curve_fit`)**: chute inicial `p0 = [max(cumulativo[-1] × 1.5, 1.0), 0.3, mediana(anos)]`, `maxfev=5000`. Se não convergir, é levantada `SCurveFitError` (não uma exceção genérica) — interpretada como "a série ainda está em fase de crescimento muito inicial, sem sinal de desaceleração para estimar K com confiança", não como erro de programação.

A taxa de crescimento instantânea plotada no gráfico é obtida por diferenciação numérica sobre a curva ajustada: `growth_rate = np.gradient(fitted, years)`.

**Pré-condição**: no mínimo 2 anos distintos com dado — abaixo disso, `fit_s_curve` levanta `ValueError` e o gráfico correspondente é pulado (registrado em `skipped`).

### 10.3 Pontos de leitura do ciclo de vida: GP, MP, SP

GP/MP/SP **são calculados explicitamente pelo código** (`fit_s_curve`, `app/core/services/s_curve.py`), invertendo a curva logística — não é uma interpretação a ser feita manualmente sobre `K`/`r`/`t₀`:

$$t = t_0 - \frac{\ln\left(\frac{1}{f} - 1\right)}{r} \quad \text{(inversão de } N(t) = f \cdot K \text{ para } t\text{)}$$

| Ponto | Definição | Fração de K (padrão) |
|---|---|---|
| **GP** — Ponto de Crescimento | Ano em que a curva acumulada atinge a fração `growth_threshold` de K; antes disso, fase embrionária | **0,10** (10%) |
| **MP** — Ponto Médio | O próprio `t₀`; ano de inflexão, taxa de publicação anual máxima | 0,50 (50%, fixo — é sempre `t₀`) |
| **SP** — Ponto de Saturação | Ano em que a curva atinge a fração `saturation_threshold` de K; a partir daí, fase de maturidade | **0,90** (90%) |

`growth_threshold` e `saturation_threshold` são parâmetros configuráveis (não valores fixos na fórmula — decisão deliberada, ver §1.3/OCP), com os valores acima como *default*. Se o ano calculado para GP/MP/SP for maior que o último ano observado, ele é uma **projeção** (extrapolação do ajuste), não um valor observado.

### 10.4 Diagnóstico de confiabilidade do ajuste (`fit_quality`)

Mesmo quando `curve_fit` converge sem levantar exceção, o resultado pode ser pouco confiável (ex.: poucos anos de dado levando a um platô "inventado" por sobreajuste). `fit_s_curve` retorna um bloco `fit_quality = {r_squared, reliable, warning}`, com `reliable = False` quando qualquer uma das condições abaixo é verdadeira:

| Critério | Limiar | Constante no código |
|---|---|---|
| R² do ajuste abaixo do mínimo | `R² < 0,90` | `_MIN_R_SQUARED = 0.90` |
| Saturação já alta com poucos anos de dado (sinal de sobreajuste) | saturação atual `> 85%` **e** menos de `5` anos observados | `_HIGH_SATURATION_THRESHOLD = 0.85`, `_MIN_YEARS_FOR_HIGH_SATURATION_CONFIDENCE = 5` |
| Taxa de crescimento sem sentido físico | `r ≤ 0` (zero/negativa) | — |
| Taxa de crescimento implausivelmente alta | `r > 5,0` (curva quase em degrau) | `_MAX_PLAUSIBLE_GROWTH_RATE = 5.0` |

R² é calculado da forma usual: $R^2 = 1 - \frac{SS_{res}}{SS_{tot}}$, sobre resíduos entre a curva ajustada e a série acumulada real. Quando `reliable = False`, o gráfico exibe um aviso textual sobreposto (`fit_quality["warning"]`) explicando o motivo em linguagem simples, e o mesmo texto é propagado até a resposta da API.

### 10.5 Dois pontos de entrada, dois contextos de dados

| Método | Origem dos dados | Uso |
|---|---|---|
| `ReportService._chart_s_curve` (privado, via `generate_session_report`) | Documentos (Patent/Article) já persistidos no banco, agregados por `_yearly_counts` | Curva S de **artigos**, sempre; curva S de **patentes** apenas quando não vem via `generate_patent_s_curve` |
| `ReportService.generate_patent_s_curve` (público) | `patents_by_year` recebido no corpo da requisição (`PatentSCurveRequest`) — tipicamente o mesmo dict que `/chat/final/search` já devolve para a fonte OPS | Curva S de **patentes**, chamável logo após a busca final, **sem depender da sessão já ter sido persistida no banco** |

Só `generate_patent_s_curve` aceita `growth_threshold`, `saturation_threshold` e `projection_end_year` customizados (via `PatentSCurveRequest`); `project_s_curve` gera a parte tracejada/projetada do gráfico quando `projection_end_year` é informado.

### 10.6 Contrato de resposta (`schemas/report.py::SCurveFit`)

Os parâmetros do ajuste **são expostos na resposta da API** (`ReportGraphicsResponse.patent_s_curve_fit`), não apenas os caminhos dos PNGs:

```python
class SCurveFit(BaseModel):
    K: float
    r: float
    t0: float
    gp_year: float
    mp_year: float
    sp_year: float
    current_saturation: float          # cumulativo_observado[-1] / K
    years_observed: list[int]
    cumulative_observed: list[float]
    fit_quality: SCurveFitQuality      # {r_squared, reliable, warning}
```

### 10.7 Validação do modelo (autoteste em `s_curve.py`)

O módulo inclui um teste de recuperação de parâmetros executável isoladamente (`python -m app.core.services.s_curve`), que gera uma curva logística sintética conhecida, adiciona ruído gaussiano (15% do desvio-padrão da série anual) e verifica se `fit_s_curve` recupera os parâmetros originais dentro de margem de erro aceitável:

| Parâmetro sintético | Valor verdadeiro | Tolerância de recuperação |
|---|---|---|
| K | 20.000 | 20% de erro relativo |
| r | 0,35 | 20% de erro relativo |
| t₀ | 2015 | 2 anos de erro absoluto |
| `fit_quality.reliable` | — | deve ser `True` |

Período simulado: 2000–2025 (26 anos). Esse teste é um argumento de validação metodológica citável no relatório: demonstra que o estimador recupera corretamente parâmetros conhecidos de um processo gerador simulado, antes de ser aplicado aos dados reais de patentes/artigos.

---

## 11. ✅ Implementado: Módulo de Inferência Estatística (Chao1 + Bootstrap)

**Status: implementado.** O cálculo puro está em `app/core/services/sample_statistics.py`. A orquestração fica em `statistical_inference_service.py`, exposta pela rota `POST /inference/final-search` (§4.4.1), que não persiste nada:

- **`chao1_estimate` / `chao1_diagnostics`**: estimam a riqueza pela fórmula de Chao1 com correção de viés, `S_chao1 = S_obs + f1·(f1−1) / (2·(f2+1))`. Devolvem também a saturação (`S_obs / S_chao1`), `f1`, `f2` e `f1_ratio`.
- **`is_sample_insufficient`**: critério composto. A amostra é insuficiente se qualquer uma destas condições valer:
  - saturação < 0,5;
  - `f1_ratio` > 0,7;
  - `f2` < 5.
- **`bootstrap_topk_stability`**: faz 1.000 reamostragens multinomiais vetorizadas. Para cada item do top-10 original, mede a fração das reamostragens em que ele continua no top-10.
- **Laço de enriquecimento**: `StatisticalInferenceService` repete `ChatService.run_final_search`, pedindo mais iterações, até a amostra saturar ou o tempo configurado acabar. Em seguida resume o resultado em top-10, estabilidade de cada item e relevância semântica ao tema (SBERT).

A motivação original do módulo continua valendo:
- **Estimador Chao1**: para verificar a **saturação da amostra** — se o número de termos/entidades únicas observadas já se aproxima do total estimado da "população" real, ou se ainda há descobertas relevantes não capturadas por falta de volume amostral. Aplicável principalmente sobre a contagem de depositantes/instituições/autores únicos, e sobre a diversidade de termos/CPC observada.
- **Bootstrap**: para verificar a **estabilidade dos rankings top-10** (top depositantes, top instituições, top temas, top CPC) — reamostrando os documentos com reposição múltiplas vezes e observando a variância da composição/ordem do top-10 resultante. Um ranking instável (que muda muito entre reamostragens) é sinal de que a amostra ainda é pequena demais para aquele agregado específico.
- **Aplicação esperada**: como CPC e áreas de estudo tendem a ter cardinalidade baixa (poucas categorias distintas), a saturação (Chao1) e a estabilidade de ranking (bootstrap) devem ser atingidas com amostras relativamente pequenas. Já depositantes/instituições têm cardinalidade alta (muitas entidades distintas, cauda longa), então é esperado que esses rankings exijam volumes de amostra maiores para estabilizar — o módulo serviria justamente para **detectar e sinalizar automaticamente** quando é necessário aumentar o volume da busca final antes de confiar no ranking apresentado.

---

## 12. ✅ Implementado: Persistência de Imagens no MinIO

**Status: implementado desde então** (esta seção descrevia um gap real na época em que foi escrita - `docker-compose.yml` hoje já define o serviço `minio`, `requirements.txt` lista `minio>=7.2.0`, e `app/adapters/driven/storage/minio_adapter.py` + `SessionChart.object_key` (§9.1) são o caminho real de upload/persistência dos PNGs gerados por `ReportService`, ver §10). O texto abaixo (motivação e desenho híbrido local/institucional) continua válido como contexto de decisão.

**O que é o MinIO**: um servidor de armazenamento de objetos open-source, compatível com a API S3 da AWS — ou seja, expõe o mesmo protocolo de "buckets" e "objetos" que o Amazon S3, mas pode rodar em infraestrutura própria (self-hosted), sem depender de nuvem pública. É código livre (Apache 2.0). O serviço que ele presta é: armazenar arquivos binários (aqui, os PNGs de gráficos, e futuramente talvez o PDF/LaTeX compilado do relatório) fora do banco relacional, endereçáveis por chave (`bucket/caminho/arquivo.png`), com controle de acesso e possibilidade de geração de URLs assinadas temporárias.

**Plano de integração**: o MinIO já é usado pelo Exército Brasileiro em outra instância/ambiente. A integração planejada é rodar um **container Docker local** do MinIO (via `docker-compose.yml`, no mesmo padrão hoje usado para `postgres`), configurado para eventualmente apontar/replicar para a instância remota do MinIO do Exército — permitindo que o desenvolvimento local funcione de forma independente, mas com um caminho claro de promoção para o ambiente institucional real. O PostgreSQL local (§14) passaria a armazenar, junto dos dados de cada sessão, a **chave do objeto MinIO** (bucket + caminho) correspondente a cada imagem gerada, em vez de (ou além de) salvar o PNG em disco local do processo do backend.

---

## 13. ✅ Implementado: Relatório LaTeX via RAG local + LLM (padrão REPTEC/AGITEC)

**Status: implementado de ponta a ponta.** Isso inclui o backend, a tela "Geração do Relatório" com editor LaTeX no navegador (§13.8), a compilação de PDF, a revisão de texto (§13.7) e o download `.zip`. Há testes unitários para os módulos puros.

A estrutura do relatório foi extraída de um REPTEC real do AGITEC (`notes/REPTEC_001_2023_TETRA.pdf`, relatório 001/2023 sobre TETRA), e não inventada. Essa estrutura cobre a capa, o sumário, as 8 seções numeradas, o bloco de assinaturas e a formatação. O modelo deixou claro que nem toda seção deve passar por LLM:

| Seção | Como é produzida |
|---|---|
| Capa, Sumário | Estáticas: template Jinja2 com título em negrito e `\tableofcontents`. O sumário tem `tocdepth` 1 e itens em caixa alta. |
| 1 Finalidade | **Fixa**: `render_finalidade(tema, destinatario)` gera "Apresentar o relatório de Prospecção Tecnológica sobre <tema> a fim de fornecer informações … para <destinatário>". Saiu do fluxo de IA. |
| 2 Referências (DIEx/Ofício que originou o pedido) | Dado administrativo inserido pelo usuário e validado em `report_form_validation.py` |
| 3 Objetivo | Texto do usuário (campo do formulário), gravado como seção estática |
| 4 Introdução | **IA** (RAG + LLM) |
| 5 Metodologia (5.1–5.4) | **Fixa**. Não passa por LLM (detalhes abaixo da tabela). |
| 6 Resultados (6.1 Científicas / 6.2 Tecnológicas / 6.3 Tendências e Ciclo de Vida) | **IA** (RAG + LLM), uma chamada por subseção. Cada subseção recebe os resumos numéricos dos gráficos, que o texto posiciona e comenta (§13.6). 6.2 termina no quadro de busca, com a query e o **total real** de documentos da base. |
| 7 Conclusão | **IA** (RAG + LLM), com estrutura orientada (estágio do ciclo de vida, destaques, recomendação) |
| 8 Referências Bibliográficas | Bibliografia fixa da Metodologia, mais as obras **efetivamente citadas** no texto de IA (geradas dos metadados, §13.6), mais as adicionadas pelo usuário. O LLM nunca escreve referências. |
| Local e data, Assinaturas (Elaborado/Revisado/Aprovado) | `render_local_data` ("Rio de Janeiro, 10 de agosto de 2023."). As assinaturas saem no formato **NOME – POSTO/GRAD** em negrito e centralizado, com a **Função** na linha de baixo. Os três campos são editáveis no formulário. |

A Metodologia usa um texto-base quase idêntico em todo REPTEC:

- 5.1–5.3 trazem as figuras fixas de Madeo e Kucharavy, que ficam persistidas no MinIO (`config/report_figures/*`) e são enviadas na inicialização por `report_static_figures.py`.
- 5.4, "Apoio Computacional à Prospecção", descreve em termos gerais o apoio computacional, sem citar modelos nem a plataforma:
  - uso de LLM para elaborar as queries;
  - extração de termos com BM25F e KeyBERT;
  - buscas exploratórias (probe);
  - fusão por RRF.
- O último parágrafo interpola as palavras-chave, o período e as bases desta pesquisa, omitindo o que faltar (`config/prompts/report_static_sections.py::render_metodologia`).

Total: **6 seções de IA**, as chaves de `ReportWriterService.AI_SECTIONS`: `objetivo`, `introducao`, `informacoes_cientificas`, `informacoes_tecnologicas`, `tendencias_ciclo_vida` e `conclusao`. Das 10 esboçadas originalmente, `finalidade`, `metodologia`, `referencias` e `referencias_bibliograficas` saíram do fluxo de LLM. Na montagem, o objetivo informado pelo usuário tem precedência.

**Formatação REPTEC** (`config/prompts/report_latex_template.py`):

- **Fonte e espaçamento.** `babel` brazilian, fonte `tgtermes`, espaçamento 1,5, texto justificado com recuo na primeira linha.
- **Cabeçalho e rodapé** (`fancyhdr`). O cabeçalho, à direita, traz "REPTEC nº/ano – TEMA". O rodapé traz "Página x de y", com `lastpage` e `\pageref*` para não virar link.
- **Seções.** `titlesec` com título em negrito e caixa alta ("1 FINALIDADE").
- **Figuras e quadros.** `\DeclareCaptionType{quadro}` e as macros `\figura[fonte]{título}{arquivo}` e `\quadroimg`, com legenda acima e "Fonte: O autor." abaixo.

A imagem `latex-compiler` instala só esses pacotes via `tlmgr`: `lastpage`, `titlesec`, `tocloft` e as dependências.

### 13.1 Processo fatiado por seção, em duas rotas independentes

Pedido de design explícito: cada seção de IA passa por **duas chamadas HTTP separadas**, não uma única rota que "gera o relatório inteiro":

- `POST /report/{session_id}/sections/{section_key}/rag` - indexa (se ainda não indexado) título+resumo dos documentos da busca final dessa sessão no ChromaDB e recupera o contexto relevante pra aquela seção; persiste em `session_report_section.rag_context`. Não chama o LLM.
- `POST /report/{session_id}/sections/{section_key}/generate` - exige que a rota de RAG já tenha rodado pra aquela seção (422 caso contrário); monta o prompt (`report_prompts.get_section_prompt`) com o contexto já persistido, chama o LLM, escapa caracteres especiais de LaTeX no resultado e persiste em `generated_text`.

Motivação dupla: (1) o frontend sabe exatamente qual etapa está em andamento (loading granular por seção, não uma barra de progresso opaca), e (2) cada chamada ao LLM carrega só o prompt+contexto de **uma** seção, não o relatório inteiro - reduz a janela de tokens por chamada, relevante porque o LLM usado nessa etapa é um recurso compartilhado da intranet (§13.3).

Seções fixas/locais têm rota própria, sem RAG/LLM: `POST /report/{session_id}/sections/static` (Finalidade, Objetivo, Metodologia + Referências Bibliográficas, a partir de `config/prompts/report_static_sections.py`).

Detalhes do RAG por seção:

- **Corte relativo de relevância.** Um trecho só entra no contexto se o score dele for pelo menos `rag_relative_min_relevance` (padrão 0,75, editável em Configurações) vezes o score do trecho mais relevante. Isso corta documentos periféricos que o `top_k` traria de qualquer jeito.
- **Contexto sem scores.** O contexto enviado ao LLM não leva score de similaridade, para evitar que "Relevância: 18%" vaze para o texto.
- **Fontes citáveis.** Junto do contexto, a rota persiste `sources`: a citação e a referência ABNT de cada documento recuperado.
- **Reindexação.** O índice tem versão (`_INDEX_VERSION`), e um índice antigo, sem metadados de citação, é reindexado.

### 13.2 Montagem do `.tex` e compilação de PDF - duas rotas, PDF só sob demanda

- `POST /report/{session_id}/assemble` - lê todas as seções já persistidas (IA + estáticas), baixa **só os PNGs que já existem no MinIO** (via `SessionChart` - nunca dispara geração de gráfico novo; gráficos ausentes entram em `charts_missing` na resposta, sem bloquear), renderiza o template Jinja2 (`config/prompts/report_latex_template.py`, delimitadores customizados `\VAR{}`/`\BLOCK{}` pra não colidir com `{}` do LaTeX) e sobe o `.tex` pro MinIO. **Nunca compila PDF.**
- `POST /report/{session_id}/compile-pdf` - rota separada, só chamada quando o usuário decide compilar (nunca automaticamente); baixa o `.tex` + imagens do MinIO, chama um serviço HTTP dedicado (`latex-compiler/`, container próprio - base `texlive/texlive:latest-minimal`, ~357 MB, + só os pacotes que o template usa de fato, instalados via `tlmgr` no build da imagem; não `tectonic`, porque o alvo final é uma intranet restrita, sem acesso pra baixar pacotes em tempo de compilação - o build da imagem precisa de internet uma vez, o container pronto não) e sobe o PDF resultante. Falha de compilação não apaga o `.tex` já persistido.

Persistência: `session_report_section` (uma linha por seção, upsert por `(session_id, section_key)` - `rag_context`/`generated_text`/`status`) e `session_report` (uma linha por sessão, upsert por `session_id` - `tex_object_key`/`pdf_object_key`/`status`), ambas via migração Alembic própria, mesmo padrão "regenerar sobrescreve, não acumula" de `SessionChart` (§9.1).

### 13.3 LLM: adapter único, compatível com OpenAI, local ou intranet por configuração

O LLM usado nessa etapa é operado pelo Exército numa intranet, gratuito mas remoto (`OLLAMA_BASE_URL`/`OLLAMA_API_KEY` apontando pra um proxy compatível com a API de chat completions da OpenAI, ex. LiteLLM, em `/v1/chat/completions`) - só texto (prompt + contexto já recuperado pelo RAG) sai pra esse endpoint, nunca vetores. `app/adapters/driven/llm/openai_compatible_adapter.py` implementa um novo port, `TextGenerationPort` (`app/core/ports/outbound/text_generation_port.py` - deliberadamente menor que `LLMPort`, que é voltado a JSON estruturado das etapas de refino de tema/query, §6-§8), usando só `httpx`.

Como o Ollama local também expõe esse mesmo formato OpenAI-compatible em `/v1`, **o mesmo adapter serve os dois ambientes** - e isso já foi exercitado de fato: o pipeline foi rodado tanto contra o Ollama local quanto contra o endpoint da intranet, trocando só `base_url`/`api_key` (pela tela de Configurações ou pelo `.env`), sem mudar código. Container `ollama` (imagem oficial, `docker-compose.yml`) cobre esse teste local. `services/ollama_service.py` (API nativa do Ollama, `/api/generate`) não foi reaproveitado propositalmente, por esse motivo.

### 13.4 RAG: ChromaDB como container, embeddings reaproveitados do pipeline existente

`app/adapters/driven/storage/chroma_adapter.py` implementa `VectorStorePort` (já existia como Protocol, sem adapter concreto) contra `chromadb.HttpClient` - **container** (`chromadb/chroma`, `docker-compose.yml`), não `PersistentClient` embutido em disco: um client em processo escrevendo direto num SQLite local não seria seguro se o backend um dia subir com mais de 1 worker (`uvicorn --workers N`), e como container fica no mesmo padrão de rede dos demais serviços (postgres/minio/ollama).

Os embeddings usados pra indexar/consultar o RAG **reaproveitam o `EmbeddingPort` já existente** (sentence-transformers, o mesmo usado por KeyBERT na extração de termos, §5) via uma função de embedding customizada - não os embeddings do Ollama (`nomic-embed-text`), diferente do que o `services/rag_service.py` legado esboçava. Duas consequências: (1) corrige o bug do código legado, que nunca chamava os embeddings do Ollama de fato e usava o default do ChromaDB; (2) o RAG (indexação e busca) fica **100% independente de o LLM estar no ar** - só a geração de texto final depende do Ollama local/intranet.

Corpus indexado por sessão: título + resumo (`abstract`) dos documentos (`Patent`/`Article`, §9.1) da busca final dessa sessão, isolados por `session_id` no metadata de cada chunk (coleção única `report_rag`, não uma coleção por sessão). `Patent.abstract`/`Article.abstract` já existem como colunas e já são preenchidos no fluxo real (`session_probe_documents.py`) - mas, como o payload de artigos da busca final normalmente chega vazio do frontend (`buildProbeQueryPayload` - ver comentário em `report_router.py::generate_article_s_curve`), o corpus de RAG hoje é majoritariamente de **patentes**; o código de indexação trata artigos ausentes normalmente, sem erro.

### 13.5 O que ainda não existe
- **Limitação conhecida:** modelos locais pequenos, como o `gemma3:4b`, erram concordância verbal com sujeito distante. A revisão (§13.7) detecta esses erros, e o ponto de uso `report_review` pode apontar para um modelo melhor em português do que o da redação.
- Sessões com relatório antigo precisam **regenerar as seções e remontar o `.tex`** para receber as melhorias de §13.6. O `.tex` persistido não é reescrito automaticamente.

### 13.6 Qualidade do texto gerado: figuras, números, citações e ciclo de vida

O LLM redige, e módulos puros em Python garantem o que não pode depender do modelo:

- **Figuras no contexto** (`report_figures.py`), no padrão REPTEC: o texto apresenta a figura, a figura aparece e em seguida vem um parágrafo que interpreta os números.
  - O prompt exige esse padrão e dá um exemplo. O LLM escreve "A Figura [[REF:id]] apresenta…" e, em linha própria, `[[FIG:id]]`.
  - `place_figures`, um pós-processador puro, converte os marcadores em `\ref{}` e no bloco `\figura`/`\quadroimg`.
  - Se o LLM cita uma figura sem posicioná-la, ela entra logo após o parágrafo que a cita. Figura não citada vai para o fim da seção, na ordem REPTEC: histórico, top, quadro, curva S.
  - Só figuras da whitelist entram (§10.1).
  - `_fix_figure_word` corrige "Figura"/"Quadro" conforme o tipo, com concordância do artigo (a/o, da/do, na/no, pela/pelo, à/ao).
- **Ciclo de vida calculado, não inferido** (`report_lifecycle.py`). O estágio (Emergente, Crescimento, Maturidade ou Saturação) é determinado em Python a partir de GP/MP/SP da curva S. O estágio geral segue a curva de **patentes**. O LLM recebe o estágio pronto como fato e não o deduz.
- **Citações rastreáveis** (`report_citations.py`):
  - só são aceitas citações "(SOBRENOME et al., ano)" que existam em `sources`, e as inventadas são removidas (`filter_citations`);
  - homônimos recebem sufixo de letra (2020a/2020b);
  - nomes em escrita não latina não geram citação;
  - as referências ABNT das obras realmente citadas entram na seção 8.
- **Validador de texto** (`report_text_quality.py`):
  - corrige números para pt-BR ("17,3%", "1.800");
  - detecta vazamentos do pipeline, como "[Informação não disponível]", "(Fonte: N/A)", "Relevância: 18%", "no contexto fornecido" e listas vazias;
  - diante de vazamento, regenera **uma** vez com instrução de correção e, se persistir, levanta `SectionQualityError`.
- **Prompt de sistema** (`config/prompts/report_prompts.py`): texto impessoal, sem "Fonte:", sem N/A e sem scores de relevância. Os títulos oficiais CPC entram como fatos.
- **Escape LaTeX**: `escape_latex` mantém os indicadores ordinais º/ª, para que "DIEx Nº 256" e "1º Ten" saiam corretos, e remove CJK, que o pdflatex não compila.

### 13.7 Revisão do `.tex` no editor (LanguageTool + IA opcional)

`POST /report/{id}/review` (`report_review.py`, parte pura, + `report_review_service.py`, I/O) revisa o `.tex` atual do editor:

1. **Lint de LaTeX** (`lint_latex`, limitado ao corpo do documento): chaves e ambientes desbalanceados, `\ref` sem rótulo, imagens referenciadas inexistentes, caracteres especiais sem escape e erros do último log de compilação.
2. **Escopo** (`review_scope`): revisa só as **seções geradas por IA** e as **linhas editadas pelo usuário**. As linhas editadas saem da comparação com o baseline `main.assembled.tex` salvo na montagem. Texto fixo e revisado (Metodologia etc.) não é reprocessado.
3. **LanguageTool** (container `erikvl87/languagetool:6.8`, porta 8010, `Java_Xmx=1g`, idioma `languagetool_language`, padrão pt-BR, editável em Configurações). O texto vai pela API *annotated text*, em que comandos LaTeX viram marcação e não são analisados. Só categorias úteis são mantidas: ortografia, acentuação, concordância e gramática.
4. **IA opcional** (ponto de uso `report_review`): segunda opinião por parágrafo, restrita a concordância, acentuação e ortografia. A sugestão só é aceita se o trecho original existir literalmente e se a correção não mexer em números, citações ou comandos LaTeX (`validate_ai_suggestion`). Sugestões sobrepostas às do LanguageTool são descartadas.

O frontend (`ReviewPanel.tsx` + `utils/reviewApply.ts`) lista as sugestões por seção. O usuário aplica ou ignora cada uma individualmente, com recálculo de offsets. Se o LanguageTool ou a IA falhar, o painel mostra um aviso e os problemas de LaTeX continuam valendo.

### 13.8 Tela "Geração do Relatório" e editor

- **Formulário** (`ReportGeneration.tsx`): número/ano, destinatário, objetivo, local, referências administrativas, bibliografia adicional e as três assinaturas (Nome, Posto/Graduação, Função). Tudo passa pelas mesmas validações no frontend (`utils/reportFormValidation.ts`) e no backend (`report_form_validation.py`), que recusam valores de preenchimento como "sdasd".
- **Editor** (`ReportDocumentEditor.tsx`): editor do `.tex` com as ações Salvar, Revisão, Download `.zip` (ícone à esquerda de Compilar) e Compilar PDF. Mensagens de erro do backend (`detail`) aparecem na tela.
- **Painel de imagens**:
  - abre e fecha pelo botão com ícone de imagem na barra lateral (`ReportImagesToggleButton.tsx`), verde quando ativo; fechado, fica oculto;
  - cada imagem tem um menu: Adicionar ao `.tex`, Abrir em nova aba, Download e Excluir (este só para anexos);
  - o subpainel "Anexos" tem um botão "+" para enviar imagens próprias;
  - inserir uma imagem **preserva a posição de rolagem** do editor.
- **Bundle** `.zip` (`POST /bundle`): `.tex` + todas as imagens referenciadas (geradas, fixas e anexos), nomeado `REPTEC_<num>_<ano>.zip`. O nome vem no header `Content-Disposition`, exposto via CORS.

---

## 14. ✅ Implementado: Persistência SQL: PostgreSQL (incl. chaves MinIO)

O PostgreSQL **já está ativo hoje** como banco de produção (não é trabalho futuro) — `.env`/`.env.example` definem `DATABASE_URL=postgresql+asyncpg://...`, `docker-compose.yml` já sobe um serviço `postgres:16-alpine` (+ `pgadmin`), e `core/config.py` tem esse mesmo valor como default. O arquivo `app.db` (SQLite) presente na raiz do projeto é resíduo legado — o fallback para SQLite em `db/session.py` só ocorre se `DATABASE_URL` não estiver definida (usado nos testes automatizados, via `tests/conftest.py`).

A parte antes descrita como faltante em §12 já existe: `SessionChart.object_key` (§9.1) guarda a chave do objeto MinIO de cada gráfico gerado por `ReportService`, e `SessionReport.tex_object_key`/`pdf_object_key` (§9.1, §13.2) fazem o mesmo pro `.tex`/PDF do relatório final - ambos String(500), referenciando `bucket/caminho` diretamente, sem URL livre. Os campos `latex_content`/`report_url` mencionados nas versões anteriores desta seção eram do schema legado (§9.4, `db/research_models.py`), que não é o caminho real.

---

## 15. Fluxo de Dados Ponta a Ponta (resumo)

```
[Usuário] → Tema/Descrição/Keywords/Área
      │
      ▼
[LLM remota] Refinar tema (persona + few-shot) ──► 4 variações candidatas
      │  (usuário escolhe/edita/especifica)
      ▼
[LLM remota] Gerar query PROBE (persona + CoT + guardrail de complexidade)
      │  QueryComplexityAnalyzer avalia cada tentativa (§6); retry até 3x
      ▼
[Query Builder] traduz LLMOutput → CQL/JSON/query_string por API (§7.1)
      │
      ▼
[Busca real - OPS/Scopus] resultados diversificados por ano, filtrados por idioma
      │  (Scopus: resumos enriquecidos via OpenAlex)
      ▼
[NLP local] PatternRank (candidatos) + BM25F + KeyBERT → RRF + C-value (§5) ──► termos rankeados
      │  (usuário seleciona termos + variante: específica/balanceada/ampla)
      ▼
[LLM remota] Gerar query FINAL da variante escolhida, usando termos selecionados
      │  QueryComplexityAnalyzer + retry novamente
      ▼
[Busca real - OPS/Scopus, volume maior] até 250-500 resultados + total_count real (§7.3)
      │  (opcional: POST /inference/final-search - Chao1 + bootstrap, §11)
      ▼
[Persistência PostgreSQL] research_session → session_input → session_probe_query
      │  (tipo=NULL para probe, tipo=variant para final) → patent/article (dedup global)
      ▼
[ReportService] gráficos da whitelist (curva S + volume anual + top + quadros CPC/área) → PNG + resumo numérico
      │
      ▼
[MinIO] upload dos PNGs, chave + summary salvos no Postgres (SessionChart)
      │
      ▼  (por seção de IA - objetivo/introdução/resultados x3/conclusão)
[RAG local - ChromaDB + EmbeddingPort] POST .../sections/{key}/rag
      │  indexa título+resumo da busca final (isolado por session_id), recupera contexto + sources citáveis
      ▼
[LLM local/intranet - OpenAI-compatible] POST .../sections/{key}/generate
      │  só texto sai pro LLM; citações filtradas, números pt-BR, validador + 1 retry (§13.6)
      ▼
[Seções fixas/locais] POST .../sections/static (Finalidade, Objetivo, Metodologia 5.1-5.4, Bibliografia)
      │
      ▼
[Relatório LaTeX, padrão REPTEC/AGITEC] POST .../assemble → place_figures → .tex editável + baseline no MinIO
      │
      ▼
[Editor no frontend] edição do .tex, painel de imagens/anexos
      │  POST .../review → lint LaTeX + LanguageTool + IA opcional (§13.7)
      ▼  (sob demanda do usuário, rota separada - nunca automático)
[Compilação PDF] POST .../compile-pdf → latex-compiler (TeX Live) → PDF no MinIO
      │
      ▼
[Download] POST .../bundle → REPTEC_num_ano.zip (.tex + imagens)
```

---

## 16. Notas de Integridade do Código (para o relatório não citar como real o que não é)

Estes pontos foram verificados diretamente no código-fonte atual e **contradizem documentação antiga presente no repositório** — não usar as fontes abaixo como base para o relatório sem esta ressalva:

- **`ambinte.md`** (raiz do repositório): é uma análise de uma versão **anterior** do projeto (caminho de outro usuário/máquina, referencia `research_router.py`, `param_init.py`/`ParamInit`, `ResearchService` como rotas/tabelas ativas). Nenhuma dessas rotas/tabelas existe mais na árvore atual — confirmado por busca direta nos diretórios de rotas. **Não usar como fonte.**
- **`notes/db_schema_atual.md`**: ✅ regenerado a partir dos modelos SQLAlchemy (`scripts/generate_db_schema_docs.py`) e agora confiável; versões antigas afirmavam que `research_router.py`/`metrics_aggregator.py` usavam o schema legado (§9.4).
- **`frontend/BPMN_IMPLEMENTATION.md`**: descreve uma arquitetura de frontend diferente e nunca construída (`types/flow.ts`, `services/flowApi.ts`, `store/flowStore.ts`, rotas `/flow/*`, exportação PDF/DOCX) — a implementação real usa `/chat/*`, `useFormStore.ts` e os componentes em `components/steps/*` (§3).
- **`config/prompts/probe_system_prompt copy.txt`**: backup obsoleto — `PromptLoader` só carrega `probe_system_prompt.txt`. A cópia serve apenas como evidência histórica de que o bloco de restrição de complexidade foi adicionado depois.
- **`tests/test_routes.py`**: testa endpoints que não existem mais (pré-refatoração hexagonal). Só os testes de `/health` continuam válidos.
- **`services/token_cost_calculator.py`**: código morto, não importado em nenhum lugar do app.
- **`services/nlp/keyword_service.py`**: utilitário separado, não conectado ao pipeline principal de extração de termos (§5.3).
- **`session_chart` com `chart_type` fora da whitelist** (ex.: `top_inventors`, `geographic_distribution` de sessões antigas): continuam no banco, mas nunca entram no `.tex` nem no painel de imagens (§10.1).
- **`services/report_visualizations.py`**: implementação mais antiga de gráficos, com ajuste de curva S simplificado (parâmetros fixos, não regressão real) — não conectada a nenhuma rota; a implementação de produção é `app/core/services/report_service.py` (§10).
- **`db/models.py` e `db/research_models.py`**: schemas criados no banco na inicialização, com código de repositório/adaptador em parte funcional, mas sem nenhum caminho de execução real que escreva neles hoje (§9.4).
