import { apiClient } from './api'
import type { QueryOptionResult } from './probeQuery'

export interface SessionInputRootPayload {
  theme: string
  description: string | null
  area_of_study: string | null
  keywords: string[] | null
  year_from: number | null
  year_to: number | null
}

export interface SessionInputGeneratedPayload {
  theme: string
  description: string | null
  iterations: number
}

interface FormInput {
  theme: string
  description: string | null
  keywords: string | null
  studyArea: string | null
}

// Converte o shape do useFormStore.input para o payload raiz esperado pelo
// endpoint /session-input, fazendo o split de keywords (string separada por
// vírgula) em uma lista sem vazios.
export function mapInputToSessionInputRoot(input: FormInput): SessionInputRootPayload {
  const keywordsArray = input.keywords
    ? input.keywords.split(',').map((k) => k.trim()).filter(Boolean)
    : null

  return {
    theme: input.theme,
    description: input.description || null,
    area_of_study: input.studyArea || null,
    keywords: keywordsArray && keywordsArray.length > 0 ? keywordsArray : null,
    year_from: null,
    year_to: null,
  }
}

export interface SessionProbeQueryPayload {
  fonte: 'ops' | 'scopus'
  query_text: string
  fields: Record<string, string[]> | null
  year_from: number | null
  year_to: number | null
  complexity_score: number | null
  complexity_level: string | null
  iterations: number
  result_count: number | null
}

// Monta o payload de uma query do Step3 pronta pra enviar no finalize, a
// partir da opção selecionada numa seção (patente ou artigo). `iterations`
// é o contador interno da store (0-based: 0 = gerada uma vez, sem retry) -
// aqui vira o valor de negócio "nº de vezes que a query foi gerada" (1+).
// `resultCount` vem da busca real já rodada no Step3 (ver runProbeSearch),
// null se por algum motivo não tiver rodado ainda.
// Retorna null se não há uma seleção válida (nada gerado, ou a tentativa
// selecionada falhou) - mesma condição usada no `canProceed` do Step3.
export function buildProbeQueryPayload(
  selected: QueryOptionResult | undefined,
  fonte: 'ops' | 'scopus',
  iterations: number,
  resultCount: number | null = null,
): SessionProbeQueryPayload | null {
  if (!selected?.success) return null
  return {
    fonte,
    query_text: selected.query?.query ?? '',
    fields: selected.fields ?? null,
    year_from: selected.year_range?.from ?? null,
    year_to: selected.year_range?.to ?? null,
    complexity_score: selected.complexity?.score ?? null,
    complexity_level: selected.complexity?.level ?? null,
    iterations: iterations + 1,
    result_count: resultCount,
  }
}

export interface SessionProbeQueryRow extends SessionProbeQueryPayload {
  id: number
  session_id: number
}

export interface SessionInputRow {
  id: number
  session_id: number
  parent_id: number | null
  theme: string
  description: string | null
  area_of_study: string | null
  keywords: string[] | null
  year_from: number | null
  year_to: number | null
  iterations: number
}

export interface SaveSessionResponse {
  session_id: number
  session_public_id: string
  session_name: string
  completed: boolean
  root: SessionInputRow
  generated: SessionInputRow | null
  probe_queries: SessionProbeQueryRow[]
}

// Fatia do useFormStore necessária pra montar o payload de save - qualquer
// objeto com pelo menos esses campos serve (ex: `useFormStore.getState()`).
export interface SaveSessionFormState {
  input: FormInput
  step2SelectedTheme: { id: string; theme: string; description: string } | null
  step2Iterations: number
  step3Queries: QueryOptionResult[] | null
  step3SelectedIndex: number | null
  step3Iterations: number
  step3PatentResults: { resultsCount: number } | null
  step3ArticleQueries: QueryOptionResult[] | null
  step3ArticleSelectedIndex: number | null
  step3ArticleIterations: number
  step3ArticleResults: { resultsCount: number } | null
}

export interface SaveSessionPayload {
  root: SessionInputRootPayload
  generated: SessionInputGeneratedPayload | null
  probe_queries: SessionProbeQueryPayload[]
  completed: boolean
}

// Monta o payload de save a partir do estado atual do form store - tolera
// progresso parcial (só o Step1 preenchido já basta: `root.theme` é o único
// campo obrigatório no backend). Usado tanto pelo botão "Salvar progresso"
// (completed=false) quanto pelo botão de finalizar (completed=true).
export function buildSaveSessionPayload(
  formState: SaveSessionFormState,
  completed: boolean,
): SaveSessionPayload {
  const wasRefinedByAI =
    !!formState.step2SelectedTheme && formState.step2SelectedTheme.id !== 'input'
  const generated = wasRefinedByAI
    ? {
        theme: formState.step2SelectedTheme!.theme,
        description: formState.step2SelectedTheme!.description || null,
        iterations: formState.step2Iterations,
      }
    : null

  const patentQuery = buildProbeQueryPayload(
    formState.step3SelectedIndex !== null ? formState.step3Queries?.[formState.step3SelectedIndex] : undefined,
    'ops',
    formState.step3Iterations,
    formState.step3PatentResults?.resultsCount ?? null,
  )
  const articleQuery = buildProbeQueryPayload(
    formState.step3ArticleSelectedIndex !== null
      ? formState.step3ArticleQueries?.[formState.step3ArticleSelectedIndex]
      : undefined,
    'scopus',
    formState.step3ArticleIterations,
    formState.step3ArticleResults?.resultsCount ?? null,
  )

  return {
    root: mapInputToSessionInputRoot(formState.input),
    generated,
    probe_queries: [patentQuery, articleQuery].filter(
      (q): q is SessionProbeQueryPayload => q !== null
    ),
    completed,
  }
}

// Salva (cria, se `sessionId` for null) ou atualiza (se já existir) a sessão.
// A primeira chamada de "Salvar progresso" ou "Finalizar" cria a sessão via
// POST; qualquer save seguinte (inclusive o finalize de uma sessão retomada)
// faz PUT, evitando duplicar as linhas de session_input/session_probe_query.
export async function saveSession(
  sessionId: number | null,
  name: string,
  payload: SaveSessionPayload,
): Promise<SaveSessionResponse> {
  const body = { name, ...payload }
  const { data } = sessionId
    ? await apiClient.put(`/research-session/${sessionId}`, body)
    : await apiClient.post('/session-input', body)
  return data.data
}
