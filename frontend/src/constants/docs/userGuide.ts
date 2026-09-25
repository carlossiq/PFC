import type { DocPageData } from './types'

export const userGuidePage: DocPageData = {
  title: 'Guia do Usuário',
  description:
    'Passo a passo do fluxo de prospecção, da criação da sessão até o relatório compilado. Para entender o que acontece por trás de cada etapa, veja Pipeline de Prospecção.',
  sections: [
    {
      id: 'input-inicial',
      title: 'Etapa 1 — Input Inicial',
      subsections: [
        {
          title: 'Preenchendo o tema',
          blocks: [
            {
              type: 'paragraph',
              text: 'Toda sessão começa aqui: Tema (obrigatório), Descrição, Palavras-chave e Área de Estudo. Nada é enviado ao servidor enquanto a sessão não é salva; até lá, tudo fica no navegador.',
            },
            {
              type: 'paragraph',
              text: '"Refinar parâmetros" leva à etapa seguinte, onde a IA sugere variações mais específicas do tema. "Gerar Query" pula esse refinamento e vai direto para a Exploração Inicial, usando o tema exatamente como digitado.',
            },
            {
              type: 'note',
              text: 'Editar qualquer campo aqui invalida o que já foi refinado nas etapas seguintes. Veja a FAQ sobre isso.',
            },
          ],
        },
        {
          title: 'Refinamento de Parâmetros',
          blocks: [
            {
              type: 'paragraph',
              text: 'A IA gera 4 variações mais específicas do tema. É possível escolher uma delas, editá-la manualmente com "Editar" (sem custo de IA) ou usar "Especificar" para a IA refinar ainda mais a variação selecionada. Quanto mais específica, mais afunilada a busca, que pode acabar retornando poucos resultados.',
            },
            {
              type: 'paragraph',
              text: 'Reabrir essa tela sem ter mudado nada no Input Inicial reaproveita as variações já geradas, sem chamar a IA de novo. Para obter variações novas, altere o Input Inicial e clique em "Refinar parâmetros" outra vez.',
            },
          ],
        },
      ],
    },
    {
      id: 'exploracao-inicial',
      title: 'Etapa 2 — Exploração Inicial',
      subsections: [
        {
          title: 'Escolha da Query',
          blocks: [
            {
              type: 'paragraph',
              text: 'Duas seções independentes: Patentes (OPS) e Artigos (Scopus). Cada uma mostra queries candidatas geradas pela IA, que podem ser editadas campo a campo ou geradas de novo. O medidor de complexidade avisa quando uma query tende a falhar ou zerar na API.',
            },
            {
              type: 'paragraph',
              text: '"Próximo" executa a busca exploratória com a query escolhida. Se a mesma query já foi buscada antes, o app reaproveita os resultados.',
            },
          ],
        },
        {
          title: 'Resultados Iniciais',
          blocks: [
            {
              type: 'paragraph',
              text: 'Tela somente leitura com a amostra de patentes e artigos trazida pela busca exploratória.',
            },
          ],
        },
        {
          title: 'Amostragem de Termos',
          blocks: [
            {
              type: 'paragraph',
              text: 'Os termos são extraídos automaticamente dos títulos e resumos da amostra, por NLP local e sem IA generativa, e aparecem ordenados por score. Marque os que devem entrar na query final e escolha a variante: específica, balanceada ou ampla.',
            },
            {
              type: 'paragraph',
              text: '"Gerar Query Final" só chama a IA de novo se os termos marcados ou a variante mudaram desde a última geração. Detalhes em Extração de Termos.',
            },
          ],
        },
      ],
    },
    {
      id: 'exploracao-final',
      title: 'Etapa 3 — Exploração Final',
      subsections: [
        {
          title: 'Revisão da Query Final',
          blocks: [
            {
              type: 'paragraph',
              text: 'Mostra a query final gerada para cada fonte. Ela pode ser editada ou gerada de novo antes de confirmar. "Confirmar e buscar" sempre executa a busca final, mesmo que a mesma query já tenha sido buscada.',
            },
          ],
        },
        {
          title: 'Análise de Resultados',
          blocks: [
            {
              type: 'paragraph',
              text: 'Estatísticas agregadas da busca final: depositantes e códigos CPC mais frequentes para patentes; instituições e áreas de estudo para artigos. São mostrados tanto o total real da base quanto o tamanho da amostra analisada.',
            },
            {
              type: 'paragraph',
              text: 'A curva S (Fisher-Pry) é gerada automaticamente por fonte a partir da distribuição por ano. Nela é possível ajustar "Anos para projetar" e baixar o gráfico em PNG. A legenda explica os pontos GP, MP e SP e o aviso de ajuste pouco confiável.',
            },
          ],
        },
        {
          title: 'Criação de Gráficos',
          blocks: [
            {
              type: 'paragraph',
              text: 'Tela automática: salva a sessão, roda a inferência estatística (saturação da amostra e estabilidade dos rankings) e gera os gráficos de top depositantes/instituições, distribuição CPC/áreas de estudo e histórico anual. Ao terminar, avança sozinha para a Geração do Relatório.',
            },
            {
              type: 'note',
              text: 'Se algo falhar, a tela mostra o erro com "Tentar novamente". Gráficos já gerados são reaproveitados: voltar a esta tela sem mudar a busca final não refaz o trabalho.',
            },
          ],
        },
      ],
    },
    {
      id: 'relatorio',
      title: 'Etapa 4 — Geração do Relatório',
      subsections: [
        {
          title: 'Metadados do REPTEC',
          blocks: [
            {
              type: 'paragraph',
              text: 'Preencha número e ano do relatório, destinatário, objetivo (opcional; se vazio, a IA escreve), local, referências administrativas (ex.: "DIEx Nº 115-A3/DCT de 6 de janeiro de 2023"), bibliografia adicional em ABNT e as assinaturas (Elaborado, Revisado e Aprovado por: nome, posto/graduação e função).',
            },
            {
              type: 'note',
              text: 'Os campos são validados: valores de preenchimento como "teste" ou "sdasd" são recusados. Elaborado por é obrigatório; Revisado e Aprovado por podem ficar vazios.',
            },
          ],
        },
        {
          title: 'Seções do relatório',
          blocks: [
            {
              type: 'paragraph',
              text: '"Gerar Seções" monta as seções fixas e gera, uma a uma, as seções de IA (Objetivo, Introdução, Informações Científicas, Informações Tecnológicas, Tendências e Ciclo de Vida, Conclusão). Cada seção mostra seu andamento (recuperando contexto → gerando) e pode ser gerada de novo individualmente. Se uma falhar, "Continuar geração" retoma de onde parou.',
            },
          ],
        },
        {
          title: 'Montar .tex',
          blocks: [
            {
              type: 'paragraph',
              text: 'Monta o documento LaTeX com as seções e os gráficos e abre o editor.',
            },
            {
              type: 'warning',
              text: 'Montar o .tex conclui a sessão: a partir daí não é mais possível editar a pesquisa (queries, termos, buscas), só o texto do relatório.',
            },
          ],
        },
        {
          title: 'Editor do documento',
          blocks: [
            {
              type: 'list',
              items: [
                'Edite o `.tex` diretamente. Macros, pacotes e escapes estão em Relatório e LaTeX.',
                'Painel de imagens (ícone de imagem na barra lateral): insere gráficos, figuras fixas e anexos no `.tex`, abre ou baixa cada imagem. Em "Anexos", o botão "+" envia imagens próprias.',
                '"Revisão": sugestões de LaTeX, ortografia, acentuação e concordância. Cada uma é aplicada ou ignorada individualmente.',
                '"Compilar" gera o PDF, e "Visualizar PDF" abre a última versão compilada.',
                'O ícone de download baixa um `.zip` com o `.tex` e as imagens, para compilar ou editar fora do sistema.',
                '"Remontar .tex" refaz o documento do zero e descarta as edições manuais.',
                '"Concluir e voltar para Pesquisa" encerra o fluxo e abre a tela de Busca.',
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'geral',
      title: 'Comportamentos gerais',
      subsections: [
        {
          title: 'Salvar Progresso',
          blocks: [
            {
              type: 'paragraph',
              text: 'Disponível durante a prospecção, exceto enquanto a IA está processando algo. A primeira vez que você salva, uma sessão é criada; os salvamentos seguintes atualizam essa mesma sessão. O tema é obrigatório para salvar.',
            },
          ],
        },
        {
          title: 'Voltar / Avançar',
          blocks: [
            {
              type: 'paragraph',
              text: 'Navegar entre etapas não descarta o que já foi gerado. O conteúdo fica guardado enquanto a sessão está aberta, e cada etapa só oferece gerar de novo se algo do qual ela depende tiver mudado.',
            },
          ],
        },
        {
          title: 'Tela de Busca: continuar ou ver relatório',
          blocks: [
            {
              type: 'paragraph',
              text: 'A tela de Busca lista as sessões salvas, com filtro por status (pendentes ou concluídas). "Continuar pesquisa" reabre uma sessão pendente na etapa em que ela foi salva, com documentos e termos restaurados. "Ver Relatório" abre o editor de uma sessão concluída.',
            },
          ],
        },
        {
          title: 'Configurações',
          blocks: [
            {
              type: 'paragraph',
              text: 'Parâmetros agrupados em Geral, Busca, Inteligência Artificial, Extração de Termos, Relevância & Qualidade e Inferência Estatística. Em Inteligência Artificial, cada ponto de uso (refino de tema, queries, redação e revisão do relatório) pode apontar para um modelo diferente.',
            },
          ],
        },
        {
          title: 'Saindo de uma prospecção em andamento',
          blocks: [
            {
              type: 'paragraph',
              text: 'Enquanto uma sessão está em andamento, o menu lateral fica bloqueado e o navegador avisa antes de fechar a aba, para evitar perda de progresso não salvo.',
            },
          ],
        },
      ],
    },
  ],
}
