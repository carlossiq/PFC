# Verificação de Referências, Tabelas e Figuras — PFC Main.tex

**Data:** 2026-10-16  
**Status:** ⚠️ Existem problemas a corrigir

---

## 📊 RESUMO EXECUTIVO

| Métrica | Valor | Status |
|---------|-------|--------|
| Total de `\ref{}` | 79+ | 🔴 23 quebradas |
| Total de `\label{}` | 66+ | 🟡 17 órfãs |
| Tabelas | 12 | ✅ Todas referenciadas |
| Figuras | 29 | 🟡 9 não referenciadas |

---

## 🔴 REFERÊNCIAS SEM LABELS (23 quebradas)

### Listagens (lst:*) — 15 referências
Esses são "Listing" (código) e precisam de labels `\label{lst:*}`:
- `lst:fase1-msg`
- `lst:fase1-prompt`
- `lst:fase2-dica`
- `lst:fase2-msg` (aparece 2x)
- `lst:fase2-prompt`
- `lst:fase2-retry` (aparece 2x)
- `lst:fase4-contexto`
- `lst:fase4-prompt`
- `lst:fase5-retry`
- `lst:fase5-revisao`
- `lst:fase5-secao`
- `lst:fase5-sistema`

**Ação necessária:** Adicionar `\label{lst:*}` após cada `\begin{lstlisting}` ou bloco de código

### Seções — 6 referências
- `sec:complexidade` (aparece 4x) — ✅ Tem label em linha 1341
- `sec:config-llm` — ✅ Tem label em linha 1319  
- `sec:extracao-termos` — ✅ Tem label em linha 1522

**Nota:** Essas parecem estar corretas; pode ser duplicação na contagem.

### Apêndice — 1 referência
- `ap:caso-catalisador` — ✅ Tem label em linha 2235

---

## 🟡 LABELS NÃO REFERENCIADOS (17 órfãs)

### Seções não citadas no texto (6)
- `sec:prompt` (linha 905)
- `sec:rag` (linha 917)  
- `sec:fase2` (linha 1511)
- `sec:modelagem-bd` (linha 1414)
- `sec:inconsistencias-caso-estudo` (linha 2386)
- `sec:limitacoes` (linha 1676)
- `sec:tecnologias` (linha 1391)

**Recomendação:** Verificar se devem ser adicionadas referências a essas seções no texto, ou se são labels desnecessárias.

### Figuras não referenciadas no texto (9)
- `fig:perfil-cientifico-tecnologico` (linha 701)
- `fig:relatorio-1` (linha 708)
- `fig:relatorio-2` (linha 715)
- `fig:s-curve-madeo` (linha 736)
- `fig:curva-s-sintetica` (linha 844)
- `fig:self-attention` (linha 895)
- `fig:modelo-dados-der` (linha 1474)
- `fig:pipeline-cinco-fases` (linha 1503)

**Recomendação:** Adicionar `Figura~\ref{fig:*}` no texto próximo a cada figura, ou remover as labels se desnecessárias.

### Apêndices não referenciados (2)
- `ap:prompts` (linha 2045)
- `ap:manual-interface` (linha 2409)

**Recomendação:** Adicionar `Apêndice~\ref{ap:*}` no texto principal, ou remover.

---

## ✅ TABELAS (12) — TODAS REFERENCIADAS

| Label | Linha | Referenciada em | Status |
|-------|-------|---|--------|
| `tab:gpmpsp` | 824 | linha 819 | ✅ |
| `tab:secoes-relatorio` | 1046 | linha 1040 | ✅ |
| `tab:rf` | 1180 | linha 1091 | ✅ |
| `tab:rnf` | 1251 | linha 1186 | ✅ |
| `tab:camadas` | 1263 | linha 1258 | ✅ |
| `tab:complexidade` | 1377 | linha 1372 | ✅ |
| `tab:solid` | 969 | linha 1277 | ✅ |
| `tab:entidades-bd` | 1421 | linha 1416 | ✅ |
| `tab:mapeamento-fase-entidade` | 1450 | linha 1444 | ✅ |
| `tab:prompts-resumo` | 2066 | linha 2058 | ✅ |
| `tab:prompt-origem` | 2198 | linha 2188 | ✅ |
| `tab:apb-termos` | 2330 | linha 2291 | ✅ |

---

## 📷 FIGURAS (29) — STATUS MISTO

