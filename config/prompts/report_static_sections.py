"""
Conteúdo fixo/local do relatório REPTEC/AGITEC - seções que NÃO passam por
LLM (ver app/core/services/report_writer_service.py e notes/REPTEC_001_2023_TETRA.pdf
pra estrutura real do documento):

- Metodologia (seção 5): texto-base quase idêntico em todo REPTEC, só com um
  parágrafo final interpolado com dados desta pesquisa (palavras-chave,
  período, bases de dados) - nunca gerado por LLM.
- Referências Bibliográficas (seção 8): lista fixa das obras sempre citadas
  pelo texto-base da Metodologia, + referências adicionais que o usuário
  incluir para este relatório específico - nunca gerada por LLM (evita
  citação inventada, mesma regra já em REPORT_SYSTEM_PROMPT).
- Assinaturas: nomes/postos default, sobrescrevíveis por requisição (e mais
  tarde pelo front).

Isolado de report_prompts.py (que só cobre as seções de IA) pra deixar claro
que nada aqui nunca vira prompt de LLM.
"""

from __future__ import annotations

# Texto fixo da Metodologia (seção 5 + subseções 5.1-5.3 com as figuras
# MADEO/KUCHARAVY) mora direto no template LaTeX (report_latex_template.py),
# porque tem estrutura (subseções, figuras, notas de rodapé) - aqui só o
# último parágrafo, o único interpolado com dados desta pesquisa. Trechos
# sem dado (sem palavras-chave, sem período, sem base) são OMITIDOS da
# frase, nunca preenchidos com "[não especificado]".
LEGACY_METODOLOGIA_PREFIX = "Os estudos de prospecção tecnológica"

# Todas as obras citadas no texto fixo da Metodologia (template) e nas
# fontes das figuras fixas - nunca adicionar aqui uma referência que o
# texto fixo não cite de fato. BORSCHIVER/ERNST/KUCHARAVY mantêm o texto
# exato de versões anteriores (dedupe com sessões já montadas, ver
# merge_bibliography).
DEFAULT_BIBLIOGRAPHY: list[str] = [
    "ANDRADE, J. L.; MOURA, D. F. C.; BORSCHIVER, S. Estudo pré-prospectivo para Roadmap "
    "tecnológico sobre rádio cognitivo: evolução científico-patentária entre 1970-2017. "
    "Cadernos de Prospecção, v. 11, n. 3, p. 861, 2018.",
    "BORSCHIVER, S.; LEMOS, A. Technology Roadmap: planejamento estratégico "
    "para alinhar mercado-produto-tecnologia. Rio de Janeiro, RJ: Ed. "
    "Interciência, 2016.",
    "DAIM, T. U.; RUEDA, G. R.; MARTIN, H. T. Technology forecasting using bibliometric "
    "analysis and system dynamics. Technology Management: A Unifying Discipline for Melting "
    "the Boundaries, 2005. Disponível em: https://ieeexplore.ieee.org/document/1509681.",
    "ERNST, H. The use of patent data for technological forecasting: the "
    "diffusion of CNC-technology in the machine tool industry. Small "
    "business economics, v. 9, n. 4, p. 361-381, 1997.",
    "FRANÇA JR., J. A.; GALDINO, J. Gestão de sistemas de material de emprego militar. "
    "Coleção Meira Mattos: revista das ciências militares, v. 13, n. 47, p. 155-176, 2019.",
    "KUCHARAVY, D.; DE GUIO, R. Application of S-shaped curves. Procedia "
    "Engineering, v. 9, p. 559-572, 2011.",
    "LEZAMA-NICOLÁS, R. et al. A bibliometric method for assessing technological maturity: "
    "the case of additive manufacturing. Scientometrics, v. 117, n. 3, p. 1425-1452, 2018.",
    "LINDEN, R.; BARBOSA, L. F.; DIGIAMPIETRI, L. A. “Brazilian style science”: an analysis "
    "of the difference between Brazilian and international Computer Science departments and "
    "graduate programs using social networks analysis and bibliometrics. Social Network "
    "Analysis and Mining, v. 7, p. 1-19, 2017.",
    "MADEO, F. C. B. Prospecção tecnológica utilizando a análise multicritério e técnicas "
    "bibliométricas: estudo de caso para o setor de Defesa. 2019. 144 p. Dissertação "
    "(Mestrado em Engenharia de Defesa) - Instituto Militar de Engenharia, Rio de Janeiro, 2019.",
    "NIETO, M.; LOPÉZ, F.; CRUZ, F. Performance analysis of technology using the S curve "
    "model: the case of digital signal processing (DSP) technologies. Technovation, v. 18, "
    "n. 6-7, p. 439-457, 1998.",
    "PORTER, A. L. QTIP: Quick technology intelligence processes. Technological Forecasting "
    "and Social Change, v. 72, n. 9, p. 1070-1081, 2005.",
]

