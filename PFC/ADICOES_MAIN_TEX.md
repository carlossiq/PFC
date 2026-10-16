# Adições sugeridas para o `main.tex`

Lacunas encontradas ao comparar o `main.tex` com o código (`app/`, `services/`, `config/`).
Cada item traz: **onde inserir**, o **que falta** e um **texto sugerido** em LaTeX, no tom
impessoal do documento. Os números de linha são os do `main.tex` na data desta análise.

Convenção: itens marcados **[VERIFICAR]** dependem de algo que não pude confirmar no código
ou na literatura e devem ser conferidos antes de entrar no texto.

---

## 0. Correções a fazer antes das adições

| # | Linha | Problema | Correção |
|---|---|---|---|
| C1 | 1443 | Diz "exclusão de citações inválidas **perante o banco relacional**". O filtro (`filter_citations`, `report_citations.py`) compara com as **fontes recuperadas pelo RAG naquela seção**, não com o PostgreSQL. Contradiz a linha 2069, que está correta. | Trocar por "exclusão de citações que não correspondem a nenhum documento recuperado para a seção". |
| C2 | 1423 | Fala em "escore final RRF **normalizado** $\ge 0{,}024$". Os comentários de `services/nlp/term_extraction.py:972-979` dizem que o `final_rrf_score` **não é normalizado** (faixa ~0,018–0,033) e que a versão normalizada foi removida. **[VERIFICAR]** o limiar atual em `core/config.py` (`term_extraction_score_threshold`). | Ajustar a redação e o valor conforme o código atual. |

---

## 1. RAG e citações (Seção 3.x, após a linha 1441)

### 1.1 O que é indexado e o papel dos metadados

**O que falta:** o texto diz que há fragmentos de 1.000 caracteres, mas não diz que o autor e a
referência viajam como **metadado** e não entram no embedding.

```latex
  Cada documento é indexado a partir da concatenação de título e resumo. Apenas esse texto é
convertido em representação vetorial. A autoria, o ano e a entrada bibliográfica correspondente
são calculados em código a partir dos metadados da base de origem (OPS ou Scopus) e armazenados
como metadados do fragmento, associados a ele no ChromaDB, mas sem participar do cálculo do
\textit{embedding}. Assim, a recuperação é puramente semântica sobre o conteúdo, e a identificação
da obra acompanha o fragmento recuperado sem depender do modelo de linguagem.
```

### 1.2 Como a consulta é formada e como o top-$k$ é obtido

**O que falta:** a linha 2060 cita a origem da consulta de forma resumida; não há a fórmula, o
critério de similaridade nem o funcionamento do corte relativo.

```latex
  A consulta de recuperação de cada seção é construída de forma determinística pela
concatenação do tema da pesquisa com o nome e a descrição da seção, ambos fixados no código
(por exemplo, para a Introdução: ``contexto histórico, mercado, \textit{players} e estado da
arte da tecnologia''). Nenhum modelo de linguagem participa dessa etapa. A consulta e os
fragmentos são representados no mesmo espaço vetorial, e a coleção utiliza distância de cosseno,
sendo a relevância definida como $1 - d_{\cos}$. Recuperam-se os $k = 5$ fragmentos de maior
relevância, restritos à sessão corrente, e descartam-se aqueles cuja relevância seja inferior a
$75\%$ da relevância do melhor fragmento:
$$ \text{relevância}(f) \ge 0{,}75 \cdot \max_{f'} \text{relevância}(f') $$
  O parâmetro $k$ limita o tamanho do \textit{prompt}; o corte relativo evita que documentos
periféricos, recuperados apenas para completar $k$, sejam tratados pelo modelo como assunto
central.
```

### 1.3 Controle de citações e referências

**O que falta:** desambiguação (2020a/2020b), regra "não citar" na origem, e a geração da lista
de referências a partir do texto final.

```latex
  A citação no formato (SOBRENOME \textit{et al.}, ano) é calculada em código a partir do
primeiro autor (ou inventor) e do ano de publicação; documentos sem autoria em alfabeto latino
ou sem ano não geram citação e são sinalizados ao modelo como ``não citar''. Quando duas obras
distintas produzem a mesma citação, acrescenta-se uma letra ao ano (2020a, 2020b), conforme a
ABNT. Após a geração, citações que não correspondam a nenhum documento recuperado para a seção
são removidas do texto. Por fim, a seção de Referências Bibliográficas é montada apenas com as
entradas das citações que permaneceram no texto final, de modo que toda citação possui
referência correspondente e nenhuma referência permanece sem citação.
```

### 1.4 Limitação a registrar (Seção de limitações, ~linhas 1558–1594)

