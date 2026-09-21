# Pipeline de Extração e Pontuação de Termos (N-gramas)

> Documento de referência minucioso do processo implementado em
> `services/nlp/term_extraction.py` (classe `TermExtractor`, método
> `extract_and_rank_terms`). Cobre desde a entrada (título + resumo dos
> documentos recuperados) até a lista final de termos com score, passando por
> todos os filtros, thresholds e fórmulas usados atualmente no código
> (verificado linha a linha em 2026-09-17, não a partir do docstring da função,
> que está desatualizado em alguns pontos — ver §12).

---

## 0. Onde isso entra no sistema

`TermExtractor.extract_and_rank_terms()` é chamado por
`ChatService.extract_terms()` (`app/core/services/chat_service.py:1812`),
que recebe uma lista de `items` (resultados de uma busca probe já filtrados
por idioma em `services/nlp/language_filter.py`, a montante — descarta
resumos que não parecem estar em inglês) e os original_params (tema/descrição
digitados pelo usuário). Não há LLM nessa etapa: é 100% local
(spaCy + KeyBERT + TF-IDF/scikit-learn).

```
busca probe (API externa) → filtro de idioma → extract_terms()
                                                     │
                                                     ▼
                                    extract_and_rank_terms() (este documento)
                                                     │
                                                     ▼
                              lista de termos com score → curadoria pelo usuário
```

Uma única instância de `TermExtractor` é compartilhada entre requisições
(`get_term_extractor()`, `term_extraction.py:1129`) porque carregar o spaCy e o
KeyBERT é caro; a instância não guarda estado mutável entre chamadas.

O parâmetro `top_k` da função é **ignorado** (marcado como deprecated no
código) — quem limita a quantidade final é o threshold de score (§9) somado a
um teto rígido de 60 termos (§10).

---

## 1. Entrada de dados

Para cada item em `enriched_results`, o código tenta primeiro a estrutura
`biblio` (`item["biblio"]["invention_title"]`/`"title"`/`"abstract"`) e cai
para acesso direto (`item["title"]`/`"abstract"`) se `biblio` não existir.
Itens sem título **e** sem resumo são descartados.

Título e resumo de cada documento são tratados como **dois conjuntos de texto
sempre separados** (`title_texts` e `abstract_texts`) — nunca concatenados
antes da pontuação. Isso permite pesos e scores diferentes por fonte (§6, §7).

---

## 2. Normalização de texto (`_clean_text`, linha 221)

Aplicada a título, resumo e também aos `original_params` (tema/descrição do
usuário):

1. `lower()` — tudo em minúsculas.
2. Remove URLs: regex `http\S+|www.\S+` → vazio.
3. Normaliza hífens para espaço (`"salt-water"` → `"salt water"`).
4. Colapsa espaços múltiplos e remove espaços nas pontas (regex `\s+` → `" "`, depois `.strip()`).

**Pontuação NÃO é removida aqui de propósito** — o comentário no código
explica que a pontuação é mantida para que o spaCy detecte tokens de
fronteira (tags POS `PUNCT`), usados na etapa de segmentação (§4.2).

Os `original_params` (tema, descrição etc.) passam pelo mesmo `_clean_text` e
viram um `set` de palavras (`_normalize_original_params`, linha 553) — usado
depois no filtro de termos originais (§8).

---

## 3. Geração de candidatos — parte 1: noun chunks (`_extract_noun_chunks`, linha 285)

Cada texto (título ou resumo, já limpo) é processado pelo spaCy
(`en_core_web_sm`). O código itera `doc.noun_chunks` (sintagmas nominais
detectados linguisticamente) e, para cada chunk:

1. Extrai tokens e suas tags POS.
2. Aplica **limpeza de bordas POS** (`_clean_pos_tags`, linha 249): remove
   tokens do **início e do fim** da sequência cujo POS esteja no conjunto
   `{DET, ADP, CCONJ, SCONJ, PART, PUNCT, SPACE, SYM}` (ex.: remove "the" do
   início, "of" do fim). Só as bordas são cortadas — POS indesejado no meio do
   chunk não é removido nesta etapa (isso é tratado na segmentação por
   fronteiras, §4.2).
