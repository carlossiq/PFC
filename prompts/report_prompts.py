"""
Prompts for technology prospecting report generation.

Each prompt is tailored to a specific section with instructions
to maintain accuracy and use only provided data.
"""

REPORT_SYSTEM_PROMPT = """Você é um especialista em redação de relatórios de prospecção tecnológica no estilo REPTEC/AGITEC.

INSTRUÇÕES OBRIGATÓRIAS:
1. Escreva em português formal e técnico
2. Use estilo de relatório institucional profissional
3. NÃO invente números, estatísticas ou datas
4. NÃO crie referências ou fontes fictícias
5. Use APENAS dados e contexto fornecidos
6. Quando usar dados do contexto, cite a fonte entre parênteses: (Fonte: nome_da_fonte)
7. Estruture com títulos e subtítulos claros
8. Use linguagem ativa e precisa
9. Se informação não estiver disponível, indique explicitamente: [Informação não disponível]
10. Interprete gráficos e dados bibliométricos de forma objetiva

FORMATO:
- Parágrafos bem estruturados com 3-5 frases cada
- Use bullets ou numeração quando apropriado
- Inclua conclusões baseadas em evidências"""


def get_section_prompt(
    section_name: str,
    section_type: str,
    theme: str,
    context: str,
    data: dict,
) -> str:
    """
    Generate prompt for a specific report section.

    Args:
        section_name: Name of section (e.g., "Introdução")
        section_type: Type of section (introduction, methodology, results, etc)
        theme: Research theme
        context: Retrieved context from RAG
        data: Relevant data for the section

    Returns:
        Formatted prompt
    """

    if section_type == "finalidade":
        return _finalidade_prompt(theme, data)
    elif section_type == "referencias":
        return _referencias_prompt(data)
    elif section_type == "objetivo":
        return _objetivo_prompt(theme, data)
    elif section_type == "introducao":
        return _introducao_prompt(theme, context, data)
    elif section_type == "metodologia":
        return _metodologia_prompt(theme, data)
    elif section_type == "informacoes_cientificas":
        return _informacoes_cientificas_prompt(context, data)
    elif section_type == "informacoes_tecnologicas":
        return _informacoes_tecnologicas_prompt(context, data)
    elif section_type == "tendencias_ciclo_vida":
        return _tendencias_ciclo_vida_prompt(context, data)
    elif section_type == "conclusao":
        return _conclusao_prompt(theme, context, data)
    elif section_type == "referencias_bibliograficas":
        return _referencias_bibliograficas_prompt(data)
    else:
        return f"Gere uma seção sobre {section_name}:\n\n{context}"


def _finalidade_prompt(theme: str, data: dict) -> str:
    """Prompt for Finalidade (Purpose) section."""
    area = data.get("area_of_study", "")
    keywords = data.get("keywords", [])

    return f"""## Seção: Finalidade

Escreva a seção de Finalidade para um relatório de prospecção tecnológica sobre: {theme}

Dados:
- Área de Estudo: {area}
- Palavras-chave: {', '.join(keywords) if keywords else 'Não especificadas'}
- Período de Pesquisa: {data.get('period_start', '?')} a {data.get('period_end', '?')}

A Finalidade deve:
1. Deixar claro o objetivo geral da prospecção
2. Contextualizar a importância do tema
3. Indicar aplicações práticas

Escreva 2-3 parágrafos bem estruturados."""


def _referencias_prompt(data: dict) -> str:
    """Prompt for Referências section."""
    refs = data.get("references", [])

    refs_text = "\n".join([f"- {ref}" for ref in refs]) if refs else "[Nenhuma referência fornecida]"

    return f"""## Seção: Referências

Resuma e contextualize as seguintes referências:

{refs_text}

Indique:
1. O escopo das referências
2. Como elas fundamentam a pesquisa
3. Qualquer padrão ou tendência nas fontes

Escreva 1-2 parágrafos."""


def _objetivo_prompt(theme: str, data: dict) -> str:
    """Prompt for Objetivo (Objective) section."""
    return f"""## Seção: Objetivo

Descreva o objetivo específico desta prospecção tecnológica.

Tema: {theme}
Área: {data.get('area_of_study', 'N/A')}

O Objetivo deve:
1. Ser específico e mensurável
2. Estar alinhado com a Finalidade
3. Indicar escopo da pesquisa (temporal, geográfico, técnico)
4. Deixar claro o que será analisado

Escreva 2-3 parágrafos em português formal."""


def _introducao_prompt(theme: str, context: str, data: dict) -> str:
    """Prompt for Introdução (Introduction) section."""
    return f"""## Seção: Introdução

Contexto Recuperado:
{context}

Escreva a Introdução para um relatório de prospecção tecnológica sobre: {theme}

A Introdução deve:
1. Apresentar o tema de forma clara e contextualizada
2. Explicar por que o tema é relevante
3. Indicar o estado atual da tecnologia
4. Motivar a leitura do relatório
5. Usar dados e informações do contexto fornecido

Escreva 3-4 parágrafos bem estruturados em português formal."""


