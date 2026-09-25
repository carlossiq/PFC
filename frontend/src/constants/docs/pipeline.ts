import type { DocPageData } from './types'

// Resumo, voltado ao usuário, de RELATORIO_TECNICO_SISTEMA.md (§6, §7, §10,
// §11, §15). Valores numéricos espelham core/config.py,
// app/core/services/query_complexity.py, s_curve.py e sample_statistics.py.
export const pipelinePage: DocPageData = {
  title: 'Pipeline de Prospecção',
  description:
    'Como os dados fluem pelo sistema, do tema digitado até os gráficos que alimentam o relatório, e quais mecanismos garantem que cada etapa produza algo utilizável.',
  sections: [
    {
      id: 'visao-geral',
      title: 'Visão geral',
      subsections: [
        {
          title: 'Fluxo de ponta a ponta',
          blocks: [
            {
              type: 'code',
              code: `Tema / descrição / palavras-chave / área
  │
  ▼  LLM ─ refino do tema (4 variações)                 [opcional]
  ▼  LLM ─ query PROBE por fonte  + função de complexidade (até 3 tentativas)
  ▼  Query builder ─ traduz para a sintaxe de cada API (CQL, Scopus…)
  ▼  Busca PROBE (OPS / Scopus) ─ amostra pequena, diversificada por ano
  ▼  NLP local ─ PatternRank + BM25F + KeyBERT → RRF → C-value
  │     usuário escolhe os termos e a variante
  ▼  LLM ─ query FINAL (específica | balanceada | ampla) + complexidade
  ▼  Busca FINAL ─ volume maior + total real da base
  ▼  Inferência estatística (Chao1 + bootstrap) e gráficos → MinIO
  ▼  RAG (ChromaDB) + LLM por seção → .tex REPTEC → revisão → PDF`,
            },
            {
              type: 'note',
              text: 'Nada é gravado no servidor até a sessão ser salva ("Salvar progresso") ou até a Criação de Gráficos, que salva a sessão automaticamente antes de gerar qualquer gráfico.',
            },
          ],
        },
        {
          title: 'Onde a IA entra (pontos de uso)',
          blocks: [
            {
              type: 'paragraph',
              text: 'Cada ponto de uso pode apontar para um modelo diferente em Configurações › Inteligência Artificial: Anthropic, Gemini ou qualquer servidor compatível com a API da OpenAI (Ollama local ou o LLM da intranet).',
            },
            {
              type: 'table',
              headers: ['Ponto de uso', 'Etapa', 'Função'],
              rows: [
                ['`theme_candidates`', 'Refinamento de Parâmetros', 'Gera e especifica variações do tema'],
                ['`probe_query`', 'Exploração Inicial', 'Gera as queries exploratórias'],
                ['`final_query`', 'Exploração Final', 'Gera as três variantes da query final'],
                ['`report_writing`', 'Geração do Relatório', 'Redige as seções analíticas via RAG'],
                ['`report_review`', 'Editor do relatório', 'Segunda opinião opcional na revisão do texto'],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'queries',
      title: 'Geração de queries',
      subsections: [
        {
          title: 'Query builders',
          blocks: [
            {
              type: 'paragraph',
              text: 'A IA não escreve a sintaxe final da API. Ela devolve campos estruturados (termos de título, resumo, classificação etc.), e um query builder específico de cada fonte traduz esses campos. Título e resumo entram combinados com OR; os demais campos, com AND; o intervalo de anos vira um filtro.',
            },
            {
              type: 'table',
              headers: ['Fonte', 'Sintaxe', 'Limite de tamanho'],
              rows: [
                ['OPS (patentes)', 'CQL — `ti = "termo" OR ab = "termo"`', '10.000 caracteres'],
                ['Scopus (artigos)', '`TITLE(("t1" OR "t2"))`, `ABS(...)`, `SUBJAREA(CÓDIGO)`, termos sempre entre aspas', '10.000 caracteres'],
                ['Lens (patentes/acadêmico)', 'query_string / bool-query do Elasticsearch', '50.000 caracteres'],
              ],
            },
            {
              type: 'paragraph',
              text: 'Campos editados manualmente na tela são reconstruídos pelo mesmo builder, sem chamar a IA de novo.',
            },
          ],
        },
        {
          title: 'Função de complexidade',
          blocks: [
            {
              type: 'paragraph',
              text: 'Queries longas e muito aninhadas não trazem mais resultados: elas quebram o parser das APIs remotas ou zeram a busca. Por isso, toda query gerada pela IA passa por uma nota de complexidade de 0 a 100 antes de ser enviada.',
            },
            {
              type: 'code',
              caption: 'Nota = combinação ponderada de quatro sub-notas (cada uma limitada a 100)',
              code: `operadores  (AND/OR/NOT, base 10)       × 0,2
aninhamento (profundidade de parênteses, base 5) × 0,3
termos      (termos entre aspas, base 20) × 0,3
tamanho     (caracteres, base 1000)       × 0,2`,
            },
            {
              type: 'table',
              headers: ['Nota', 'Nível'],
              rows: [
                ['< 25', 'Simples'],
                ['25 – 49', 'Moderado'],
                ['50 – 74', 'Complexo'],
                ['≥ 75', 'Muito Complexo'],
              ],
            },
            {
              type: 'paragraph',
              text: 'Se a nota passa do limite (`llm_max_query_complexity`, padrão 0,6 → 60/100), o prompt é reenviado pedindo simplificação, citando o que estava complexo demais. São até 3 tentativas. Se nenhuma ficar abaixo do limite, o sistema usa a menos complexa e mostra um aviso na tela, em vez de falhar.',
            },
          ],
        },
        {
          title: 'Variantes da query final',
          blocks: [
            {
              type: 'table',
              headers: ['Variante', 'Estratégia', 'Termos oferecidos à IA'],
              rows: [
                ['Específica', 'Alta precisão: só os conceitos centrais, combinados com AND; grupos OR de 3–4 termos', 'Score normalizado > 0,4'],
                ['Balanceada', 'Equilíbrio entre cobertura e precisão; grupos OR de 4–6 termos, 1–2 combinações AND', 'Score normalizado > 0,3'],
                ['Ampla', 'Alta cobertura: todos os termos acima do limiar, mínimo de AND', 'Score normalizado > 0,2'],
              ],
            },
            {
              type: 'paragraph',
              text: 'O score normalizado é a posição do termo entre o menor e o maior score dos termos marcados (min-max, 0 a 1). No máximo 20 termos vão para o prompt. Para patentes, a IA também recebe os códigos IPC/CPC realmente observados na busca exploratória, e só pode usar esses.',
            },
          ],
        },
      ],
    },
    {
      id: 'buscas',
      title: 'Buscas',
      subsections: [
        {
          title: 'Busca exploratória (probe)',
          blocks: [
            {
              type: 'paragraph',
              text: 'Traz uma amostra pequena (`probe_top_k`, padrão 10) diversificada por ano, para não ficar enviesada para os documentos mais recentes. Documentos em outro idioma são filtrados. Antes da extração de termos, um filtro de relevância compara cada documento ao tema (similaridade de cosseno ≥ `relevance_threshold`, padrão 0,4).',
            },
          ],
        },
        {
          title: 'Busca final',
          blocks: [
            {
              type: 'list',
              items: [
                'Baixa um volume maior de documentos, com paginação adaptada a cada API, e informa também o total real que a base tem para a query. O quadro de busca do relatório usa o total real; as análises usam a amostra baixada.',
                'Na OPS, as estatísticas (depositantes, CPC, patentes por ano) vêm agregadas.',
                'No Scopus, a contagem por ano, base da curva S de artigos, é refeita em caso de falha de rede e nunca registrada como zero. Um ano que falha de vez é omitido, para não criar um "vale" falso na curva.',
                'Depositantes com nome em escrita não latina (chinês, japonês, coreano) usam a forma latinizada, porque o LaTeX não compila esses caracteres.',
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'estatistica',
      title: 'Inferência estatística',
      subsections: [
        {
          title: 'Saturação da amostra (Chao1)',
          blocks: [
            {
              type: 'paragraph',
              text: 'Na Criação de Gráficos, o sistema verifica se a amostra baixada já cobre a diversidade real de depositantes, instituições, CPCs e áreas, ou se ainda há muita coisa não observada. O estimador Chao1 estima a riqueza total a partir dos itens vistos uma vez (f1) e duas vezes (f2):',
            },
            {
              type: 'code',
              code: 'S_chao1 = S_obs + f1·(f1 − 1) / (2·(f2 + 1))\nsaturação = S_obs / S_chao1',
            },
            {
              type: 'paragraph',
              text: 'A amostra é considerada insuficiente se a saturação for menor que 0,5, se mais de 70% dos itens aparecerem uma única vez (f1_ratio > 0,7) ou se f2 < 5. Nesse caso, o serviço repete a busca final pedindo mais resultados, até saturar ou até o tempo configurado acabar.',
            },
          ],
        },
        {
          title: 'Estabilidade dos rankings (bootstrap)',
          blocks: [
            {
              type: 'paragraph',
              text: 'Para cada item do top-10, o sistema faz 1.000 reamostragens e mede em quantas ele continua no top-10. Um ranking que muda muito entre reamostragens indica que a amostra ainda é pequena para aquele agregado. Isso é esperado em depositantes e instituições, que têm cauda longa, e raro em CPC e áreas de estudo, que têm poucas categorias.',
            },
          ],
        },
      ],
    },
    {
      id: 'curva-s',
      title: 'Curva S e ciclo de vida',
      subsections: [
        {
          title: 'Modelo',
          blocks: [
            {
              type: 'paragraph',
              text: 'A curva logística de Fisher-Pry é ajustada ao volume acumulado de documentos por ano. São necessários pelo menos 2 anos distintos com dados.',
            },
            {
              type: 'code',
              code: 'N(t) = K / (1 + e^(−r·(t − t0)))\n\nK  = platô de saturação (total estimado quando a tecnologia amadurecer)\nr  = taxa de crescimento\nt0 = ponto de inflexão (ano de crescimento máximo, N = K/2)',
            },
          ],
        },
        {
          title: 'Pontos de leitura',
          blocks: [
            {
              type: 'table',
              headers: ['Ponto', 'Definição', 'Fração de K'],
              rows: [
                ['GP — Ponto de Crescimento', 'Fim da fase embrionária', '10%'],
                ['MP — Ponto Médio', 'Inflexão (t0): taxa anual máxima', '50%'],
                ['SP — Ponto de Saturação', 'Início da maturidade', '90%'],
              ],
            },
            {
              type: 'paragraph',
              text: 'Um ponto calculado depois do último ano observado é uma projeção. A parte tracejada do gráfico cobre os "Anos para projetar" escolhidos na Análise de Resultados (padrão 5), e só é desenhada quando o ajuste é confiável.',
            },
            {
              type: 'paragraph',
              text: 'O estágio do ciclo de vida (Emergente, Crescimento, Maturidade ou Saturação) é calculado em Python a partir de GP/MP/SP da curva de patentes e passado pronto ao LLM, que não o deduz sozinho.',
            },
          ],
        },
        {
          title: 'Quando o ajuste não é confiável',
          blocks: [
            {
              type: 'table',
              headers: ['Critério', 'Limite'],
              rows: [
                ['R² do ajuste', 'abaixo de 0,90'],
                ['Saturação alta com poucos dados (sobreajuste)', 'saturação > 85% com menos de 5 anos observados'],
                ['Taxa de crescimento sem sentido físico', 'r ≤ 0'],
                ['Taxa implausivelmente alta (curva em degrau)', 'r > 5,0'],
              ],
            },
            {
              type: 'note',
              text: 'Nesses casos o gráfico mostra um aviso sobreposto explicando o motivo, e a legenda da curva S aparece na tela de Análise de Resultados. Se o ajuste nem converge, a série ainda está em fase inicial demais para estimar K, e o gráfico é pulado.',
            },
          ],
        },
      ],
    },
    {
      id: 'graficos',
      title: 'Gráficos gerados',
      subsections: [
        {
          title: 'Whitelist do relatório',
          blocks: [
            {
              type: 'paragraph',
              text: 'Os gráficos são gerados a partir dos dados já compilados da busca final (nenhum dispara busca nova), enviados ao MinIO e registrados com um resumo numérico que o relatório usa para comentar cada figura. Só estes 8 entram no relatório:',
            },
            {
              type: 'table',
              headers: ['Gráfico', 'Patentes', 'Artigos'],
              rows: [
                ['Histórico por ano', 'Depósitos por ano', 'Publicações por ano'],
                ['Top 10', 'Depositantes', 'Instituições'],
                ['Quadro top 10', 'Classificações CPC', 'Áreas de estudo'],
                ['Curva S', 'Informações tecnológicas', 'Informações científicas'],
              ],
            },
          ],
        },
      ],
    },
  ],
}