3. Descarta o chunk se, depois da limpeza, sobrar uma string vazia ou com
   ≤ 2 caracteres (`len(" ".join(cleaned)) > 2`).

Se o spaCy não estiver disponível (`self.nlp is None`), essa etapa retorna
lista vazia — n-gramas simplesmente não são extraídos (sem fallback por
regex).

---

## 4. Geração de candidatos — parte 2: sub-n-gramas (`_extract_subngramas_from_chunk`, linha 323)

Cada noun chunk (já limpo na etapa 3) é reprocessado pelo spaCy para obter
tokens/POS novamente, e então:

### 4.1 Segmentação por fronteiras (`_split_by_boundaries`, linha 373)

Percorre os tokens do chunk e corta a sequência em sub-segmentos sempre que
encontra um **token de fronteira** ou um **POS de fronteira**:

- **Tokens de fronteira**: `config/ngram_boundary_tokens.json`, lista
  fechada de ~90 palavras (comparação exata, case-insensitive), agrupadas por
  categoria:
  - Pronomes relativos / conjunções subordinativas de patente: `wherein,
    whereby, whereof, whereas, where, when, while, whilst, which, that, who,
    whom, whose`
  - Conjunções coordenativas: `and, or, nor, but, yet, so`
  - Conjunções subordinativas / conectivos: `if, unless, although, though,
    because, since, therefore, thereby, thereof, therein, thereon, therewith,
    herein, hereby, hereof, hereto`
  - Verbos de "boilerplate" de patente: `comprising, comprises, comprise,
    including, includes, include, containing, contains, contain, having,
    has, have, provided, providing, formed, forming, configured, adapted,
    arranged, disposed, mounted, attached, connected, coupled`
  - Outros verbos/termos de ligação de patente: `relates, relating,
    according, said`
  - Preposições / advérbios de ligação: `using, used, based, via, through,
    by, with, without, from, into, onto, upon, over, under, between, among,
    during, before, after`
  - Advérbios de grau/qualificação: `respectively, particularly, preferably,
    generally, typically, specifically, substantially, approximately`
- **POS de fronteira** (`config/pos_patterns.json` → `ngram_boundary_pos`):
  `ADP, CCONJ, SCONJ, PUNCT, SPACE, NUM`.

Ao encontrar um token/POS de fronteira, o segmento corrente é fechado (se
não-vazio) e um novo começa. Tokens puramente não-alfanuméricos (pontuação
isolada) são descartados mesmo dentro de um segmento; um token como
`"don't"` é mantido porque contém caracteres alfanuméricos. Se nenhuma
fronteira for encontrada, o chunk inteiro vira um único segmento.

### 4.2 Extração dos n-gramas dentro de cada segmento

Para cada segmento resultante (tokens que **não** atravessam nenhuma
fronteira), gera todos os n-gramas contíguos de tamanho `n = 1` até
`min(3, tamanho_do_segmento)` (janela deslizante). Ou seja: **o tamanho
máximo de qualquer termo candidato é 3 palavras** — não existem 4-gramas ou
maiores neste pipeline.

Cada sub-n-grama passa de novo por `_clean_pos_tags` (limpeza de bordas POS)
e só é aceito se sobrar texto com mais de 2 caracteres.

**Efeito prático combinado (etapas 3+4):** um noun chunk como
`"a water desalination process wherein the membrane"` seria: (a) limpo nas
bordas pelo passo 3, (b) quebrado no token de fronteira `wherein` pelo passo
4.1, produzindo dois segmentos independentes, e (c) cada segmento gera seus
próprios uni/bi/trigramas — nenhum n-grama final atravessa o `wherein`.

### 4.3 Deduplicação e rastreamento de frequência/fonte

Todos os n-gramas de todos os títulos e todos os resumos são acumulados em
`all_ngrams`, com:
- `ngram_frequency` (um `Counter`) contando quantas vezes cada string de
  n-grama aparece no corpus inteiro (títulos + resumos, todos os documentos).
