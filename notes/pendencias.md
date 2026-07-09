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

---
