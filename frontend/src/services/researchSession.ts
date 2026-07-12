import { apiClient } from './api'
import type { SessionInputRow, SessionProbeQueryRow } from './sessionInput'

export interface ResearchSessionSummary {
  id: number
  public_id: string
  name: string | null
  status: string
  created_at: string
  inputs: SessionInputRow[]
  probe_queries: SessionProbeQueryRow[]
}

// Busca sessões pelo tema de qualquer um de seus session_input (raiz ou gerado
// por IA). Sem theme (ou string vazia), retorna as sessões mais recentes.
export async function searchSessions(theme?: string): Promise<ResearchSessionSummary[]> {
  const { data } = await apiClient.get('/research-session', {
    params: theme && theme.trim() ? { theme: theme.trim() } : {},
  })
  return data.data
}

// Apaga a sessão e, em cascata no backend, todas as suas linhas de session_input.
export async function deleteSession(sessionId: number): Promise<void> {
  await apiClient.delete(`/research-session/${sessionId}`)
}

// Soma as iterações dos três estágios de IA de uma sessão: refinamento de
// parâmetros (Step2, na linha de session_input gerada) + geração da query de
// patente + geração da query de artigos (Step3). Mesmo cálculo usado no badge
// do SessionCard e no gráfico de estatísticas, centralizado aqui pra não duplicar.
export function getSessionTotalIterations(session: ResearchSessionSummary): number {
  const generated = session.inputs.find((i) => i.parent_id !== null)
  const patentQuery = session.probe_queries.find((q) => q.fonte === 'ops')
  const articleQuery = session.probe_queries.find((q) => q.fonte === 'scopus')
  return (generated?.iterations ?? 0) + (patentQuery?.iterations ?? 0) + (articleQuery?.iterations ?? 0)
}