- `ngram_sources[ngram] = {"title": n, "abstract": m}` contando em quantos
  textos de título / de resumo o n-grama apareceu.
- `unique_ngrams = list(dict.fromkeys(all_ngrams))` — deduplicação
  preservando a ordem de primeira ocorrência.

Se `unique_ngrams` ficar vazio, a função retorna lista vazia imediatamente.

---

## 5. Pontuação bruta: KeyBERT + TF-IDF (calculados separadamente para título e resumo → 4 dicionários de score)

spaCy é usado **apenas** como gerador de candidatos (etapas 3-4); a
pontuação em si vem de dois métodos independentes, cada um rodado uma vez
sobre `title_texts` e uma vez sobre `abstract_texts`:

### 5.1 KeyBERT (`_extract_keybert_scores`, linha 418)

Modelo: `distiluse-base-multilingual-cased-v2` por padrão, configurável via
`settings.llm_keybert_model` (carregado no `__init__`, linha 74-79).

1. Concatena todos os textos do grupo (`" ".join(texts)`) em um único bloco —
   **não há chunking por documento**; o KeyBERT roda uma vez sobre o texto
   combinado do grupo inteiro.
2. **Passe restrito**: `keybert.extract_keywords(combined_text,
   candidates=unique_ngrams, top_n=min(len(ngrams), 50))` — o KeyBERT
   pontua apenas os candidatos já extraídos (não gera novas frases), e
   devolve no máximo 50.
3. **Critério de fallback**: se `len(scores) < len(ngrams) * 0.5` (cobertura
   menor que 50% dos candidatos), roda um **segundo passe irrestrito**:
   `extract_keywords(combined_text, top_n=min(len(ngrams), 100))` (sem
   `candidates` — o KeyBERT extrai suas próprias keyphrases livremente).
4. Para cada n-grama ainda sem score depois do passe restrito, calcula um
   score por **sobreposição de palavras** com as keywords do passe
   irrestrito:
   ```
   overlap = |palavras_comuns(ngrama, keyword)| / |palavras(ngrama)|
   score_escalado = score_da_keyword × overlap
   ```
   Toma o **máximo** entre todas as keywords candidatas para aquele n-grama
   (`best_score = max(best_score, scaled_score)`); só atribui score se
   `best_score > 0`.

O score bruto do KeyBERT é uma similaridade tipo cosseno, teoricamente em
`[-1, 1]`, mas na prática (embeddings de sentence-transformers) tende a ser
não-negativo; o código não recorta essa faixa explicitamente.

### 5.2 TF-IDF (`_extract_tfidf_scores`, linha 493)

Usa `sklearn.feature_extraction.text.TfidfVectorizer(analyzer="word",
lowercase=True)`, ajustado (`fit_transform`) sobre o grupo de textos
(títulos ou resumos, separadamente).

Para cada n-grama candidato:
- Se o n-grama inteiro estiver no vocabulário do vectorizer (comum para
  unigramas, raro para bi/trigramas — o `TfidfVectorizer` padrão só indexa
  unigramas), o score é a **média da coluna TF-IDF entre todos os
  documentos** daquele grupo: `tfidf_matrix[:, idx].mean()`.
- Se for multi-palavra e **não** estiver diretamente no vocabulário, só
  recebe score se **todos** os tokens componentes estiverem no vocabulário
  (nenhum score parcial é dado se faltar algum token); nesse caso o score é
  a **média aritmética simples** dos scores TF-IDF médios de cada token
  componente.
- N-gramas que não atendem nenhum dos dois critérios acima **não recebem
  entrada no dicionário** (ausência ≠ zero explícito, mas é tratado como 0.0
  downstream via `.get(ngram, 0.0)`).

Ao final, os scores do grupo são **normalizados pelo próprio máximo**:
`scores = {k: v / max(scores.values()) for k, v in scores.items()}` — ou
seja, o TF-IDF já sai normalizado em `[0, 1]` desta função (o maior termo do
grupo sempre vale exatamente 1.0).

---

## 6. Normalização adicional do KeyBERT

