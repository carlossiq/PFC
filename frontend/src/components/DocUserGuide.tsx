interface GuideNote {
  text: string
}

interface GuideSubsection {
  title: string
  paragraphs: string[]
  notes?: GuideNote[]
  inProgress?: boolean
}

interface GuideSection {
  id: string
  title: string
  intro?: string
  subsections: GuideSubsection[]
}

const sections: GuideSection[] = [
  {
    id: 'input-inicial',
    title: 'Etapa 1 — Input Inicial',
    subsections: [
      {
        title: 'Preenchendo o tema',
        paragraphs: [
          'Toda sessão começa aqui: Tema (obrigatório), Descrição, Palavras-chave e Área de Estudo. Nenhuma dessas informações é enviada ao servidor enquanto a sessão não é salva ou finalizada — até lá, tudo fica no navegador.',
          '"Refinar parâmetros" leva para a etapa seguinte, onde a IA sugere variações mais específicas do tema. "Gerar Query" pula esse refinamento e vai direto para a Exploração Inicial, usando o tema exatamente como digitado.',
        ],
        notes: [
          { text: 'Editar qualquer campo aqui invalida o que já foi refinado nas etapas seguintes — veja a FAQ sobre isso.' },
        ],
      },
      {
        title: 'Refinamento de Parâmetros',
        paragraphs: [
          'A IA gera 4 variações mais específicas do tema. É possível escolher uma delas, editá-la manualmente (sem custo de IA), ou pedir "Especificar" para a IA refinar ainda mais a variação selecionada.',
          '"Gerar Outros Parâmetros" pede um novo conjunto de variações. Reabrir essa tela sem ter mudado nada no Input Inicial reaproveita as variações já geradas, sem chamar a IA de novo.',
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
        paragraphs: [
          'Duas seções independentes: Patentes (busca via OPS) e Artigos (busca via Scopus). Cada uma gera queries candidatas por IA, que podem ser editadas manualmente ou regeneradas com "Gerar outras".',
          '"Próximo" executa a busca de verdade com a query escolhida. Se a mesma query já foi buscada antes, o app reaproveita os resultados em vez de buscar de novo.',
        ],
      },
      {
        title: 'Resultados Iniciais',
        paragraphs: [
          'Tela somente leitura com os resultados da busca inicial de patentes e artigos.',
        ],
        notes: [
          {
            text: 'O botão "Finalizar Sessão" aqui já salva a sessão como concluída no sistema — hoje esse é o ponto real de conclusão, mesmo havendo mais duas etapas na barra de progresso depois dele.',
          },
        ],
      },
      {
        title: 'Amostragem de Termos',
        paragraphs: [
          'Termos são extraídos automaticamente dos resultados (sem uso de IA generativa, por isso não há botão de "gerar outros" aqui). Marque ou desmarque quais termos entram na query final e escolha o tipo de query (específica, balanceada ou genérica).',
          '"Gerar Query Final" só chama a IA de novo se os termos marcados ou o tipo escolhido mudaram desde a última geração.',
        ],
      },
    ],
  },
  {
    id: 'exploracao-final',
    title: 'Etapa 3 — Exploração Final',
    subsections: [
      {
        title: 'Confirmação da Query Final',
        paragraphs: [
          'Mostra a query final gerada por fonte (patentes e artigos). "Gerar de novo" sempre chama a IA, sem checagem de reuso. "Confirmar e buscar" sempre executa a busca final, mesmo que a mesma query já tenha sido buscada antes.',
        ],
      },
      {
        title: 'Análise de Resultados',
        paragraphs: [
          'Estatísticas agregadas dos resultados finais: depositantes e códigos CPC mais frequentes para patentes; instituições e áreas de estudo para artigos.',
          'Um gráfico de Curva S (Fisher-Pry) é gerado automaticamente por fonte a partir da distribuição por ano, com opção de baixar o gráfico em PNG.',
        ],
      },
    ],
  },
  {
    id: 'relatorio',
    title: 'Etapa 4 — Geração do Relatório',
    subsections: [
      {
        title: 'Reportar',
        paragraphs: [
          'Esta etapa ainda está em construção: por enquanto ela só mostra os botões de navegação, sem gerar nenhum relatório. Como a sessão já é marcada como concluída na etapa "Resultados Iniciais" (ver acima), chegar até aqui não é hoje um requisito para considerar a pesquisa finalizada.',
        ],
        inProgress: true,
      },
    ],
  },
  {
    id: 'geral',
    title: 'Comportamentos gerais',
    subsections: [
      {
        title: 'Salvar Progresso',
        paragraphs: [
          'Disponível a qualquer momento durante a prospecção (exceto enquanto a IA está processando algo). A primeira vez que você salva, uma sessão é criada; salvamentos seguintes atualizam essa mesma sessão. O tema é obrigatório para poder salvar.',
        ],
      },
      {
        title: 'Voltar / Avançar',
        paragraphs: [
          'Navegar entre etapas não descarta o que já foi gerado — o conteúdo fica guardado enquanto a sessão está aberta, e cada etapa só oferece gerar de novo se algo do qual ela depende tiver mudado.',
        ],
      },
      {
        title: 'Retomando uma sessão salva',
        paragraphs: [
          'Pela tela de Busca é possível continuar uma sessão salva anteriormente. Hoje a sessão sempre reabre na primeira etapa (não no ponto exato em que você parou), e os resultados de busca da Exploração Inicial não ficam salvos — pode ser necessário confirmar a query de novo para trazê-los de volta.',
        ],
      },
      {
        title: 'Saindo de uma prospecção em andamento',
        paragraphs: [
          'Enquanto uma sessão está em andamento, o menu lateral fica bloqueado e o navegador avisa antes de fechar a aba, para evitar perda de progresso não salvo.',
        ],
      },
    ],
  },
]

export function DocUserGuide() {
  return (
    <div className="w-full">
      <h2 className="text-3xl font-bold mb-2 text-gray-900">Guia do Usuário</h2>
      <p className="text-base text-gray-600 mb-8">
        Passo a passo do fluxo de prospecção, da criação da sessão até a conclusão. O produto está em
        desenvolvimento, então cada seção indica o que já funciona hoje.
      </p>

      <div className="space-y-10">
        {sections.map((section) => (
          <div key={section.id}>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">{section.title}</h3>
            {section.intro && <p className="text-base text-gray-700 mb-3">{section.intro}</p>}

            <div className="ml-4 space-y-6">
              {section.subsections.map((sub) => (
                <div key={sub.title}>
                  <p className="text-lg font-medium text-gray-800 mb-1 flex items-center gap-2">
                    {sub.title}
                    {sub.inProgress && (
                      <span className="text-sm font-normal text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                        em construção
                      </span>
                    )}
                  </p>
                  <div className="space-y-2">
                    {sub.paragraphs.map((p, i) => (
                      <p key={i} className="text-base text-gray-600 leading-relaxed">
                        {p}
                      </p>
                    ))}
                  </div>
                  {sub.notes && (
                    <div className="mt-2 space-y-1">
                      {sub.notes.map((note, i) => (
                        <p
                          key={i}
                          className="text-base text-gray-700 bg-gray-100 border-l-2 border-gray-400 rounded-r-md px-3 py-2"
                        >
                          {note.text}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
