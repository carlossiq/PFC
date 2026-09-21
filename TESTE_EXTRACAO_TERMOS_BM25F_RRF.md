# Teste Comparativo: Pipeline Antigo vs. BM25F + RRF + PatternRank + C-value

> Relatório do teste pedido sobre a migração de `services/nlp/term_extraction.py`
> descrita na spec "TermExtractor para BM25F + RRF nativos no Elasticsearch".
> Cobre: (1) 10 testes com o pipeline **antigo**, (2) decisões de adaptação
> tomadas para a "realidade do nosso programa", (3) os mesmos 10 testes com o
> pipeline **novo**, (4) comparação e veredito.

---

## 0. Metodologia

**Corpus de teste**: 10 "buscas probe" sintéticas, uma por domínio tecnológico
(dessalinização por membrana, bateria de estado sólido, edição gênica CRISPR,
célula solar de perovskita, transferência de energia sem fio, catalisador de
célula a combustível, manufatura aditiva, LIDAR automotivo, blockchain em
cadeia de suprimentos, biosensor vestível de glicose). Cada domínio tem 4
documentos (título + abstract em inglês, estilo patente/paper), **escritos
para este teste** (não copiados de fonte real, sem preocupação de PI). Cada
domínio também tem um `original_params` (tema + descrição) simulando o que o
usuário digitaria.

**Execução**: script Python que instancia `TermExtractor` e chama
`extract_and_rank_terms(original_params, enriched_results)` uma vez por
domínio, cronometrando cada chamada isoladamente (spaCy/KeyBERT já carregados
antes de zerar o cronômetro — mede só o custo de extração, não o carregamento
do modelo). Ambiente: mesma máquina, mesmo processo Python, execuções
sequenciais (sem paralelismo), cache do KeyBERT já quente após a 1ª chamada
de cada rodada.

**Hardware/software**: Windows, Python (venv do projeto), spaCy 3.8.14,
scikit-learn 1.5.1, KeyBERT com `distiluse-base-multilingual-cased-v2`
(mesmo modelo nos dois pipelines).

---

## 1. Decisão de adaptação: por que não Elasticsearch real

A spec original assume um índice Elasticsearch efêmero por requisição
(`probe-terms-{request_id}`) com BM25F via `combined_fields` e `knn` via
`dense_vector`, fundidos pelo retriever `rrf` nativo do ES. **Verifiquei a
infraestrutura real do projeto antes de implementar**:

- `docker-compose.yml`: serviços existentes são `postgres`, `pgadmin`,
  `minio`, `ollama`, `chromadb`, `latex-compiler` — **nenhum Elasticsearch**.
- `requirements.txt`: nenhuma dependência `elasticsearch` (o client oficial
  Python). As únicas menções a "Elasticsearch" no código são comentários em
  `lens_patent_query_builder.py`/`lens_scholarly_query_builder.py` descrevendo
  a **sintaxe de query** da API externa Lens (que usa sintaxe estilo ES),
  não um cluster ES local.

Subir um cluster Elasticsearch (serviço novo no compose, ILM, índice efêmero
por requisição, ciclo de vida/cleanup) só para uma função de sugestão de
termos é uma mudança de infraestrutura desproporcional ao problema, e não
validável nesta sessão (não há cluster para testar contra). **Adaptação**:
implementei BM25F e RRF **nativamente em Python puro** (fórmulas, sem
dependência de serviço externo):

- **BM25F**: fórmula de Okapi BM25 com *pseudo-frequência* combinada por
  campo (Robertson/Zaragoza) — calculada sobre o corpus em memória da
  requisição (os mesmos documentos que seriam indexados no ES), com os
  mesmos pesos título×resumo (3.0/1.0) que a query `combined_fields` teria
  usado (`title^3`, `abstract^1`).
- **RRF**: a fórmula `RRF(t) = Σ 1/(k+rank_i(t))` é trivial e idêntica à
  usada pelo Elasticsearch internamente — implementá-la em Python não perde
  nada da técnica, só não precisa do serviço.
- **Canal semântico**: em vez de `knn` contra `dense_vector` indexado, mantive
  o KeyBERT (mesmo modelo, já configurado) computando similaridade de
  cosseno diretamente — é o mesmo cálculo que o `knn` do ES faria, sem
  precisar indexar embeddings em um serviço externo para um corpus que já
  cabe inteiro em memória.