Diferente do TF-IDF (já normalizado dentro de `_extract_tfidf_scores`), o
KeyBERT é normalizado depois, fora da função de extração, com a mesma lógica
(`normalize_scores`, linha 902): `score / max(scores.values())` por grupo,
aplicada **separadamente** para `keybert_title_scores` e
`keybert_abstract_scores`. Isso garante que os dois métodos fiquem na mesma
escala `[0, 1]` antes de serem combinados, evitando que um domine o outro por
causa de faixas de valor diferentes.

---

## 7. Combinação de scores

### 7.1 Combinação por fonte (título ou resumo)

Pesos fixos no código (não configuráveis):

```
w_tfidf   = 0.6
w_keybert = 0.4

combinado_fonte = 0.6 × tfidf_normalizado_da_fonte + 0.4 × keybert_normalizado_da_fonte
```
Calculado separadamente: `title_combined` (usando os scores de título) e
`abstract_combined` (usando os scores de resumo).

### 7.2 Agregação título × resumo (score base)

Pesos configuráveis (`core/config.py`):

| Config | Valor atual (default) |
|---|---|
| `term_extraction_title_weight` | **3.0** |
| `term_extraction_abstract_weight` | **1.0** |

Ou seja, título pesa **3× mais** que resumo por padrão. Regra:

```python
if title_combined > 0 and abstract_combined > 0:
    # aparece nas duas fontes: média ponderada
    base_score = (title_combined * title_weight + abstract_combined * abstract_weight) \
                 / (title_weight + abstract_weight)
elif title_combined > 0:
    base_score = title_combined       # só apareceu no título
elif abstract_combined > 0:
    base_score = abstract_combined    # só apareceu no resumo
else:
    base_score = 0.0                  # não pontuado em nenhuma fonte
```

---

## 8. Ajustes de score: bônus e penalidades (`_get_score_adjustments`, linha 577)

Aplicado a **cada** n-grama sobre o `base_score`, retornando um par
`(bonus, penalty)` somado depois: `final_score = base_score + bonus +
penalty`, com piso em zero (`max(0, final_score)`).

### 8.1 Ajuste por tamanho do n-grama

| Config | Valor real (config.py) | Efeito |
|---|---|---|
| `term_extraction_unigram_penalty` | **-0.4** | Penaliza termos de 1 palavra |
| `term_extraction_bigram_bonus` | **0.0** | Neutro para termos de 2 palavras |
| `term_extraction_trigram_bonus` | **0.25** | Bonifica termos de 3 palavras |

> ⚠️ O `getattr(settings, "term_extraction_trigram_bonus", 0.3)` no código
> usa `0.3` como fallback, mas esse fallback nunca é de fato usado porque
> `settings` sempre define o atributo — o valor **realmente aplicado** em
> runtime é o de `core/config.py`: **0.25**. O mesmo vale para os thresholds
> de score e overlap (ver §12 — inconsistência entre docstring/fallback e
> config real).

### 8.2 Penalidade por padrão POS "ruim"

O n-grama é re-processado pelo spaCy isoladamente (`self.nlp(ngram)`) para
obter a sequência de tags POS, comparada contra listas fechadas em
`config/pos_patterns.json`:

```
bad_bigrams  = [(VERB,VERB), (ADV,VERB), (VERB,ADJ), (ADJ,VERB)]
bad_trigrams = [(VERB,VERB,NOUN), (ADV,VERB,NOUN), (ADV,ADJ,NOUN), (VERB,NOUN,VERB)]
```

Se a sequência de POS do n-grama (2 ou 3 palavras) bater **exatamente** com
um desses padrões, soma-se a penalidade adicional:

| Config | Valor | Quando se aplica |
|---|---|---|
| `term_extraction_bad_bigram_penalty` | **-0.8** | bigrama com POS em `bad_bigrams` |
| `term_extraction_bad_trigram_penalty` | **-0.8** | trigrama com POS em `bad_trigrams` |

Uma penalidade de -0.8 é, na prática, quase sempre suficiente para empurrar
o termo para abaixo do threshold final de 0.35 (§9), efetivamente eliminando
n-gramas gramaticalmente estranhos (ex.: "efficiently removes", padrão
ADV+VERB) mesmo que tenham boa pontuação semântica/estatística bruta.

