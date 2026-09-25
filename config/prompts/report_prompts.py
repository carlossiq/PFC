"""
Prompts das seções de IA do relatório de prospecção (padrão REPTEC/AGITEC,
ver notes/REPTEC_001_2023_TETRA.pdf).

Princípio: tudo que é FATO (contagens, anos, estágio do ciclo de vida,
significado de códigos CPC, citações) chega pronto em `data`, calculado em
Python - o LLM só redige. Nada de "Fonte: ...", score de busca ou
marcadores internos no texto (ver report_text_quality.py, que rejeita
esses padrões e força uma regeneração).

Formato de `data` (todas as chaves opcionais):
    area_of_study, keywords, objetivo_usuario
    article_count, patent_count (já formatados pt-BR, ex.: "1.800")
    figures: list[{id, kind ("Figura"|"Quadro"), caption, summary}] -
        catálogo das figuras da seção (ver report_figures.py)
    cpc_titles: list[(código, título oficial)] - só pra 6.2
    lifecycle: {"article"/"patent": {stage, gp, mp, sp}, "overall_stage"}
        - estágio calculado da curva S (ver report_lifecycle.py)
    brazil: {"patents": int, "articles": int} - documentos com Brasil na
        amostra persistida
    results_digest: str - fatos dos Resultados, só pra Conclusão
"""

from __future__ import annotations

REPORT_SYSTEM_PROMPT = """Você é um especialista em redação de relatórios de prospecção tecnológica no estilo REPTEC/AGITEC do Exército Brasileiro.

REGRAS OBRIGATÓRIAS:
1. Português formal, técnico e IMPESSOAL ("observa-se", "recomenda-se" - nunca "observamos", "recomendamos").
2. Use APENAS os fatos e documentos fornecidos no pedido. NÃO invente números, datas, normas, regulamentos, mercados, empresas ou autores.
3. Citações: somente no formato (SOBRENOME et al., ano), exatamente como indicado em "citar como" de cada documento. Documento marcado "não citar" não pode ser citado. Nunca escreva "Fonte:", "N/A" ou percentuais de relevância/similaridade.
4. Nunca mencione o material de apoio ("contexto fornecido", "dados fornecidos", "documentos recuperados"). Escreva como se o conhecimento fosse seu.
5. Se um dado não existir, simplesmente não trate daquele ponto - nunca escreva "[Informação não disponível]" nem frases sobre ausência de dados.
6. Mantenha o foco no TEMA do relatório. Documentos sobre assuntos periféricos servem só como exemplo pontual, nunca como assunto central.
7. Números em formato brasileiro: vírgula decimal (17,3%) e ponto de milhar (1.800).
8. Não inclua título/cabeçalho da seção (ex.: "## Seção") - comece direto pelo primeiro parágrafo.
9. Parágrafos corridos, sem listas com marcadores e sem Markdown."""


def retry_instruction(issues: list[str]) -> str:
    """Anexada ao prompt na regeneração (ver ReportWriterService)."""
    listed = "\n".join(f"- {issue}" for issue in issues)
    return (
        "\n\nATENÇÃO: a versão anterior deste texto foi rejeitada pelos seguintes problemas:\n"
        f"{listed}\nReescreva o texto inteiro sem nenhum desses problemas, seguindo as regras obrigatórias."
    )


def get_section_prompt(
    section_name: str,
    section_type: str,
    theme: str,
    context: str,
    data: dict,
) -> str:
    builders = {
        "objetivo": lambda: _objetivo_prompt(theme, data),
        "introducao": lambda: _introducao_prompt(theme, context, data),
        "informacoes_cientificas": lambda: _informacoes_cientificas_prompt(theme, context, data),
        "informacoes_tecnologicas": lambda: _informacoes_tecnologicas_prompt(theme, context, data),
        "tendencias_ciclo_vida": lambda: _tendencias_ciclo_vida_prompt(theme, context, data),
        "conclusao": lambda: _conclusao_prompt(theme, data),
    }
    builder = builders.get(section_type)
    if builder is None:
        raise ValueError(f"Seção sem prompt de IA: {section_type}")
    return builder()


