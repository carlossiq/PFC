import { apiClient } from './api'
import type { SessionInputRow } from './sessionInput'

export interface ResearchSessionSummary {
  id: number
  public_id: string
  name: string | null
  status: string
  created_at: string
  inputs: SessionInputRow[]
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