```latex
  A citação utiliza apenas o primeiro autor, e a entrada bibliográfica é uma versão simplificada
da ABNT (autor, título, periódico ou depositante, ano), sem volume, páginas ou DOI. A consulta
de recuperação é única por seção, de modo que temas com múltiplas facetas são representados por
um único vetor.
```

---

## 2. Geração do documento LaTeX (Seção 3.x, após a linha 1443)

**O que falta:** o `main.tex` menciona reparo por regex (linha 1252) e TeX Live (linha 1325),
mas não explica **quem escreve o LaTeX** nem o fluxo texto → `.tex` → PDF.

```latex
  O modelo de linguagem não produz comandos \LaTeX{}. Ele devolve texto corrido, acrescido
apenas de marcadores próprios para figuras (\texttt{[[REF:id]]} e \texttt{[[FIG:id]]}). A
conversão para \LaTeX{} é inteiramente determinística e ocorre em quatro etapas: (i) remoção
de cabeçalhos e conversão de negrito em Markdown, eventualmente emitidos por modelos menores;
(ii) escape dos caracteres especiais (\texttt{\& \% \$ \# \_ \{ \}}) e descarte de caracteres
fora do alfabeto latino, comuns em nomes de inventores e que interromperiam a compilação;
(iii) substituição dos marcadores por \verb|\ref| e pelo bloco \verb|\figura| ou
\verb|\quadroimg|, validando os identificadores contra o catálogo de gráficos existentes (id
desconhecido é removido; figura repetida mantém apenas a primeira ocorrência; figura citada sem
marcador de posição é inserida após o parágrafo que a cita; figura nunca citada é posicionada
ao final da seção); e (iv) inserção do texto resultante em um \textit{template} Jinja2.
  O \textit{template} fixa a estrutura do documento (capa, sumário, numeração, seções e
subseções, quadro de busca, assinaturas, bibliografia), de modo que o modelo decide apenas o
conteúdo dos parágrafos. Seções formais, como Finalidade e Metodologia, são produzidas por código.
O arquivo \texttt{.tex} é compilado no serviço TeX Live, e uma verificação estática posterior
detecta referências sem rótulo, figuras inexistentes e marcadores residuais.
```

### 2.1 Justificativa do uso de LaTeX (decisões de projeto)

```latex
  Optou-se por \LaTeX{} em vez de Markdown por exigência do padrão REPTEC, que requer capa com
numeração de página própria, cabeçalho e rodapé, sumário automático, figuras e quadros com
legenda, fonte e numeração, referências cruzadas e margens conforme a ABNT. Tais recursos são
nativos em \LaTeX{} e dependem, em Markdown, de ferramentas externas de conversão. As referências
cruzadas por \verb|\label| e \verb|\ref| garantem que a numeração permaneça correta mesmo que a
ordem das figuras se altere. Como contrapartida, \LaTeX{} é menos tolerante a erros de
sintaxe, o que motivou o escape sistemático e a verificação estática descritos acima.
```

---

## 3. Curva S de Fisher-Pry (Seção 2.x e Seção 3.x)

**O que o `main.tex` já cobre:** modelo logístico, inversão para GP/MP/SP (linhas 800–838), $R^2$
(849–855), critérios de confiabilidade (1229–1235), inicialização de $K$ (1227).

**O que falta:** o método de ajuste, a acumulação, o tratamento de falha de convergência, a
projeção, o estágio do ciclo de vida e a ressalva sobre o $R^2$.

### 3.1 Método de ajuste (após a linha 855, ou na Seção 3.x do pipeline)

```latex
  Os parâmetros $(K, r, t_0)$ são estimados por mínimos quadrados não lineares sobre a série
\textbf{acumulada} anual, isto é, minimiza-se
$$ E(K, r, t_0) = \sum_i \left[ N_i - \frac{K}{1 + e^{-r(t_i - t_0)}} \right]^2 $$
em que $N_i$ é o total acumulado até o ano $t_i$. Como a função é não linear nos parâmetros,
não há solução fechada, e emprega-se a rotina \texttt{curve\_fit} do SciPy \cite{virtanen2020},
que, na ausência de limites, adota o algoritmo de Levenberg-Marquardt. A cada iteração, calcula-se
o Jacobiano $J$ (aqui, por diferenças finitas) e resolve-se
$$ (J^\top J + \lambda I)\,\delta = J^\top \mathbf{r}, $$
em que $\mathbf{r}$ é o vetor de resíduos. O passo $\delta$ é aceito se reduzir $E$, diminuindo-se
$\lambda$ (comportamento próximo ao de Gauss-Newton, rápido perto do mínimo); caso contrário, é
rejeitado e $\lambda$ aumenta (comportamento próximo à descida de gradiente, mais seguro longe
do mínimo). Por convergir a um mínimo local, o resultado depende do ponto de partida, fixado em
$K_0 = 1{,}5 \cdot N_{\text{final}}$, $r_0 = 0{,}3$ e $t_{0,0}$ igual à mediana dos anos
observados, limitando-se o processo a 5.000 avaliações da função.
```

