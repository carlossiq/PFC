"""
Template LaTeX do relatório REPTEC/AGITEC (ver notes/REPTEC_001_2023_TETRA.pdf
pra estrutura real: capa, sumário, 8 seções numeradas, assinaturas).

Usa Jinja2 com delimitadores customizados (\\VAR{}/\\BLOCK{}) pra não colidir
com `{}` do LaTeX - `render_report_latex` é a única função pública, chamada
por app/core/services/report_latex_service.py. Todo texto solto (seções de
IA) já deve chegar aqui escapado (ver
app.core.services.report_writer_service.escape_latex) - este módulo só
monta o documento, não sanitiza texto.

Formato esperado de `context` (todas as chaves com default seguro se
ausentes - seções ainda não geradas aparecem como "[Seção ainda não
gerada]" em vez de quebrar a renderização):
    numero, ano, tema: str - capa
    capa_imagem: str | None - nome do arquivo (basename) da imagem de capa
        configurada em Configurações > Geral (ver
        app/core/services/report_cover_image.py), já padronizada em tamanho
        - None pula o bloco da imagem inteiro (nenhuma imagem configurada
        no momento em que esta sessão foi montada)
    finalidade, objetivo, introducao: str - seções de IA (1, 3, 4)
    referencias_administrativas: list[str] - seção 2, dado do usuário
    metodologia: str - só o ÚLTIMO parágrafo da seção 5 (o interpolado
        com palavras-chave/período/bases, ver
        config/prompts/report_static_sections.py::render_metodologia) - o
        resto da seção (inclusive 5.1-5.3 e as figuras fixas madeo.png/
        kucharavy.png, ver report_static_figures.py) é fixo aqui
    quadro_busca: dict com patente/artigo (conteúdo já escapado de cada
        célula do Quadro de estratégias de busca) ou None
    informacoes_cientificas, informacoes_tecnologicas, tendencias_ciclo_vida: str
        - subseções 6.1/6.2/6.3, seções de IA JÁ com as figuras/quadros
        inseridos no lugar (ver app/core/services/report_figures.py)
    conclusao: str - seção 7, seção de IA
    referencias_bibliograficas: list[str] - seção 8, fixa + usuário
    assinaturas: dict com elaborado_por/revisado_por/aprovado_por, cada um
        uma LISTA de {"nome", "posto", "funcao"} (1+ assinantes por papel -
        ver ReportGeneration.tsx) - sai como "NOME -- POSTO" (negrito) e a
        função na linha de baixo, como no REPTEC
"""

from __future__ import annotations

from typing import Any

from jinja2 import Environment

REPORT_LATEX_TEMPLATE = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazilian]{babel}
\usepackage[margin=2.5cm]{geometry}
\usepackage{tgtermes}
\usepackage{setspace}
\onehalfspacing
\usepackage{graphicx}
\usepackage{float}
\usepackage{indentfirst}
\usepackage{microtype}
\usepackage{tabularx}
\usepackage{array}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage{titlesec}
\usepackage{tocloft}
\usepackage{caption}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}

\setlength{\parindent}{1.25cm}
\setlength{\headheight}{15pt}

% Cabeçalho/rodapé em toda página exceto a capa (titlepage já é "empty").
\pagestyle{fancy}
\fancyhf{}
\fancyhead[R]{REPTEC \VAR{numero}/\VAR{ano} -- \MakeUppercase{\VAR{tema}}}
\fancyfoot[R]{Página \thepage\ de \pageref*{LastPage}}
\renewcommand{\headrulewidth}{0pt}