---

## 9. Filtro de termos originais (linha 957)

Remove do conjunto de candidatos:
1. N-gramas **idênticos** a alguma palavra normalizada do tema/descrição
   original do usuário (`original_terms`, de §2).
2. **Apenas unigramas** cuja palavra esteja em `original_terms` — n-gramas de
   2-3 palavras são mantidos mesmo que contenham uma palavra original
   (ex.: se o usuário buscou "water", o termo "salt water desalination"
   sobrevive; o termo "water" sozinho é removido).

---

## 10. Filtro de qualidade textual (`_apply_quality_filters`, linha 698, config `config/string_quality_filter.json`)

Três listas fechadas de palavras, todas comparadas em minúsculas:

### 10.1 `boundary_stopwords` — descarta se a **primeira ou última** palavra do termo estiver na lista
```
a, an, the, and, or, of, in, on, at, to, for, with, by, from, is, are, was,
were, be, been, being, have, has, had, do, does, did, will, would, could,
should, may, might, shall, this, that, these, those, it, its, as, up, free,
standing, based, related, high, low, new, good, such, each, both, about,
into, through, which, who, whom, whose, what, when, where, why, how,
flowing, exiting
```

### 10.2 `patent_structural_words` — descarta se **qualquer** palavra do termo estiver na lista
```
wherein, comprising, comprises, comprised, said, first, second, third,
fourth, opposing, planar, having, thereof, therein, whereby, herein,
thereby, configured, adapted, provided, disposed, coupled, connected,
attached, formed, plurality, substantially, approximately, device
```

### 10.3 `scholarly_structural_words` — descarta se **qualquer** palavra do termo estiver na lista
```
proposed, presented, described, discussed, studied, investigated, analyzed,
examined, evaluated, assessed, demonstrated, showed, found, observed,
reported, novel, new, improved, enhanced, efficient, effective, significant,
important, relevant, various, several, different, specific, particular,
general, overall, results, findings, conclusion, approach, method,
technique, framework, model, system, process, based, using, used, via,
among, between, compared, contrast, addition, furthermore, however,
substantial, absence, edge, edges, pore, pores
```

Um termo é rejeitado assim que **qualquer** uma das três checagens falhar
(curto-circuito: as demais nem são avaliadas, mas o resultado é o mesmo —
rejeição). Note a sobreposição intencional entre estas listas e os
`ngram_boundary_tokens` do §4.1: as boundary tokens impedem que o termo
*atravesse* essas palavras durante a geração; este filtro pega os casos em
que a palavra ainda aparece *dentro* do termo (ex.: como primeira/última
palavra sem ter sido cortada, ou em qualquer posição para as duas listas
estruturais).

> Nota histórica no código: havia uma etapa de remoção de todos os unigramas
> (`if len(term.split()) >= 2`), hoje **desativada** — o comentário no código
> explica que a penalidade de -0.4 em unigramas (§8.1) combinada com o
> threshold final de score já suprime naturalmente a maioria dos unigramas
> fracos, sem precisar de uma regra rígida que também descartaria unigramas
> fortes.

---

## 11. Ranking por score puro e filtro de sobreposição/subsunção

### 11.1 Primeiro ranking (score combinado, sem bônus/penalidade)

`ranked_by_score = sorted(filtered_ngrams, key=combined_scores, reverse=True)`
— ordena pelo `base_score` da etapa 7 (KeyBERT+TF-IDF combinados), **antes**
de aplicar os ajustes de §8.

> Nota histórica: o código documenta que aqui havia um passo de **MMR
> (Maximal Marginal Relevance)**, removido por ser O(N³) em um loop guloso —
> inviável para centenas de candidatos. Foi substituído pelo filtro de
> sobreposição abaixo, que persegue o mesmo objetivo (evitar termos
> redundantes) em O(N × |selecionados|). As configurações
> `term_extraction_mmr_lambda` e `term_extraction_mmr_similarity_threshold`
> ainda existem em `core/config.py`, mas **não são lidas em nenhum lugar do
> código atual** — são configuração morta.

