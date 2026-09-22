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
    metodologia: str - seção 5, já renderizada localmente (ver
        config/prompts/report_static_sections.py)
    quadro_busca: dict com patente_query/patente_count/artigo_query/artigo_count
    informacoes_cientificas, informacoes_tecnologicas, tendencias_ciclo_vida: str
        - subseções 6.1/6.2/6.3, seções de IA
    charts_cientificas, charts_tecnologicas, charts_ciclo_vida: list[dict]
        com {"filename": str, "caption": str} - gráficos já baixados do
        MinIO (ver ReportLatexService), agrupados por subseção de Resultados
    conclusao: str - seção 7, seção de IA
    referencias_bibliograficas: list[str] - seção 8, fixa + usuário
    assinaturas: dict com elaborado_por/revisado_por/aprovado_por, cada um
        uma LISTA de {"nome": str, "posto_funcao": str} (1+ assinantes por
        papel - ver ReportGeneration.tsx)
"""

from __future__ import annotations

from typing import Any

from jinja2 import Environment

REPORT_LATEX_TEMPLATE = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazil]{babel}
\usepackage[margin=2.5cm]{geometry}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{enumitem}

\title{}
\author{}
\date{}

\begin{document}

\begin{titlepage}
    \centering
    \vspace*{2cm}
    \BLOCK{ if capa_imagem }
    \includegraphics[width=4cm]{\VAR{capa_imagem}}
    \vspace{1cm}
    \BLOCK{ endif }
    {\LARGE\bfseries RELATÓRIO DE PROSPECÇÃO TECNOLÓGICA\par}
    \vspace{0.5cm}
    {\Large \VAR{numero}/\VAR{ano} -- AGITEC\par}
    \vspace{1.5cm}
    {\Large \VAR{tema}\par}
    \vfill
\end{titlepage}

\tableofcontents
\newpage

\section{Finalidade}
\VAR{finalidade}

\section{Referências}
\BLOCK{ if referencias_administrativas }
\begin{itemize}[leftmargin=*]
\BLOCK{ for ref in referencias_administrativas }
    \item \VAR{ref}
\BLOCK{ endfor }
\end{itemize}
\BLOCK{ else }
Nenhuma referência administrativa informada.
\BLOCK{ endif }

\section{Objetivo}
\VAR{objetivo}

\section{Introdução}
\VAR{introducao}

\section{Metodologia}
\VAR{metodologia}

\section{Resultados}

\BLOCK{ if quadro_busca }
\begin{itemize}[leftmargin=*]
\VAR{quadro_busca.patente_line}
\VAR{quadro_busca.artigo_line}
\end{itemize}
\BLOCK{ endif }

\subsection{Informações Científicas}
\VAR{informacoes_cientificas}

\BLOCK{ for chart in charts_cientificas }
\begin{center}
\includegraphics[width=0.85\textwidth]{\VAR{chart.filename}}
\end{center}
\begin{center}\small \VAR{chart.caption}\end{center}
\BLOCK{ endfor }

\subsection{Informações Tecnológicas}
\VAR{informacoes_tecnologicas}

\BLOCK{ for chart in charts_tecnologicas }
\begin{center}
\includegraphics[width=0.85\textwidth]{\VAR{chart.filename}}
\end{center}
\begin{center}\small \VAR{chart.caption}\end{center}
\BLOCK{ endfor }

\subsection{Tendências e Ciclo de Vida da Tecnologia}
\VAR{tendencias_ciclo_vida}

\BLOCK{ for chart in charts_ciclo_vida }
\begin{center}
\includegraphics[width=0.85\textwidth]{\VAR{chart.filename}}
\end{center}
\begin{center}\small \VAR{chart.caption}\end{center}
\BLOCK{ endfor }

\section{Conclusão}
\VAR{conclusao}

\section{Referências Bibliográficas}
\BLOCK{ if referencias_bibliograficas }
\begin{enumerate}[leftmargin=*]
\BLOCK{ for ref in referencias_bibliograficas }
    \item \VAR{ref}
\BLOCK{ endfor }
\end{enumerate}
\BLOCK{ else }
Nenhuma referência bibliográfica informada.
\BLOCK{ endif }

\vspace{2cm}
\noindent Elaborado por:
\BLOCK{ for signer in assinaturas.elaborado_por }
\vspace{0.5cm}\\[1cm]
\noindent\rule{8cm}{0.4pt}\\
\VAR{signer.nome}\\
\VAR{signer.posto_funcao}
\BLOCK{ endfor }

\vspace{1cm}
\noindent Revisado por:
\BLOCK{ if assinaturas.revisado_por }
\BLOCK{ for signer in assinaturas.revisado_por }
\vspace{0.5cm}\\[1cm]
\noindent\rule{8cm}{0.4pt}\\
\VAR{signer.nome}\\
\VAR{signer.posto_funcao}
\BLOCK{ endfor }
\BLOCK{ else }
\VAR{assinaturas.revisado_por_comment}
\BLOCK{ endif }

\vspace{1cm}
\noindent Aprovo:
\BLOCK{ if assinaturas.aprovado_por }
\BLOCK{ for signer in assinaturas.aprovado_por }
\vspace{0.5cm}\\[1cm]
\noindent\rule{8cm}{0.4pt}\\
\VAR{signer.nome}\\
\VAR{signer.posto_funcao}
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
    "charts_cientificas": [],
    "charts_tecnologicas": [],
    "charts_ciclo_vida": [],
    "conclusao": "[Seção ainda não gerada]",
    "referencias_bibliograficas": [],
    "assinaturas": {
        "elaborado_por": [{"nome": "", "posto_funcao": ""}],
        "revisado_por": [],
        "revisado_por_comment": "% Revisado por: não informado",
        "aprovado_por": [],
        "aprovado_por_comment": "% Aprovado por: não informado",
    },
}


def render_report_latex(context: dict[str, Any]) -> str:
    merged = {**_DEFAULT_CONTEXT, **context}
    return _TEMPLATE.render(**merged)
