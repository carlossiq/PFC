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
    # Obras citadas em 5.4 Apoio Computacional à Prospecção (ver
    # render_apoio_computacional) - os mesmos dados da bibliografia do PFC
    # (PFC/main.tex).
    "BROWN, T. B. et al. Language models are few-shot learners. Advances in Neural Information "
    "Processing Systems, v. 33, p. 1877-1901, 2020. Disponível em: https://arxiv.org/abs/2005.14165.",
    "CHAO, A. Nonparametric estimation of the number of classes in a population. Scandinavian "
    "Journal of Statistics, v. 11, n. 4, p. 265-270, 1984.",
    "CORMACK, G. V.; CLARKE, C. L. A.; BUETTCHER, S. Reciprocal rank fusion outperforms Condorcet "
    "and individual rank learning methods. In: INTERNATIONAL ACM SIGIR CONFERENCE ON RESEARCH AND "
    "DEVELOPMENT IN INFORMATION RETRIEVAL, 32., 2009, Boston. Proceedings. New York: ACM, 2009. "
    "p. 758-759.",
    "EFRON, B. Bootstrap methods: another look at the jackknife. The Annals of Statistics, v. 7, "
    "n. 1, p. 1-26, 1979.",
    "FISHER, J. C.; PRY, R. H. A simple substitution model of technological change. Technological "
    "Forecasting and Social Change, v. 3, p. 75-88, 1971.",
    "FRANTZI, K.; ANANIADOU, S.; MIMA, H. Automatic recognition of multi-word terms: the "
    "C-value/NC-value method. International Journal on Digital Libraries, v. 3, n. 2, p. 115-130, 2000.",
    "GAO, Y. et al. Retrieval-augmented generation for large language models: a survey. arXiv, "
    "arXiv:2312.10997, 2024. Disponível em: https://arxiv.org/abs/2312.10997.",
    "GROOTENDORST, M. KeyBERT: minimal keyword extraction with BERT. Zenodo, 2020. "
    "DOI: 10.5281/zenodo.4461265.",
    "JI, Z. et al. Survey of hallucination in natural language generation. ACM Computing Surveys, "
    "v. 55, n. 12, art. 248, 2023.",
    "LEWIS, P. et al. Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in "
    "Neural Information Processing Systems, v. 33, p. 9459-9474, 2020. Disponível em: "
    "https://arxiv.org/abs/2005.11401.",
    "REIMERS, N.; GUREVYCH, I. Sentence-BERT: sentence embeddings using siamese BERT-networks. In: "
    "CONFERENCE ON EMPIRICAL METHODS IN NATURAL LANGUAGE PROCESSING (EMNLP), 2019, Hong Kong. "
    "Proceedings. Stroudsburg: Association for Computational Linguistics, 2019. p. 3982-3992.",
    "ROBERTSON, S.; ZARAGOZA, H.; TAYLOR, M. Simple BM25 extension to multiple weighted fields. In: "
    "ACM INTERNATIONAL CONFERENCE ON INFORMATION AND KNOWLEDGE MANAGEMENT (CIKM), 13., 2004, "
    "Washington. Proceedings. New York: ACM, 2004. p. 42-49.",
    "SCHOPF, T.; KLIMEK, S.; MATTHES, F. PatternRank: leveraging pretrained language models and part "
    "of speech for unsupervised keyphrase extraction. In: INTERNATIONAL CONFERENCE ON KNOWLEDGE "
    "DISCOVERY AND INFORMATION RETRIEVAL (KDIR), 14., 2022, Valletta. Proceedings. Setúbal: "
    "SciTePress, 2022. p. 243-248.",
    "VASWANI, A. et al. Attention is all you need. Advances in Neural Information Processing "
    "Systems, v. 30, 2017. Disponível em: https://arxiv.org/abs/1706.03762.",
    "WEI, J. et al. Chain-of-thought prompting elicits reasoning in large language models. Advances "
    "in Neural Information Processing Systems, v. 35, p. 24824-24837, 2022. Disponível em: "
    "https://arxiv.org/abs/2201.11903.",
    "WHITE, J. et al. A prompt pattern catalog to enhance prompt engineering with ChatGPT. arXiv, "
    "arXiv:2302.11382, 2023. Disponível em: https://arxiv.org/abs/2302.11382.",
    "ZHAO, W. X. et al. A survey of large language models. arXiv, arXiv:2303.18223, 2023. "
    "Disponível em: https://arxiv.org/abs/2303.18223.",
]

# Cada papel é uma LISTA de assinantes (não mais um único bloco) - o front
# permite adicionar mais de um colaborador/revisor/aprovador por papel (ver
# ReportGeneration.tsx), sempre com pelo menos um item.
DEFAULT_SIGNATURES: dict[str, list[dict[str, str]]] = {
    "elaborado_por": [{"nome": "", "posto": "", "funcao": ""}],
    "revisado_por": [{"nome": "", "posto": "", "funcao": ""}],
    "aprovado_por": [{"nome": "", "posto": "", "funcao": ""}],
}