% Títulos: "1 FINALIDADE" (seções em caixa alta, escrita no próprio
% template) e "5.1 Informações Científicas" (subseções em caixa mista),
% ambos em negrito - igual ao REPTEC de referência.
\titleformat{\section}{\normalfont\normalsize\bfseries}{\thesection}{0.5em}{}
\titleformat{\subsection}{\normalfont\normalsize\bfseries}{\thesubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{12pt}{6pt}
\titlespacing*{\subsection}{0pt}{12pt}{6pt}

% Sumário: só as seções principais (sempre em caixa alta), título à
% esquerda, pontilhado até o número da página em todas as entradas.
\setcounter{tocdepth}{1}
\renewcommand{\cfttoctitlefont}{\normalsize\bfseries}
\renewcommand{\cftaftertoctitle}{}
\renewcommand{\cftsecfont}{\normalfont}
\renewcommand{\cftsecpagefont}{\normalfont}
\renewcommand{\cftsecleader}{\cftdotfill{\cftdotsep}}

% Figuras: "Figura N: título" acima, "Fonte: ..." abaixo - o título nunca
% vem desenhado dentro da imagem (ver report_service.py).
\captionsetup{labelsep=colon, font=normalsize, justification=centering}
\DeclareCaptionType{quadro}[Quadro][Lista de Quadros]
\newcommand{\figura}[3][O autor.]{%
  \begin{figure}[H]
    \centering
    \caption{#2}
    \includegraphics[width=0.85\textwidth,height=0.55\textheight,keepaspectratio]{#3}\par
    \vspace{0.2cm}Fonte: #1
  \end{figure}}
% Imagem apresentada como Quadro (ex.: heatmaps de CPC/áreas de estudo -
% no REPTEC são "Quadro 2"/"Quadro 3", não Figura). minipage: legenda,
% imagem e fonte nunca se separam numa quebra de página.
\newcommand{\quadroimg}[3][O autor.]{%
  \par\vspace{0.5cm}\noindent\begin{minipage}{\textwidth}\centering
    \captionof{quadro}{#2}
    \includegraphics[width=0.85\textwidth,height=0.5\textheight,keepaspectratio]{#3}\par
    \vspace{0.2cm}Fonte: #1
  \end{minipage}\par\vspace{0.5cm}}

\begin{document}

\begin{titlepage}
    \centering
    \vspace*{2cm}
    \BLOCK{ if capa_imagem }
    \includegraphics[width=4cm]{\VAR{capa_imagem}}\par
    \vspace{1cm}
    \BLOCK{ endif }
    {\LARGE\bfseries RELATÓRIO DE PROSPECÇÃO TECNOLÓGICA\par}
    \vspace{0.5cm}
    {\Large\bfseries \VAR{numero}/\VAR{ano} -- AGITEC\par}
    \vspace{1.5cm}
    {\Large\bfseries \MakeUppercase{\VAR{tema}}\par}
    \vfill
\end{titlepage}
% A capa conta como página 1 (igual ao REPTEC de referência).
\setcounter{page}{2}

\tableofcontents
% tocloft força \thispagestyle{plain} na página do sumário - sem isso ela
% sairia sem cabeçalho e com o número de página solto no rodapé.
\thispagestyle{fancy}
\newpage

\section{FINALIDADE}
\VAR{finalidade}

\section{REFERÊNCIAS}
\BLOCK{ if referencias_administrativas }
\begin{itemize}[label=-, leftmargin=*]
\BLOCK{ for ref in referencias_administrativas }
    \item \VAR{ref}
\BLOCK{ endfor }
\end{itemize}
\BLOCK{ else }
Nenhuma referência administrativa informada.
\BLOCK{ endif }

\section{OBJETIVO}
\VAR{objetivo}

\section{INTRODUÇÃO}
\VAR{introducao}

\section{METODOLOGIA}
Os estudos de prospecção tecnológica, também chamados de estudos de futuro, ou \textit{forecast(ing)}, \textit{foresight(ing)} ou \textit{future studies}, fornecem as principais tendências no contexto mundial, sendo possível segmentar estas tecnologias por setor da economia. Estes estudos auxiliam a identificação de tecnologias promissoras, úteis para determinada organização, bem como apontam para possibilidades de negócios e parcerias. A sistematização da prática de monitoramento tecnológico, a ser coberta pela prospecção tecnológica e de inovação, visa congregar a busca de soluções adequadas para a identificação e priorização de uma agenda de P\&D, articulada com instituições de pesquisa, que possa inclusive influenciar a agenda de P\&D nacional e criar demandas para a cadeia inovativa do setor (BORSCHIVER; LEMOS, 2016).

Estudos de Prospecção Tecnológica são elementos essenciais de informações que se propõem a auxiliar processos decisórios de organizações complexas e de capilaridade como o Exército Brasileiro, face aos desafios impostos pelo cenário de instabilidades internacional e nacional e seus reflexos para as expressões do poder nacional. O desenvolvimento de estudos dessa natureza mormente contempla informações técnicas e quantitativas, em que são empregadas ferramentas bibliométricas, e as informações qualitativas, nas quais a participação de especialistas é fundamental para coletar, reunir e codificar (registrar) o conhecimento tácito que integra o capital humano da organização, muitas vezes, pulverizado por integrantes nas mais diversas OM do país.

Entre os óbices da fase inicial dos estudos de prospecção elaborados pelo EB, pode-se citar a dificuldade de identificar profissionais ou OM mais apropriados a contribuírem com o tema. Esse esforço inicial é superado com a participação de pesquisadores que compõem o \textit{networking} dos analistas de prospecção. Esses profissionais das Instituições Científico-Tecnológicas (ICT) militares auxiliam a otimizar o estudo preliminar aclarando aspectos que podem ser explorados, evitando o envolvimento prematuro de um amplo rol de profissionais. Superada essa etapa inicial, segue-se uma pesquisa externa à AGITEC, em que são coletadas informações de especialistas de profissionais dedicados ao tema, ainda que dispersos por inúmeras OM do Brasil, o que se mostra promissor, em razão de integrar conhecimentos de especialistas ou técnicos versados no assunto com o rol de ferramentas e capacidades de analistas de prospecção tecnológica.

O recrutamento assertivo do capital humano para os temas propostos é essencial para o estudo prospectivo, pois colabora na identificação dos desafios institucionais impostos pelo tema e a complexidade tecnológica envolvida, permitindo criar um canal de acesso direto e fluência de competências técnicas de que o Exército dispõe, no entanto, face à sua distribuição pelo continente nacional, não é trivial reunir e considerar as visões complementares entre especialistas de Órgãos de Direção Setorial e Operacional, e de analistas de prospecção tecnológica.

O Método de Prospecção Tecnológica busca explorar o conhecimento explícito, acessado a partir de registros e repositórios diversos como fontes de notícias, informações científicas e informações tecnológicas; e o conhecimento tácito, por meio da contribuição dos especialistas integrantes do Exército.

Pretende-se revelar o estado atual referente ao ciclo de vida da tecnologia. Para isso, por intermédio da bibliometria de patentes, da literatura científica (artigos, capítulos de livros, anais de congressos etc.) e de fontes ostensivas de informações atuais, buscam-se evidências que colaborem com a área em questão. Para tanto, são empregadas bases de dados de patentes e de literatura científica, além de refinamentos sucessivos de modo a produzir novos conhecimentos acerca do tema alvo.

Estudos bibliométricos a partir de artigos, patentes e fontes ostensivas têm sido cada vez mais empregados como técnicas de monitoramento de capacidades tecnológicas em Setores do Governo, Indústria e Academia. Entende-se que os artigos científicos são ativos que denotam o conhecimento técnico que resulta do esforço de Instituições Científico-Tecnológicas (ICT) e também de Empresas de Base Tecnológica (EBT). Deste modo, serão analisadas informações bibliométricas sobre \VAR{tema} com o propósito de aclarar o cenário tecnológico, no mundo e no Brasil, e verificar o estado atual da tecnologia em relação ao seu ciclo de vida.

Cabe ressaltar a necessidade de estabelecer estratégias de buscas adequadas e assertivas que permitam explorar o tema com a abrangência e profundidade requeridas. O uso de palavras-chave inicialmente válidas pode indexar conteúdo não pretendido pelo pesquisador, ou ainda, termos técnicos devidamente justificados podem apresentar mais de uma semântica e se aplicar a mais de uma área do conhecimento, fora do escopo a ser investigado. Desse modo, a interação é fundamental para reduzir o ruído no retorno das informações impróprias, ou seja, resultados que prejudiquem a coleta de dados e sua posterior análise. Ao modelar as estratégias de busca é possível acessar o conjunto de documentos mais assertivos como ostensivos, artigos científicos e patentes, de modo a produzir elementos essenciais de informação sobre o tema.

Como principal consequência do método, pode-se listar a elaboração mais consistente do Estado da arte, da escolha do repositório de artigos científicos, de patentes, de fontes de notícias, além da melhor estruturação de taxonomias e as curvas de extrapolação que auxiliam a visualizar perspectivas da evolução tecnológica futura. Nas Seções a seguir, serão detalhadas as etapas percorridas na execução do presente estudo prospectivo.

\subsection{Informações Científicas}
A informação científica é o conhecimento que constituiu, em certo momento da evolução da ciência, um acréscimo ao entendimento universal então existente sobre algum fato ou fenômeno, tendo-se tornado disponível como resultado de uma pesquisa científica, ou seja, de um trabalho de investigação conduzido segundo o método científico (BORSCHIVER; LEMOS, 2016).

O elemento primordial para o desempenho da atividade científica reside na informação que se encontra codificada de maneira verbal, manifesta em fontes como periódicos científicos e registros de conferências acadêmicas. Por conseguinte, o produto fundamental gerado por essa atividade, ou seja, o artigo científico veiculado em uma revista especializada, também assume esse viés. Tal produto desempenha um papel fundamental como matéria-prima para investigações científicas subsequentes, formando, dessa forma, um ciclo contínuo (BORSCHIVER; LEMOS, 2016).

O Perfil Científico reflete a visão da academia sobre o assunto, envolvendo resultados preponderantemente de pesquisa básica e aplicada. Neste caso, geralmente, nos níveis iniciais de uma escala de maturidade tecnológica (FRANÇA JR.; GALDINO, 2019). Ainda, permite analisar informações contidas nas publicações científicas, como: produção de instituições e a produtividade de autores em função do tempo; autores mais relevantes; coautorias; instituições com desenvolvimento destacado; colaborações existentes entre instituições e países; fontes de financiamento; entre outros indicadores ou sinais que contemplem informações passadas, mas possibilitem amparar, elucidar e constituir visão futura.

Em amplo senso, entende-se que no início do ciclo de geração de uma nova tecnologia, o artigo científico é uma das primeiras expressões de codificação do conhecimento, período que usualmente reflete a baixa maturidade da tecnologia analisada. Ademais, a publicação de artigos acompanha grande parte do ciclo de vida de tecnologias em seus diferentes estágios de maturidade tecnológica, o que permite estabelecer interessantes associações e extrapolações, restritas às áreas que dependem de pesquisa básica e aplicada (LINDEN; BARBOSA; DIGIAMPIETRI, 2017; ERNST, 1997; NIETO; LOPÉZ; CRUZ, 1998).

\subsection{Informações Tecnológicas}
As patentes apresentam-se como excelentes indicadores de inovação, na medida em que servem para mensurar o resultado de P\&D, a produtividade, a estrutura e o desenvolvimento de uma tecnologia/indústria específica (BORSCHIVER; LEMOS, 2016).

A busca em repositório estruturado que proporcione o acesso a informações de patentes, sobre a qual recai a expectativa de maior potencial para converter a pesquisa em produto, ou ainda, se constitui em forte indício de aplicação comercial, é uma estratégia essencial para direcionar a inovação e maximizar as oportunidades de desenvolvimento de novos produtos e tecnologias. Através desse tipo de busca em um repositório estruturado de patentes, é possível identificar padrões, tendências e \textit{gaps} no mercado, permitindo uma análise mais precisa das oportunidades e ameaças presentes no cenário tecnológico. Com base nessa abordagem, é possível tomar decisões assertivas sobre investimentos em P\&D, parcerias estratégicas e ações de propriedade intelectual, visando tanto o crescimento operacional quanto a consolidação de uma posição estratégica.

Integram essa fonte as patentes indexadas em bases de abrangência internacional, que espelham jurisdições da maior parte dos países. O Perfil Tecnológico permite analisar informações contidas em portfólio de empresas e áreas de atuação de \textit{startups}, recursos voltados para P\&D e depósitos de patentes (fontes mais vocacionadas à geração de inovação), tais como produção e interesse pela tecnologia, depositantes, possíveis parcerias, tecnologias associadas entre outros. Há robusto pressuposto de que o aumento do interesse por novas tecnologias reflete-se no aumento da atividade de P\&D que, por sua vez, acarreta o aumento de depósito de patentes (DAIM; RUEDA; MARTIN, 2005; PORTER, 2005). Pode-se inferir também que as tecnologias que figuram neste repositório, em amplo senso, já atingiram um nível de maturidade tecnológica mais elevado, portanto, mais propensos, na iminência, ou mesmo já se encontram em uso ou em operação no mercado (ANDRADE; MOURA; BORSCHIVER, 2018; LEZAMA-NICOLÁS et al., 2018).

\subsection{Análise de Tendências e o Ciclo de Vida (CVT) de uma Tecnologia}
A análise de tendências se baseia no pressuposto de que os comportamentos do passado serão mantidos no futuro. Esta análise utiliza técnicas matemáticas e estatísticas para extrapolar séries temporais para o futuro (BORSCHIVER; LEMOS, 2016).

A extrapolação por meio de regressão logística abarca métodos de previsão a partir de robustas ferramentas matemáticas e estatísticas, como Loglet\footnote{Disponível em \url{https://logletlab.com/loglet/documentation/index}.} e Sigmaplot\footnote{Disponível em \url{https://osbsoftware.com.br/produto/sigmaplot/}.}. Permitem, ainda, acompanhar, em grande medida a evolução científico-tecnológica, e gerar curvas S, para avaliar o desempenho de tecnologias, prever mudanças populacionais, analisar a penetração de mercado, elaborar estudos micro e macroeconômicos, verificar mecanismos de difusão de invenções tecnológicas e sociais, processos de modelagem ecológica, entre outros fins, o que fora confirmado por outros autores (KUCHARAVY; DE GUIO, 2011; LEZAMA-NICOLÁS et al., 2018; NIETO; LOPÉZ; CRUZ, 1998).

Ernst foi um dos precursores em evidenciar a relação entre o desenvolvimento de pedidos de patentes ao longo do tempo e o processo de difusão tecnológica, empregando para tanto, um controle numérico computadorizado (CNC) (ERNST, 1997, p. 363). O autor descreve os quatro estágios do ciclo de vida da tecnologia que abarcam o seu desenvolvimento:

\begin{enumerate}[label=\alph*.]
    \item \textbf{estágio emergente}: caracterizado por um crescimento relativamente baixo do desempenho tecnológico em comparação com a quantidade de esforços de P\&D;
    \item \textbf{estágio de crescimento}: na qual o progresso tecnológico marginal sobre os gastos cumulativos de P\&D é positivo;
    \item \textbf{estágio de maturidade}: onde a relação anterior torna-se negativa; e o
    \item \textbf{estágio de saturação}: no qual pequenas melhorias de desempenho tecnológico são obtidas por meio de esforços de P\&D muito elevados.
\end{enumerate}

A Figura \ref{fig:madeo} apresenta os quatro estágios do ciclo de vida de uma tecnologia.

\figura[MADEO, 2019, p. 37. Adaptado de Ernst (1997).]{Estágios do ciclo de vida de uma tecnologia.\label{fig:madeo}}{madeo.png}

Em síntese, o desempenho da tecnologia é diretamente proporcional ao tempo de investimento, e a difusão do conhecimento codificado afeto a um tema repercute nos indicadores bibliométricos. Na fase embrionária, percebem-se poucas publicações de artigos e patentes, normalmente espaçadas ao longo do tempo. Na fase de crescimento, o aumento de interesse da comunidade científico-tecnológica no tema provoca uma rápida evolução numérica de registros, caracterizada por uma curva ascendente do gráfico, que corresponde, normalmente, ao aumento de produtividade do setor acadêmico, ou ainda de expectativas comerciais de setores competitivos que ambicionam proteger nichos por intermédio de patentes, ou seja, há proeminência ou protagonismo do setor privado no desenvolvimento da área tecnológica analisada.

Na fase de maturidade a produção anual científica ou dos depósitos de patentes apresentam sinais de arrefecimento e passam a ocorrer em menor intensidade, sinalizando que as evoluções técnicas se tornam mais espaçadas. Finalmente, o ciclo tecnológico atinge sua fase de saturação: a inflexão da curva à direita prenuncia um platô, em que os novos depósitos estabilizam, sofrem pequenas oscilações ou mesmo decaem.

Essa fase, contudo, pode ser sucedida por um novo ciclo de inovações incrementais, o que possibilitará alongar a vida útil da aludida tecnologia, ensejando novo avanço da Curva S, ou ainda, perder competitividade para uma tecnologia emergente, que pode superar a tecnologia dominante, substituí-la e ensejar a mobilização científico-tecnológica. Como resultado final, a tecnologia em saturação sinaliza o desinteresse comercial ou que a tecnologia segue para a obsolescência, o que pode ser caracterizado por declínio abrupto de publicações, prenúncio ou evidência de sua descontinuidade.

\figura[KUCHARAVY; DE GUIO, 2011, p. 3.]{Diagrama esquemático de uma curva logística incluindo seus estágios do ciclo de vida e os parâmetros relacionados.}{kucharavy.png}

Como apresentado brevemente, o ciclo de vida da tecnologia pode ser monitorado, e suas perspectivas de desenvolvimento futuro podem ser visualizadas por métodos matemáticos de extrapolação, proporcionando análises que compreendem a antevisão de comportamentos na produção científica e patentária de determinado tipo de tecnologia e a comparação entre tecnologias concorrentes.

\VAR{metodologia}

\subsection{Apoio Computacional à Prospecção}
As etapas descritas nesta seção foram conduzidas com o apoio de ferramentas computacionais que integram técnicas de Inteligência Artificial (IA) e de Processamento de Linguagem Natural (PLN) à análise bibliométrica, sempre com a revisão e a validação do analista de prospecção em cada etapa.

Inicialmente, modelos de linguagem de grande porte (\textit{Large Language Models} -- LLM) propõem estratégias de busca a partir do tema e das palavras-chave informados, respeitando a sintaxe de cada base de dados e um índice de complexidade que evita consultas excessivamente restritivas. Essas estratégias são executadas em buscas exploratórias (\textit{probe}), cujos documentos fornecem o vocabulário efetivamente empregado na literatura e nas patentes sobre o tema. Desse conjunto são extraídos termos candidatos por padrões gramaticais, posteriormente ranqueados por dois critérios complementares: um estatístico-lexical, pelo algoritmo BM25F, e um semântico, pelo método KeyBERT, cujos resultados são combinados por fusão de rankings (\textit{Reciprocal Rank Fusion}). Os termos mais representativos orientam a construção da estratégia de busca final, em três níveis de abrangência (específica, balanceada ou ampla), selecionada pelo analista.

A busca final é realizada ano a ano, preservando a série histórica completa, e a amostra analisada é ampliada até que um critério estatístico indique sua saturação, conferindo robustez aos rankings de depositantes, instituições e classificações. As curvas S são ajustadas automaticamente pelo modelo logístico, com a identificação dos pontos GP, MP e SP e do estágio correspondente do ciclo de vida. Por fim, a redação das seções analíticas deste relatório contou com o apoio de LLM, fundamentada exclusivamente nos documentos recuperados nas buscas e nos indicadores calculados, com a citação das respectivas fontes e submetida à revisão final do analista.

\section{RESULTADOS}

\BLOCK{ if quadro_busca }
As estratégias de busca utilizadas para identificar a produção científica e tecnológica sobre o tema podem ser vistas no Quadro \ref{quadro:busca}.

% minipage: legenda, tabela e fonte nunca se separam numa quebra de página.
\noindent\begin{minipage}{\textwidth}
\centering
\captionof{quadro}{Estratégias de busca.\label{quadro:busca}}
\begin{tabularx}{\textwidth}{|>{\raggedright\arraybackslash}X|>{\raggedright\arraybackslash}X|}
\hline
\textbf{Depósito de Patentes} & \textbf{Publicações Científicas} \\
\hline
\VAR{quadro_busca.patente} & \VAR{quadro_busca.artigo} \\
\hline
\end{tabularx}
\par\vspace{0.2cm}Fonte: O autor.
\end{minipage}
\vspace{0.5cm}
\BLOCK{ endif }

\subsection{Informações Científicas}
\VAR{informacoes_cientificas}

\subsection{Informações Tecnológicas}
\VAR{informacoes_tecnologicas}

\subsection{Tendências e Ciclo de Vida da Tecnologia}
\VAR{tendencias_ciclo_vida}

\section{CONCLUSÃO}
\VAR{conclusao}

\section{REFERÊNCIAS BIBLIOGRÁFICAS}
\BLOCK{ if referencias_bibliograficas }
\begin{list}{}{\setlength{\leftmargin}{0pt}\setlength{\itemsep}{6pt}}
\BLOCK{ for ref in referencias_bibliograficas }
    \item \VAR{ref}
\BLOCK{ endfor }
\end{list}
\BLOCK{ else }
Nenhuma referência bibliográfica informada.
\BLOCK{ endif }

\vspace{1cm}
\BLOCK{ if local_data }
\noindent \VAR{local_data}

\BLOCK{ endif }
\vspace{1cm}
\noindent Elaborado por:
\BLOCK{ for signer in assinaturas.elaborado_por }
\begin{center}
\vspace{1cm}
\rule{8cm}{0.4pt}\\
\textbf{\VAR{signer.nome} -- \VAR{signer.posto}}\BLOCK{ if signer.funcao }\\
\VAR{signer.funcao}\BLOCK{ endif }
\end{center}
\BLOCK{ endfor }

\vspace{1cm}
\noindent Revisado por:
\BLOCK{ if assinaturas.revisado_por }
\BLOCK{ for signer in assinaturas.revisado_por }
\begin{center}
\vspace{1cm}
\rule{8cm}{0.4pt}\\
\textbf{\VAR{signer.nome} -- \VAR{signer.posto}}\BLOCK{ if signer.funcao }\\
\VAR{signer.funcao}\BLOCK{ endif }
\end{center}
\BLOCK{ endfor }
\BLOCK{ else }
\VAR{assinaturas.revisado_por_comment}
\BLOCK{ endif }

\vspace{1cm}
\noindent APROVO:
\BLOCK{ if assinaturas.aprovado_por }
\BLOCK{ for signer in assinaturas.aprovado_por }
\begin{center}
\vspace{1cm}
\rule{8cm}{0.4pt}\\
\textbf{\VAR{signer.nome} -- \VAR{signer.posto}}\BLOCK{ if signer.funcao }\\
\VAR{signer.funcao}\BLOCK{ endif }
\end{center}
\BLOCK{ endfor }
\BLOCK{ else }
\VAR{assinaturas.aprovado_por_comment}
\BLOCK{ endif }

\end{document}
"""

_env = Environment(
    variable_start_string="\\VAR{",
    variable_end_string="}",
    block_start_string="\\BLOCK{",
    block_end_string="}",
    comment_start_string="\\#{",
    comment_end_string="}",
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
)

_TEMPLATE = _env.from_string(REPORT_LATEX_TEMPLATE)

_DEFAULT_CONTEXT: dict[str, Any] = {
    "numero": "000",
    "ano": "",
    "tema": "",
    "capa_imagem": None,
    "finalidade": "[Seção ainda não gerada]",
    "objetivo": "[Seção ainda não gerada]",
    "introducao": "[Seção ainda não gerada]",
    "referencias_administrativas": [],
    "metodologia": "[Seção ainda não gerada]",
    "quadro_busca": None,
    "informacoes_cientificas": "[Seção ainda não gerada]",
    "informacoes_tecnologicas": "[Seção ainda não gerada]",
    "tendencias_ciclo_vida": "[Seção ainda não gerada]",
    "conclusao": "[Seção ainda não gerada]",
    "referencias_bibliograficas": [],
    "local_data": None,
    "assinaturas": {
        "elaborado_por": [{"nome": "", "posto": "", "funcao": ""}],
        "revisado_por": [],
        "revisado_por_comment": "% Revisado por: não informado",
        "aprovado_por": [],
        "aprovado_por_comment": "% Aprovado por: não informado",
    },
}


def render_report_latex(context: dict[str, Any]) -> str:
    merged = {**_DEFAULT_CONTEXT, **context}
    return _TEMPLATE.render(**merged)