def _metodologia_prompt(theme: str, data: dict) -> str:
    """Prompt for Metodologia (Methodology) section."""
    period_start = data.get("period_start", "N/A")
    period_end = data.get("period_end", "N/A")
    apis = data.get("apis_used", [])

    apis_text = ", ".join(apis) if apis else "múltiplas fontes"

    return f"""## Seção: Metodologia

Tema: {theme}
Período: {period_start} a {period_end}
Fontes: {apis_text}

Escreva a Metodologia descrevendo:
1. Fontes de dados utilizadas (patentes, artigos científicos)
2. Período de cobertura e justificativa
3. Critérios de busca e filtros aplicados
4. Ferramentas utilizadas para análise
5. Estrutura do relatório

Seja específico e técnico. Use dados reais do projeto (número de patentes, artigos, etc. se disponíveis).

Escreva 3-4 parágrafos."""


def _informacoes_cientificas_prompt(context: str, data: dict) -> str:
    """Prompt for Informações Científicas (Scientific Information) section."""
    article_count = data.get("article_count", "não especificado")
    top_journals = data.get("top_journals", [])
    top_fields = data.get("top_fields", [])

    journals_text = (
        ", ".join([f["journal"] for f in top_journals[:5]]) if top_journals else "N/A"
    )
    fields_text = ", ".join(top_fields[:5]) if top_fields else "N/A"

    return f"""## Seção: Informações Científicas

Contexto:
{context}

Dados Disponíveis:
- Total de artigos científicos: {article_count}
- Principais periódicos: {journals_text}
- Principais campos de estudo: {fields_text}

Analise e descreva:
1. Volume e tendência de publicações científicas
2. Principais periódicos e autores
3. Campos de estudo predominantes
4. Evolução temporal da pesquisa
5. Instituições e países líderes

Use dados do contexto e interprete os padrões encontrados.

Escreva 4-5 parágrafos estruturados."""


def _informacoes_tecnologicas_prompt(context: str, data: dict) -> str:
    """Prompt for Informações Tecnológicas (Technological Information) section."""
    patent_count = data.get("patent_count", "não especificado")
    top_applicants = data.get("top_applicants", [])
    top_cpcs = data.get("top_cpc_codes", [])

    applicants_text = (
        ", ".join([f["name"] for f in top_applicants[:5]]) if top_applicants else "N/A"
    )
    cpcs_text = ", ".join(top_cpcs[:5]) if top_cpcs else "N/A"

    return f"""## Seção: Informações Tecnológicas

Contexto:
{context}

Dados Disponíveis:
- Total de patentes: {patent_count}
- Principais depositantes: {applicants_text}
- Principais classificações CPC: {cpcs_text}

Analise e descreva:
1. Volume e tendência de depósitos de patentes
2. Principais depositantes e estratégias de patenteamento
3. Classificações técnicas predominantes
4. Evolução temporal dos depósitos
5. Distribuição geográfica das patentes

Explique o significado das classificações CPC. Use dados do contexto para fundamentar.

Escreva 4-5 parágrafos estruturados."""


def _tendencias_ciclo_vida_prompt(context: str, data: dict) -> str:
    """Prompt for Tendências e Ciclo de Vida section."""
    s_curve_phase = data.get("s_curve_phase", "não disponível")
    growth_rate = data.get("growth_rate", "não especificado")
    peak_year = data.get("peak_year", "não especificado")

    return f"""## Seção: Tendências e Ciclo de Vida da Tecnologia

Contexto:
{context}

Dados da Curva-S:
- Fase atual: {s_curve_phase}
- Taxa de crescimento: {growth_rate}
- Ano de pico: {peak_year}

Analise e descreva:
1. Fase do ciclo de vida (Emergente, Crescimento, Maturidade, Declínio)
2. Tendências identificadas (crescimento/estabilização/declínio)
3. Fatores impulsionadores de inovação
4. Riscos e oportunidades baseadas no ciclo
5. Previsões de evolução

Use a Curva-S para fundamentar análises sobre o estágio da tecnologia.

Escreva 4-5 parágrafos estruturados."""


def _conclusao_prompt(theme: str, context: str, data: dict) -> str:
    """Prompt for Conclusão (Conclusion) section."""
    main_findings = data.get("main_findings", [])

    findings_text = "\n".join([f"- {f}" for f in main_findings]) if main_findings else "Sem achados específicos"

    return f"""## Seção: Conclusão

Tema: {theme}

Contexto da Pesquisa:
{context}

Principais Achados:
{findings_text}

Escreva a Conclusão sintetizando:
1. Resumo das principais descobertas
2. Estado atual da tecnologia
3. Oportunidades identificadas
4. Recomendações para próximas etapas
5. Impacto potencial da tecnologia

A conclusão deve ser assertiva mas baseada exclusivamente em dados apresentados.

Escreva 3-4 parágrafos estruturados."""


def _referencias_bibliograficas_prompt(data: dict) -> str:
    """Prompt for Referências Bibliográficas section."""
    references = data.get("references", [])

    if references:
        refs_formatted = "\n".join([f"{i+1}. {ref}" for i, ref in enumerate(references)])
    else:
        refs_formatted = "[Nenhuma referência disponível]"

    return f"""## Seção: Referências Bibliográficas

Organize e apresente as seguintes referências em formato de lista estruturada:

{refs_formatted}

Inclua:
1. Numeração sequencial
2. Dados completos de cada referência
3. Organização por tipo se aplicável (artigos, patentes, livros, websites)

Formato: Autor(es). Título. Fonte. Ano."""
