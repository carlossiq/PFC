# Busca de artigos (Scopus): erro 401, ausência de abstract e SUBJAREA quebrado

Resumo da investigação e da correção de três problemas encadeados na busca de
artigos (Scopus), encontrados ao testar o fluxo completo de busca de patentes
e artigos. Os dois primeiros bloqueavam a busca inteira (401 e queries sempre
zeradas); o segundo (ausência de abstract) é uma limitação de acesso da
Elsevier contornada com uma fonte complementar.

---

## 1. Problema 1 — busca de artigos falhando com 401 Unauthorized

**Sintoma:** toda busca de artigos no Scopus retornava erro, enquanto a busca
de patentes (OPS) funcionava normalmente.

**Causa raiz:** `services/query_builders/scopus_query_builder.py`, na
montagem dos parâmetros da requisição (`build_query`), o campo `view` estava
fixo em `"COMPLETE"`. Esse é um nível de detalhe da Scopus Search API que
exige *entitlement* institucional/Text Mining junto à Elsevier — a API key
do projeto não tem esse nível de acesso.

**Como foi confirmado:** testando a mesma query direto na API da Elsevier:
- Com `view=COMPLETE` → `401 AUTHORIZATION_ERROR`:
  *"The requestor is not authorized to access the requested view or fields
  of the resource"*
- Sem esse parâmetro (ou com `view=STANDARD`) → `200 OK`, resultados normais.

**Correção:**

`services/query_builders/scopus_query_builder.py:164`
```python
params = {
    "query": scopus_query,
    "count": count,
    "start": 0,
    "sort": "citedby-count",
    "view": "STANDARD",   # antes: "COMPLETE"
}
```

---

## 2. Problema 2 — mesmo corrigido o 401, artigos vêm sem abstract

**Causa raiz:** a Scopus Search API, com a entitlement dessa API key, **não
devolve o campo de abstract** (`dc:description`) em nenhum nível de detalhe
— nem em `COMPLETE` (se fosse acessível), nem no endpoint dedicado de
abstract (*Abstract Retrieval API*, `/content/abstract/scopus_id/{id}`).
Confirmado testando os dois endpoints diretamente: os dados bibliográficos
vêm completos (título, autores, DOI, citações...), mas o campo de abstract
sempre vem ausente.

Isso é uma limitação de acesso da Elsevier (normalmente requer assinatura
institucional), não um bug de código — não há parâmetro de query que
resolva isso com a chave atual.

### Solução adotada: abstract complementar via OpenAlex