# Cada papel é uma LISTA de assinantes (não mais um único bloco) - o front
# permite adicionar mais de um colaborador/revisor/aprovador por papel (ver
# ReportGeneration.tsx), sempre com pelo menos um item.
DEFAULT_SIGNATURES: dict[str, list[dict[str, str]]] = {
    "elaborado_por": [{"nome": "", "posto_funcao": ""}],
    "revisado_por": [{"nome": "", "posto_funcao": ""}],
    "aprovado_por": [{"nome": "", "posto_funcao": ""}],
}


def _join_pt(items: list[str]) -> str:
    """"a", "a e b", "a, b e c"."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " e " + items[-1]


def render_metodologia(keywords: list[str], period_start: object, period_end: object, databases: list[str]) -> str:
    """Último parágrafo da Metodologia (5.3), texto puro (o chamador escapa
    pra LaTeX) - o resto da seção é fixo no template."""
    sentences: list[str] = []
    clean_keywords = [k.strip() for k in keywords or [] if k and k.strip()]
    if clean_keywords:
        sentences.append(f"Neste relatório, as curvas de extrapolação empregam as palavras-chave {_join_pt(clean_keywords)}.")

    dataset = "O conjunto de dados entabulado"
    if period_end:
        dataset += f", acumulado até {period_end}"
        if period_start:
            dataset += f" (a partir de {period_start})"
        dataset += " para patentes e artigos"
    clean_databases = [d.strip() for d in databases or [] if d and d.strip()]
    if clean_databases:
        label = "da base de dados" if len(clean_databases) == 1 else "das bases de dados"
        dataset += f"{',' if period_end else ''} obtido {label} {_join_pt(clean_databases)}"
    if period_end or clean_databases:
        dataset += ","
    dataset += " se constitui nos dados de entrada para o cálculo das Curvas S correspondentes à tecnologia alvo deste estudo."
    sentences.append(dataset)
    sentences.append(
        "Para este estudo foi utilizado o modelo logístico, cuja taxa relativa de crescimento "
        "decresce linearmente com o tempo."
    )
    return " ".join(sentences)


def legacy_metodologia_to_paragraph(stored_text: str) -> str:
    """Sessões montadas antes da Metodologia completa ir pro template
    guardaram o boilerplate INTEIRO (3 parágrafos) em
    session_report_section - aproveita só o último (o interpolado), já que
    o resto agora vem do template, e tira o "[não especificadas]" que a
    versão antiga inseria quando faltava dado."""
    if not stored_text.startswith(LEGACY_METODOLOGIA_PREFIX):
        return stored_text
    last = [p for p in stored_text.split("\n\n") if p.strip()][-1]
    last = last.replace("foram empregadas as palavras-chave [não especificadas], ", "")
    last = last.replace(", utilizando as bases de dados [não especificadas]", "")
    last = last.replace(" (a partir de [não especificado] quando disponível)", "")
    last = last.replace(", com dados acumulados até [não especificado]", "")
    last = last.replace("Para o presente estudo, com dados", "Para o presente estudo, foram utilizados dados")
    return last.strip()


def _bibliography_sort_key(ref: str) -> str:
    return ref.replace("\\", "").casefold()


def merge_bibliography(escaped_defaults: list[str], stored: list[str]) -> list[str]:
    """Obras fixas (sempre presentes, mesmo em sessão montada antes da lista
    crescer) + as já persistidas pela sessão (inclui as adicionadas pelo
    usuário), sem duplicar, em ordem alfabética (ABNT)."""
    merged: list[str] = []
    for ref in [*escaped_defaults, *stored]:
        if ref.strip() and ref not in merged:
            merged.append(ref)
    return sorted(merged, key=_bibliography_sort_key)
