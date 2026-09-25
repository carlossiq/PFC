import type { DocPageData } from './types'

export const introPage: DocPageData = {
  title: 'Introdução',
  description:
    'O AGIA conduz uma prospecção tecnológica completa, do tema de pesquisa até um relatório REPTEC compilado em PDF, com a IA propondo e o usuário validando cada etapa.',
  sections: [
    {
      id: 'o-que-e',
      title: 'O que o sistema faz',
      subsections: [
        {
          title: 'Em uma frase',
          blocks: [
            {
              type: 'paragraph',
              text: 'A partir de um tema, o sistema monta e executa buscas em bases de patentes e artigos, extrai termos relevantes dos resultados, refina a busca, analisa o volume encontrado (rankings, distribuições, curva S) e redige um relatório técnico editável no padrão REPTEC da AGITEC.',
            },
          ],
        },
        {
          title: 'As quatro etapas do fluxo',
          blocks: [
            {
              type: 'table',
              headers: ['Etapa', 'O que acontece'],
              rows: [
                ['1. Input Inicial', 'Tema, descrição, palavras-chave e área de estudo. Opcionalmente, a IA sugere variações mais específicas do tema.'],
                ['2. Exploração Inicial', 'A IA gera queries exploratórias ("probe") para patentes e artigos, a busca traz uma amostra pequena e o NLP local extrai termos candidatos dela.'],
                ['3. Exploração Final', 'Com os termos escolhidos, a IA gera a query final (específica, balanceada ou ampla). A busca final traz o volume completo, seguida de inferência estatística e gráficos.'],
                ['4. Geração do Relatório', 'Formulário do REPTEC, geração das seções (fixas + IA com RAG), montagem do .tex, edição, revisão e compilação para PDF.'],
              ],
            },
          ],
        },
        {
          title: 'Princípios',
          blocks: [
            {
              type: 'list',
              items: [
                'Humano no circuito: nenhuma query é executada e nenhuma seção entra no relatório sem que o usuário possa revisar, editar ou gerar de novo.',
                'IA só onde agrega: refino de tema, geração de queries e redação das seções analíticas. Extração de termos, estatística, curva S, ciclo de vida, citações e formatação são calculados de forma determinística.',
                'Nada inventado no relatório: o texto da IA é ancorado nos documentos recuperados (RAG), citações que não existem nas fontes são removidas e os números vêm dos gráficos já calculados.',
                'Reaproveitamento: o app só chama a IA de novo quando algo do qual a etapa depende mudou.',
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'mapa',
      title: 'Mapa da documentação',
      subsections: [
        {
          title: 'Onde encontrar cada assunto',
          blocks: [
            {
              type: 'table',
              headers: ['Página', 'Conteúdo'],
              rows: [
                ['Guia do Usuário', 'Passo a passo de cada tela do fluxo, do Input Inicial ao editor do relatório.'],
                ['Pipeline de Prospecção', 'Como os dados fluem pelo sistema: queries, função de complexidade, buscas, inferência estatística e curva S.'],
                ['Extração de Termos', 'O processo de extração (PatternRank, BM25F, KeyBERT, RRF, C-value), os modelos KeyBERT disponíveis e os parâmetros ajustáveis.'],
                ['Relatório e LaTeX', 'Estrutura do REPTEC, macros e pacotes LaTeX aceitos no editor, escapes e a revisão automática.'],
                ['Erros e Soluções', 'Mensagens de erro comuns, a causa provável e o que fazer.'],
                ['Referência da API', 'Rotas do backend agrupadas por módulo.'],
                ['FAQ', 'Dúvidas frequentes sobre o comportamento do app.'],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'glossario',
      title: 'Glossário',
      subsections: [
        {
          title: 'Termos usados no app',
          blocks: [
            {
              type: 'table',
              headers: ['Termo', 'Significado'],
              rows: [
                ['Sessão', 'Uma prospecção completa (tema, queries, resultados, gráficos e relatório). Fica pendente até o .tex ser montado; depois, concluída.'],
                ['Query probe', 'Query exploratória da Exploração Inicial, feita para trazer uma amostra pequena e precisa de documentos.'],
                ['Query final', 'Query da Exploração Final, construída com os termos extraídos, em uma de três variantes de abrangência.'],
                ['OPS', 'Open Patent Services, a API de patentes do Escritório Europeu de Patentes (EPO).'],
                ['CPC / IPC', 'Classificações de patentes. A OPS devolve IPC na busca final, mas o relatório as trata como CPC.'],
                ['Curva S', 'Curva logística (Fisher-Pry) ajustada ao volume acumulado de documentos por ano, usada para estimar o estágio de maturidade da tecnologia.'],
                ['RAG', 'Geração aumentada por recuperação: antes de escrever uma seção, o sistema recupera os trechos mais relevantes dos documentos da sessão e só esse contexto vai para o LLM.'],
                ['REPTEC', 'Relatório de Prospecção Tecnológica, no formato padronizado da AGITEC.'],
                ['Ponto de uso', 'Cada lugar do sistema que chama um LLM (refino de tema, query probe, query final, redação e revisão do relatório). Cada um pode usar um modelo diferente.'],
              ],
            },
          ],
        },
      ],
    },
  ],
}
