import { apiClient } from './api'
import type { SessionAiCallRow, SessionInputRow, SessionProbeQueryRow } from './sessionInput'

export interface ResearchSessionSummary {
  id: number
  public_id: string
  name: string | null
  completed: boolean
  created_at: string
  inputs: SessionInputRow[]
  probe_queries: SessionProbeQueryRow[]
  ai_calls: SessionAiCallRow[]
}

// Busca sessões pelo tema de qualquer um de seus session_input (raiz ou gerado
// por IA). Sem theme (ou string vazia), retorna as sessões mais recentes.
export async function searchSessions(theme?: string): Promise<ResearchSessionSummary[]> {
  const { data } = await apiClient.get('/research-session', {
    params: theme && theme.trim() ? { theme: theme.trim() } : {},
  })
  return data.data
}

// Busca uma sessão específica com todas as suas linhas de session_input e
// session_probe_query - usado ao retomar uma sessão pendente ("Continuar
// pesquisa"), pra garantir dados frescos em vez de reaproveitar a listagem.
export async function getSessionById(sessionId: number): Promise<ResearchSessionSummary> {
  const { data } = await apiClient.get(`/research-session/${sessionId}`)
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

// Soma o total de tokens (entrada + saída) de todas as chamadas de IA
// registradas na sessão - inclui tentativas descartadas (retries por
// complexidade, "gerar outras"), não só a query final escolhida.
export function getSessionTotalTokens(session: ResearchSessionSummary): number {
  return session.ai_calls.reduce((sum, call) => sum + (call.total_tokens ?? 0), 0)
}

// Modelo de IA usado na sessão. O provedor é uma configuração global do
// backend (core/config.py: llm_provider) - todas as chamadas de uma mesma
// sessão usam o mesmo provider/model, então a primeira linha já representa
// o modelo usado na sessão inteira.
export function getSessionModel(session: ResearchSessionSummary): string | null {
  return session.ai_calls[0]?.model ?? null
}