FINALIDADE_TEMPLATE = (
    "Apresentar o relatório de Prospecção Tecnológica sobre {tema} a fim de fornecer informações "
    "de tendências e ciclo de vida da tecnologia para {destinatario}."
)

_MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def render_finalidade(tema: str, destinatario: str) -> str:
    """Finalidade do REPTEC: sempre UMA frase fixa (nunca gerada por IA -
    a versão por IA repetia o Objetivo em três parágrafos)."""
    return FINALIDADE_TEMPLATE.format(tema=tema.strip(), destinatario=destinatario.strip().rstrip("."))


def render_local_data(local: str, when) -> str:
    """"Rio de Janeiro, 10 de agosto de 2023." (antes das assinaturas)."""
    return f"{local.strip()}, {when.day} de {_MESES[when.month - 1]} de {when.year}."


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


# ---------------------------------------------------------------------------
# 5.4 Apoio Computacional à Prospecção
# ---------------------------------------------------------------------------
# Etapa registrada em session_ai_call (`step`) -> como a etapa é nomeada na
# Metodologia. A ordem aqui é a ordem das etapas no texto.
MODEL_STAGE_LABELS: list[tuple[tuple[str, ...], str]] = [
    (("refine_topic", "specify_topic"), "refinamento do tema"),
    (("probe_query", "probe_queries_multi"), "estratégias de busca exploratória"),
    (("final_query",), "estratégia de busca final"),
    (("report_writing",), "redação das seções analíticas"),
    (("extract_terms",), "representação vetorial de textos (KeyBERT e recuperação semântica)"),
]
REPORT_WRITING_STEP_PREFIX = "report_writing:"


def models_by_stage(calls: list[tuple[str, str]], embedding_model: str = "") -> list[tuple[str, list[str]]]:
    """(etapa, modelos) a partir das chamadas registradas em session_ai_call,
    em ordem cronológica: `calls` = [(step, model), ...].

    Redação ("report_writing:<seção>"): vale só a chamada MAIS RECENTE de
    cada seção - o modelo que escreveu o texto que está no documento, não os
    de gerações descartadas. Nas demais etapas entram todos os modelos usados
    (se o analista trocou de modelo no meio, os dois aparecem).
    `embedding_model` completa a etapa de representação vetorial quando a
    extração de termos não foi registrada (o mesmo modelo serve o RAG)."""
    latest_writer: dict[str, str] = {}
    used: dict[str, list[str]] = {}
    for step, model in calls:
        if not model:
            continue
        if step.startswith(REPORT_WRITING_STEP_PREFIX):
            latest_writer[step] = model
            continue
        used.setdefault(step, [])
        if model not in used[step]:
            used[step].append(model)
    used["report_writing"] = list(dict.fromkeys(latest_writer.values()))
    if embedding_model and not used.get("extract_terms"):
        used["extract_terms"] = [embedding_model]

    stages: list[tuple[str, list[str]]] = []
    for steps, label in MODEL_STAGE_LABELS:
        models = list(dict.fromkeys(m for step in steps for m in used.get(step, [])))
        if models:
            stages.append((label, models))
    return stages


def _texttt(model: str) -> str:
    return "\\texttt{" + model + "}"