### Referenciadas (20) ✅
- `fig:arquiterura` (linha 1082, ref. 1085)
- `fig:hexagonal-camadas` (linha 1283, ref. 1286)
- `fig:fluxograma` (linha 1292, ref. 1295)
- `fig:apb-config-llm` (linha 2245, ref. 2239)
- `fig:apb-header-audit` (linha 2254, ref. 2248)
- `fig:apb-intake` (linha 2265, ref. 2259)
- `fig:apb-probe-cards` (linha 2304, ref. 2272)
- `fig:apb-pat-sample` (linha 2313, ref. 2280)
- `fig:apb-art-sample` (linha 2320, ref. 2287)
- `fig:apb-curvas-s-frontend` (linha 2374, ref. 2314)
- `fig:apb-historico` (linha 2419, ref. 2315)
- `fig:apb-intake-geral` (linha 2428, ref. 2320)
- `fig:apb-refinamento-tema` (linha 2435, ref. 2327)
- `fig:apb-probe-query` (linha 2446, ref. 2334)
- `fig:apb-probe-docs` (linha 2453, ref. 2341)
- `fig:apb-termos-pln` (linha 2464, ref. 2358)
- `fig:apb-query-final` (linha 2471, ref. 2363)
- `fig:apb-curvas-painel` (linha 2482, ref. 2370)
- `fig:apb-metadados-form` (linha 2493, ref. 2383)
- `fig:apb-secoes-rag` (linha 2500, ref. 2391)
- `fig:apb-editor-latex` (linha 2509, ref. 2398)
- `fig:apb-revisao-texto` (linha 2516, ref. 2405)
- `fig:apb-config-ia-painel` (linha 2527, ref. 2412)
- `fig:apb-config-geral-painel` (linha 2534, ref. 2419)

### NÃO Referenciadas (9) 🟡
- `fig:perfil-cientifico-tecnologico` (linha 701) — **NO CAPTION**
- `fig:relatorio-1` (linha 708) — **NO CAPTION**
- `fig:relatorio-2` (linha 715) — **NO CAPTION**
- `fig:s-curve-madeo` (linha 736) — **NO CAPTION**
- `fig:curva-s-sintetica` (linha 844) — **NO CAPTION**
- `fig:self-attention` (linha 895) — **NO CAPTION**
- `fig:modelo-dados-der` (linha 1474) — **NO CAPTION**
- `fig:pipeline-cinco-fases` (linha 1503) — **NO CAPTION**

---

## 📝 FIGURAS SEM CAPTIONS (explicações) — 8

As seguintes figuras têm labels mas **NÃO têm `\caption{}`**:

1. **Linha 701** — `fig:perfil-cientifico-tecnologico`
2. **Linha 708** — `fig:relatorio-1`
3. **Linha 715** — `fig:relatorio-2`
4. **Linha 736** — `fig:s-curve-madeo`
5. **Linha 844** — `fig:curva-s-sintetica`
6. **Linha 895** — `fig:self-attention`
7. **Linha 1474** — `fig:modelo-dados-der`
8. **Linha 1503** — `fig:pipeline-cinco-fases`

**Ação necessária:** Adicionar `\caption{Descrição da figura}` após cada figura, ou remover se forem meramente ilustrativas.

---

## 🎯 RECOMENDAÇÕES DE AÇÃO

### Prioridade 🔴 ALTA

1. **Adicionar labels para Listagens (lst:*)**
   - Encontre cada `\begin{lstlisting}` ou bloco de código mencionado
   - Adicione `\label{lst:fase1-prompt}`, etc., logo após `\begin{lstlisting}`

### Prioridade 🟡 MÉDIA

2. **Adicionar captions para figuras órfãs**
   - Adicione `\caption{...}` para as 8 figuras sem descrição
   - Ou remova o `\label{}` se a figura é apenas ilustrativa

3. **Referenciar ou remover labels órfãs**
   - Se `sec:rag`, `sec:prompt`, etc., são importantes, adicione `Seção~\ref{sec:*}` no texto
   - Se não são usadas, remova o `\label{}`

4. **Referenciar apêndices**
   - Adicione `Apêndice~\ref{ap:prompts}` e `Apêndice~\ref{ap:manual-interface}` no texto principal

---

## ✅ PRÓXIMOS PASSOS

1. ✅ Verificar LinéAsm 701–1503 para figuras sem captions
2. ✅ Localizar blocos de código e adicionar labels `lst:*`
3. ✅ Adicionar referências ao texto para seções órfãs
4. ✅ Re-compilar LaTeX para validar todas as referências

