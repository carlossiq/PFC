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

METODOLOGIA_BOILERPLATE = """\
Os estudos de prospecção tecnológica, também chamados de estudos de futuro \
ou tech foresight, fornecem as principais tendências no contexto mundial \
sobre um tema, auxiliando a identificação de tecnologias promissoras e \
possibilidades de negócios e parcerias. Pretende-se revelar o estado atual \
referente ao ciclo de vida da tecnologia por meio da bibliometria de \
patentes e da literatura científica, buscando evidências que colaborem com \
a área em questão (BORSCHIVER; LEMOS, 2016).

A análise de tendências se baseia no pressuposto de que os comportamentos \
do passado serão mantidos no futuro, utilizando técnicas matemáticas e \
estatísticas para extrapolar séries temporais - a extrapolação por \
regressão logística permite acompanhar a evolução científico-tecnológica e \
gerar curvas-S para avaliar o desempenho de tecnologias (KUCHARAVY; DE GUIO, \
2011). Ernst (1997) descreve quatro estágios do ciclo de vida de uma \
tecnologia: estágio emergente, caracterizado por crescimento relativamente \
baixo em relação ao esforço de P&D; estágio de crescimento, no qual o \
progresso tecnológico marginal sobre os gastos cumulativos de P&D é \
positivo; estágio de maturidade, no qual essa relação se torna negativa; e \
estágio de saturação, no qual pequenas melhorias de desempenho exigem \
esforços de P&D muito elevados.

Para o presente estudo, foram empregadas as palavras-chave {keywords}, com \
dados acumulados até {period_end} (a partir de {period_start} quando \
disponível), utilizando as bases de dados {databases}. O conjunto de dados \
entabulado se constitui nos dados de entrada para o cálculo das Curvas-S \
correspondentes, empregando o modelo logístico, cuja taxa relativa de \
crescimento decresce linearmente com o tempo.\
"""

# Só as obras efetivamente citadas em METODOLOGIA_BOILERPLATE acima - nunca
# adicionar aqui uma referência que o texto fixo não cita de fato.
DEFAULT_BIBLIOGRAPHY: list[str] = [
    "BORSCHIVER, S.; LEMOS, A. Technology Roadmap: planejamento estratégico "
    "para alinhar mercado-produto-tecnologia. Rio de Janeiro, RJ: Ed. "
    "Interciência, 2016.",
    "ERNST, H. The use of patent data for technological forecasting: the "
    "diffusion of CNC-technology in the machine tool industry. Small "
    "business economics, v. 9, n. 4, p. 361-381, 1997.",
    "KUCHARAVY, D.; DE GUIO, R. Application of S-shaped curves. Procedia "
    "Engineering, v. 9, p. 559-572, 2011.",
]

# Cada papel é uma LISTA de assinantes (não mais um único bloco) - o front
# permite adicionar mais de um colaborador/revisor/aprovador por papel (ver
# ReportGeneration.tsx), sempre com pelo menos um item.
DEFAULT_SIGNATURES: dict[str, list[dict[str, str]]] = {
    "elaborado_por": [{"nome": "", "posto_funcao": ""}],
    "revisado_por": [{"nome": "", "posto_funcao": ""}],
    "aprovado_por": [{"nome": "", "posto_funcao": ""}],
}


def render_metodologia(keywords: list[str], period_start: object, period_end: object, databases: list[str]) -> str:
    keywords_text = ", ".join(keywords) if keywords else "[não especificadas]"
    databases_text = ", ".join(databases) if databases else "[não especificadas]"
    return METODOLOGIA_BOILERPLATE.format(
        keywords=keywords_text,
        period_start=period_start or "[não especificado]",
        period_end=period_end or "[não especificado]",
        databases=databases_text,
    )
