import type { DocPageData } from './types'

// Espelha config/prompts/report_latex_template.py (preâmbulo, macros,
// seções), app/core/services/report_figures.py (FIGURE_SPECS, rótulos
// fig:/quadro:), report_writer_service.py::escape_latex, o Dockerfile do
// latex-compiler (pacotes instalados) e report_review.py. A lista de pacotes
// "disponíveis/ausentes" foi conferida com kpsewhich no container
// pfc_latex_compiler - refazer a checagem se o Dockerfile mudar.
export const latexPage: DocPageData = {
  title: 'Relatório e LaTeX',
  description:
    'Estrutura do REPTEC gerado pelo sistema e referência do que pode ser usado no editor do `.tex`: macros, pacotes, escapes e o que a revisão automática verifica.',
  sections: [
    {
      id: 'estrutura',
      title: 'Estrutura do REPTEC',
      subsections: [
        {
          title: 'Como cada seção é produzida',
          blocks: [
            {
              type: 'table',
              headers: ['Seção', 'Origem'],
              rows: [
                ['Capa e Sumário', 'Fixas (template). A imagem da capa é definida em Configurações.'],
                ['1 Finalidade', 'Fixa: frase-padrão com o tema e o destinatário do formulário.'],
                ['2 Referências', 'Formulário: referências administrativas (DIEx, Ofício…) que originaram o pedido.'],
                ['3 Objetivo', 'Formulário, se preenchido; senão, gerado pela IA.'],
                ['4 Introdução', 'IA (RAG + LLM).'],
                ['5 Metodologia (5.1 a 5.4)', 'Fixa, com as figuras de Madeo e Kucharavy. O último parágrafo interpola palavras-chave, período e bases da pesquisa.'],
                ['6.1 Informações Científicas', 'IA, com os gráficos de artigos.'],
                ['6.2 Informações Tecnológicas', 'IA, com os gráficos de patentes e o quadro de busca (query + total real).'],
                ['6.3 Tendências e Ciclo de Vida', 'IA, com as curvas S e o estágio do ciclo de vida já calculado.'],
                ['7 Conclusão', 'IA, com estrutura orientada: estágio, destaques e recomendação.'],
                ['8 Referências Bibliográficas', 'Bibliografia da Metodologia + obras realmente citadas pela IA + bibliografia adicional do formulário. O LLM nunca escreve referências.'],
                ['Local, data e assinaturas', 'Formulário: Elaborado / Revisado / Aprovado por, no formato NOME – POSTO/GRAD, com a função abaixo.'],
              ],
            },
          ],
        },
        {
          title: 'Do formulário ao PDF',
          blocks: [
            {
              type: 'list',
              ordered: true,
              items: [
                '"Gerar Seções" monta as seções fixas e, para cada seção de IA, recupera o contexto (RAG) e gera o texto. Cada seção pode ser gerada de novo individualmente.',
                '"Montar .tex" renderiza o template com as seções e os gráficos já existentes. A sessão passa a ser concluída e a pesquisa não pode mais ser editada, só o texto.',
                'No editor, o `.tex` pode ser editado livremente. "Revisão" sugere correções, "Compilar" gera o PDF e o ícone de download baixa um `.zip` (`REPTEC_<num>_<ano>.zip`) com o `.tex` e todas as imagens referenciadas.',
                '"Remontar .tex" refaz o documento do zero com os dados atuais e descarta as edições manuais. É útil quando uma edição impede a compilação.',
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'macros',
      title: 'Macros do template',
      subsections: [
        {
          title: 'Figuras e quadros',
          blocks: [
            {
              type: 'paragraph',
              text: 'O template define duas macros no padrão REPTEC: título acima ("Figura N:" ou "Quadro N:"), imagem centralizada e "Fonte:" abaixo. O primeiro argumento, opcional, é a fonte (padrão "O autor.").',
            },
            {
              type: 'code',
              code: `\\figura[fonte]{título}{arquivo}      % Figura N: título
\\quadroimg[fonte]{título}{arquivo}   % Quadro N: título (não quebra entre páginas)`,
            },
            {
              type: 'code',
              caption: 'Exemplo com rótulo e referência cruzada',
              code: `A Figura~\\ref{fig:patent_yearly_volume} apresenta o histórico de depósitos.

\\figura{Histórico de depósitos de patentes (patentes por ano).\\label{fig:patent_yearly_volume}}{patent_yearly_volume.png}

\\quadroimg[Adaptado de OPS/EPO.]{10 classificações (CPC) mais encontradas.\\label{quadro:patent_top10_heatmap}}{patent_top10_heatmap.png}`,
            },
            {
              type: 'note',
              text: 'O `\\label` vai dentro do título. Rótulos de figura usam o prefixo `fig:` e os de quadro, `quadro:`. Na montagem, "Figura"/"Quadro" antes de cada `\\ref` é corrigido para o tipo certo, com a concordância do artigo (a/o, da/do, na/no…).',
            },
          ],
        },
        {
          title: 'Arquivos de imagem disponíveis',
          blocks: [
            {
              type: 'table',
              headers: ['Arquivo', 'Tipo', 'Conteúdo'],
              rows: [
                ['`patent_yearly_volume.png`', 'Figura', 'Histórico de depósitos de patentes'],
                ['`patent_top_depositants.png`', 'Figura', 'Top 10 depositantes'],
                ['`patent_top10_heatmap.png`', 'Quadro', '10 classificações CPC mais encontradas'],
                ['`patent_s_curve.png`', 'Figura', 'Curva S das informações tecnológicas'],
                ['`article_yearly_volume.png`', 'Figura', 'Histórico de publicações científicas'],
                ['`article_top_institutions.png`', 'Figura', 'Top 10 instituições'],
                ['`article_top10_heatmap.png`', 'Quadro', 'Áreas de estudo'],
                ['`article_s_curve.png`', 'Figura', 'Curva S das informações científicas'],
                ['`madeo.png`, `kucharavy.png`', 'Figura', 'Figuras fixas da Metodologia'],
                ['`anexo-<nome>.png|jpg`', 'Figura', 'Imagens enviadas por você no painel de imagens (até 10 MB, PNG ou JPG)'],
              ],
            },
            {
              type: 'paragraph',
              text: 'O painel de imagens do editor ("Adicionar ao .tex") insere o bloco certo na posição do cursor. Para anexos, o título entra como "Título da figura", para você substituir.',
            },
            {
              type: 'warning',
              text: 'Excluir um anexo que ainda é referenciado no `.tex` faz a compilação falhar com "arquivo não encontrado". Remova a referência antes de excluir.',
            },
          ],
        },
        {
          title: 'Marcadores usados na geração (referência)',
          blocks: [
            {
              type: 'paragraph',
              text: 'O LLM escreve `[[REF:id]]` onde cita uma figura e `[[FIG:id]]` em linha própria onde ela deve aparecer, por exemplo `[[REF:patent_s_curve]]`. Na montagem, esses marcadores são convertidos em `\\ref{…}` e no bloco `\\figura`/`\\quadroimg`. Eles nunca aparecem no `.tex` final e não têm efeito se digitados no editor.',
            },
          ],
        },
      ],
    },
    {
      id: 'pacotes',
      title: 'Pacotes LaTeX',
      subsections: [
        {
          title: 'Já carregados pelo template',
          blocks: [
            {
              type: 'paragraph',
              text: 'Estes pacotes já estão no preâmbulo e podem ser usados diretamente no corpo do documento, sem `\\usepackage`:',
            },
            {
              type: 'table',
              headers: ['Pacote', 'Para que serve no corpo do texto'],
              rows: [
                ['`graphicx`, `float`', '`\\includegraphics`, posicionamento `[H]`'],
                ['`tabularx`, `array`', 'Tabelas com largura fixa e colunas `X`, `p{…}`, `m{…}`'],
                ['`enumitem`', 'Listas `itemize`/`enumerate` com rótulos customizados, ex.: `[label=\\alph*)]`'],
                ['`caption`', '`\\caption`, `\\captionof{quadro}{…}`'],
                ['`hyperref`', '`\\ref`, `\\pageref`, `\\url{…}`, `\\href{url}{texto}` (sem cor nos links)'],
                ['`setspace`', '`\\singlespacing`, `\\onehalfspacing` (o documento usa 1,5)'],
                ['`babel` (brazilian)', 'Hifenização e nomes em português ("Figura", "Sumário")'],
                ['`fancyhdr`, `lastpage`, `titlesec`, `tocloft`', 'Cabeçalho, rodapé "Página x de y", títulos e sumário; já configurados'],
                ['`microtype`, `indentfirst`, `tgtermes`', 'Tipografia, recuo do primeiro parágrafo, fonte Times'],
              ],
            },
          ],
        },
        {
          title: 'Instalados, mas não carregados',
          blocks: [
            {
              type: 'paragraph',
              text: 'O compilador tem as coleções `collection-latex`, `collection-latexrecommended` e `collection-fontsrecommended`. Estes pacotes, por exemplo, funcionam se você adicionar o `\\usepackage` no preâmbulo:',
            },
            {
              type: 'code',
              code: `amsmath, amssymb   % fórmulas e símbolos matemáticos
booktabs           % \\toprule, \\midrule, \\bottomrule
longtable          % tabelas que quebram entre páginas
xcolor, colortbl   % cores, fundo de célula
multicol           % texto em colunas
subcaption         % subfiguras
listings           % código-fonte
tikz               % desenhos`,
            },
          ],
        },
        {
          title: 'Não disponíveis',
          blocks: [
            {
              type: 'warning',
              text: 'O compilador roda sem acesso à internet e não baixa pacotes na hora. Um `\\usepackage` de um pacote não instalado interrompe a compilação com "File <pacote>.sty not found". Exemplos de pacotes ausentes: `multirow`, `makecell`, `siunitx`, `wrapfig`, `ulem`, `soul`. Para instalar outros, é preciso incluí-los no `tlmgr install` de `latex-compiler/Dockerfile` e reconstruir a imagem.',
            },
            {
              type: 'note',
              text: 'O documento é compilado com pdflatex (`latexmk -pdf -halt-on-error`, limite de 120 s). Por isso, `fontspec` e recursos de XeLaTeX/LuaLaTeX não funcionam, e caracteres fora do alfabeto latino (chinês, japonês, cirílico…) não compilam.',
            },
          ],
        },
      ],
    },
    {
      id: 'escrita',
      title: 'Escrevendo no editor',
      subsections: [
        {
          title: 'Caracteres especiais',
          blocks: [
            {
              type: 'table',
              headers: ['Caractere', 'Escreva', 'Observação'],
              rows: [
                ['%', '`\\%`', 'Sem escape, o resto da linha vira comentário'],
                ['&', '`\\&`', 'Sem escape, só é válido dentro de tabelas'],
                ['_', '`\\_`', 'Comum em siglas e nomes de arquivo'],
                ['#', '`\\#`', ''],
                ['$', '`\\$`', 'Sem escape, abre modo matemático'],
                ['{ }', '`\\{ \\}`', ''],
                ['~', '`\\textasciitilde{}`', 'Sozinho, `~` é um espaço que não quebra linha'],
                ['^', '`\\textasciicircum{}`', ''],
                ['\\', '`\\textbackslash{}`', ''],
                ['º ª', 'digite direto', 'Preservados: "DIEx Nº 256", "1º Ten"'],
              ],
            },
            {
              type: 'note',
              text: 'O texto gerado pela IA e os campos do formulário já saem escapados. Só o que você digita no editor precisa de atenção.',
            },
          ],
        },
        {
          title: 'Trechos prontos',
          blocks: [
            {
              type: 'code',
              caption: 'Tabela simples com legenda de Quadro',
              code: `\\begin{table}[H]
  \\centering
  \\captionof{quadro}{Comparativo entre tecnologias.}
  \\begin{tabularx}{\\textwidth}{|l|X|}
    \\hline
    \\textbf{Tecnologia} & \\textbf{Observação} \\\\ \\hline
    Tecnologia A & Maior volume de patentes no período. \\\\ \\hline
    Tecnologia B & Crescimento recente em artigos. \\\\ \\hline
  \\end{tabularx}\\par
  \\vspace{0.2cm}Fonte: O autor.
\\end{table}`,
            },
            {
              type: 'code',
              caption: 'Listas',
              code: `\\begin{itemize}
  \\item Primeiro destaque;
  \\item Segundo destaque.
\\end{itemize}

\\begin{enumerate}[label=\\alph*)]
  \\item primeira recomendação;
  \\item segunda recomendação.
\\end{enumerate}`,
            },
            {
              type: 'code',
              caption: 'Citação no padrão aceito pelo sistema e nova referência',
              code: `... conforme apontado por (SILVA et al., 2021).

% Referências Bibliográficas: cada obra é um \\item da lista da seção 8
\\item SILVA, J. et al. \\textbf{Título da obra}. Periódico, v. 1, n. 2, p. 10--20, 2021.`,
            },
          ],
        },
      ],
    },
    {
      id: 'revisao',
      title: 'Revisão automática',
      subsections: [
        {
          title: 'O que o botão "Revisão" verifica',
          blocks: [
            {
              type: 'list',
              items: [
                'Lint de LaTeX (corpo do documento): chaves e ambientes desbalanceados, `\\ref` sem `\\label` correspondente, imagens inexistentes, caracteres especiais sem escape e erros do último log de compilação.',
                'LanguageTool (pt-BR, configurável em Configurações › Geral): ortografia, acentuação, concordância e gramática. Comandos LaTeX são ignorados na análise.',
                'IA opcional (ponto de uso `report_review`): segunda opinião por parágrafo, limitada a concordância, acentuação e ortografia. Uma sugestão só é aceita se o trecho original existir literalmente e se a correção não mexer em números, citações ou comandos LaTeX.',
              ],
            },
            {
              type: 'paragraph',
              text: 'A revisão cobre só as seções geradas por IA e as linhas que você editou (comparadas com a versão montada). O texto fixo, como a Metodologia, não é reprocessado. Nada é alterado sem aprovação: cada sugestão é aplicada ou ignorada individualmente.',
            },
          ],
        },
        {
          title: 'Garantias do texto da IA',
          blocks: [
            {
              type: 'list',
              items: [
                'Citações: só "(SOBRENOME et al., ano)" de documentos que estão de fato no contexto recuperado. As inventadas são removidas, e homônimos recebem sufixo (2020a, 2020b).',
                'Números no padrão brasileiro ("17,3%", "1.800").',
                'Vazamentos do pipeline, como "[Informação não disponível]", "Relevância: 18%" ou "no contexto fornecido", são detectados. A seção é gerada de novo uma vez com instrução de correção e, se persistir, dá erro.',
                'Markdown solto devolvido pelo modelo é tratado: linhas de título (### …) são removidas e **negrito** vira `\\textbf{…}`.',
              ],
            },
          ],
        },
      ],
    },
  ],
}
