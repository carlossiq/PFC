# Plano Estruturado de Correções — PFC Main.tex
**Objetivo:** Adicionar as explicações faltantes sem alterar/sobrescrever o que já foi feito.
**Data:** 2026-10-16  
**Estratégia:** Localizações exatas, insersões (não substituições), ordem segura.

---

## 🔴 FASE 1: Correções Factuais (SEM RISCO — substituem texto claramente errado)

| # | Linha Atual | Problema | Solução | Risco |
|---|---|---|---|---|
| **C1** | 1549 | "exclusão de citações inválidas **perante o banco relacional**" | Trocar por: "exclusão de citações que não correspondem a nenhum documento recuperado para a seção" | ✅ Baixo — é correção, não remoção |
| **C2** | 1529 (verificar) | "escore final RRF **normalizado** ≥ 0,024" — checar se está correto | Verificar `core/config.py` se `term_extraction_score_threshold` é normalizado ou não. Se não, remover "normalizado" | ✅ Baixo — é clarificação |

**Ação:** Fazer C1 e C2 PRIMEIRO. Ambas são correções textuais isoladas, sem impacto no resto.

---

## 🟡 FASE 2: Adições em Seção Existente (Fase 5 — RAG)

**Local:** Após linha 1541 `\subsection{Fase 5: Geração e Revisão do Relatório Técnico}`

**Inserção (ANTES dos passos atuais, como parágrafo introdutório expandido):**

```latex
### 2.1 Indexação e Metadados (NOVO — após linha 1541)
```
- Adicionar: O que é indexado (título+resumo), metadados não entram no embedding, como citações são calculadas
- Texto sugerido em ADICOES_MAIN_TEX.md item 1.1 (linhas 28-34)

**Inserção:** APÓS a seção inicial de Fase 5, ANTES dos Passos Atuais (1548+)

---

## 🟡 FASE 3: Adições em Seção Existente (Fase 3 — Extração de Termos)

**Local:** Linha 1541 é Fase 5. Fase 3 começa em ~1513 `\subsection{Fase 3: Extração e Ranqueamento de Termos}`

**O que já foi adicionado em Fase 3:**
- ✅ Parâmetros BM25F (w, k₁, b) explicados
- ✅ Parâmetro RRF k=60 explicado
- ✅ Penalidades/bonificações (-0,4, +0,25) explicadas
- ✅ Escore final RRF ≥ 0,024 com justificativa
- ✅ Variantes de busca (0,4/0,3/0,2) explicadas

**O que FALTA em Fase 3:**
- Nenhuma adição planejada — está suficientemente documentada

---

## 🟡 FASE 4: Adições em Seção Curva S

**Local:** Seção 2.4.4 (Curva S) começa ~linha 790. Adicionar APÓS linha 855 (`$R^2$ mensura...`):

**Inserção 3.1 (Método de ajuste — Levenberg-Marquardt):**
- Localização: APÓS a fórmula do $R^2$ (linha 855)
- Texto sugerido em ADICOES_MAIN_TEX.md item 3.1 (linhas 132-146)
- ⚠️ Nota: Será inserido no Capítulo 2 (Fundação Teórica), não no pipeline

**Inserção 3.2 (Falha de convergência, projeção):**
- Localização: Seção 3.x do pipeline, após explicação de GP/MP/SP
- Procurar por onde está a explicação atual de GP/MP/SP no pipeline

**Inserção 3.3 (Estágio do ciclo de vida):**
- Localização: Seção 3.x do pipeline, perto de onde se menciona "ciclo de vida"

**Inserção 3.4 (Ressalvas sobre R²):**
- Localização: Seção de Limitações (~linha 1558–1594)
- Texto sugerido em ADICOES_MAIN_TEX.md item 3.4 (linhas 172-179)

---

## 🟡 FASE 5: Adições sobre Geração LaTeX (Seção 3.x)

**Local:** Após linha 1549 (atual menção a LaTeX)

**Inserção 2 (Pipeline texto → .tex → PDF):**
- Localização: APÓS linha 1549, novo parágrafo antes de Fase 5 terminar
- Texto sugerido em ADICOES_MAIN_TEX.md item 2 (linhas 89-105)

**Inserção 2.1 (Justificativa LaTeX vs. Markdown):**
- Localização: Mesma seção, como parágrafo seguinte
- Texto sugerido em ADICOES_MAIN_TEX.md item 2.1 (linhas 110-117)

---

## 📋 ORDEM DE EXECUÇÃO SEGURA

### Etapa 1 (Hoje — Correções): ~5 min
1. ✏️ Corrigir C1 (linha 1549)
2. ✏️ Corrigir C2 (linha 1529 — verificar primeiro)

### Etapa 2 (Próximo — Fundação Teórica): ~15 min
3. 📝 Adicionar 3.1 (após linha 855 — Curva S método)
4. 🔍 **VERIFICAR** onde estão 3.2, 3.3 mencionados atualmente

### Etapa 3 (Fase 5 — RAG): ~20 min
5. 📝 Adicionar 1.1 (indexação, metadados)
6. 📝 Adicionar 1.2 (se necessário — fórmula cosseno, k=5)
7. 📝 Adicionar 1.3 (se necessário — citações, desambiguação)
8. 📝 Adicionar 2 (pipeline LaTeX)

### Etapa 4 (Limitações): ~15 min
9. 📝 Adicionar 1.4 (limitações RAG)
10. 📝 Adicionar 3.4 (limitações Curva S)
11. 📝 Adicionar 5.3 (limitações RRF)

---

## ✅ CHECKLIST DE SEGURANÇA

**Antes de CADA inserção:**
- [ ] Ler 5 linhas ANTES do ponto de inserção
- [ ] Ler 5 linhas DEPOIS do ponto de inserção
- [ ] Verificar se há seções que conflitem
- [ ] Checar se há referências cruzadas (`\ref`) que sejam afetadas

**Após CADA inserção:**
- [ ] Rodar `pdflatex` para compilar
- [ ] Checar se há erros de referência (⚠️ "Cannot find reference")
- [ ] Rever a seção inteira para ver se flui bem

---

## 📌 LOCALIZAÇÕES CRÍTICAS (Não Tocar)

| Seção | Linhas | Status | Motivo |
|-------|--------|--------|--------|
| Titulo e Abstrato | 1–150 | ✅ OK | Estrutura fixa |
| Fundação Teórica (Cap 2) | 500–1300 | ⚠️ Cuidado | Pode haver inserções em 800-900 (Curva S) |
| Pipeline (Cap 3) | 1400–1550 | ⚠️ Cuidado | Muitas linhas adicionadas; verificar referencias antes |
| Estudo de Caso | 2200–2450 | ✅ OK | Não alterar (teste realizado) |
| Limitações | 1560–1600 | 🟡 Inserir aqui | Espaço reservado |

---

## 🎯 RESULTADO FINAL ESPERADO

✅ **Total de adições:** ~1.200 palavras (~5 páginas)  
✅ **Nenhuma perda de trabalho anterior**  
✅ **Todas as lacunas ADICOES_MAIN_TEX.md cobertas**  
✅ **Documento pronto para defesa**

