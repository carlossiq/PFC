// Campos exibidos/editáveis no Step3 por API de busca. Espelha
// ChatService._PROBE_FIELDS_BY_API no backend - IPC (exibido como "CPC",
// mesma nomenclatura do relatório) é o campo extra pra
// patentes (classificação ampla de tecnologia), Field of Study é o
// equivalente pra artigos (classificação ampla de área/assunto).
// Só ops/scopus por enquanto DE PROPÓSITO: várias partes do front (ver
// probeQuery.ts/finalQuery.ts/ProbeResultsPanel.tsx) decidem o shape dos
// campos com `api === 'ops' ? campoOPS : campoScopus` - um binário, não um
// switch por API. Se lens_patent/lens_scholarly virasse a API ativa aqui,
// essas checagens tratariam os dados da Lens como se fossem Scopus/OPS
// (campos errados). Wiring dinâmico (ver Step3.tsx) só troca ops<->scopus
// quando é isso que search_api_selection tiver salvo; Lens ativo cai em
// fallback pro default - ver PLANO_MIGRACAO_CONFIG_BANCO.md § "Lens sem
// paridade de agregação" (o mesmo motivo, agora também no probe/parsing).
export const PROBE_FIELDS_BY_API = {
  ops: {
    order: ['title', 'abstract', 'ipc', 'year'] as const,
    labels: {
      title: 'Title',
      abstract: 'Abstract',
      ipc: 'CPC',
      year: 'Year',
    } as Record<string, string>,
  },
  scopus: {
    order: ['title', 'abstract', 'field_of_study', 'year'] as const,
    labels: {
      title: 'Title',
      abstract: 'Abstract',
      field_of_study: 'Field of Study',
      year: 'Year',
    } as Record<string, string>,
  },
} as const

export type ProbeApi = keyof typeof PROBE_FIELDS_BY_API
