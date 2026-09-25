import type { DocPageData } from './types'

// Espelha os decorators @router.* de app/adapters/driving/http/*.py (todas
// as rotas sob settings.api_prefix = "/api/v1"). Payloads completos: Swagger
// do FastAPI (/docs), linkado no topo da página (ver DocApi.tsx).
const HEADERS = ['Método', 'Rota', 'Descrição']

export const apiPage: DocPageData = {
  title: 'Referência da API',
  description:
    'Rotas do backend agrupadas por módulo. Todas ficam sob o prefixo `/api/v1`. Os schemas completos de request e response estão no Swagger gerado pelo FastAPI.',
  sections: [
    {
      id: 'convencoes',
      title: 'Convenções',
      subsections: [
        {
          title: 'Envelope de resposta e erros',
          blocks: [
            {
              type: 'list',
              items: [
                'As respostas seguem o envelope `{ success, data, message, run_id }`.',
                'Cada requisição recebe um `run_id` (UUID), devolvido no header `X-Run-Id` e usado nos logs do backend. Informe-o ao reportar um problema.',
                'Nas rotas `/chat`, erros de negócio voltam com HTTP 200, `success: false` e a mensagem em `data.error`. Nas demais, voltam como erro HTTP (400, 404, 409, 413, 422, 502, 503) com a mensagem em `detail`.',
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'chat',
      title: '/chat — fluxo de prospecção',
      subsections: [
        {
          title: 'Status e utilitários',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                ['GET', '`/chat/apis`', 'Fontes de busca habilitadas/configuradas'],
                ['GET', '`/chat/models`', 'Provedores de LLM configurados'],
                ['GET', '`/chat/current-provider`', 'Provedor de LLM ativo'],
                ['GET', '`/chat/ops-token-status`', 'Validade do token OAuth do OPS/EPO'],
                ['POST', '`/chat/analyze-query`', 'Nota de complexidade de uma query (sem LLM)'],
              ],
            },
          ],
        },
        {
          title: 'Tema e queries',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                ['POST', '`/chat/refine-topic`', 'LLM gera 4 variações do tema'],
                ['POST', '`/chat/specify-topic`', 'LLM estreita um tema escolhido'],
                ['POST', '`/chat/probe/queries-multi?api=`', 'Gera as queries exploratórias, com retry por complexidade'],
                ['POST', '`/chat/probe/rebuild-query?api=`', 'Reconstrói a query probe a partir de campos editados (sem LLM)'],
                ['POST', '`/chat/probe/validate-query?api=`', 'Valida uma query probe editada como texto livre'],
                ['POST', '`/chat/final/query-variant?variant=&api=`', 'Gera a query final (specific, balanced ou generic) com os termos extraídos'],
                ['POST', '`/chat/final/rebuild-query?api=`', 'Reconstrói a query final a partir de campos editados'],
                ['POST', '`/chat/final/validate-query?api=`', 'Valida uma query final editada como texto livre'],
              ],
            },
          ],
        },
        {
          title: 'Buscas e termos',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                ['POST', '`/chat/probe/search?api=&top_k=`', 'Busca exploratória (amostra pequena, diversificada por ano)'],
                ['POST', '`/chat/final/search?api=&year_from=&year_to=&max_results=`', 'Busca final: documentos, agregados e total real'],
                ['POST', '`/chat/extract-terms?top_k=`', 'Extração de termos por NLP local (sem LLM)'],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'sessoes',
      title: '/research-session e /session-input — sessões',
      subsections: [
        {
          title: 'Persistência de sessões',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                ['POST', '`/session-input`', 'Cria uma sessão (input, queries, documentos). `completed` indica se é progresso ou conclusão'],
                ['GET', '`/research-session?theme=&limit=`', 'Lista/busca sessões, mais recentes primeiro'],
                ['GET', '`/research-session/{id}`', 'Sessão completa, com documentos e termos reidratados para retomar o fluxo'],
                ['PUT', '`/research-session/{id}`', 'Atualiza uma sessão já salva (upsert)'],
                ['DELETE', '`/research-session/{id}`', 'Exclui a sessão e todos os dados vinculados'],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'inferencia-graficos',
      title: '/inference e /report — estatística e gráficos',
      subsections: [
        {
          title: 'Inferência estatística',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [['POST', '`/inference/final-search`', 'Chao1 + bootstrap sobre a busca final, com enriquecimento até saturar (não persiste)']],
            },
          ],
        },
        {
          title: 'Gráficos',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                ['POST', '`/report/{id}/graphics`', 'Curva S de patentes (Fisher-Pry, GP/MP/SP, projeção opcional)'],
                ['POST', '`/report/{id}/article-s-curve`', 'Curva S de artigos'],
                ['POST', '`/report/{id}/patents-yearly-volume`', 'Histórico anual de patentes'],
                ['POST', '`/report/{id}/yearly-volume`', 'Histórico anual (patentes ou artigos)'],
                ['POST', '`/report/{id}/top-entities`', 'Top depositantes / instituições'],
                ['POST', '`/report/{id}/top10-heatmap`', 'Quadro top-10 de CPC / áreas de estudo'],
                ['GET', '`/report/{id}/existing-chart?require_summary=`', 'Reaproveita um gráfico já gerado'],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'relatorio',
      title: '/report — documento do relatório',
      subsections: [
        {
          title: 'Seções',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                ['POST', '`/report/{id}/sections/static`', 'Seções fixas: Finalidade, Objetivo do usuário, Metodologia, Bibliografia'],
                ['POST', '`/report/{id}/sections/{key}/rag`', 'Recupera e salva o contexto RAG (e as fontes citáveis) da seção'],
                ['POST', '`/report/{id}/sections/{key}/generate`', 'Gera o texto da seção com o LLM (exige o RAG antes)'],
              ],
            },
            {
              type: 'paragraph',
              text: 'Valores de `{key}`: `objetivo`, `introducao`, `informacoes_cientificas`, `informacoes_tecnologicas`, `tendencias_ciclo_vida`, `conclusao`.',
            },
          ],
        },
        {
          title: 'Documento, PDF e imagens',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                ['POST', '`/report/{id}/assemble`', 'Monta o `.tex` a partir das seções e gráficos existentes e conclui a sessão'],
                ['POST', '`/report/{id}/reassemble`', 'Remonta o `.tex` do zero com os dados da última montagem'],
                ['GET', '`/report/{id}/document`', '`.tex` atual (para o editor)'],
                ['POST', '`/report/{id}/compile-pdf`', 'Compila o `.tex` no container latex-compiler'],
                ['GET', '`/report/{id}/pdf`', 'PDF compilado mais recente'],
                ['GET', '`/report/{id}/charts`', 'Imagens disponíveis (geradas, fixas e anexos)'],
                ['POST', '`/report/{id}/attachments`', 'Envia um anexo de imagem (PNG/JPG, até 10 MB)'],
                ['DELETE', '`/report/{id}/attachments/{filename}`', 'Exclui um anexo'],
                ['POST', '`/report/{id}/review`', 'Revisão: lint LaTeX + LanguageTool + IA opcional'],
                ['POST', '`/report/{id}/bundle`', '`.zip` com o `.tex` e as imagens referenciadas'],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'config',
      title: '/config — configurações',
      subsections: [
        {
          title: 'Tela de Configurações',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [
                ['GET', '`/config/settings`', 'Parâmetros editáveis (busca, extração, relevância, RAG…)'],
                ['PUT', '`/config/settings/{key}`', 'Altera um parâmetro'],
                ['GET', '`/config/search-apis`', 'API ativa de cada família (patentes/artigos)'],
                ['PUT', '`/config/search-apis/{family}`', 'Troca a API ativa de uma família'],
                ['GET', '`/config/llm/providers`', 'Provedores de LLM suportados'],
                ['GET / POST', '`/config/llm/configs`', 'Lista / cria configurações de LLM (provedor + modelo + credenciais)'],
                ['PUT / DELETE', '`/config/llm/configs/{config_id}`', 'Altera / remove uma configuração de LLM'],
                ['GET', '`/config/llm/call-sites`', 'Pontos de uso de LLM e a configuração vinculada a cada um'],
                ['PUT', '`/config/llm/call-sites/{call_site}`', 'Vincula um ponto de uso a uma configuração'],
                ['GET / POST / DELETE', '`/config/report-cover-image`', 'Imagem da capa do relatório'],
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'health',
      title: '/health',
      subsections: [
        {
          title: 'Monitoramento',
          blocks: [
            {
              type: 'table',
              headers: HEADERS,
              rows: [['GET', '`/health`', 'Checagem simples de que o backend está no ar (sem dependência de banco)']],
            },
          ],
        },
      ],
    },
  ],
}