# ---------------------------------------------------------------------------
# Blocos compartilhados
# ---------------------------------------------------------------------------


def _documents_block(context: str) -> str:
    if not context.strip():
        return ""
    return f"DOCUMENTOS DE APOIO (use só o que for pertinente ao tema):\n{context}\n\n"


# Como chamar os documentos de cada figura - o exemplo do prompt dizia
# sempre "publicações científicas", e o modelo repetia isso nas figuras de
# PATENTES.
_DOCUMENT_NOUNS = {"patent": "dos depósitos de patentes", "article": "das publicações científicas"}


def _structure_example(document_type: str) -> str:
    """Exemplo de estrutura figura-texto no vocabulário do tipo de documento
    da seção (patentes: depósitos; artigos: publicações científicas)."""
    if document_type == "patent":
        return (
            '"No total, foram identificados 321 depósitos de patentes entre 1992 e 2022. A Figura '
            "[[REF:patent_yearly_volume]] mostra a distribuição desses depósitos ao longo do tempo.\n\n"
            "[[FIG:patent_yearly_volume]]\n\n"
            "Entre 1993 e 2013, observa-se crescimento gradual, com o pico de 25 depósitos em 2013; a partir de "
            "então, nota-se queda sustentada, chegando a 2 depósitos em 2022, o que sugere redução do interesse "
            'comercial pela tecnologia."'
        )
    return (
        '"No total, foram identificadas 321 publicações científicas entre 1992 e 2022. A Figura '
        "[[REF:article_yearly_volume]] mostra a distribuição dessas publicações ao longo do tempo.\n\n"
        "[[FIG:article_yearly_volume]]\n\n"
        "Entre 1993 e 2013, observa-se crescimento gradual, com o pico de 25 publicações em 2013; a partir de "
        "então, nota-se queda sustentada, chegando a 2 publicações em 2022, o que sugere redução do interesse "
        'acadêmico pela tecnologia."'
    )


def _figures_block(data: dict) -> str:
    figures = data.get("figures") or []
    if not figures:
        return ""
    lines = []
    for fig in figures:
        lines.append(f"- id: {fig['id']} | {fig['kind']}: {fig['caption']}\n  Dados: {fig['summary']}")
    catalog = "\n".join(lines)
    first = figures[0]
    noun = _DOCUMENT_NOUNS.get(first.get("document_type", ""), "dos documentos")
    return f"""FIGURAS E QUADROS DESTA SEÇÃO (os números abaixo são os mesmos desenhados em cada imagem):
{catalog}

LEITURA DOS DADOS: cada número vem com a sua unidade - respeite-a. Anos são anos (nunca "2007 publicações"); valores ACUMULADOS não são valores anuais; figuras de patentes falam de patentes/depósitos (nunca "publicações científicas" ou "artigos"); figuras de artigos falam de publicações científicas. Em rankings, o 1º colocado é o que lidera - mantenha a ordem.

COMO APRESENTAR CADA FIGURA/QUADRO (padrão do REPTEC - obrigatório para TODOS os itens da lista acima):
1. Um parágrafo que APRESENTA a figura e cita pelo marcador [[REF:id]], precedido da palavra Figura ou Quadro. Ex.: "A {first['kind']} [[REF:{first['id']}]] mostra a distribuição {noun} ao longo do tempo."
2. Na linha seguinte, sozinho, o marcador [[FIG:id]] - é onde a imagem entra.
3. Logo depois, um parágrafo que INTERPRETA os dados da figura: cite os números dela (totais, pico e ano do pico, primeiros colocados e suas quantidades), descreva a tendência (crescimento, estabilização, queda) e o que isso indica sobre o tema.
Exemplo de estrutura (números fictícios - use os dos "Dados"):
{_structure_example(first.get("document_type", ""))}
Regras: use cada figura exatamente uma vez; nunca coloque duas figuras seguidas sem texto entre elas; nunca termine a seção com figuras; não invente ids; todo número sobre uma figura deve vir dos "Dados" dela.

"""


