// Campos exibidos/editáveis no Step3 por API de busca. Espelha
// ChatService._PROBE_FIELDS_BY_API no backend - IPC é o campo extra pra
// patentes (classificação ampla de tecnologia), Field of Study é o
// equivalente pra artigos (classificação ampla de área/assunto).
export const PROBE_FIELDS_BY_API = {
  ops: {
    order: ['title', 'abstract', 'ipc', 'year'] as const,
    labels: {
      title: 'Title',
      abstract: 'Abstract',
      ipc: 'IPC',
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