### 3.2 Casos sem ajuste e projeção (Seção 3.x)

```latex
  Exigem-se ao menos dois anos distintos com dados; caso contrário, o gráfico é omitido com o
motivo registrado. Se o algoritmo não convergir, o que ocorre tipicamente quando a série ainda
não exibe sinal de desaceleração e, portanto, não contém informação para estimar $K$, a curva
não é ajustada e apresenta-se apenas a série acumulada observada. Marcos (GP, MP ou SP)
posteriores ao último ano observado constituem projeções do modelo, e não valores observados;
a porção futura da curva é desenhada em traço tracejado, por um número configurável de anos
além do último dado.
```

### 3.3 Estágio do ciclo de vida

```latex
  O estágio do ciclo de vida é determinado comparando-se o último ano completo com os marcos
ajustados: Emergente ($<$ GP), Crescimento (GP a MP), Maturidade (MP a SP) e Saturação ($\ge$ SP).
O estágio geral da tecnologia é o obtido pela curva de patentes, por refletir interesse
comercial, recorrendo-se à curva de artigos apenas na ausência daquela.
```

### 3.4 Ressalvas (Seção de limitações)

```latex
  O $R^2$ é calculado sobre a série acumulada, monotônica e naturalmente suave, o que tende a
produzir valores elevados mesmo para ajustes medianos, sendo, portanto, um critério mais
permissivo do que seria sobre as contagens anuais. O modelo supõe um único ciclo com saturação
e ajusta-se mal a tecnologias com segunda onda de crescimento ou séries muito ruidosas. A
estimativa de $K$ é instável em séries curtas, o que justifica os critérios de confiabilidade
da Seção~X. Por fim, a série depende da cobertura da busca: consultas restritas refletem o
recorte, e não a tecnologia inteira.
```

---

## 4. BM25F (Seção 3.x, após a linha 1417)

**O que o `main.tex` já cobre:** definição conceitual (linha 940) e parâmetros $w$, $k_1$, $b$ (1417).

**O que falta:** que o BM25F é aplicado **a termos candidatos** (não a documentos para uma
consulta), as fórmulas e onde a saturação atua.

```latex
  Diferentemente do uso clássico, em que o BM25F ordena documentos para uma consulta, aqui ele
pontua \textbf{termos candidatos} (n-gramas) segundo sua relevância no corpus de títulos e
resumos recuperados. Para cada termo $t$ e documento $d$ em que $t$ ocorre, calcula-se a
frequência combinada
$$ \tilde{f}_{t,d} = w_{\text{tít}} \frac{f^{\text{tít}}_{t,d}}{B^{\text{tít}}_d}
 + w_{\text{res}} \frac{f^{\text{res}}_{t,d}}{B^{\text{res}}_d},
 \qquad B^{c}_d = (1-b) + b \frac{|d_c|}{\overline{|d_c|}}, $$
em que $f^{c}_{t,d}$ é o número de ocorrências do termo no campo $c$, $|d_c|$ é o comprimento do
campo e $\overline{|d_c|}$ sua média no corpus. A pontuação do termo é
$$ s(t) = \text{IDF}(t) \sum_{d \,:\, t \in d} \frac{\tilde{f}_{t,d}}{k_1 + \tilde{f}_{t,d}},
 \qquad \text{IDF}(t) = \ln\!\left(1 + \frac{N - n_t + 0{,}5}{n_t + 0{,}5}\right), $$
sendo $N$ o número de documentos e $n_t$ aquele em que $t$ ocorre.
  A saturação $\tilde{f}/(k_1 + \tilde{f})$ é aplicada \textbf{por documento}, antes da soma:
cada documento contribui com no máximo uma unidade, de modo que um termo repetido muitas vezes
em um único documento não supera outro presente em muitos documentos. O IDF, calculado uma vez
por termo, trata a raridade entre documentos, e a saturação trata a repetição dentro de cada um.
A frequência é a contagem literal de subcadeias por campo, o que equivale à frequência de frase
sem necessidade de índice invertido em um corpus pequeno e por requisição. A saturação omite o
fator $(k_1 + 1)$ da formulação original, constante para todos os termos e, portanto, sem efeito
sobre o ordenamento.
```

