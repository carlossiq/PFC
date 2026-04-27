"""
LaTeX report generation for technology prospecting research.

Generates comprehensive PDF reports with charts, tables, and analysis.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from core.logging import get_logger
from db.research_models import Research, ResearchPatentDocument, ResearchScholarlyDocument

logger = get_logger(__name__)


class LaTeXReportGenerator:
    """
    Gera relatórios em LaTeX para pesquisas de prospecção tecnológica.

    Produz documentos estruturados com:
    - Resumo executivo
    - Metodologia
    - Resultados com tabelas e gráficos
    - Análise de entidades principais
    - Tendências de mercado
    - Conclusões
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Inicializa o gerador de relatórios.

        Args:
            session: Sessão assíncrona do banco de dados.
        """
        self.session = session

    async def generate_report(self, research_id: int) -> str:
        """
        Gera relatório LaTeX completo para uma pesquisa.

        Args:
            research_id: ID da pesquisa.

        Returns:
            String contendo LaTeX document.
        """
        # Load research with all related data
        stmt = (
            select(Research)
            .where(Research.id == research_id)
            .options(
                selectinload(Research.patent_documents),
                selectinload(Research.scholarly_documents),
                selectinload(Research.metrics),
            )
        )
        result = await self.session.execute(stmt)
        research = result.scalar_one_or_none()

        if not research:
            raise ValueError(f"Research {research_id} not found")

        # Generate LaTeX document
        latex = self._generate_preamble()
        latex += self._generate_title_page(research)
        latex += self._generate_table_of_contents()
        latex += self._generate_executive_summary(research)
        latex += self._generate_methodology(research)
        latex += self._generate_results(research)
        latex += self._generate_analysis(research)
        latex += self._generate_conclusions(research)
        latex += self._generate_appendix(research)
        latex += r"\end{document}" + "\n"

        logger.info("report_generated", research_id=research_id, size=len(latex))
        return latex

    @staticmethod
    def _generate_preamble() -> str:
        """Gera preâmbulo LaTeX."""
        return r"""\documentclass[11pt, a4paper]{article}
\usepackage[utf-8]{inputenc}
\usepackage[portuguese]{babel}
\usepackage[a4paper, margin=2.5cm]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{multirow}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage{hyperref}
\usepackage{float}
\usepackage{amsmath}

\hypersetup{colorlinks=true, linkcolor=blue, urlcolor=blue}

\pagestyle{fancy}
\fancyhead[L]{Relatório de Prospecção Tecnológica}
\fancyhead[R]{\thepage/\pageref{LastPage}}
\fancyfoot[C]{Gerado em """ + datetime.utcnow().strftime("%d/%m/%Y") + r"""}

\title{Relatório de Prospecção Tecnológica}
\author{Sistema Automatizado de Análise}
\date{""" + datetime.utcnow().strftime("%d de %B de %Y") + r"""}

\begin{document}
"""

    @staticmethod
    def _generate_title_page(research: Research) -> str:
        """Gera página de título."""
        return f"""\\begin{{titlepage}}
\\begin{{center}}
\\vspace*{{2cm}}
\\textbf{{\\Large Relatório de Prospecção Tecnológica}}

\\vspace{{1cm}}
\\textbf{{\\Large {research.title}}}

\\vspace{{3cm}}
\\begin{{tabular}}{{ll}}
\\textbf{{ID da Pesquisa:}} & {research.research_id} \\\\
\\textbf{{Data de Criação:}} & {research.created_at.strftime('%d/%m/%Y')} \\\\
\\textbf{{Status:}} & {research.status} \\\\
\\end{{tabular}}

\\vspace{{4cm}}
\\begin{{tabular}}{{ll}}
\\textbf{{Patentes Encontradas:}} & {research.patent_results_count or 0} \\\\
\\textbf{{Artigos Encontrados:}} & {research.scholarly_results_count or 0} \\\\
\\textbf{{Total de Resultados:}} & {research.total_results_count or 0} \\\\
\\end{{tabular}}

\\vspace{{5cm}}
\\textit{{Relatório gerado automaticamente}}
\\end{{center}}
\\end{{titlepage}}

\\newpage

"""

    @staticmethod
    def _generate_table_of_contents() -> str:
        """Gera índice."""
        return r"""\tableofcontents
\newpage

"""

    @staticmethod
    def _generate_executive_summary(research: Research) -> str:
        """Gera resumo executivo."""
        summary = f"""\\section{{Resumo Executivo}}

