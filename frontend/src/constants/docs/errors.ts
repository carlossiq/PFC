import type { DocPageData } from './types'

// Mensagens citadas aqui são as que o app de fato mostra (frontend) ou que a
// API devolve em `detail`/`data.error` (app/adapters/driving/http/*.py,
// app/core/services/chat_service.py, report_writer_service.py,
// report_form_validation.py). Atualizar junto se o texto mudar lá.
const HEADERS = ['Sintoma / mensagem', 'Causa provável', 'O que fazer']

export const errorsPage: DocPageData = {
  title: 'Erros e Soluções',
  description:
    'Mensagens de erro e comportamentos inesperados mais comuns, organizados pela etapa em que aparecem, com a causa provável e o que fazer.',
  sections: [
    {
      id: 'ia',
      title: 'Refinamento e geração de queries (IA)',
      subsections: [
        {
          title: 'Falhas do modelo de linguagem',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                [
                  '"Não foi possível gerar variações do tema no momento" / "Falha ao gerar parâmetros com IA"',
                  'O provedor de LLM do ponto de uso `theme_candidates` está fora do ar, sem chave de API ou devolveu uma resposta fora do formato esperado.',
                  'Tente de novo. Se persistir, confira em Configurações › Inteligência Artificial se o provedor está configurado e disponível, ou aponte o ponto de uso para outro modelo. Também é possível pular o refinamento com "Gerar Query".',
                ],
                [
                  '"Falha ao gerar query após 3 tentativas" / "Falha ao gerar a query final com IA"',
                  'As 3 tentativas falharam (erro do provedor ou saída inválida).',
                  'Gere de novo. Se o modelo for local e pequeno, considere um modelo maior para `probe_query`/`final_query`. A query também pode ser editada manualmente pelos campos.',
                ],
                [
                  'Aviso de query complexa demais ao lado da query gerada',
                  'Nenhuma das 3 tentativas ficou abaixo do limite de complexidade; o sistema usou a menos complexa.',
                  'Revise a query: remova termos redundantes ou grupos OR longos. Se o tema exige queries maiores, aumente "Complexidade máxima de query" em Configurações › Relevância & Qualidade.',
                ],
                [
                  '"A query não pode ficar vazia."',
                  'Todos os campos da query foram apagados na edição manual.',
                  'Preencha ao menos um campo ou gere a query de novo.',
                ],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'busca',
      title: 'Buscas (OPS e Scopus)',
      subsections: [
        {
          title: 'Resultados e credenciais',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                [
                  '"Sem documentos encontrados nesta fonte."',
                  'A query é restritiva demais, o período é curto ou a sintaxe gerou uma query válida mas vazia (por exemplo, `SUBJAREA` incompatível).',
                  'Volte e gere outra query, edite os campos (menos termos com AND, mais termos com OR) ou amplie o período em Configurações › Busca. Na Exploração Final, experimente a variante balanceada ou ampla.',
                ],
                [
                  '"Failed to obtain OPS token" / "OPS credentials error"',
                  'Chave/segredo do OPS ausentes ou inválidos, ou o serviço de autenticação do EPO está fora do ar.',
                  'Confira `OPS_CONSUMER_KEY`/`OPS_CONSUMER_SECRET` no `.env` do backend. O status do token pode ser consultado em `GET /chat/ops-token-status`.',
                ],
                [
                  '"API \'…\' not enabled or not found"',
                  'A fonte não está habilitada ou não tem credencial configurada.',
                  'Habilite a fonte em Configurações › Busca e confira a chave correspondente (ex.: `SCOPUS_API_KEY`).',
                ],
                [
                  'Busca demorada ou "Falha ao buscar resultados finais"',
                  'Limite de requisições (429), instabilidade da API remota ou volume muito grande. Erros 408/429/5xx já são repetidos automaticamente antes de falhar.',
                  'Aguarde alguns minutos e tente de novo. Reduzir "Top-K da busca final" diminui o tempo.',
                ],
                [
                  'Poucos resultados de artigos na curva S / anos faltando',
                  'Falha de rede persistente em alguns anos da contagem do Scopus. Esses anos são omitidos de propósito, em vez de contados como zero.',
                  'Refaça a busca final para tentar recuperar os anos faltantes.',
                ],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'termos',
      title: 'Extração de termos',
      subsections: [
        {
          title: 'Amostragem de Termos',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                [
                  '"No items with non-empty title or abstract" / "Falha ao extrair termos."',
                  'Os documentos da busca exploratória não têm título nem resumo (comum em alguns registros de patente), ou nenhum passou pelo filtro de relevância.',
                  'Volte e gere outra query exploratória. Se o filtro estiver rígido demais, reduza "Threshold de relevância" em Configurações.',
                ],
                [
                  'Termos genéricos ou irrelevantes no topo da lista',
                  'Amostra pequena ou pouco focada; modelo KeyBERT pouco adequado ao domínio.',
                  'Refine o tema ou a query exploratória. Para patentes, experimente `all-mpnet-base-v2` como modelo do KeyBERT (exige reiniciar o backend).',
                ],
                [
                  'Poucos termos (em torno de 10)',
                  'O limiar de score cortou quase tudo e o piso de 10 termos entrou em ação.',
                  'Normal em amostras pequenas. Aumente "Top-K da probe" para ter mais documentos ou reduza o "Threshold de score".',
                ],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'graficos',
      title: 'Criação de Gráficos',
      subsections: [
        {
          title: 'Inferência e gráficos',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                [
                  '"Não foi possível salvar a sessão para gerar os gráficos."',
                  'O backend ou o PostgreSQL está fora do ar, ou a sessão não tem tema.',
                  'Confira se o backend está rodando e clique em "Tentar novamente". O progresso do navegador não é perdido.',
                ],
                [
                  'Um gráfico não aparece no relatório (`charts_missing` na montagem)',
                  'A geração daquele gráfico falhou (falhas de gráfico não bloqueiam as demais etapas) ou não havia dados para ele.',
                  'Volte à Criação de Gráficos para gerar de novo. Sem dados na fonte, o gráfico é realmente omitido. Na montagem, só entram PNGs que já existem.',
                ],
                [
                  'Aviso sobreposto na curva S ("ajuste pouco confiável")',
                  'R² < 0,90, poucos anos de dados com saturação alta, ou taxa de crescimento implausível.',
                  'A curva ainda é exibida, mas deve ser lida com cautela. Buscas mais amplas (mais anos, mais documentos) costumam melhorar o ajuste. Veja o Pipeline de Prospecção.',
                ],
                [
                  'Curva S ausente',
                  'Menos de 2 anos com dados, ou o ajuste não convergiu (tecnologia ainda muito no início).',
                  'Amplie o período da busca. Se a tecnologia é realmente emergente, a ausência é esperada.',
                ],
                [
                  'Erro no MinIO ao gerar ou baixar gráficos',
                  'O container `minio` está fora do ar.',
                  'Suba o container (`docker compose up -d minio`) e tente de novo.',
                ],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'relatorio',
      title: 'Geração do Relatório',
      subsections: [
        {
          title: 'Formulário do REPTEC',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                [
                  'Referência "…" fora do formato',
                  'Referências administrativas precisam ter tipo, número e data.',
                  'Siga o exemplo: "DIEx Nº 115-A3/DCT de 6 de janeiro de 2023".',
                ],
                [
                  'Referência bibliográfica fora do padrão ABNT',
                  'A bibliografia adicional deve começar por "SOBRENOME, Iniciais." e incluir o ano.',
                  'Ex.: "SILVA, J. Título da obra. Editora, 2021."',
                ],
                [
                  '"… não parece um nome completo" / "posto/graduação inválido" / "informe a função"',
                  'Assinatura incompleta.',
                  'Informe nome e sobrenome, posto/graduação e a função. Blocos de Revisado/Aprovado por totalmente vazios são aceitos e omitidos.',
                ],
                [
                  '"…: texto inválido."',
                  'Campo com menos de 2 palavras ou com valor de preenchimento, como "teste" ou "sdasd".',
                  'Escreva o conteúdo real do campo.',
                ],
              ],
            },
          ],
        },
        {
          title: 'Geração das seções',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                [
                  '"ChromaDB indisponível - verifique o container \'chromadb\'." (503)',
                  'O banco vetorial do RAG está fora do ar.',
                  'Suba o container (`docker compose up -d chromadb`) e reinicie o backend, se necessário. Clique em "Continuar geração".',
                ],
                [
                  '"Falha ao gerar texto via LLM: …" (502)',
                  'O servidor do LLM de redação (Ollama local ou intranet) está fora do ar, recusou a chave ou estourou o tempo limite.',
                  'Confira o provedor do ponto de uso `report_writing`. Para modelos lentos, aumente "Timeout do Ollama" em Configurações › Geral. Com Ollama local, confira se o modelo foi baixado (`ollama pull <modelo>`).',
                ],
                [
                  '"O texto gerado para \'…\' continuou com problemas após regenerar" (422)',
                  'O modelo insistiu em vazar marcas internas ("[Informação não disponível]", "Relevância: …", "no contexto fornecido").',
                  'Gere a seção de novo. Se for recorrente, use um modelo maior para `report_writing`.',
                ],
                [
                  '"Contexto de RAG ainda não calculado" (422)',
                  'A geração foi chamada antes da recuperação de contexto daquela seção (chamada direta à API).',
                  'Pela tela, "Gerar" sempre roda as duas etapas em ordem. Via API, chame `.../rag` antes de `.../generate`.',
                ],
                [
                  'Texto da IA com poucas citações ou sem a obra esperada',
                  'Só são mantidas citações de documentos que estavam no contexto recuperado; o RAG corta trechos com relevância abaixo de 75% do mais relevante.',
                  'Reduza "Corte relativo do RAG" ou aumente "Top-K do RAG por seção" em Configurações › Geral e gere a seção de novo.',
                ],
                [
                  'Texto com erros de concordância',
                  'Limitação conhecida de modelos locais pequenos (ex.: `gemma3:4b`).',
                  'Use "Revisão" no editor ou aponte `report_writing`/`report_review` para um modelo melhor em português.',
                ],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'editor',
      title: 'Editor e compilação',
      subsections: [
        {
          title: 'Compilação do PDF',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                [
                  '"Falha ao compilar o PDF" com "File ….sty not found"',
                  'Um `\\usepackage` de pacote não instalado no compilador.',
                  'Remova o pacote ou use uma alternativa instalada (veja Relatório e LaTeX › Pacotes LaTeX).',
                ],
                [
                  '"Missing } inserted" / "Extra }" / "\\begin{…} ended by \\end{…}"',
                  'Chaves ou ambientes desbalanceados após uma edição.',
                  'Rode "Revisão": o lint aponta a linha. Em último caso, "Remontar .tex" (descarta as edições manuais).',
                ],
                [
                  '"File anexo-….png not found"',
                  'A imagem referenciada foi excluída ou o nome foi digitado errado.',
                  'Corrija o nome ou reinsira a imagem pelo painel de imagens.',
                ],
                [
                  '"Missing $ inserted" / texto cortado após %',
                  'Caractere especial sem escape (`_`, `$`, `%`, `&`, `#`).',
                  'Escape o caractere (veja Relatório e LaTeX › Escrevendo no editor).',
                ],
                [
                  'Compilação interrompida por tempo',
                  'O documento excedeu o limite de 120 s (imagens muito grandes, laços de macro).',
                  'Reduza o tamanho das imagens anexadas e revise macros adicionadas manualmente.',
                ],
              ],
            },
            {
              type: 'note',
              text: 'Uma falha de compilação nunca apaga o `.tex`: o documento continua salvo e editável.',
            },
          ],
        },
        {
          title: 'Revisão, anexos e download',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                [
                  'Aviso de que o LanguageTool ou a IA não responderam',
                  'O container `languagetool` (porta 8010) ou o modelo de `report_review` está fora do ar.',
                  'Os problemas de LaTeX continuam valendo. Suba o container (`docker compose up -d languagetool`) e rode a revisão de novo.',
                ],
                [
                  '"Imagem maior que 10 MB." / "Formato não suportado"',
                  'Anexos aceitam só PNG ou JPG de até 10 MB.',
                  'Converta ou reduza a imagem antes de enviar.',
                ],
                [
                  '"Só anexos enviados pelo usuário podem ser excluídos."',
                  'Tentativa de excluir um gráfico gerado ou uma figura fixa.',
                  'Gráficos e figuras fixas não podem ser excluídos. Basta remover a referência do `.tex`.',
                ],
                [
                  '"Relatório ainda não montado" (422)',
                  'Compilar, revisar ou baixar o `.zip` antes de montar o `.tex`.',
                  'Conclua "Montar .tex" na tela de Geração do Relatório.',
                ],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'sessoes',
      title: 'Sessões e ambiente',
      subsections: [
        {
          title: 'Gerais',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                [
                  '"Session not found" (404)',
                  'A sessão foi excluída em outra aba ou o banco foi recriado.',
                  'Volte à tela de Busca e abra uma sessão existente ou inicie outra.',
                ],
                [
                  '"Falha ao salvar progresso"',
                  'Tema vazio, backend fora do ar ou erro de banco.',
                  'Preencha o tema (obrigatório) e confira se backend e PostgreSQL estão rodando.',
                ],
                [
                  'Troca do modelo KeyBERT sem efeito',
                  'O modelo é carregado só na inicialização.',
                  'Reinicie o backend.',
                ],
                [
                  'Várias telas falhando ao mesmo tempo',
                  'Algum container de apoio está parado.',
                  'Rode `docker ps` e confira `postgres`, `minio`, `chromadb`, `ollama`, `languagetool` e `latex_compiler`. O backend responde em `GET /api/v1/health`.',
                ],
              ],
            },
          ],
        },
      ],
    },
  ],
}