**[VERIFICAR]** Como a contagem é por subcadeia (`str.count`), um termo curto pode ser contado
dentro de palavras maiores. Vale registrar como limitação ou conferir se há tratamento anterior.

---

## 5. RRF (Seção 2.x, após a linha 948; e Seção 3.x, linhas 1419–1423)

### 5.1 Justificativa de $k = 60$ e propriedades (após a linha 948)

```latex
  O parâmetro $k$ controla o quanto a posição no ranking importa. Para $k$ pequeno, apenas o
topo é relevante e um item bem colocado em um único canal pode dominar; para $k$ grande, as
posições tornam-se quase equivalentes e o método perde poder discriminatório. Com $k = 60$, a
razão entre as contribuições da primeira e da décima posição é de cerca de $1{,}15$, de modo que
um termo bem classificado em \textbf{ambos} os canais supera outro excelente em apenas um deles.
O valor $k = 60$ foi adotado por Cormack \textit{et al.}~\cite{cormack2009} em suas avaliações e
é a convenção em implementações de busca híbrida; trata-se de um valor empírico, sem justificativa
teórica, ao qual o desempenho é relativamente pouco sensível. Por considerar apenas posições, o
método dispensa a normalização de escalas heterogêneas (como o BM25F, sem limite superior, e o
cosseno, restrito a $[-1, 1]$), ao custo de descartar a magnitude das diferenças entre notas.
```

**[VERIFICAR]** a descrição do `k = 60` no artigo original (Cormack, Clarke e Buettcher, SIGIR
2009) e a afirmação de que é padrão em motores de busca (por exemplo, Elasticsearch,
OpenSearch, Azure AI Search, Weaviate, Qdrant, Vespa, LangChain). Consultar o PDF e a documentação
vigente de cada ferramenta antes de citar.

### 5.2 Uso em dois estágios (linhas 1419–1421)

```latex
  O RRF é aplicado em dois estágios. No primeiro, fundem-se os rankings do canal lexical
(BM25F) e do canal semântico (KeyBERT), gerando o escore de saliência. No segundo, funde-se o
ranking de saliência com o de qualidade estrutural do termo, que favorece determinados tamanhos
de n-grama e penaliza padrões gramaticais inadequados, gerando o escore final. Em seguida,
aplicam-se o filtro de C-value, a remoção de termos aninhados e o corte por limiar. O RRF, em sua
formulação original, funde rankings de documentos para uma consulta; aqui foi adaptado para
fundir rankings de termos candidatos.
```

### 5.3 Limitações (Seção de limitações)

```latex
  O escore RRF é relativo ao lote de candidatos e não constitui escala absoluta: sua faixa de
valores varia com o tamanho do lote e a composição dos candidatos, de modo que um limiar fixo
pode excluir todos os termos de um lote. Para evitá-lo, o sistema completa a lista com os
termos mais bem classificados abaixo do limiar até o mínimo de dez termos. Dois termos podem
receber o mesmo escore, e a ordem entre eles segue a ordenação estável da linguagem. O valor
$k = 60$ não foi ajustado ao corpus deste trabalho.
```

**Sugestão de experimento (opcional, fortalece a defesa):** rodar a extração de termos com
$k \in \{10, 60, 200\}$ sobre a mesma sessão e comparar quantos dos termos do topo mudam. Se
mudarem pouco, há evidência própria de que o valor não é crítico.

---

## 6. Resumo: onde cada adição entra

| Item | Local sugerido | Tipo |
|---|---|---|
| C1, C2 | linhas 1443 e 1423 | Correção |
| 1.1–1.3 | Após a linha 1441 (RAG) | Nova explicação |
| 1.4, 3.4, 5.3 | Seção de limitações (~1558–1594) | Limitações |
| 2, 2.1 | Após a linha 1443 | Nova explicação e decisão de projeto |
| 3.1 | Após a linha 855 (ou Seção 3.x) | Método |
| 3.2, 3.3 | Seção 3.x do pipeline (~1440) | Nova explicação |
| 4 | Após a linha 1417 | Fórmulas |
| 5.1 | Após a linha 948 | Fundamentação |
| 5.2 | Linhas 1419–1421 | Detalhamento |

Observações finais:
- Os rótulos `\ref` e a referência "Seção~X" em 3.4 precisam ser ajustados aos rótulos reais do documento.
- Todas as citações (`virtanen2020`, `cormack2009`) já existem na bibliografia; nenhuma obra nova foi introduzida.
- Os trechos foram escritos no tom impessoal do documento e podem ser encurtados conforme o limite de páginas.