def _lifecycle_lines(lifecycle: dict) -> str:
    labels = {"article": "Publicações científicas (artigos)", "patent": "Depósitos de patentes"}
    lines = []
    for key in ("article", "patent"):
        curve = lifecycle.get(key)
        if not curve:
            continue
        points = ", ".join(
            f"{name} = {curve[name.lower()]}" for name in ("GP", "MP", "SP") if curve.get(name.lower()) is not None
        )
        lines.append(f"- {labels[key]}: estágio de {curve['stage'].upper()} ({points}).")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Seções
# ---------------------------------------------------------------------------


def _objetivo_prompt(theme: str, data: dict) -> str:
    return f"""Escreva a seção OBJETIVO de um relatório de prospecção tecnológica sobre: {theme}

Modelo do REPTEC (um único parágrafo curto, 1 a 2 frases):
"O presente trabalho consiste em realizar um estudo de prospecção tecnológica sobre Terrestrial Trunked Radio (TETRA) confeccionado como subsídio para a elaboração de estudos acerca de parceria entre a IMBEL e a empresa ROHILL."

Área de estudo informada: {data.get('area_of_study') or '(não informada)'}

Escreva UM parágrafo curto no mesmo estilo, só com o tema e a área acima. Não cite normas, regulamentos, mercados, países nem períodos."""


def _introducao_prompt(theme: str, context: str, data: dict) -> str:
    return f"""{_documents_block(context)}Escreva a INTRODUÇÃO de um relatório de prospecção tecnológica sobre: {theme}

A Introdução deve, em 3 a 4 parágrafos:
1. Apresentar a tecnologia "{theme}" e seu funcionamento geral;
2. Explicar por que o tema é relevante;
3. Indicar o estado atual da tecnologia, citando (SOBRENOME et al., ano) os documentos de apoio pertinentes;
4. Motivar a leitura do relatório.

O assunto central é sempre "{theme}"; documentos sobre outros assuntos só podem aparecer como exemplo pontual."""


def _informacoes_cientificas_prompt(theme: str, context: str, data: dict) -> str:
    facts = []
    if data.get("article_count"):
        facts.append(f"- Total de publicações científicas encontradas: {data['article_count']}")
    facts_text = "\n".join(facts)
    return f"""{_documents_block(context)}{_figures_block(data)}Escreva a subseção 6.1 INFORMAÇÕES CIENTÍFICAS do relatório de prospecção sobre: {theme}

Fatos:
{facts_text}

No estilo do REPTEC, em 3 a 5 parágrafos: comece pelo total de publicações e o período coberto; comente a evolução ao longo do tempo (crescimento, pico, queda) com base nos dados das figuras; depois as instituições que mais publicaram e as áreas de estudo predominantes. Cite (SOBRENOME et al., ano) apenas documentos de apoio pertinentes ao tema. Esta subseção trata SOMENTE de PUBLICAÇÕES CIENTÍFICAS (artigos) - não fale de patentes aqui."""


