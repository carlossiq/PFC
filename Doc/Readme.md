# Pipeline do Sistema de Prospecção Tecnológica

## Visão Geral
O sistema proposto segue um pipeline composto por cinco macroetapas:

- Entrada do usuário  
- Estratégia de busca  
- Recuperação de documentos  
- Processamento e análise de dados  
- Geração de relatório  

---

## Pipeline Geral

Usuário → Estratégia de busca → Busca → Processamento → Análise → Relatório

---

## 1. Entrada do Usuário

O usuário fornece:

- Tema ou tecnologia de interesse : necessário
- Objetivo da prospecção : opcional
- Recorte temporal : não necessário
- Tipo de documento (artigos, patentes ou ambos) : sempre ambos
- Palavras-chave iniciais : opcional

**Saída:** conjunto inicial de termos e parâmetros de busca.

---

## 2. Estratégia de Busca

### 2.1 Geração da Query Inicial (LLM)

Um modelo de linguagem (LLM) gera uma query inicial baseada no tema informado.
"Gemini 3.1 Pro / Opus 4.6"

Funções:
- Sugerir palavras-chave relevantes  
- Gerar sinônimos técnicos  
- Estruturar operadores booleanos  
- Separar termos por tipo de documento  

**Saída:** query inicial estruturada.

---

### 2.2 Busca Inicial (Lens API)

A query inicial é executada na Lens API para recuperar documentos reais.

Dados coletados:
- Título  
- Resumo  
- Palavras-chave  
- Autores  
- Ano  
- Instituições  
- Citações  
- Classificações tecnológicas (IPC/CPC, se aplicável)  

**Saída:** conjunto preliminar de documentos.

---

### 2.3 Extração de Termos (KeyBERT)

Os textos recuperados (títulos, resumos, keywords) são processados pelo KeyBERT.

Objetivos:
- Extrair termos relevantes do corpus real  
- Identificar vocabulário técnico recorrente  
- Reduzir dependência do LLM  

**Saída:** lista de termos candidatos.

---

### 2.4 Filtragem e Normalização dos Termos

Os termos extraídos passam por filtragem:

- Remoção de termos genéricos  
- Eliminação de duplicatas  
- Lematização (spaCy)  
- Similaridade semântica (SBERT)  
- Filtro por relevância  

**Saída:** lista refinada de termos relevantes.

---

### 2.5 Refinamento da Query (LLM)

O LLM utiliza:

- Query inicial  
- Termos extraídos e filtrados  
- Contexto do problema  

Para gerar uma query refinada.

**Saída:** query final otimizada.

---

## 3. Busca Final

A query refinada é executada nas bases de dados.

### 3.1 Literatura Científica
- Lens Scholarly  
- Outras bases (se disponíveis)

### 3.2 Patentes
- Lens Patents  
- Outras APIs (se aplicável)

**Saída:** dataset consolidado.

---

## 4. Processamento dos Dados

### 4.1 Limpeza
- Remoção de duplicatas  
- Padronização de campos  
- Tratamento de valores ausentes  

### 4.2 Estruturação
Criação de tabelas como:
- Publicações por ano  
- Documentos por país  
- Autores e instituições  
- Áreas tecnológicas  
- Classes IPC/CPC  

**Saída:** base estruturada para análise.

---

## 5. Análise

### 5.1 Indicadores Bibliométricos
- Produção por ano  
- Autores mais relevantes  
- Instituições mais produtivas  
- Países com maior atividade  
- Documentos mais citados  

### 5.2 Indicadores Tecnológicos
- Depósitos de patentes por ano  
- Principais depositantes  
- Classes tecnológicas dominantes  
- Evolução do domínio tecnológico  

### 5.3 Curvas e Gráficos
- Séries temporais  
- Distribuições por categoria  
- Rankings  
- Curvas S de maturidade tecnológica  

---

## 6. Geração de Relatório

O sistema gera um relatório contendo:

- Tema analisado  
- Metodologia de busca  
- Query final utilizada  
- Bases consultadas  
- Indicadores gerados  
- Gráficos e curvas  
- Interpretação dos resultados  
- Conclusões sobre maturidade tecnológica  

---

## Fluxograma Resumido

Tema do usuário  
→ LLM gera query inicial  
→ Busca preliminar (Lens API)  
→ Extração de termos (KeyBERT)  
→ Filtragem e NLP  
→ LLM refina a query  
→ Busca final  
→ Tratamento dos dados  
→ Análise e geração de gráficos  
→ Relatório final  

---

## Arquitetura Modular

- **Módulo 1:** Entrada do usuário  
- **Módulo 2:** Geração da estratégia de busca  
- **Módulo 3:** Coleta de dados (APIs)  
- **Módulo 4:** Processamento NLP (KeyBERT, spaCy, SBERT)  
- **Módulo 5:** Análise e indicadores  
- **Módulo 6:** Geração de relatório  

---