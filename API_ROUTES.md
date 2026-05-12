# 📡 Todas as Rotas da API

## 🤖 AI / Geração (IA)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/flow/ai/generate-params` | Gera parâmetros com IA |
| `POST` | `/flow/ai/specify-params` | Especifica/refina parâmetros |
| `POST` | `/flow/ai/choose-terms` | Sugere termos relevantes |
| `POST` | `/flow/ai/create-query` | Cria query CQL refinada |

---

## 🔍 Busca (Search)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/flow/search/initial` | Busca inicial com parâmetros |
| `POST` | `/flow/search/final` | Busca final com query refinada |

---

## 📋 Parâmetros (Params)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/flow/params/store` | Armazena parâmetros no histórico |
| `GET` | `/flow/params/last-sample` | Recupera última amostra salva |
| `GET` | `/flow/params/history` | Lista histórico de parâmetros |

---

## 🔗 Query (Busca Refinada)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/flow/query/history` | Armazena query refinada no histórico |
| `GET` | `/flow/query/history` | Lista histórico de queries |

---

## 📊 Gráficos (Charts)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/flow/charts/generate` | Gera gráficos dos resultados |
| `POST` | `/flow/charts/add-to-report` | Adiciona gráfico ao relatório |
| `DELETE` | `/flow/charts/{id}` | Descarta/remove um gráfico |

---

## 📈 Dados (Data)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/flow/data/synthesize` | Sintetiza dados em texto |
| `POST` | `/flow/data/store-final` | Armazena dados finais no histórico |

---

## 📄 Relatório (Report)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/flow/report/generate` | Gera relatório completo |
| `POST` | `/flow/report/create-file` | Cria arquivo (PDF/XLSX/DOCX) |
| `GET` | `/flow/reports/history` | Lista histórico de relatórios |

---

## 📊 Resumo Total

- **POST (Ações):** 16 rotas
- **GET (Recuperação):** 4 rotas  
- **DELETE (Remoção):** 1 rota
- **TOTAL:** 21 rotas

---

## 🔄 Fluxo de Execução (Ordem)

```
1. generate-params (IA cria) → 2. specify-params (Refina)
3. params/store (Salva) → 4. search/initial (Busca)
5. [Satisfeito?] SIM → search/final | NÃO → loop:
   - choose-terms (Sugere)
   - create-query (Cria CQL)
   - query/history (Salva)
   - volta search/final
6. charts/generate (Gera gráficos)
7. [Satisfeito?] SIM → continue | NÃO → delete/{id} + loop
8. charts/add-to-report (Adiciona)
9. data/synthesize (Sintetiza texto)
10. report/generate (Gera relatório)
11. report/create-file (Cria arquivo)
12. data/store-final (Salva tudo)

GET endpoints: params/history, params/last-sample, query/history, reports/history
```

---

## 🎯 Agrupado por Funcionalidade

### Geração/Criação (10)
```
/flow/ai/generate-params
/flow/ai/specify-params
/flow/ai/choose-terms
/flow/ai/create-query
/flow/search/initial
/flow/search/final
/flow/charts/generate
/flow/data/synthesize
/flow/report/generate
/flow/report/create-file
```

### Armazenamento (4)
```
/flow/params/store
/flow/query/history (POST)
/flow/charts/add-to-report
/flow/data/store-final
```

### Recuperação (4)
```
/flow/params/last-sample
/flow/params/history
/flow/query/history (GET)
/flow/reports/history
```

### Remoção (1)
```
/flow/charts/{id}
```

---

**Status:** ✅ 21 rotas implementadas