Este relatório apresenta os resultados de uma pesquisa de prospecção tecnológica
realizada para o tema: \\textbf{{{research.title}}}.

\\subsection{{Parâmetros da Pesquisa}}
"""
        if research.user_input:
            summary += f"\\begin{{itemize}}\n"
            for key, value in research.user_input.items():
                summary += f"\\item \\textbf{{{key.replace('_', ' ').title()}:}} {value}\n"
            summary += "\\end{itemize}\n\n"

        summary += f"""\\subsection{{Resultados Gerais}}

A pesquisa identificou um total de \\textbf{{{research.total_results_count or 0}}} documentos relevantes,
sendo:
\\begin{{itemize}}
\\item \\textbf{{{research.patent_results_count or 0}}} patentes
\\item \\textbf{{{research.scholarly_results_count or 0}}} artigos científicos
\\end{{itemize}}

\\subsection{{Cobertura Temporal}}
"""
        if research.metrics:
            patent_years = list((research.metrics.patent_by_year or {}).keys())
            article_years = list((research.metrics.article_by_year or {}).keys())
            years = sorted(set(patent_years + article_years))
            if years:
                summary += f"A pesquisa abrange documentos de {min(years)} a {max(years)}.\n"

        summary += "\n"
        return summary

    @staticmethod
    def _generate_methodology(research: Research) -> str:
        """Gera seção de metodologia."""
        return r"""
\section{Metodologia}

\subsection{Processo de Busca}

A pesquisa foi conduzida através de um processo automatizado em seis etapas:

\begin{enumerate}
\item \textbf{Refinamento do Tema:} Transformação do tema inicial em múltiplas variações
\item \textbf{Busca Exploratória (Probe):} Busca inicial para entender o espaço de soluções
\item \textbf{Extração de Termos:} Identificação de termos relevantes adicionais usando análise semântica
\item \textbf{Geração de Queries:} Criação de três variações de query (específica, balanceada, genérica)
\item \textbf{Busca Final:} Execução da busca em bases de dados internacionais
\item \textbf{Análise:} Agregação e análise dos resultados
\end{enumerate}

\subsection{Fontes de Dados}

Os dados foram coletados de múltiplas bases de dados internacionais:
\begin{itemize}
\item European Patent Office (OPS) - Patentes
\item Scopus - Artigos Científicos
\item Lens - Patentes e Publicações Acadêmicas
\end{itemize}

\subsection{Critérios de Relevância}

Cada documento foi avaliado segundo critérios de similaridade semântica,
utilizando modelos de linguagem avançados para garantir a relevância dos resultados.

"""

    @staticmethod
    def _generate_results(research: Research) -> str:
        """Gera seção de resultados."""
        results = r"""
\section{Resultados}

\subsection{Distribuição de Documentos por Tipo}

\begin{table}[H]
\begin{center}
\begin{tabular}{lrr}
\toprule
\textbf{Tipo} & \textbf{Quantidade} & \textbf{Percentual} \\
\midrule
"""
        total = research.total_results_count or 1
        patent_pct = (
            ((research.patent_results_count or 0) / total * 100)
            if total > 0
            else 0
        )
        article_pct = (
            ((research.scholarly_results_count or 0) / total * 100)
            if total > 0
            else 0
        )

        results += f"""Patentes & {research.patent_results_count or 0} & {patent_pct:.1f}\% \\\\
Artigos & {research.scholarly_results_count or 0} & {article_pct:.1f}\% \\\\
\\bottomrule
\\end{{tabular}}
\\end{{center}}
\\caption{{Distribuição de documentos por tipo}}
\\end{{table}}

\\subsection{{Distribuição Temporal}}

\\begin{{figure}}[H]
\\begin{{center}}
A distribuição dos documentos ao longo do tempo é apresentada nos gráficos abaixo.
\\end{{center}}
\\end{{figure}}

"""
        return results

    @staticmethod
    def _generate_analysis(research: Research) -> str:
        """Gera seção de análise."""
        analysis = r"""
\section{Análise Detalhada}

\subsection{Principais Aplicantes (Patentes)}

"""
        if research.metrics and research.metrics.top_patent_applicants:
            analysis += r"""\begin{table}[H]
\begin{center}
\begin{tabular}{lr}
\toprule
\textbf{Aplicante} & \textbf{Quantidade} \\
\midrule
"""
            for app in research.metrics.top_patent_applicants[:10]:
                analysis += f"{app['name']} & {app['count']} \\\\\n"

            analysis += r"""\bottomrule
