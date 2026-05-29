from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ReportService:
    """
    Geração de relatórios LaTeX e mapeamento de dados de pesquisa.

    Recebe dicts puros (sem dependências de ORM ou bibliotecas externas).
    """

    # ------------------------------------------------------------------
    # Geração de LaTeX
    # ------------------------------------------------------------------

    def generate_latex(self, report_data: dict[str, Any]) -> str:
        """
        Gera documento LaTeX completo a partir de dados de pesquisa.

        Args:
            report_data: Dict com as chaves: theme, description, research_id,
                created_at, status, patent_results_count, scholarly_results_count,
                total_results_count, user_input, metrics, timing.
        """
        latex = self._preamble()
        latex += self._title_page(report_data)
        latex += self._table_of_contents()
        latex += self._executive_summary(report_data)
        latex += self._methodology()
        latex += self._results(report_data)
        latex += self._analysis(report_data)
        latex += self._conclusions(report_data)
        latex += self._appendix(report_data)
        latex += r"\end{document}" + "\n"

        logger.info("latex_generated theme=%s size=%d", report_data.get("theme"), len(latex))
        return latex

    @staticmethod
    def _preamble() -> str:
        return (
            r"\documentclass[11pt, a4paper]{article}" + "\n"
            r"\usepackage[utf-8]{inputenc}" + "\n"
            r"\usepackage[portuguese]{babel}" + "\n"
            r"\usepackage[a4paper, margin=2.5cm]{geometry}" + "\n"
            r"\usepackage{graphicx}" + "\n"
            r"\usepackage{booktabs}" + "\n"
            r"\usepackage{array}" + "\n"
            r"\usepackage{multirow}" + "\n"
            r"\usepackage{xcolor}" + "\n"
            r"\usepackage{fancyhdr}" + "\n"
            r"\usepackage{lastpage}" + "\n"
            r"\usepackage{hyperref}" + "\n"
            r"\usepackage{float}" + "\n"
            r"\usepackage{amsmath}" + "\n"
            "\n"
            r"\hypersetup{colorlinks=true, linkcolor=blue, urlcolor=blue}" + "\n"
            "\n"
            r"\pagestyle{fancy}" + "\n"
            r"\fancyhead[L]{Relat\'{o}rio de Prospec\c{c}\~{a}o Tecnol\'{o}gica}" + "\n"
            r"\fancyhead[R]{\thepage/\pageref{LastPage}}" + "\n"
            r"\fancyfoot[C]{Gerado em " + datetime.utcnow().strftime("%d/%m/%Y") + r"}" + "\n"
            "\n"
            r"\begin{document}" + "\n"
        )

    @staticmethod
    def _title_page(data: dict[str, Any]) -> str:
        theme = data.get("theme", "")
        research_id = data.get("research_id", "")
        created_at = data.get("created_at", "")
        status = data.get("status", "")
        patents = data.get("patent_results_count", 0) or 0
        scholarly = data.get("scholarly_results_count", 0) or 0
        total = data.get("total_results_count", 0) or 0

        return (
            r"\begin{titlepage}" + "\n"
            r"\begin{center}" + "\n"
            r"\vspace*{2cm}" + "\n"
            r"\textbf{\Large Relat\'{o}rio de Prospec\c{c}\~{a}o Tecnol\'{o}gica}" + "\n\n"
            r"\vspace{1cm}" + "\n"
            f"\\textbf{{\\Large {theme}}}\n\n"
            r"\vspace{3cm}" + "\n"
            r"\begin{tabular}{ll}" + "\n"
            f"\\textbf{{ID da Pesquisa:}} & {research_id} \\\\\n"
            f"\\textbf{{Data de Cria\\c{{c}}\\~{{a}}o:}} & {created_at} \\\\\n"
            f"\\textbf{{Status:}} & {status} \\\\\n"
            r"\end{tabular}" + "\n\n"
            r"\vspace{4cm}" + "\n"
            r"\begin{tabular}{ll}" + "\n"
            f"\\textbf{{Patentes Encontradas:}} & {patents} \\\\\n"
            f"\\textbf{{Artigos Encontrados:}} & {scholarly} \\\\\n"
            f"\\textbf{{Total de Resultados:}} & {total} \\\\\n"
            r"\end{tabular}" + "\n\n"
            r"\vspace{5cm}" + "\n"
            r"\textit{Relat\'{o}rio gerado automaticamente}" + "\n"
            r"\end{center}" + "\n"
            r"\end{titlepage}" + "\n\n"
            r"\newpage" + "\n\n"
        )

    @staticmethod
    def _table_of_contents() -> str:
        return r"\tableofcontents" + "\n" + r"\newpage" + "\n\n"

    @staticmethod
    def _executive_summary(data: dict[str, Any]) -> str:
        theme = data.get("theme", "")
        patents = data.get("patent_results_count", 0) or 0
        scholarly = data.get("scholarly_results_count", 0) or 0
        total = data.get("total_results_count", 0) or 0
        user_input: dict[str, Any] = data.get("user_input") or {}
        metrics: dict[str, Any] = data.get("metrics") or {}

        body = (
            r"\section{Resumo Executivo}" + "\n\n"
            f"Este relat\\'orio apresenta os resultados de uma pesquisa de prospec\\'c\\'ao tecnol\\'ogica"
            f" realizada para o tema: \\textbf{{{theme}}}.\n\n"
            r"\subsection{Par\^{a}metros da Pesquisa}" + "\n"
        )

        if user_input:
            body += r"\begin{itemize}" + "\n"
            for key, value in user_input.items():
                body += f"\\item \\textbf{{{key.replace('_', ' ').title()}:}} {value}\n"
            body += r"\end{itemize}" + "\n\n"

        body += (
            r"\subsection{Resultados Gerais}" + "\n\n"
            f"A pesquisa identificou um total de \\textbf{{{total}}} documentos relevantes, sendo:\n"
            r"\begin{itemize}" + "\n"
            f"\\item \\textbf{{{patents}}} patentes\n"
            f"\\item \\textbf{{{scholarly}}} artigos cient\\'ificos\n"
            r"\end{itemize}" + "\n\n"
            r"\subsection{Cobertura Temporal}" + "\n"
        )

        patent_years = list((metrics.get("patent_by_year") or {}).keys())
        article_years = list((metrics.get("article_by_year") or {}).keys())
        years = sorted(set(patent_years + article_years))
        if years:
            body += f"A pesquisa abrange documentos de {min(years)} a {max(years)}.\n"

        return body + "\n"

    @staticmethod
    def _methodology() -> str:
        return (
            "\n"
            r"\section{Metodologia}" + "\n\n"
            r"\subsection{Processo de Busca}" + "\n\n"
            r"A pesquisa foi conduzida atrav\'{e}s de um processo automatizado em seis etapas:" + "\n\n"
            r"\begin{enumerate}" + "\n"
            r"\item \textbf{Refinamento do Tema:} Transforma\c{c}\~{a}o do tema inicial em m\'{u}ltiplas varia\c{c}\~{o}es" + "\n"
            r"\item \textbf{Busca Explorat\'{o}ria (Probe):} Busca inicial para entender o espa\c{c}o de solu\c{c}\~{o}es" + "\n"
            r"\item \textbf{Extra\c{c}\~{a}o de Termos:} Identifica\c{c}\~{a}o de termos relevantes adicionais usando an\'{a}lise sem\^{a}ntica" + "\n"
            r"\item \textbf{Gera\c{c}\~{a}o de Queries:} Cria\c{c}\~{a}o de tr\^{e}s varia\c{c}\~{o}es de query (espec\'{i}fica, balanceada, gen\'{e}rica)" + "\n"
            r"\item \textbf{Busca Final:} Execu\c{c}\~{a}o da busca em bases de dados internacionais" + "\n"
            r"\item \textbf{An\'{a}lise:} Agrega\c{c}\~{a}o e an\'{a}lise dos resultados" + "\n"
            r"\end{enumerate}" + "\n\n"
            r"\subsection{Fontes de Dados}" + "\n\n"
            r"\begin{itemize}" + "\n"
            r"\item European Patent Office (OPS) - Patentes" + "\n"
            r"\item Scopus - Artigos Cient\'{i}ficos" + "\n"
            r"\item Lens - Patentes e Publica\c{c}\~{o}es Acad\^{e}micas" + "\n"
            r"\end{itemize}" + "\n\n"
        )

    @staticmethod
    def _results(data: dict[str, Any]) -> str:
        patents = data.get("patent_results_count", 0) or 0
        scholarly = data.get("scholarly_results_count", 0) or 0
        total = data.get("total_results_count", 1) or 1
        patent_pct = (patents / total * 100) if total > 0 else 0
        article_pct = (scholarly / total * 100) if total > 0 else 0

        return (
            "\n"
            r"\section{Resultados}" + "\n\n"
            r"\subsection{Distribui\c{c}\~{a}o de Documentos por Tipo}" + "\n\n"
            r"\begin{table}[H]" + "\n"
            r"\begin{center}" + "\n"
            r"\begin{tabular}{lrr}" + "\n"
            r"\toprule" + "\n"
            r"\textbf{Tipo} & \textbf{Quantidade} & \textbf{Percentual} \\" + "\n"
            r"\midrule" + "\n"
            f"Patentes & {patents} & {patent_pct:.1f}\\% \\\\\n"
            f"Artigos & {scholarly} & {article_pct:.1f}\\% \\\\\n"
            r"\bottomrule" + "\n"
            r"\end{tabular}" + "\n"
            r"\end{center}" + "\n"
            r"\caption{Distribui\c{c}\~{a}o de documentos por tipo}" + "\n"
            r"\end{table}" + "\n\n"
        )

    @staticmethod
    def _analysis(data: dict[str, Any]) -> str:
        metrics: dict[str, Any] = data.get("metrics") or {}
        top_applicants: list[dict] = metrics.get("top_patent_applicants") or []
        top_authors: list[dict] = metrics.get("top_article_authors") or []
        top_journals: list[dict] = metrics.get("top_article_journals") or []

        body = "\n" + r"\section{An\'{a}lise Detalhada}" + "\n\n"

        body += r"\subsection{Principais Aplicantes (Patentes)}" + "\n\n"
        if top_applicants:
            body += (
                r"\begin{table}[H]" + "\n"
                r"\begin{center}" + "\n"
                r"\begin{tabular}{lr}" + "\n"
                r"\toprule" + "\n"
                r"\textbf{Aplicante} & \textbf{Quantidade} \\" + "\n"
                r"\midrule" + "\n"
            )
            for app in top_applicants[:10]:
                body += f"{app.get('name', '')} & {app.get('count', 0)} \\\\\n"
            body += (
                r"\bottomrule" + "\n"
                r"\end{tabular}" + "\n"
                r"\end{center}" + "\n"
                r"\caption{Top 10 aplicantes por n\'{u}mero de patentes}" + "\n"
                r"\end{table}" + "\n\n"
            )

        body += r"\subsection{Principais Autores (Artigos)}" + "\n\n"
        if top_authors:
            body += (
                r"\begin{table}[H]" + "\n"
                r"\begin{center}" + "\n"
                r"\begin{tabular}{lr}" + "\n"
                r"\toprule" + "\n"
                r"\textbf{Autor} & \textbf{Quantidade} \\" + "\n"
                r"\midrule" + "\n"
            )
            for auth in top_authors[:10]:
                body += f"{auth.get('name', '')} & {auth.get('count', 0)} \\\\\n"
            body += (
                r"\bottomrule" + "\n"
                r"\end{tabular}" + "\n"
                r"\end{center}" + "\n"
                r"\caption{Top 10 autores por n\'{u}mero de publica\c{c}\~{o}es}" + "\n"
                r"\end{table}" + "\n\n"
            )

        body += r"\subsection{Principais Revistas (Artigos)}" + "\n\n"
        if top_journals:
            body += (
                r"\begin{table}[H]" + "\n"
                r"\begin{center}" + "\n"
                r"\begin{tabular}{lr}" + "\n"
                r"\toprule" + "\n"
                r"\textbf{Revista/Fonte} & \textbf{Artigos} \\" + "\n"
                r"\midrule" + "\n"
            )
            for journal in top_journals[:10]:
                body += f"{journal.get('name', '')} & {journal.get('count', 0)} \\\\\n"
            body += (
                r"\bottomrule" + "\n"
                r"\end{tabular}" + "\n"
                r"\end{center}" + "\n"
                r"\caption{Top 10 revistas por n\'{u}mero de publica\c{c}\~{o}es}" + "\n"
                r"\end{table}" + "\n\n"
            )

        return body

    @staticmethod
    def _conclusions(data: dict[str, Any]) -> str:
        timing: dict[str, float] = data.get("timing") or {}
        timing_section = ""

        if timing:
            timing_section = (
                r"\subsection{Tempo de Execu\c{c}\~{a}o}" + "\n\n"
                r"\begin{table}[H]" + "\n"
                r"\begin{center}" + "\n"
                r"\begin{tabular}{lr}" + "\n"
                r"\toprule" + "\n"
                r"\textbf{Etapa} & \textbf{Tempo (s)} \\" + "\n"
                r"\midrule" + "\n"
            )
            total_time = 0.0
            for phase, duration in timing.items():
                timing_section += f"{phase} & {duration:.2f} \\\\\n"
                total_time += duration
            timing_section += (
                r"\midrule" + "\n"
                f"Total & {total_time:.2f} \\\\\n"
                r"\bottomrule" + "\n"
                r"\end{tabular}" + "\n"
                r"\end{center}" + "\n"
                r"\caption{Tempo de execu\c{c}\~{a}o por etapa}" + "\n"
                r"\end{table}" + "\n\n"
            )

        return (
            "\n"
            r"\section{Conclus\~{o}es}" + "\n\n"
            r"Este relat\'{o}rio de prospec\c{c}\~{a}o tecnol\'{o}gica apresentou uma an\'{a}lise abrangente do cen\'{a}rio"
            r" para o tema de pesquisa especificado." + "\n\n"
            r"\subsection{Achados Principais}" + "\n\n"
            r"\begin{itemize}" + "\n"
            r"\item O mercado apresenta uma evolu\c{c}\~{a}o temporal significativa" + "\n"
            r"\item M\'{u}ltiplos atores relevantes atuam neste espa\c{c}o tecnol\'{o}gico" + "\n"
            r"\item Existem m\'{u}ltiplas abordagens e solu\c{c}\~{o}es documentadas" + "\n"
            r"\end{itemize}" + "\n\n"
            + timing_section
            + r"\newpage" + "\n\n"
        )

    @staticmethod
    def _appendix(data: dict[str, Any]) -> str:
        research_id = data.get("research_id", "")
        theme = data.get("theme", "")
        description = data.get("description") or "N/A"
        status = data.get("status", "")
        created_at = data.get("created_at", "")
        updated_at = data.get("updated_at", "")

        return (
            "\n"
            r"\section*{Ap\^{e}ndice: Par\^{a}metros da Busca}" + "\n"
            r"\addcontentsline{toc}{section}{Ap\^{e}ndice: Par\^{a}metros da Busca}" + "\n\n"
            r"\begin{table}[H]" + "\n"
            r"\begin{center}" + "\n"
            r"\begin{tabular}{ll}" + "\n"
            r"\toprule" + "\n"
            r"\textbf{Campo} & \textbf{Valor} \\" + "\n"
            r"\midrule" + "\n"
            f"ID da Pesquisa & {research_id} \\\\\n"
            f"T\\'itulo & {theme} \\\\\n"
            f"Descri\\'c\\'ao & {description} \\\\\n"
            f"Status & {status} \\\\\n"
            f"Data de Cria\\'c\\'ao & {created_at} \\\\\n"
            f"\\'Ultima Atualiza\\'c\\'ao & {updated_at} \\\\\n"
            r"\bottomrule" + "\n"
            r"\end{tabular}" + "\n"
            r"\end{center}" + "\n"
            r"\caption{Metadados da pesquisa}" + "\n"
            r"\end{table}" + "\n\n"
        )

    # ------------------------------------------------------------------
    # Mapeamento de dados de pesquisa
    # ------------------------------------------------------------------

    def map_research_data(
        self,
        research: dict[str, Any],
        patents: list[dict[str, Any]],
        articles: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Consolida dados de pesquisa (pesquisa + patentes + artigos) no formato
        esperado por generate_latex.
        """
        patent_data = self._extract_patent_data(patents)
        article_data = self._extract_article_data(articles)
        metrics_data = self._extract_metrics(research)

        chosen: dict[str, Any] = research.get("chosen_candidate") or {}
        user_input: dict[str, Any] = research.get("user_input") or {}

        result = {
            **research,
            "area_of_study": chosen.get("area_of_study", ""),
            "keywords": chosen.get("keywords", []),
            "period_start": user_input.get("period_start"),
            "period_end": user_input.get("period_end"),
            "apis_used": self._get_apis_used(research),
            "patent_data": patent_data,
            "scientific_data": article_data,
            "metrics": {**metrics_data, **patent_data, **article_data},
            "s_curve_data": self._extract_s_curve(research),
        }

        logger.info(
            "research_data_mapped research_id=%s patents=%d articles=%d",
            research.get("research_id"),
            len(patents),
            len(articles),
        )
        return result

    @staticmethod
    def _extract_patent_data(patents: list[dict[str, Any]]) -> dict[str, Any]:
        by_year: dict[str, int] = {}
        applicants: dict[str, int] = {}
        cpcs: dict[str, int] = {}
        inventors: dict[str, int] = {}

        for p in patents:
            year = p.get("year")
            if year:
                by_year[str(year)] = by_year.get(str(year), 0) + 1
            for app in p.get("applicants") or []:
                applicants[app] = applicants.get(app, 0) + 1
            for cpc in p.get("cpc_codes") or []:
                cpcs[cpc] = cpcs.get(cpc, 0) + 1
            for inv in p.get("inventors") or []:
                inventors[inv] = inventors.get(inv, 0) + 1

        top_applicants = sorted(applicants.items(), key=lambda x: x[1], reverse=True)[:10]
        top_cpcs = sorted(cpcs.items(), key=lambda x: x[1], reverse=True)[:10]
        top_inventors = sorted(inventors.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "patent_count": len(patents),
            "patent_by_year": by_year,
            "top_patent_applicants": [{"name": n, "count": c} for n, c in top_applicants],
            "top_inventors": [{"name": n, "count": c} for n, c in top_inventors],
            "top_cpc_codes": [cpc[0] for cpc in top_cpcs],
            "cpc_distribution": {cpc[0]: cpc[1] for cpc in top_cpcs},
        }

    @staticmethod
    def _extract_article_data(articles: list[dict[str, Any]]) -> dict[str, Any]:
        by_year: dict[str, int] = {}
        journals: dict[str, int] = {}
        fields: dict[str, int] = {}
        authors: dict[str, int] = {}
        citations_total = 0

        for a in articles:
            year = a.get("year")
            if year:
                by_year[str(year)] = by_year.get(str(year), 0) + 1
            journal = a.get("journal_or_source")
            if journal:
                journals[journal] = journals.get(journal, 0) + 1
            for f in a.get("field_of_study") or []:
                fields[f] = fields.get(f, 0) + 1
            for auth in a.get("authors") or []:
                authors[auth] = authors.get(auth, 0) + 1
            citations_total += a.get("citations") or 0

        top_journals = sorted(journals.items(), key=lambda x: x[1], reverse=True)[:10]
        top_fields = sorted(fields.items(), key=lambda x: x[1], reverse=True)[:10]
        top_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:10]
        avg_citations = (citations_total / len(articles)) if articles else 0.0

        return {
            "article_count": len(articles),
            "article_by_year": by_year,
            "top_article_journals": [{"name": j, "count": c} for j, c in top_journals],
            "top_article_authors": [{"name": a, "count": c} for a, c in top_authors],
            "top_fields": [f[0] for f in top_fields],
            "field_distribution": {f[0]: f[1] for f in top_fields},
            "citations": {"total": citations_total, "average": round(avg_citations, 2)},
        }

    @staticmethod
    def _extract_metrics(research: dict[str, Any]) -> dict[str, Any]:
        metrics = research.get("metrics") or {}
        if not metrics:
            return {}
        return {
            "patent_by_applicant": metrics.get("patent_by_applicant") or {},
            "patent_by_ipc": metrics.get("patent_by_ipc") or {},
            "patent_by_legal_status": metrics.get("patent_by_legal_status") or {},
            "article_by_journal": metrics.get("article_by_journal") or {},
            "article_by_field": metrics.get("article_by_field") or {},
            "patent_growth_trend": metrics.get("patent_growth_trend") or {},
            "article_growth_trend": metrics.get("article_growth_trend") or {},
        }

    @staticmethod
    def _extract_s_curve(research: dict[str, Any]) -> dict[str, Any]:
        metrics = research.get("metrics") or {}
        trend = (metrics.get("patent_growth_trend") or {})
        if not trend:
            return {}
        growth_rate = trend.get("growth_rate", 0)
        if growth_rate > 0.2:
            phase = "GROWTH"
        elif growth_rate > 0.05:
            phase = "EMERGING"
        elif growth_rate > -0.05:
            phase = "MATURITY"
        else:
            phase = "DECLINE"
        return {
            "phase": phase,
            "growth_rate": round(growth_rate, 3),
            "peak_year": trend.get("peak_year"),
            "trend": trend,
        }

    @staticmethod
    def _get_apis_used(research: dict[str, Any]) -> list[str]:
        apis = []
        if (research.get("patent_results_count") or 0) > 0:
            apis.append("OPS")
        if (research.get("scholarly_results_count") or 0) > 0:
            apis.append("Scopus")
        return apis

    # ------------------------------------------------------------------
    # Conversão para RAG
    # ------------------------------------------------------------------

    @staticmethod
    def convert_to_rag_documents(
        patents: list[dict[str, Any]],
        articles: list[dict[str, Any]],
        max_patents: int = 50,
        max_articles: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Converte patentes e artigos em documentos para indexação RAG.
        """
        documents: list[dict[str, Any]] = []

        for patent in patents[:max_patents]:
            text = (
                f"Título: {patent.get('title', '')}\n\n"
                f"Resumo: {patent.get('abstract') or 'N/A'}\n\n"
                f"Aplicantes: {', '.join(patent.get('applicants') or [])}\n\n"
                f"Inventores: {', '.join(patent.get('inventors') or [])}\n\n"
                f"Classificação CPC: {', '.join(patent.get('cpc_codes') or [])}\n\n"
                f"Classificação IPC: {', '.join(patent.get('ipc_codes') or [])}\n\n"
                f"Ano de Publicação: {patent.get('year')}\n\n"
                f"Status Legal: {patent.get('legal_status')}\n\n"
                f"Número de Publicação: {patent.get('publication_number')}"
            )
            documents.append({
                "text": text.strip(),
                "source": f"Patent_OPS_{patent.get('publication_number')}",
                "type": "patent",
                "year": patent.get("year"),
                "api": "OPS",
            })

        for article in articles[:max_articles]:
            text = (
                f"Título: {article.get('title', '')}\n\n"
                f"Resumo: {article.get('abstract') or 'N/A'}\n\n"
                f"Autores: {', '.join(article.get('authors') or [])}\n\n"
                f"Afiliações: {', '.join(article.get('affiliations') or [])}\n\n"
                f"Periódico: {article.get('journal_or_source') or 'N/A'}\n\n"
                f"Campos de Estudo: {', '.join(article.get('field_of_study') or [])}\n\n"
                f"Palavras-chave: {', '.join(article.get('keywords') or [])}\n\n"
                f"Ano de Publicação: {article.get('year')}\n\n"
                f"Citações: {article.get('citations') or 0}\n\n"
                f"DOI: {article.get('doi') or 'N/A'}"
            )
            documents.append({
                "text": text.strip(),
                "source": f"Article_Scopus_{article.get('doi') or article.get('id')}",
                "type": "article",
                "year": article.get("year"),
                "api": "Scopus",
            })

        logger.info(
            "rag_documents_created patents=%d articles=%d",
            sum(1 for d in documents if d["type"] == "patent"),
            sum(1 for d in documents if d["type"] == "article"),
        )
        return documents
