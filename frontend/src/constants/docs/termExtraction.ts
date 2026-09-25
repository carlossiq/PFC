import type { DocPageData } from './types'

// Espelha services/nlp/term_extraction.py (pipeline atual), core/config.py
// (defaults), db/config_seed.py (o que é editável em Configurações),
// config/pos_patterns.json e config/string_quality_filter.json. Detalhes
// completos em EXTRACAO_TERMOS_NGRAMAS.md e RELATORIO_TECNICO_SISTEMA.md §5.
export const termExtractionPage: DocPageData = {
  title: 'Extração de Termos',
  description:
    'Como a Amostragem de Termos transforma os títulos e resumos da busca exploratória em uma lista ranqueada de termos, sem IA generativa, e como ajustar esse processo.',
  sections: [
    {
      id: 'visao-geral',
      title: 'Visão geral',
      subsections: [
        {
          title: 'Por que extrair termos',
          blocks: [
            {
              type: 'paragraph',
              text: 'A query exploratória nasce só do tema digitado. Os documentos que ela traz usam o vocabulário real da área: nomes técnicos, variantes e siglas que o usuário nem sempre conhece. Extrair esses termos e oferecê-los à IA na query final amplia a cobertura da busca com termos que de fato aparecem na literatura.',
            },
            {
              type: 'paragraph',
              text: 'A extração roda localmente, separada para patentes (OPS) e artigos (Scopus), sobre título + resumo dos documentos aprovados pelo filtro de relevância. Como não usa IA generativa, a tela não tem botão de "gerar outros": o resultado é determinístico para a mesma amostra.',
            },
          ],
        },
        {
          title: 'O processo em 9 passos',
          blocks: [
            {
              type: 'list',
              ordered: true,
              items: [
                'Candidatos (PatternRank): frases nominais maximais com o padrão gramatical `<J.*>*<N.*>+` (adjetivos opcionais seguidos de substantivos), extraídas com spaCy `en_core_web_sm`. Candidatos com mais de 5 palavras são cortados.',
                'Filtros: remove unigramas idênticos aos termos do próprio usuário e aplica os filtros de qualidade de texto (ver abaixo) antes de contar frequências.',
                'Canal léxico (BM25F): relevância estatística do termo, ponderada por campo. Título pesa 3,0 e resumo, 1,0.',
                'Canal semântico (KeyBERT): similaridade de cosseno entre o embedding do termo e o do texto.',
                '1ª fusão (RRF): combina as posições do termo nos dois rankings, `RRF(t) = Σ 1/(k + posição)`, com k = 60. Fundir posições, e não notas, evita que um canal com escala maior domine o outro. O resultado é o `salience_score`.',
                'Qualidade estrutural: prefere n-gramas maiores (penaliza unigramas, bonifica trigramas) e penaliza padrões gramaticais ruins, como verbo + verbo.',
                '2ª fusão (RRF): saliência × qualidade estrutural, gerando o `final_rrf_score`.',
                'C-value: trata termos aninhados. Um termo contido em outro de posição melhor é descartado; por exemplo, "ultrafiltration membrane" some quando "composite ultrafiltration membrane" já está na lista.',
                'Corte: mantém termos com `final_rrf_score ≥ 0,024`, completa até um piso de 10 termos se o limiar cortar demais e limita a 60 termos.',
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'keybert',
      title: 'Modelos KeyBERT',
      subsections: [
        {
          title: 'Modelos disponíveis',
          blocks: [
            {
              type: 'paragraph',
              text: 'O KeyBERT usa um modelo sentence-transformers para gerar os embeddings. O modelo é definido em Configurações › Geral › "Modelo do KeyBERT" (`llm_keybert_model`).',
            },
            {
              type: 'table',
              headers: ['Modelo', 'Perfil', 'Quando usar'],
              rows: [
                ['`distiluse-base-multilingual-cased-v2` (padrão)', 'Genérico, multilíngue', 'Uso geral; temas digitados em português com documentos em inglês'],
                ['`all-mpnet-base-v2`', 'Inglês, alta qualidade em textos técnicos', 'Prospecções focadas em patentes (OPS)'],
                ['`allenai/specter`', 'Treinado em artigos acadêmicos', 'Prospecções focadas em literatura científica (Scopus)'],
              ],
            },
            {
              type: 'warning',
              text: 'O modelo é carregado uma única vez, na inicialização do backend: trocar a configuração só tem efeito depois de reiniciar o servidor. Na primeira vez, o modelo novo é baixado do Hugging Face, o que exige acesso à internet.',
            },
            {
              type: 'note',
              text: 'O mesmo modelo gera os embeddings do filtro de relevância documento-tema e do RAG do relatório. Depois de trocá-lo, os índices de RAG de sessões antigas ficam em outro espaço vetorial; regenere as seções do relatório dessas sessões.',
            },
          ],
        },
      ],
    },
    {
      id: 'filtros',
      title: 'Filtros de qualidade',
      subsections: [
        {
          title: 'Listas de palavras (config/string_quality_filter.json)',
          blocks: [
            {
              type: 'table',
              headers: ['Filtro', 'Regra', 'Exemplos'],
              rows: [
                ['`boundary_stopwords`', 'Descarta o termo se a primeira ou a última palavra estiver na lista', '"the", "of", "based", "related", "high", "new"'],
                ['`patent_structural_words`', 'Descarta se qualquer palavra do termo estiver na lista (jargão de patente)', '"wherein", "comprising", "said", "plurality", "configured"'],
                ['`scholarly_structural_words`', 'Descarta se qualquer palavra estiver na lista (jargão acadêmico)', '"proposed", "results", "method", "framework", "novel"'],
              ],
            },
          ],
        },
        {
          title: 'Padrões gramaticais ruins (config/pos_patterns.json)',
          blocks: [
            {
              type: 'table',
              headers: ['Tamanho', 'Padrões penalizados'],
              rows: [
                ['Bigramas', 'VERB VERB, ADV VERB, VERB ADJ, ADJ VERB'],
                ['Trigramas', 'VERB VERB NOUN, ADV VERB NOUN, ADV ADJ NOUN, VERB NOUN VERB'],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'parametros',
      title: 'Parâmetros ajustáveis',
      subsections: [
        {
          title: 'Configurações › Extração de Termos',
          blocks: [
            {
              type: 'table',
              headers: ['Parâmetro', 'Padrão', 'Efeito'],
              rows: [
                ['Peso do título', '3,0', 'Quanto um termo no título vale mais que no resumo (BM25F)'],
                ['Peso do abstract', '1,0', 'Peso do resumo no BM25F'],
                ['Threshold de score', '0,024', 'Maior → menos termos, só os melhores. Menor → mais termos, incluindo contexto'],
                ['Piso de termos devolvidos', '10', 'Mínimo garantido mesmo quando o threshold corta demais'],
                ['Penalidade de unigrama', '−0,4', 'Desfavorece termos de uma palavra (genéricos demais)'],
                ['Bônus de bigrama', '0,0', 'Ajuste para termos de duas palavras'],
                ['Bônus de trigrama', '+0,25', 'Favorece termos de três ou mais palavras (mais específicos)'],
                ['Penalidade de bigrama/trigrama ruim', '−0,8', 'Aplicada quando o termo casa um padrão gramatical ruim'],
                ['BM25 k1 / b', '1,2 / 0,75', 'Saturação de frequência e normalização por tamanho do texto (valores clássicos do Okapi BM25)'],
                ['RRF k', '60', 'Suaviza a fusão de rankings. Maior → posições diferentes pesam menos'],
                ['Frequência mínima (C-value)', '1', 'Candidatos que aparecem menos vezes que isso são descartados'],
              ],
            },
            {
              type: 'note',
              text: 'Os bônus e penalidades não somam à nota final: eles ordenam os candidatos no canal de qualidade estrutural, que entra na 2ª fusão RRF.',
            },
          ],
        },
        {
          title: 'Configurações › Relevância & Qualidade',
          blocks: [
            {
              type: 'table',
              headers: ['Parâmetro', 'Padrão', 'Efeito'],
              rows: [
                ['Threshold de relevância', '0,4', 'Similaridade mínima documento × tema para o documento entrar na extração'],
                ['Complexidade máxima de query', '0,6', 'Limite da função de complexidade (ver Pipeline de Prospecção)'],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'uso',
      title: 'Usando os termos',
      subsections: [
        {
          title: 'Na tela Amostragem de Termos',
          blocks: [
            {
              type: 'list',
              items: [
                'Marque os termos que devem entrar na query final. A lista vem ordenada do maior para o menor score (`final_rrf_score`), exibido ao lado de cada termo.',
                'Escolha a variante (específica, balanceada ou ampla). Os scores dos termos marcados são normalizados para 0–1 dentro do próprio lote, e cada variante só recebe os termos acima do seu limiar: 0,4, 0,3 e 0,2, respectivamente. Por isso, a variante específica usa menos termos que a ampla.',
                'A query final só é gerada de novo se os termos marcados ou a variante mudarem desde a última geração.',
              ],
            },
          ],
        },
      ],
    },
  ],
}