Cada artigo que o Scopus retorna já vem com **DOI** (identificador universal
do artigo, não exclusivo da Elsevier). A ideia: usar esse DOI para consultar
o [OpenAlex](https://openalex.org/) — uma API pública, gratuita e sem
necessidade de key — que mantém abstracts de grande parte da literatura
acadêmica.

- O **Scopus continua sendo quem decide** quais artigos aparecem na busca
  (a query, a relevância, a ordenação — nada disso muda).
- O OpenAlex só **preenche o campo de texto do abstract** que o Scopus se
  recusa a entregar, usando o DOI que o próprio Scopus já forneceu.

**Cobertura medida (teste manual com 10 artigos reais de uma busca
"drone"):** 7 de 10 (~70%) tinham abstract disponível no OpenAlex. Os que
não têm são, em geral, artigos muito recentes/pouco indexados ou de
editoras que retêm o abstract (ex: alguns títulos da Nature/ScienceDirect).

Como a cobertura não é de 100%, a estratégia foi: **buscar mais candidatos
do que o necessário e descartar os que ficarem sem abstract**, garantindo
que o número de resultados finais devolvidos (`top_k`) tenha sempre
abstract preenchido.

---

## 3. Onde cada parte foi implementada

### Novo serviço: `services/search/openalex_service.py`
Classe `OpenAlexService`, isolada e reutilizável:
- `fetch_abstract(doi)` — busca 1 DOI no OpenAlex (`GET
  api.openalex.org/works/doi:{doi}`), reconstrói o abstract a partir do
  formato "índice invertido" que o OpenAlex usa (palavra → posições no
  texto, não o texto pronto), e devolve `None` em qualquer falha (DOI não
  indexado, timeout, etc.) — nunca derruba a busca por causa disso.
- `fetch_abstracts(dois)` — roda várias buscas em paralelo, limitando a 8
  chamadas simultâneas (`asyncio.Semaphore`) pra não sobrecarregar a API
  pública.

### Injeção de dependência: `app/container.py:96-99, 113`
```python
from services.search.openalex_service import OpenAlexService

openalex_service = OpenAlexService()
_services_to_close.append(openalex_service)   # fecha o client HTTP no shutdown
...
chat_service = ChatService(
    llm=llm,
    patent_pairs=patent_pairs,
    scholarly_pairs=scholarly_pairs,
    settings=settings,
    openalex=openalex_service,                # novo parâmetro
)
```

### Lógica de busca + descarte: `app/core/services/chat_service.py:893-926`
Novo método `_enrich_scopus_abstracts(items, top_k)`:
1. Pega uma janela de candidatos maior que o pedido (`3x top_k`, calibrado
   pela taxa de acerto de ~70% medida no teste).
2. Busca o abstract de todos os DOIs dessa janela em paralelo no OpenAlex.
3. Percorre os candidatos **na ordem de relevância que o Scopus já
   devolveu**, mantendo só os que vieram com abstract, até completar
   `top_k` itens.
4. Cada item mantido ganha o campo `dc:description` preenchido (mesma
   convenção de chave crua já usada pelo restante do código pra
   título/autor do Scopus).

Chamado a partir de `run_probe_search` e `run_final_search` (mesmo arquivo),
só quando `api == "scopus"` — a busca de patentes (OPS) não é afetada, já
que ela sempre teve abstract.

---

## 3.1. Bug extra encontrado ao testar o fix em produção

Depois de corrigir o 401 e subir a mudança, o primeiro teste real trouxe
"10 artigos, 0 com abstract" — número bem abaixo dos ~70% esperados. Não
era problema do OpenAlex: era um bug de paginação, exposto só agora porque
antes o 401 impedia de chegar nesse código.

**Causa:** quando uma query não tem nenhum resultado, a Scopus **não**
devolve uma lista vazia — devolve `"entry": [{"error": "Result set was
empty"}]`, um item-placeholder. A checagem de paginação em
`services/search/scopus_service.py` só olhava `len(page_results) > 0`, e
esse placeholder conta como 1 item — então o código achava que sempre havia
"mais uma página" e repetia a mesma chamada 10 vezes (limite configurado),
acumulando 10 cópias do placeholder como se fossem 10 artigos reais (sem
título, sem DOI — por isso 0 abstracts).

**Correção:** `services/search/scopus_service.py:256-264` — filtra
entradas com chave `"error"` antes de contar como resultado real:
```python
raw_results = search_results.get("entry", [])
results = [r for r in raw_results if not r.get("error")]
```
Testado direto com uma query real sem resultados: antes rodava 10 páginas
de lixo, agora para corretamente na 1ª página com 0 resultados.

---

## 4. Problema 3 — `SUBJAREA` com texto livre zerava a busca inteira

**Sintoma:** buscas que preenchiam `field_of_study` (área de estudo)
voltavam com **0 resultados**, mesmo quando o mesmo tema, sem esse campo,
tinha milhões de artigos relevantes no Scopus (confirmado testando TITLE/ABS
isolados).

**Causa raiz:** o campo `SUBJAREA` da Scopus é diferente dos outros campos
simples (`AUTH`, `AFFIL`, `KEY`, `SRCTITLE`) — ele **não aceita texto livre
entre aspas**, só um dos 27 códigos ASJC de 4 letras, sem aspas (ex:
`SUBJAREA(COMP)`). O código genérico que monta esses campos
(`_build_simple_query`) sempre embrulhava o valor em aspas:
`f'{scopus_field}("{v}")'` — formato certo pros outros campos, mas inválido
pra SUBJAREA. A LLM gera nomes de área livres e granulares (ex: `"Medical
Informatics"`, `"Artificial Intelligence"`, `"Health Sciences"` — ver
exemplo em `config/prompts/general_system_prompt.txt`), então a cláusula
gerada (`SUBJAREA("Artificial Intelligence")`) era sintaticamente aceita
pela API, mas **nunca casava com nenhum artigo**. Como essa cláusula é
combinada com `AND` ao resto da query, ela zerava a busca inteira mesmo
quando TITLE/ABS sozinhos tinham resultado de sobra.

**Como foi confirmado:** testando isoladamente contra a API real:
- `SUBJAREA("Computer Science")` → **0 resultados** (aspas + nome livre)
- `SUBJAREA(COMP)` → **11.043.439 resultados** (código correto, sem aspas)

**Correção — mapeamento em arquivo de constantes:**

Novo arquivo `services/query_builders/constants/scopus_subject_areas.py`:
- `ASJC_SUBJECT_AREAS` — os 27 códigos oficiais ASJC (código → nome).
- `_KEYWORD_TO_CODE` — tabela de aliases mapeando termos comuns que a LLM
  gera (ex: "artificial intelligence", "medical informatics", "remote
  sensing", "robotics"...) pro código ASJC mais próximo.
- `resolve_asjc_code(free_text)` — resolve um texto livre pro código (match
  exato → alias → substring); devolve `None` se não achar correspondência
  confiável, em vez de arriscar um código errado.

`services/query_builders/scopus_query_builder.py`:
- `field_of_study` saiu do loop genérico de campos simples.
- Novo método `_build_subject_area_query`: resolve cada valor da LLM pro
  código ASJC, remove duplicatas, **descarta os valores sem mapeamento**
  (em vez de gerar uma cláusula quebrada), e monta a cláusula sem aspas:
  `SUBJAREA(COMP) OR SUBJAREA(MEDI)`.

**Resultado do teste** (mesma busca "IA e saúde" que antes zerava):
```
Antes:  SUBJAREA("Medical Informatics") OR SUBJAREA("Artificial Intelligence")...
        → 0 resultados

Depois: SUBJAREA(COMP) OR SUBJAREA(MEDI) OR SUBJAREA(HEAL)
        → 1.411.016 resultados
```

---

## 5. Melhoria adicional — restringir a `DOCTYPE(ar)` (só artigos de revista)

Sem esse filtro, a busca no Scopus traz qualquer tipo de documento: review,
paper de conferência, editorial, carta, nota, errata etc. Adicionado
`DOCTYPE(ar)` fixo (não vem do LLM, é sempre aplicado) em
`services/query_builders/scopus_query_builder.py`, restringindo a resultado
só a artigos de revista de verdade.

**Efeito medido** (mesma busca "IA e saúde" usada nos testes acima):
```
Sem DOCTYPE(ar): 1.411.016 resultados
Com DOCTYPE(ar): 1.010.580 resultados   (~28% a menos, ruído removido)
```

---

## 6. Bug de precedência — partes da query não ficavam entre parênteses

**Sintoma:** a query final unia as partes só com `AND`, sem envolver cada
parte em parênteses: `X AND SUBJAREA(COMP) OR SUBJAREA(ENGI) OR
SUBJAREA(HEAL) AND (pd within ...) AND DOCTYPE(ar)`. Como o `OR` da cláusula
SUBJAREA não estava isolado, o resultado final dependia inteiramente de como
a Elsevier resolve precedência entre `AND`/`OR` sem parênteses explícitos -
um comportamento não documentado e arriscado de assumir. Em alguns casos
testados não fez diferença numérica, mas é uma falha de construção real, não
uma coincidência que se possa confiar.

**Causa raiz:** `services/query_builders/scopus_query_builder.py`, a junção
final das partes da query (`" AND ".join(query_parts)`) não envolvia cada
parte em parênteses - diferente do builder do OPS, que já fazia isso certo
(`" AND ".join([f"({c})" for c in cql_clauses])`). Qualquer parte que
internamente gerasse um `OR` sem parênteses próprios (SUBJAREA com múltiplos
códigos, `KEY`/`AUTH`/`SRCTITLE` com múltiplos valores, campos textuais com
múltiplos grupos `OR`) ficava exposta a esse risco.

**Correção:** `services/query_builders/scopus_query_builder.py:153`
```python
scopus_query = " AND ".join(f"({part})" for part in query_parts)
```
Agora toda parte fica isolada entre parênteses, eliminando qualquer
ambiguidade de precedência, independente do que a Elsevier faz internamente.
Testado contra a API real após a correção — resultado (`(TITLE(...) AND
TITLE(...)) AND (SUBJAREA(...) OR SUBJAREA(...)) AND (PUBYEAR...) AND
(DOCTYPE(ar))`) segue retornando resultados normalmente (200 OK).

---

## 7. Bug de sintaxe — termos de múltiplas palavras sem aspas zeravam TITLE/ABS

**Sintoma:** uma query de tema militar (drones/swarm intelligence) com vários
termos de TITLE e ABS voltava com **0 artigos**, mesmo isolando só o
`TITLE(...)` ou só o `ABS(...)` sem nenhum outro filtro (SUBJAREA, ano,
DOCTYPE) - ou seja, o problema estava na cláusula de texto em si, não nos
filtros que já tínhamos corrigido antes.

**Causa raiz:** `_escape_scopus_term` (usado por `_build_textual_query`, que
monta `TITLE()`/`ABS()`) **remove** aspas do termo e nunca as recoloca -
diferente de `_build_simple_query` (usado por `AUTH`/`KEY`/`SRCTITLE`), que
já embrulha em aspas corretamente. Termos de uma palavra só (`drone`, `UAV`)
não têm problema, mas termos de **múltiplas palavras sem aspas** (`unmanned
aircraft system`, `collective intelligence`...) são tratados pela Scopus
como busca de proximidade implícita - e quando **duas ou mais** dessas
frases sem aspas aparecem unidas por `OR` no mesmo campo, o parser da
Scopus quebra e zera o resultado inteiro, mesmo que cada termo isoladamente
tenha milhares de resultados.

**Como foi confirmado** - testado incrementalmente, adicionando um termo de
cada vez em `TITLE(...)`, até identificar exatamente onde zerava:
```
TITLE(("UAV" OR ... OR "swarm intelligence"))                    → 20
+ "unmanned aircraft system" (sem aspas, 2ª frase multi-palavra)  → 0
```
E isolado o mínimo caso que reproduz:
```
TITLE("collective intelligence" OR "unmanned aircraft system")   → 2.967 (com aspas)
TITLE(collective intelligence OR unmanned aircraft system)       →     0 (sem aspas)
```

**Correção:** `services/query_builders/scopus_query_builder.py:221`
```python
escaped_terms = [f'"{self._escape_scopus_term(term)}"' for term in group.terms]
```
Todo termo de TITLE/ABS/description/full_text agora sempre vai entre aspas,
independente de ter uma ou várias palavras. Testado com a query real do
tema militar: **0 → 69.679 resultados**, sem regressão nas queries já
testadas antes (ex: "IA e saúde" continua retornando na casa do milhão).

---

## 8. Resultado

- Busca de artigos (Scopus) volta a funcionar (sem 401).
- Queries com área de estudo preenchida não zeram mais a busca.
- Resultados restritos a artigos de revista (`DOCTYPE(ar)`), sem
  review/conference paper/editorial/carta/nota/errata.
- Cada parte da query fica isolada entre parênteses, sem depender de
  precedência implícita de `AND`/`OR` da Elsevier.
- Termos de múltiplas palavras em TITLE/ABS sempre entre aspas - não zeram
  mais a busca quando combinados com `OR`.
- Artigos retornados sempre vêm com abstract preenchido (quando disponível
  em qualquer uma das duas fontes) — os sem abstract em nenhuma fonte são
  descartados antes de chegar no resultado final, em vez de aparecerem
  vazios pro usuário.
- Nenhuma mudança na busca de patentes (OPS).

## 9. Limitações conhecidas

- Cobertura de abstract não é 100% — em buscas muito restritas (poucos
  resultados relevantes no Scopus), pode retornar menos que o `top_k`
  pedido se a maioria dos candidatos não tiver abstract em nenhuma fonte.
- Dependência de uma API externa adicional (OpenAlex) — se ela ficar fora
  do ar, a busca de artigos ainda funciona, só não enriquece com abstract
  (retorna a lista sem descartar, ver fallback em
  `_enrich_scopus_abstracts` quando `self.openalex` é `None`).
- O mapeamento de área de estudo (`resolve_asjc_code`) é por palavra-chave,
  não é exaustivo — termos muito específicos ou fora da tabela de aliases
  são descartados silenciosamente (logados como
  `scopus_subject_area_unmapped`) em vez de causar erro. Cobre os termos
  observados em testes reais, mas pode precisar de novos aliases conforme
  aparecerem temas diferentes.



topico pra comentar: 

Reimplemente o filtro (descartar documentos sem abstract em inglês, usando o buffer pra compensar)