### 11.2 Filtro de sobreposição (`_apply_subsumption_filter`, linha 643)

Percorre `ranked_by_score` (já do maior para o menor score) e constrói
`selected` incrementalmente: um candidato só entra na lista final se sua
**razão de sobreposição de palavras** com **todos** os termos já
selecionados ficar **abaixo** do threshold — caso contrário, é descartado
por ser considerado redundante com um termo de score maior já aceito.

```
overlap_ratio(a, b) = |palavras(a) ∩ palavras(b)| / min(|palavras(a)|, |palavras(b)|)
```

| Config | Valor real |
|---|---|
| `term_extraction_overlap_threshold` | **0.66** |

Rejeita se `overlap_ratio >= 0.66` contra qualquer termo já aceito. Exemplos
documentados nos comentários do próprio código:

| Termo A | Termo B | Overlap | Resultado |
|---|---|---|---|
| `salt water` | `water desalination` | 1/2 = 0.50 | mantém os dois (abaixo do limiar) |
| `ultrafiltration membrane` | `composite ultrafiltration membranes` | 2/2 = 1.0 | remove o de menor score |
| `desalination` | `water desalination` | 1/1 = 1.0 | remove o de menor score |

---

## 12. Reordenação final pelo score ajustado

Só depois do filtro de sobreposição os bônus/penalidades de §8 (calculados
antes, mas guardados à parte em `score_adjustments`) são somados de fato:

```
adjusted_score = pure_score(combined_scores) + bonus + penalty
```

A lista sobrevivente ao filtro de sobreposição é **reordenada** por
`adjusted_score` (descendente) — esse é o score que efetivamente decide a
posição final e o corte por threshold, não o `pure_score` usado no primeiro
ranking (§11.1).

> ⚠️ Isso significa que a ordem usada para decidir *quais* termos sobrevivem
> ao filtro de sobreposição (§11.2, baseada no `pure_score`) é diferente da
> ordem final devolvida ao usuário (baseada no `adjusted_score`). Um termo
> "vencedor" da disputa de sobreposição por `pure_score` pode aparecer mais
> abaixo na lista final se sua penalidade for maior que a de um concorrente
> que não teve overlap suficiente para ser removido.

---

## 13. Filtro final por threshold de score

```python
ranked_terms = [t for t in ranked_terms if adjusted_scores[t] >= score_threshold]
```

| Config | Valor real (config.py) | Comentário do getattr no código |
|---|---|---|
| `term_extraction_score_threshold` | **0.35** | fallback do `getattr` é `0.6` (nunca usado — settings sempre define o atributo) |

O comentário em `core/config.py` explica a calibração: valor ajustado para o
modelo `all-mpnet-base-v2` usado em contexto de patentes; aumentar → menos
termos, só os melhores; diminuir → mais termos, incluindo mais contexto.

---

## 14. Corte rígido de quantidade (`MAX_RETURNED_TERMS`, linha 1050)

```python
MAX_RETURNED_TERMS = 60
ranked_terms = ranked_terms[:MAX_RETURNED_TERMS]
```

Constante fixa no código (não configurável via `settings`). Motivo
documentado no comentário: o threshold de score sozinho não limita
quantidade (pode devolver 100+ termos numa amostra grande), o que vira uma
lista grande demais para o usuário revisar manualmente na etapa de
curadoria. Como `ranked_terms` já está ordenado por `adjusted_score`
descendente, o corte preserva sempre os 60 melhores.

---

## 15. Montagem do objeto de resultado

Para cada termo sobrevivente, o dicionário devolvido contém:

| Campo | Origem / cálculo |
|---|---|
| `term` | a string do n-grama |
| `score` | `combined_scores[term]` arredondado a 3 casas — **atenção**: este é o `pure_score` (base_score da etapa 7), **sem** bônus/penalidade, não o `adjusted_score` que decidiu a posição/corte (§12-13) |
| `n_words` | `len(term.split())` |
| `keybert_score_title` / `keybert_score_abstract` | scores normalizados (§5.1, §6), `None` se não houver textos daquela fonte |
| `tf_idf_score_title` / `tf_idf_score_abstract` | scores normalizados (§5.2), `None` se não houver textos daquela fonte |
| `frequency` | contagem bruta em `ngram_frequency` (título+resumo, todos os documentos) |
| `sources` | lista com `"title"` e/ou `"abstract"`, conforme onde o termo apareceu |
| `score_bonus` / `score_penalty` | valores de `_get_score_adjustments` (§8), arredondados |
| `title_weight` / `abstract_weight` | os pesos efetivamente usados na chamada (§7.2), para transparência/auditoria |

> ⚠️ Note a inconsistência entre o campo `score` (pure, sem ajustes) e a
> ordem/corte da lista (que usa `adjusted_score = score + bonus + penalty`,
> §12-13). Ou seja: os termos vêm ordenados por um score que **não é** o
> valor exposto no campo `score` de cada item — para reconstruir o valor que
> de fato determinou a posição/threshold é preciso somar `score + score_bonus
> + score_penalty` manualmente.

---

## 16. Fluxo lógico resumido (visão de ponta a ponta)

```
enriched_results (título + resumo por documento)
        │
        ▼
[1] normaliza original_params → set de palavras-tema
        │
        ▼
[2] separa e limpa título/resumo (_clean_text) — 2 listas paralelas
        │
        ▼
[3] spaCy noun_chunks + limpeza de bordas POS
        │
        ▼
[4] segmentação por boundary tokens/POS → sub-n-gramas 1..3 por segmento
        │
        ▼
[5] dedup + frequência + fontes (title/abstract)
        │
        ▼
[6] KeyBERT (título) ─┐   TF-IDF (título) ─┐
    KeyBERT (resumo) ─┤   TF-IDF (resumo) ─┤   (4 dicionários de score)
                       ▼                    ▼
[7] normaliza KeyBERT por grupo (TF-IDF já normalizado na extração)
        │
        ▼
[8] combina por fonte: 0.6×TF-IDF + 0.4×KeyBERT
        │
        ▼
[9] agrega título×resumo: média ponderada 3:1 (ou só a fonte disponível)  ──▶ base_score (pure_score)
        │
        ▼
[10] bônus/penalidade por tamanho (uni -0.4 / bi 0.0 / tri +0.25)
     + penalidade por POS ruim (-0.8)                                    ──▶ (bonus, penalty) guardados à parte
        │
        ▼
[11] remove termos == parâmetros originais (unigramas) ou idênticos
        │
        ▼
[12] filtro de qualidade textual (stopwords de borda / patente / acadêmico)
        │
        ▼
[13] ranking por pure_score (desc)
        │
        ▼
[14] filtro de sobreposição/subsunção (overlap ≥ 0.66 contra já aceito → descarta)
        │
        ▼
[15] soma bônus/penalidade → adjusted_score → reordena (desc)
        │
        ▼
[16] filtro: adjusted_score ≥ 0.35
        │
        ▼
[17] corta em no máximo 60 termos
        │
        ▼
lista final: {term, score(=pure_score), n_words, scores por fonte/método,
              frequency, sources, score_bonus, score_penalty, pesos}
```

---

## 17. Tabela de configuração (valores realmente efetivos em runtime)

Todos definidos em `core/config.py` (Pydantic `Settings`), lidos via
`getattr(settings, "<nome>", <fallback>)` no código — os fallbacks só
importam se o atributo não existir em `settings`, o que **não acontece** aqui
(o atributo sempre existe), então **o valor de `config.py` é o que sempre
vale**:

| Configuração | Valor efetivo | Fallback no código (não usado) | Usado em |
|---|---|---|---|
| `term_extraction_title_weight` | 3.0 | 3.0 (igual) | §7.2 |
| `term_extraction_abstract_weight` | 1.0 | 1.0 (igual) | §7.2 |
| `term_extraction_score_threshold` | **0.35** | 0.6 ⚠️ | §13 |
| `term_extraction_overlap_threshold` | **0.66** | 0.67 ⚠️ | §11.2 |
| `term_extraction_unigram_penalty` | -0.4 | -0.4 (igual) | §8.1 |
| `term_extraction_bigram_bonus` | 0.0 | 0.0 (igual) | §8.1 |
| `term_extraction_trigram_bonus` | **0.25** | 0.3 ⚠️ | §8.1 |
| `term_extraction_bad_bigram_penalty` | -0.8 | -0.8 (igual) | §8.2 |
| `term_extraction_bad_trigram_penalty` | -0.8 | -0.8 (igual) | §8.2 |
| `term_extraction_mmr_lambda` | 0.45 | — | **morto**, não lido em nenhum ponto do pipeline atual |
| `term_extraction_mmr_similarity_threshold` | 0.5 | — | **morto**, idem |
| `MAX_RETURNED_TERMS` | 60 | — | constante fixa no código, não é uma `setting` |
| pesos de combinação KeyBERT/TF-IDF (`w_tfidf`, `w_keybert`) | 0.6 / 0.4 | — | constantes fixas no código, não são `settings` |

Pesos e thresholds relacionados mas de **outro** pipeline (filtro de
documentos por relevância tema↔documento, não de termos — ver
`services/nlp/relevance_service.py`): `relevance_threshold = 0.4`.

---

## 18. Observações e pontos frágeis identificados na leitura do código

Estas notas não são pedidos de correção — apenas registram fielmente o que o
código faz hoje, incluindo pontas soltas relevantes para quem for depurar ou
recalibrar o pipeline:

1. **Docstring desatualizado**: o docstring de `extract_and_rank_terms`
   (linhas 745-759) lista "8. Apply MMR ranking (relevance + diversity)"
   como parte do processo — isso não é mais verdade; o MMR foi substituído
   pelo filtro de sobreposição de passagem única (§11.2, §16).
2. **`score` retornado ≠ score que ordena/filtra a lista**: como descrito em
   §15, o campo `score` de cada termo é o `pure_score` (sem bônus/penalidade),
   mas a posição na lista e o corte por threshold usam `adjusted_score =
   score + score_bonus + score_penalty`. Quem consumir esse resultado
   programaticamente e precisar do valor "real" de corte deve somar os três
   campos.
3. **`text_to_result` é uma variável morta**: construída nas linhas
   780-820 (mapeando texto limpo → `{source, publication_number}`), nunca é
   lida em nenhum outro ponto da função — o rastreamento de proveniência que
   de fato chega ao resultado final é feito por `ngram_sources` (título vs.
   resumo agregados, sem granularidade por documento individual).
4. **`top_k` é aceito mas ignorado**: `ChatService.extract_terms` recebe e
   repassa `top_k`, mas a assinatura de `extract_and_rank_terms` já marca o
   parâmetro como deprecated — quem de fato limita a quantidade é o par
   `score_threshold` (§13) + `MAX_RETURNED_TERMS = 60` (§14), fixos e não
   parametrizáveis por chamada.
5. **Configuração morta**: `term_extraction_mmr_lambda` e
   `term_extraction_mmr_similarity_threshold` existem em `core/config.py`
   com comentários extensos explicando como calibrá-los, mas não são lidos
   em nenhum lugar do pipeline atual (grep confirma zero usos fora de
   `config.py`). Ajustá-los hoje não tem nenhum efeito observável.
6. **TF-IDF quase nunca pontua bi/trigramas diretamente**: como o
   `TfidfVectorizer` padrão (`analyzer="word"`, sem `ngram_range`
   configurado) só indexa unigramas no vocabulário, praticamente todo
   n-grama de 2-3 palavras cai no ramo de "média dos componentes" (§5.2), e
   nunca no ramo de "match direto no vocabulário" — isso é esperado dado o
   código atual, não um bug, mas explica por que o TF-IDF de multi-palavras
   é sempre uma média de unigramas, nunca uma frequência de frase real.
7. **`KeywordService` (`services/nlp/keyword_service.py`) é um módulo
   separado**, usando o modelo `all-MiniLM-L6-v2`, que **não é chamado** por
   este pipeline (`TermExtractor` instancia seu próprio KeyBERT
   independente) — não confundir os dois ao procurar onde o KeyBERT é
   configurado.