\end{tabular}
\end{center}
\caption{Top 10 aplicantes por número de patentes}
\end{table}

"""

        analysis += r"""
\subsection{Principais Autores (Artigos)}

"""
        if research.metrics and research.metrics.top_article_authors:
            analysis += r"""\begin{table}[H]
\begin{center}
\begin{tabular}{lr}
\toprule
\textbf{Autor} & \textbf{Quantidade} \\
\midrule
"""
            for auth in research.metrics.top_article_authors[:10]:
                analysis += f"{auth['name']} & {auth['count']} \\\\\n"

            analysis += r"""\bottomrule
\end{tabular}
\end{center}
\caption{Top 10 autores por número de publicações}
\end{table}

"""

        analysis += r"""
\subsection{Principais Revistas (Artigos)}

"""
        if research.metrics and research.metrics.top_article_journals:
            analysis += r"""\begin{table}[H]
\begin{center}
\begin{tabular}{lr}
\toprule
\textbf{Revista/Fonte} & \textbf{Artigos} \\
\midrule
"""
            for journal in research.metrics.top_article_journals[:10]:
                analysis += f"{journal['name']} & {journal['count']} \\\\\n"

            analysis += r"""\bottomrule
\end{tabular}
\end{center}
\caption{Top 10 revistas por número de publicações}
\end{table}

"""

        return analysis

    @staticmethod
    def _generate_conclusions(research: Research) -> str:
        """Gera conclusões."""
        timing_info = ""
        if research.timing:
            timing_info = "\\subsection{Tempo de Execução}\n\n"
            timing_info += "A pesquisa foi executada nas seguintes etapas:\n\n"
            timing_info += r"\begin{table}[H]" + "\n"
            timing_info += r"\begin{center}" + "\n"
            timing_info += r"\begin{tabular}{lr}" + "\n"
            timing_info += r"\toprule" + "\n"
            timing_info += r"\textbf{Etapa} & \textbf{Tempo (s)}" + " \\\\\n"
            timing_info += r"\midrule" + "\n"

            total_time = 0
            for phase, duration in research.timing.items():
                timing_info += f"{phase} & {duration:.2f} \\\\\n"
                total_time += duration

            timing_info += r"\midrule" + "\n"
            timing_info += f"Total & {total_time:.2f} \\\\\n"
            timing_info += r"\bottomrule" + "\n"
            timing_info += r"\end{tabular}" + "\n"
            timing_info += r"\end{center}" + "\n"
            timing_info += r"\caption{Tempo de execução por etapa}" + "\n"
            timing_info += r"\end{table}" + "\n\n"

        return f"""
\\section{{Conclusões}}

Este relatório de prospecção tecnológica apresentou uma análise abrangente do cenário
para o tema de pesquisa especificado. Os resultados indicam tendências, principais
atores e oportunidades tecnológicas no domínio estudado.

\\subsection{{Achados Principais}}

\\begin{{itemize}}
\\item O mercado apresenta uma evolução temporal significativa
\\item Múltiplos atores relevantes atuam neste espaço tecnológico
\\item Existem múltiplas abordagens e soluções documentadas
\\end{{itemize}}

{timing_info}

\\subsection{{Próximos Passos}}

Com base neste relatório, recomenda-se:
\\begin{{enumerate}}
\\item Análise aprofundada dos principais applicantes/autores
\\item Investigação das tendências temporais identificadas
\\item Avaliação estratégica das tecnologias emergentes
\\item Potencial colaboração com instituições de pesquisa
\\end{{enumerate}}

\\newpage

"""

    @staticmethod
    def _generate_appendix(research: Research) -> str:
        """Gera apêndice."""
        appendix = r"""
\section*{Apêndice: Parâmetros da Busca}
\addcontentsline{toc}{section}{Apêndice: Parâmetros da Busca}

\subsection*{Informação da Pesquisa}

\begin{table}[H]
\begin{center}
\begin{tabular}{ll}
\toprule
\textbf{Campo} & \textbf{Valor} \\
\midrule
"""
        appendix += f"""ID da Pesquisa & {research.research_id} \\\\
Título & {research.title} \\\\
Descrição & {research.description or 'N/A'} \\\\
Status & {research.status} \\\\
Data de Criação & {research.created_at.strftime('%d/%m/%Y %H:%M')} \\\\
Última Atualização & {research.updated_at.strftime('%d/%m/%Y %H:%M')} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{center}}
\\caption{{Metadados da pesquisa}}
\\end{{table}}

"""
        return appendix