def _informacoes_tecnologicas_prompt(theme: str, context: str, data: dict) -> str:
    facts = []
    if data.get("patent_count"):
        facts.append(f"- Total de patentes encontradas: {data['patent_count']}")
    facts_text = "\n".join(facts)
    cpc_titles = data.get("cpc_titles") or []
    cpc_block = ""
    if cpc_titles:
        rows = "\n".join(f"- {code}: {title}" for code, title in cpc_titles)
        cpc_block = f"""SIGNIFICADO OFICIAL DAS CLASSIFICAÇÕES CPC (títulos oficiais, em inglês - traduza fielmente ao citar; NÃO descreva nenhum código por conta própria nem cite códigos fora desta lista):
{rows}

"""
    return f"""{_documents_block(context)}{_figures_block(data)}{cpc_block}Escreva a subseção 6.2 INFORMAÇÕES TECNOLÓGICAS do relatório de prospecção sobre: {theme}

Fatos:
{facts_text}

No estilo do REPTEC, em 3 a 5 parágrafos: comece pela distribuição temporal dos depósitos (crescimento, pico) com base nos dados das figuras; depois os principais depositantes, citando nomes e quantidades; depois as classificações CPC mais encontradas, explicando cada uma SÓ pelo significado oficial acima. Sempre escreva "CPC" (nunca "IPC"). Esta subseção trata SOMENTE de PATENTES: chame os documentos de patentes, depósitos ou registros de patente - nunca de "publicações científicas" ou "artigos"."""


def _tendencias_ciclo_vida_prompt(theme: str, context: str, data: dict) -> str:
    lifecycle = data.get("lifecycle") or {}
    lines = _lifecycle_lines(lifecycle)
    facts = f"""ESTÁGIO DO CICLO DE VIDA (calculado a partir das curvas S - use exatamente estes estágios e anos, sem reinterpretar):
{lines}
GP = ponto de crescimento (10% da saturação), MP = ponto médio (50%), SP = ponto de saturação (90%).

""" if lines else ""
    return f"""{_documents_block(context)}{_figures_block(data)}{facts}Escreva a subseção 6.3 TENDÊNCIAS E CICLO DE VIDA DA TECNOLOGIA do relatório de prospecção sobre: {theme}

No estilo do REPTEC, em 3 a 5 parágrafos: descreva a evolução das publicações e dos depósitos ao longo do tempo; discuta SEPARADAMENTE a curva S dos artigos e a curva S das patentes, informando o estágio de cada uma e os anos GP/MP/SP acima (ex.: "MP = 2011"); interprete o que isso indica sobre o interesse acadêmico e comercial pela tecnologia. Os totais das curvas S são ACUMULADOS (não fale em "pico" de um valor acumulado) e GP/MP/SP são ANOS; use exatamente o estágio informado para cada curva."""


def _conclusao_prompt(theme: str, data: dict) -> str:
    lifecycle = data.get("lifecycle") or {}
    overall = lifecycle.get("overall_stage")
    lines = _lifecycle_lines(lifecycle)
    brazil = data.get("brazil") or {}
    brazil_text = ""
    if brazil:
        brazil_text = (
            f"- Na amostra analisada: {brazil.get('patents', 0)} patente(s) depositada(s) no Brasil e "
            f"{brazil.get('articles', 0)} publicação(ões) com afiliação brasileira."
        )
    stage_text = f"- Estágio da tecnologia (definido pela curva de patentes): {overall.upper()}\n" if overall else ""
    return f"""Escreva a seção CONCLUSÃO do relatório de prospecção tecnológica sobre: {theme}

FATOS (use somente estes - não traga assuntos que não aparecem aqui):
{stage_text}{lines}
{brazil_text}
{data.get('results_digest') or ''}

Estrutura obrigatória (como no REPTEC), em 3 a 4 parágrafos impessoais:
1. Comece afirmando que a tecnologia se encontra no ESTÁGIO DE {overall.upper() if overall else '<estágio>'} em relação ao seu ciclo de vida (escreva o estágio em MAIÚSCULAS);
2. Sintetize o que os Resultados mostraram (volume, evolução, principais atores);
3. Contextualize a situação no Brasil com base nos fatos acima;
4. Faça a previsão com base nos anos de saturação (SP) informados;
5. Encerre recomendando o monitoramento tecnológico contínuo ("recomenda-se ...").
Coerência obrigatória: o estágio da tecnologia é um só ({overall.upper() if overall else 'o informado'}) - não o contradiga em outro parágrafo; os totais de documentos são os dos fatos acima (não arredonde nem recalcule)."""
