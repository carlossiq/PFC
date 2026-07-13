# Pendências de Correção

Arquivo de rastreamento de inconsistências e melhorias identificadas durante a revisão do código.
Adicionar novos itens conforme forem encontrados.

---

## app/main.py

### ~~[ALTA] `db_session.initialize()` em tempo de import~~ ✓ RESOLVIDO
Movido para dentro do `lifespan` context manager. Engine agora é criado no startup, não no import.

### [ALTA] `test_router` registrado sem guarda de ambiente
- **Linha:** ~85 (create_app)
- **Problema:** `app.include_router(test_router.router, ...)` não tem nenhuma condição (`if settings.debug` ou similar), expondo rotas de teste em produção.
- **Correção:** Envolver com `if settings.environment != "production":` ou `if settings.debug:`.

### ~~[MÉDIA] `@app.on_event` depreciado~~ ✓ RESOLVIDO
Substituído pelo `lifespan` context manager (`@asynccontextmanager`). Startup e shutdown consolidados em um único bloco.

### ~~[BAIXA] Comentário de agrupamento de rotas inconsistente~~ ✓ RESOLVIDO
Comentários ajustados: `# Rotas v2 (hexágono)` e `# Infraestrutura` distinguem os grupos.

---

## services/query_builders/scopus_query_builder.py

### ~~[CRÍTICO] `_build_simple_query` gerava sintaxe malformada para múltiplos valores~~ ✓ RESOLVIDO
O separador do `join` interpolava o nome do campo, produzindo `AUTH("x" OR "AUTH("y")`.
Corrigido para gerar predicados individuais: `AUTH("x") OR AUTH("y")`.

### ~~[CRÍTICO] `_load_field_map` não extraía a chave `field_map` do JSON~~ ✓ RESOLVIDO
O JSON tem estrutura `{"field_map": {"simple": {...}}}` mas o loader retornava o dict inteiro,
fazendo `self.field_map.get("simple")` retornar `None` — nenhum campo simples era incluído na query.
Corrigido com `data.get("field_map", data)`.

### ~~[CRÍTICO] `view=COMPLETE` causava 401 em toda busca Scopus~~ ✓ RESOLVIDO
- **Linha:** ~160 (`build_query`)
- **Problema:** os parâmetros de requisição fixavam `"view": "COMPLETE"`. Esse nível de
  detalhe da Scopus Search API exige entitlement institucional/Text Mining que a API key do
  projeto não possui — toda busca de artigos falhava com `401 AUTHORIZATION_ERROR:
  "The requestor is not authorized to access the requested view or fields of the resource"`,
  mesmo com a query e a API key corretas. Confirmado testando a mesma query direto na API da
  Elsevier: com `view=COMPLETE` → 401; sem ele (ou `view=STANDARD`) → 200 OK.
  Além disso, `COMPLETE` não trazia nenhum benefício real pra essa chave: mesmo pedindo o
  campo de abstract explicitamente (`field=dc:description`), a resposta vem sem esse campo de
  qualquer forma (abstract completo exige a Abstract Retrieval API separada, não a Search API).
- **Correção:** `"view": "COMPLETE"` → `"view": "STANDARD"`. Sem perda de dados (abstract já
  não vinha) e a busca de artigos volta a retornar resultados.

## app/adapters/driven/query_builders/scopus_query_builder_adapter.py

### ~~[MÉDIA] `search_mode` ignorado no adapter~~ ✓ RESOLVIDO
O parâmetro `search_mode` de `build_query()` nunca chegava ao builder interno.
Corrigido atualizando `self._builder.search_mode` antes de cada chamada.

## services/query_builders/lens_scholarly_query_builder.py

### ~~[CRÍTICO] `_load_field_map` não extraía a chave `field_map` do JSON~~ ✓ RESOLVIDO
Mesma estrutura aninhada do Scopus. Todos os campos (título, abstract, autores) eram ignorados.
Corrigido com `data.get("field_map", data)`.

## app/adapters/driven/query_builders/lens_patent_query_builder_adapter.py

### ~~[MÉDIA] `search_mode` ignorado no adapter~~ ✓ RESOLVIDO
Corrigido atualizando `self._builder.search_mode` antes de cada chamada.

## app/adapters/driven/query_builders/lens_scholarly_query_builder_adapter.py

### ~~[MÉDIA] `search_mode` ignorado no adapter~~ ✓ RESOLVIDO
Corrigido atualizando `self._builder.search_mode` antes de cada chamada.

## services/search/scopus_service.py

### ~~[MÉDIA] Clientes HTTP nunca fechados — resource leak~~ ✓ RESOLVIDO
`LensService`, `OPSService`, `OPSTokenManager` e `ScopusService` agora são coletados em
`_services_to_close` no container. `shutdown_container()` em `app/container.py` itera e
chama `close()` em cada um. Chamado no lifespan de `main.py` antes de `db_session.close()`.

### ~~[CRÍTICO] "Result set was empty" tratado como resultado real, paginação repetia lixo~~ ✓ RESOLVIDO
- **Linha:** ~256-264 (`_search_page`)
- **Problema:** quando uma query não tem nenhum match, a Scopus Search API não devolve
  `"entry": []` — devolve `"entry": [{"@_fa": "true", "error": "Result set was empty"}]`,
  um placeholder com 1 item. `_should_continue_pagination` só checava
  `len(page_results) > 0`, então tratava esse placeholder como página válida e repetia a
  mesma chamada por até `_MAX_PAGES` (10) tentativas, acumulando 10 itens sem título/DOI
  no resultado final — silenciosamente devolvidos como se fossem 10 artigos reais.
  Só ficou visível depois de corrigir o 401 de `view=COMPLETE` (ver item abaixo), que até
  então mascarava esse caminho de código.
- **Correção:** filtrar entradas com chave `"error"` antes de contar como resultado:
  `results = [r for r in raw_results if not r.get("error")]`. Testado com uma query real
  que retorna 0 matches: antes rodava 10 páginas de lixo, agora para na página 1 com 0
  resultados corretamente.

### ~~[CRÍTICO] `view=COMPLETE` causava 401 em toda busca Scopus~~ ✓ RESOLVIDO
- **Problema:** ver item idêntico em `services/query_builders/scopus_query_builder.py`
  acima — a mudança de código foi lá (`view: "COMPLETE"` → `"STANDARD"`), mas o sintoma
  (toda busca de artigo falhando) aparecia aqui, em `_search_page`.

---