Isso preserva a essência algorítmica da spec (BM25F, RRF, fusão de canal
léxico+semântico) sem a superfície de manutenção de um cluster ES dedicado a
uma função que hoje roda 100% local. Se o volume de documentos por requisição
crescer muito (hoje: dezenas, não milhares), a migração para ES real volta a
fazer sentido — registrado como possível trabalho futuro, não feito aqui.

### 1.1 Outras adaptações à spec (pontos [VERIFICAR] resolvidos)

- **`KeyphraseCountVectorizer` não tem parâmetro `max_words`** (verificado via
  `inspect.signature` — a spec presumia esse parâmetro, ele não existe na
  API real). Adaptação: gero os candidatos sem teto e filtro depois por
  contagem de palavras, com teto de **5** (não 3) — decisão baseada em
  evidência do próprio teste: o pipeline antigo (teto rígido de 3) **corta
  sistematicamente modificadores importantes** de frases nominais maiores
  (ver §4, dezenas de exemplos). 5 dá folga para frases técnicas reais sem
  permitir frases patologicamente longas.
- **C-value/NC-value** faz menos trabalho do que a spec antecipava: como o
  `KeyphraseCountVectorizer` já emite a frase nominal **maximal** (não todas
  as sub-janelas de 1-3 palavras como antes), a maioria dos candidatos já
  nasce sem fragmentos redundantes — o C-value entra principalmente para
  pegar frases quase-duplicadas entre documentos diferentes (ex.: "wireless
  charging" aninhado em "electric vehicle wireless charging pads"), não para
  limpar uma enxurrada de sub-n-gramas como o filtro de sobreposição antigo
  precisava fazer.
- **Threshold final recalibrado empiricamente** (script de calibração rodando
  o pipeline novo com `threshold=0.0` sobre os 10 casos, 459 termos
  observados): `min=0.0184 max=0.0325 mean=0.0244 median=0.0244`. Fixei
  `term_extraction_score_threshold = 0.024` (≈ mediana → mantém a metade
  melhor de cada amostra, ~20-27 termos/busca — volume comparável ao
  threshold antigo de 0.35 na escala 0-1).
- **Campo `score` mantido na saída** por compatibilidade de contrato: o
  frontend (`frontend/src/services/finalQuery.ts::ExtractedTerm`,
  `TermSampling.tsx` linha `t.score.toFixed(2)`) consome `score` diretamente.
  A spec original (§9) propunha removê-lo em favor só de `final_rrf_score` —
  mantive os dois (mesmo valor), preservando a saída da rota como pedido.

---

## 2. Parte 1 — Pipeline ANTIGO (spaCy noun_chunks + TF-IDF + KeyBERT, combinação linear)

| # | Domínio | Tempo | Termos | Top 3 (score) |
|---|---|---|---|---|
| 01 | Dessalinização por membrana | 5.00s | 23 | brackish water desalination (0.79), oxide modified membrane (0.73), composite ultrafiltration membrane (0.70) |
| 02 | Eletrólito de lítio sólido | 4.03s | 25 | lithium ion batteries (0.84), solid state lithium (0.84), density lithium metal (0.73) |
| 03 | Entrega de CRISPR | 4.12s | 22 | cas9 gene editing (0.88), viral genome editing (0.73), peptide conjugated cas9 (0.71) |
| 04 | Célula solar de perovskita | 3.65s | 26 | perovskite solar cells (0.89), tandem solar cell (0.73), perovskite absorber layer (0.66) |
| 05 | Transferência de energia sem fio | 3.36s | 23 | vehicle wireless charging (0.82), efficiency wireless power (0.75), resonant coil design (0.67) |
| 06 | Catalisador de célula a combustível | 3.44s | 24 | core shell catalyst (0.81), cobalt alloy catalyst (0.78), precious metal catalyst (0.76) |
| 07 | Manufatura aditiva de ligas | 3.57s | 25 | aluminum alloy parts (0.83), titanium alloy aerospace (0.82), laser powder bed (0.81) |
| 08 | LIDAR / detecção de objetos | 3.16s | 21 | lidar point cloud (0.83), state lidar architecture (0.75), compact autonomous vehicle (0.74) |
| 09 | Blockchain / cadeia de suprimentos | 3.37s | 19 | supply chain data (0.85), retail supply chains (0.80), preserving blockchain architecture (0.72) |
| 10 | Biosensor vestível de glicose | 3.59s | 26 | sweat glucose biosensor (0.94), biosensor health monitoring (0.82), continuous glucose monitoring (0.81) |
| **Total** | | **37.29s** | **234** | |

### 2.1 Avaliação qualitativa (pipeline antigo)

O problema dominante, presente em **9 dos 10 casos**, é o teto rígido de 3
palavras truncando frases nominais maiores e perdendo o modificador mais
informativo — geralmente o do início da frase:

| Frase completa no texto original | O que o pipeline devolveu | Palavra perdida |
|---|---|---|
| "ammonia carbon **dioxide** draw solution" | `dioxide draw solution` | ammonia carbon |
| "**graphene** oxide modified membrane" | `oxide modified membrane` | graphene |
| "**thin** film polyamide layer" (aparece à parte, ok) | ok em outro termo | - |
| "lithium lanthanum zirconium **oxide**" | `lithium lanthanum zirconium` | oxide |
| "**CRISPR** cas9 gene editing" | `cas9 gene editing` | CRISPR |
| "**adeno** associated virus vector" | `associated virus vector` | adeno |
| "**tin** lead mixed perovskite" | `lead mixed perovskite` | tin |
| "hole **transport** material engineering" | `transport material engineering` | hole |
| "wide bandgap top **cell**" | `wide bandgap top` | cell |
| "**privacy** preserving blockchain architecture" | `preserving blockchain architecture` | privacy |
| "**flexible** sweat glucose biosensor" | `sweat glucose biosensor` (e também `flexible sweat` solto) | flexible (fragmentado em 2 termos) |
| "**colorimetric** sweat sensor patch" | `colorimetric sweat` (solto, sem "sensor patch") | fragmentado |
| "**solid** state lidar architecture" | `state lidar architecture` | solid |

Também aparecem fragmentos de verbo net cortados de frases maiores
("control algorithm detects", "detects vehicle position", "resulting
microstructure exhibits") — resíduos de noun chunks que incluíam um verbo
adjacente antes de serem cortados.

**Nota qualitativa por caso** (1-10, legibilidade/completude/precisão do
termo para um humano curar manualmente):

| Caso | Nota | Justificativa |
|---|---|---|
| 01 | 5/10 | 3 de 3 termos do top afetados por truncamento |
| 02 | 6/10 | "lithium lanthanum zirconium" sem "oxide" é o pior caso; resto ok |
| 03 | 4/10 | "cas9 gene editing" perde CRISPR (termo #1!); "vivo crispr gene" com ordem estranha |
| 04 | 6/10 | vários truncamentos, mas top 1-2 (perovskite solar cells, tandem solar cell) completos e fortes |
| 05 | 7/10 | menos truncamento grave neste domínio; termos majoritariamente legíveis |
| 06 | 7/10 | domínio com nomes curtos (catalyst, cobalt, platinum) sofre menos com teto de 3 |
| 07 | 6/10 | "manufactured nickel superalloy" perde "turbine blades"; resto razoável |
| 08 | 6/10 | "state lidar architecture" perde "solid"; "compact autonomous vehicle" ok |
| 09 | 5/10 | "preserving blockchain architecture" perde "privacy" (conceito central do doc!); "multi party supply" perde "chain" |
| 10 | 5/10 | pior caso de fragmentação: "flexible sweat" e "colorimetric sweat" soltos, sem completar a frase |
| **Média** | **5.7/10** | |

---

## 3. Parte 2 — Pipeline NOVO (PatternRank + BM25F + RRF em 2 estágios + C-value)

| # | Domínio | Tempo | Termos | Top 3 (final_rrf_score) |
|---|---|---|---|---|
| 01 | Dessalinização por membrana | 1.49s | 27 | composite ultrafiltration membrane (0.0305), brackish water desalination (0.0303), seawater desalination (0.0290) |
| 02 | Eletrólito de lítio sólido | 1.12s | 23 | flexible lithium ion batteries (0.0315), garnet type oxide (0.0292), excellent electrochemical stability (0.0290) |
| 03 | Entrega de CRISPR | 1.10s | 25 | split cas9 architecture (0.0288), precise nucleotide conversion (0.0285), conventional crispr cas9 nuclease editing (0.0284) |
| 04 | Célula solar de perovskita | 0.94s | 24 | solar cell applications (0.0308), mixed perovskite absorber (0.0302), unencapsulated reference devices (0.0296) |
| 05 | Transferência de energia sem fio | 1.05s | 23 | electric vehicle wireless (0.0325), wireless power transfer (0.0315), resonant coil design (0.0308) |
| 06 | Catalisador de célula a combustível | 0.98s | 25 | thin platinum shell (0.0313), fuel cell catalysts (0.0313), platinum cobalt alloy catalyst (0.0306) |
| 07 | Manufatura aditiva de ligas | 0.96s | 25 | titanium alloy aerospace components (0.0299), nickel superalloy turbine blades (0.0295), selective laser melting (0.0290) |
| 08 | LIDAR / detecção de objetos | 0.88s | 25 | lidar point cloud (0.0311), point cloud segmentation network (0.0308), solid state lidar architecture (0.0298) |
| 09 | Blockchain / cadeia de suprimentos | 1.00s | 25 | retail supply chains (0.0303), supply chain participants (0.0294), supply chain traceability (0.0292) |
| 10 | Biosensor vestível de glicose | 0.88s | 24 | wearable biosensor health monitoring (0.0328), continuous glucose monitoring (0.0308), multiplexed biosensor array (0.0306) |
| **Total** | | **10.40s** | **246** | |

### 3.1 Avaliação qualitativa (pipeline novo)

O truncamento sistemático **desaparece**: candidatos são frases nominais
completas, incluindo 4 e 5 palavras quando o texto realmente tem uma frase
maior:

- `titanium alloy aerospace components` (4), `nickel superalloy turbine
  blades` (4), `solid state lithium metal batteries` (5), `wearable
  biosensor health monitoring devices` (5), `point cloud segmentation
  network` (4), `adeno associated virus vector` (4, preserva "adeno"),
  `conventional crispr cas9 nuclease editing` (5, preserva CRISPR),
  `flexible sweat glucose biosensor` (4, preserva "flexible" na mesma
  frase, sem fragmentar), `colorimetric sweat sensor patch` (4, idem).

**Limitação real encontrada** (não hipotética — apareceu no teste): o padrão
gramatical `<J.*>*<N.*>+` (adjetivo* + substantivo+) **não cobre gerúndio
modificador** (`VBG`). No caso 09, "**privacy preserving** blockchain
architecture" não vira um candidato único — "preserving" (gerúndio) quebra o
casamento do padrão, e o texto gera separadamente `privacy` (unigrama fraco),
`blockchain architecture` (bigrama, ok) e depois nem "privacy preserving
blockchain architecture" completo sobrevive. Isso confirma exatamente o
ponto de risco que a própria spec de migração já sinalizava ("testar se
termos como... estão sendo cortados, permitir `<VBG>?` no meio").
**Recomendação de ajuste futuro** (não aplicada nesta sessão, fora do escopo
do teste): estender o padrão para algo como `<J.*>*<VBG>?<N.*>+`.

**Segunda observação real**: alguns unigramas genéricos sobrevivem ao
threshold com mais frequência do que no pipeline antigo — `titanium`,
`aluminum`, `laser`, `components` (caso 07), `cars`, `self`, `network`,
`vehicles` (caso 08), `architecture`, `privacy`, `transparency`, `end` (caso
09), `sulfide`, `polymer` (caso 02), `nanoparticle`, `cells`, `cell`,
`correction` (caso 03). Causa identificada: a fusão RRF é **baseada em
posição/rank**, não em magnitude — um unigrama muito frequente (ex.
`titanium` freq=3, `vehicles` freq=4) pode ranquear #1-#5 no canal de
salience (BM25F+semântico) mesmo com péssima colocação no canal de
qualidade estrutural (penalidade -0.4), e a soma `1/(k+rank_salience) +
1/(k+rank_quality)` ainda fecha acima do threshold. No pipeline antigo, a
penalidade de -0.4 era **somada diretamente** ao score 0-1, o que quase
sempre empurrava unigramas para baixo do threshold fixo de 0.35 — um
mecanismo de supressão mais agressivo que a fusão por rank. **Trade-off
documentado, não uma regressão silenciosa**: nenhum desses unigramas é
"errado" (são termos de domínio genuínos), mas o filtro antigo os suprimia
com mais força.

**Nota qualitativa por caso**:

| Caso | Nota | Justificativa |
|---|---|---|
| 01 | 9/10 | frases completas, "long term filtration tests" preservado; só "energy" (unigrama fraco) no fim |
| 02 | 8/10 | "solid state lithium metal batteries" (5 palavras, perfeito); "sulfide"/"polymer" soltos no fim |
| 03 | 9/10 | CRISPR preservado em todos os termos relevantes; "cells"/"cell"/"correction" fracos no fim |
| 04 | 9/10 | "mixed perovskite absorber layer" completo; muito coerente |
| 05 | 9/10 | domínio já era forte antes, aqui ficou ainda mais consistente |
| 06 | 9/10 | frases de 4 palavras corretas ("platinum cobalt alloy catalyst", "non precious metal catalyst") |
| 07 | 7/10 | ótimas frases no topo, mas "titanium"/"aluminum"/"laser"/"components" soltos pesam no fim da lista |
| 08 | 6/10 | boas frases no topo, mas "cars"/"self"/"network"/"vehicles" isolados são ruído real |
| 09 | 6/10 | perde a frase "privacy preserving blockchain architecture" completa (limitação de VBG); "end"/"architecture"/"privacy"/"transparency" soltos |
| 10 | 9/10 | "wearable biosensor health monitoring devices" (5 palavras) e "flexible sweat glucose biosensor" completos, sem fragmentação |
| **Média** | **8.1/10** | |

---

## 4. Comparação direta

### 4.1 Tempo

| # | Domínio | Antes | Depois | Δ |
|---|---|---|---|---|
| 01 | Dessalinização | 5.00s | 1.49s | **-70%** |
| 02 | Lítio sólido | 4.03s | 1.12s | **-72%** |
| 03 | CRISPR | 4.12s | 1.10s | **-73%** |
| 04 | Perovskita | 3.65s | 0.94s | **-74%** |
| 05 | Wireless power | 3.36s | 1.05s | **-69%** |
| 06 | Célula combustível | 3.44s | 0.98s | **-72%** |
| 07 | Manufatura aditiva | 3.57s | 0.96s | **-73%** |
| 08 | LIDAR | 3.16s | 0.88s | **-72%** |
| 09 | Blockchain | 3.37s | 1.00s | **-70%** |
| 10 | Biosensor | 3.59s | 0.88s | **-76%** |
| **Total** | | **37.29s** | **10.40s** | **-72% (3.6x mais rápido)** |

Causa principal: o pipeline antigo chamava KeyBERT/TF-IDF **4 vezes** por
requisição (título e resumo, separadamente, ×2 métodos) mais o filtro de
sobreposição O(N×|selecionados|) sobre um conjunto de candidatos muito maior
(até 182 candidatos únicos num caso). O pipeline novo chama KeyBERT **1
vez** (corpus combinado), BM25F é aritmética pura (sem `fit_transform` de
vetorizador), e o C-value roda sobre um conjunto de candidatos bem menor
(PatternRank gera menos ruído de sub-janelas desde o início).

### 4.2 Qualidade (nota subjetiva 1-10, ver §2.1/§3.1)

| # | Domínio | Antes | Depois | Δ |
|---|---|---|---|---|
| 01 | Dessalinização | 5 | 9 | +4 |
| 02 | Lítio sólido | 6 | 8 | +2 |
| 03 | CRISPR | 4 | 9 | +5 |
| 04 | Perovskita | 6 | 9 | +3 |
| 05 | Wireless power | 7 | 9 | +2 |
| 06 | Célula combustível | 7 | 9 | +2 |
| 07 | Manufatura aditiva | 6 | 7 | +1 |
| 08 | LIDAR | 6 | 6 | 0 |
| 09 | Blockchain | 5 | 6 | +1 |
| 10 | Biosensor | 5 | 9 | +4 |
| **Média** | | **5.7** | **8.1** | **+2.4** |

### 4.3 Volume e schema

| Métrica | Antes | Depois |
|---|---|---|
| Total de termos retornados (10 casos) | 234 | 246 |
| Termos/caso (faixa) | 19-26 | 23-27 |
| Candidatos brutos antes de filtrar (ex. caso 10) | 182 | ~45-50 |
| Campos por termo | term, score, n_words, keybert_score_title/abstract, tf_idf_score_title/abstract, frequency, sources, score_bonus, score_penalty, title_weight, abstract_weight (13 campos) | term, score, salience_score, quality_score, final_rrf_score, c_value, n_words, frequency, sources (9 campos) |
| `score` = valor que decide ranking/corte? | **Não** (bug documentado em EXTRACAO_TERMOS_NGRAMAS.md §18.2 — `score` era o pure_score, ranking usava `adjusted_score`) | **Sim** (score == final_rrf_score, mesmo valor que ordena e corta) |

---

## 5. Veredito: ganho ou perda?

**Ganho líquido**, em 4 das 5 dimensões avaliadas:

| Dimensão | Resultado |
|---|---|
| Velocidade | **Ganho forte** — 3.6x mais rápido (37.29s → 10.40s nos 10 casos) |
| Completude das frases extraídas | **Ganho forte** — o truncamento sistemático de 3 palavras (presente em 9/10 casos antigos) desaparece; frases de 4-5 palavras corretas passam a existir |
| Qualidade subjetiva média | **Ganho** — 5.7 → 8.1 (+42%), com 2 casos praticamente empatados (07, 08) e nenhum caso pior |
| Consistência do schema (`score` == valor real de corte) | **Ganho** — corrige um bug documentado do pipeline antigo |
| Ruído de unigramas genéricos | **Leve perda** — a fusão RRF por rank suprime unigramas frequentes com menos força que a penalidade aditiva antiga; aparecem ~2-4 unigramas fracos a mais por caso nos domínios com palavras de alta frequência (titanium, vehicles, architecture, etc.) |

**Limitação real encontrada, não hipotética**: o padrão POS do PatternRank
não cobre gerúndio modificador (`<VBG>`), perdendo compostos como "privacy
preserving X" — caso concreto no domínio 09. Ajuste sugerido (fora do
escopo deste teste): `pos_pattern="<J.*>*<VBG>?<N.*>+"`.

**Recomendação**: migração vale a pena. Antes de ir para produção,
sugiro (a) ajustar o `pos_pattern` para cobrir gerúndio, (b) considerar um
piso mínimo de `quality_score` (ex. descartar unigramas com frequência alta
mas nenhuma ocorrência multi-palavra) para conter o ruído identificado em
§4.2, e (c) rodar contra uma amostra real de resultados de busca probe (não
só o corpus sintético deste teste) antes de calibrar o threshold em
produção — o valor `0.024` fixado aqui vem de 459 termos sintéticos, não de
histórico de curadoria real do usuário (a spec original já previa isso em
§8: calibração formal exige histórico de curadoria, que ainda não existe).

---

## 6. Arquivos alterados nesta migração

| Arquivo | Mudança |
|---|---|
| `services/nlp/term_extraction.py` | Reescrito: PatternRank (KeyphraseVectorizers) substitui spaCy noun_chunks+sub-n-gramas; BM25F substitui TfidfVectorizer; RRF (2 estágios) substitui combinação linear 0.6/0.4 + 3.0/1.0; C-value substitui filtro de sobreposição/subsunção. Removidos (dead code após a troca): `_extract_noun_chunks`, `_extract_subngramas_from_chunk`, `_split_by_boundaries`, `_clean_pos_tags`, `_extract_tfidf_scores`, `_apply_subsumption_filter`, `_get_score_adjustments`, `_load_ngram_boundary_tokens` |
| `core/config.py` | Novas settings: `term_extraction_bm25_k1`, `term_extraction_bm25_b`, `term_extraction_rrf_k`, `term_extraction_cvalue_min_frequency`. `term_extraction_score_threshold` recalibrado (0.35 → 0.024, escala mudou). `term_extraction_overlap_threshold` marcado deprecated (não lido mais) |
| `requirements.txt` | Adicionado `keyphrase-vectorizers>=0.0.13` e `spacy>=3.8.0` (spaCy já era importado pelo código mas faltava no requirements) |
| Rota (`ChatService.extract_terms`, `/chat/extract-terms`) | **Inalterada** — mesma assinatura de entrada, mesmo envelope de resposta (`success`/`terms`/`count`/`ai_usage`). Campo `score` mantido no schema de cada termo por compatibilidade com o frontend |
| `config/ngram_boundary_tokens.json` | Não usado mais pelo código (PatternRank não precisa de lista de tokens de fronteira); arquivo deixado no disco, não deletado |

Não alterados: filtro de idioma a montante, filtro de termos originais,
`patent_structural_words`/`scholarly_structural_words`
(`config/string_quality_filter.json`), `MAX_RETURNED_TERMS = 60`.
