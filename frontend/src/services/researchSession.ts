import { apiClient } from './api'
import type { SessionAiCallRow, SessionInputRow, SessionProbeQueryRow } from './sessionInput'

export interface ResearchSessionSummary {
  id: number
  public_id: string
  name: string | null
  completed: boolean
  created_at: string
  completed_at: string | null
  inputs: SessionInputRow[]
  probe_queries: SessionProbeQueryRow[]
  ai_calls: SessionAiCallRow[]
}

// Busca sessões pelo tema de qualquer um de seus session_input (raiz ou gerado
// por IA). Sem theme (ou string vazia), retorna as sessões mais recentes. O
// backend limita a 50 resultados por padrão - `limit` deixa a página de
// Estatísticas pedir mais sessões pra calcular médias/séries temporais sobre
// um conjunto maior, sem afetar quem chama sem esse argumento (ex: SearchPage).
export async function searchSessions(theme?: string, limit?: number): Promise<ResearchSessionSummary[]> {
  const params: Record<string, string | number> = {}
  if (theme && theme.trim()) params.theme = theme.trim()
  if (limit) params.limit = limit
  const { data } = await apiClient.get('/research-session', { params })
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

// Soma as iterações de todos os estágios de IA de uma sessão
export function getSessionTotalIterations(session: ResearchSessionSummary): number {
  const generated = session.inputs.find((i) => i.parent_id !== null)
  const probeQueriesTotal = session.probe_queries.reduce((sum, q) => sum + q.iterations, 0)
  return (generated?.iterations ?? 0) + probeQueriesTotal
}

// Soma o total de tokens (entrada + saída) de todas as chamadas de IA
export function getSessionTotalTokens(session: ResearchSessionSummary): number {
  return session.ai_calls.reduce((sum, call) => sum + (call.total_tokens ?? 0), 0)
}

// "distiluse-base-multilingual-cased-v2" 
const INTERNAL_AI_LABEL = 'IA interna (extração de termos)'

// Modelos de IA usados na sessão, sem repetição, na ordem em que apareceram
export function getSessionModels(session: ResearchSessionSummary): string[] {
  const seen = new Set<string>()
  const models: string[] = []
  for (const call of session.ai_calls) {
    const label = call.provider === 'internal' ? INTERNAL_AI_LABEL : call.model
    if (!seen.has(label)) {
      seen.add(label)
      models.push(label)
    }
  }
  return models
}