def render_apoio_computacional(stages: list[tuple[str, list[str]]]) -> str:
    """Subseção 5.4 (LaTeX pronto): o que é um LLM, as técnicas de
    engenharia de prompt, extração de termos, estatística, curva S e RAG -
    cada técnica com a obra que a define (todas em DEFAULT_BIBLIOGRAPHY) -
    e, por fim, os modelos usados em cada etapa desta prospecção.
    `stages` vem de models_by_stage, com os nomes de modelo JÁ escapados
    pra LaTeX pelo chamador. Descreve só o que o sistema faz de fato."""
    paragraphs = [
        "As etapas descritas nesta seção foram conduzidas com o apoio de ferramentas computacionais que "
        "integram técnicas de Inteligência Artificial (IA) e de Processamento de Linguagem Natural (PLN) à "
        "análise bibliométrica, sempre com a revisão e a validação do analista de prospecção em cada etapa.",

        "Modelos de linguagem de grande porte (\\textit{Large Language Models} -- LLM) são redes neurais "
        "baseadas na arquitetura \\textit{Transformer} (VASWANI et al., 2017), treinadas sobre grandes volumes "
        "de texto para prever a continuação de uma sequência. Em escala suficiente, esses modelos passam a "
        "executar tarefas descritas em linguagem natural a partir de instruções e de poucos exemplos, sem "
        "treinamento específico (BROWN et al., 2020; ZHAO et al., 2023). Como também podem produzir "
        "afirmações plausíveis, porém sem fundamento -- as chamadas alucinações (JI et al., 2023) --, seu uso "
        "neste estudo restringiu-se a tarefas verificáveis, com as salvaguardas descritas a seguir.",

        "A qualidade das respostas de um LLM depende da forma como a tarefa é formulada na instrução "
        "(\\textit{prompt}); a engenharia de \\textit{prompt} reúne padrões para essa formulação (WHITE et al., "
        "2023). Foram empregadas as seguintes técnicas:\n"
        "\\begin{itemize}\n"
        "    \\item \\textbf{persona}: cada instrução atribui ao modelo o papel de especialista em prospecção "
        "tecnológica e na construção de estratégias de busca (WHITE et al., 2023);\n"
        "    \\item \\textbf{exemplos na instrução (\\textit{few-shot})}: exemplos contrastantes de respostas "
        "adequadas e inadequadas orientam o nível de especificidade esperado (BROWN et al., 2020);\n"
        "    \\item \\textbf{raciocínio passo a passo (\\textit{chain-of-thought})}: a construção da estratégia "
        "de busca é decomposta em etapas explícitas -- identificar os conceitos do tema, eleger os centrais e "
        "agrupar sinônimos --, o que melhora o desempenho dos modelos em tarefas de raciocínio "
        "(WEI et al., 2022);\n"
        "    \\item \\textbf{saída estruturada}: as respostas são exigidas em formato JSON e validadas por "
        "esquema antes do uso, aproveitando-se apenas os campos aceitos por cada base de dados;\n"
        "    \\item \\textbf{autocorreção orientada por métrica}: cada estratégia gerada recebe um índice de "
        "complexidade calculado de forma determinística; quando o índice excede o limite, a medida obtida é "
        "devolvida ao modelo com a instrução de simplificar a consulta, em até três tentativas.\n"
        "\\end{itemize}",

        "Inicialmente, os LLM propõem estratégias de busca a partir do tema e das palavras-chave informados, "
        "respeitando a sintaxe de cada base de dados. Essas estratégias são executadas em buscas exploratórias "
        "(\\textit{probe}), cujos documentos fornecem o vocabulário efetivamente empregado na literatura e nas "
        "patentes sobre o tema. Desse conjunto são extraídos termos candidatos por padrões gramaticais (SCHOPF; "
        "KLIMEK; MATTHES, 2022), ranqueados por dois critérios complementares: um estatístico-lexical, pelo "
        "algoritmo BM25F (ROBERTSON; ZARAGOZA; TAYLOR, 2004), e um semântico, pelo método KeyBERT "
        "(GROOTENDORST, 2020), baseado em representações vetoriais de sentenças (REIMERS; GUREVYCH, 2019). Os "
        "dois rankings são combinados por fusão de postos (\\textit{Reciprocal Rank Fusion}) (CORMACK; CLARKE; "
        "BUETTCHER, 2009), e termos aninhados são tratados pela medida C-value (FRANTZI; ANANIADOU; MIMA, 2000). "
        "Os termos mais representativos orientam a construção da estratégia de busca final, em três níveis de "
        "abrangência (específica, balanceada ou ampla), selecionada pelo analista.",

        "A busca final é realizada ano a ano, preservando a série histórica completa, e a amostra analisada é "
        "ampliada até que o estimador de riqueza Chao1 (CHAO, 1984) indique sua saturação; a estabilidade dos "
        "rankings de depositantes, instituições e classificações é verificada por reamostragem "
        "\\textit{bootstrap} (EFRON, 1979). As curvas S são ajustadas automaticamente pelo modelo logístico de "
        "substituição (FISHER; PRY, 1971), com a identificação dos pontos GP, MP e SP e do estágio "
        "correspondente do ciclo de vida.",

        "Por fim, a redação das seções analíticas deste relatório contou com o apoio de LLM por meio de geração "
        "aumentada por recuperação (\\textit{Retrieval-Augmented Generation} -- RAG) (LEWIS et al., 2020; GAO et "
        "al., 2024): para cada seção, recuperam-se os trechos mais relevantes dos documentos obtidos nas buscas, "
        "e somente esse conteúdo, com os indicadores calculados, é fornecido ao modelo. Citações que não "
        "correspondem a um documento recuperado são descartadas automaticamente, e o texto foi submetido à "
        "revisão final do analista.",
    ]
    if stages:
        items = "; ".join(f"{label}: {', '.join(_texttt(model) for model in models)}" for label, models in stages)
        paragraphs.append(f"Os modelos utilizados em cada etapa desta prospecção foram: {items}.")
    return "\n\n".join(paragraphs)
