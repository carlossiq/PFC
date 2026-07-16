import { apiClient } from './api'
import type { QueryOptionResult } from './probeQuery'
import type { AiUsage } from './aiUsage'
import type { FinalQueryVariant } from './finalQuery'

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
  // null = a query da probe (Exploração Inicial); specific/balanced/generic
  // = a variante de query final escolhida (Escolha da Query Final) -
  // auto-relacionada à linha de probe da mesma fonte (ver
  // db/research_session_models.py:SessionProbeQuery).
  tipo: FinalQueryVariant | null
  query_text: string
  fields: Record<string, string[]> | null
  year_from: number | null
  year_to: number | null
  complexity_score: number | null
  complexity_level: string | null
  iterations: number
  result_count: number | null
  // Dicts crus dos documentos encontrados por essa query (só um dos dois
  // preenchido, conforme `fonte`) - o backend faz o mapeamento campo-a-campo
  // e persiste em patent/article (ver session_probe_documents.py).
  patents: Record<string, unknown>[]
  articles: Record<string, unknown>[]
}

// Monta o payload de uma linha de session_probe_query pronta pra enviar no
// finalize/save - usado tanto pra linha de probe (tipo=null, Step3) quanto
// pra linha de query final (tipo=variante escolhida, Escolha da Query
// Final), a partir da opção selecionada numa seção. `iterations` é o
// contador interno da store (0-based: 0 = gerada uma vez, sem retry) - aqui
// vira o valor de negócio "nº de vezes que a query foi gerada" (1+); pra
// query final, o chamador já soma iterações de amostragem de termos +
// regeneração da query final antes de passar aqui. `resultCount` vem da
// busca real já rodada (Step3 ou Escolha da Query Final), null se ainda não
// rodou. Retorna null se não há uma seleção válida (nada gerado, ou a
// tentativa selecionada falhou) - mesma condição usada no `canProceed` do
// Step3/FinalExploration.
export function buildProbeQueryPayload(
  selected: QueryOptionResult | undefined,
  fonte: 'ops' | 'scopus',
  iterations: number,
  resultCount: number | null = null,
  rawItems: Record<string, unknown>[] = [],
  tipo: FinalQueryVariant | null = null,
): SessionProbeQueryPayload | null {
  if (!selected?.success) return null
  return {
    fonte,
    tipo,
    query_text: selected.query?.query ?? '',
    fields: selected.fields ?? null,
    year_from: selected.year_range?.from ?? null,
    year_to: selected.year_range?.to ?? null,
    complexity_score: selected.complexity?.score ?? null,
    complexity_level: selected.complexity?.level ?? null,
    iterations: iterations + 1,
    result_count: resultCount,
    patents: fonte === 'ops' && tipo === null ? rawItems : [],
    articles: fonte === 'scopus' && tipo === null ? rawItems : [],
  }
}

export interface SessionProbeQueryRow extends SessionProbeQueryPayload {
  id: number
  session_id: number
  // Documentos persistidos (patent/article) vinculados a essa query, no
  // formato "cru" que o probe search devolveria - só vem populado por GET
  // /research-session/{id} (retomar sessão), usado por sessionHydration.ts.
  documents: Record<string, unknown>[]
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

// Uma chamada de IA (refino de tema, especificação, geração de query
// probe/final) medida no backend e registrada na sessão - log append-only,
// pode ter várias linhas por step (inclusive tentativas descartadas em
// "gerar outras"). Ver schemas/session_input.py:SessionAiCallRow.
export interface SessionAiCallRow {
  id: number
  session_id: number
  step: string
  provider: string
  model: string
  duration_ms: number
  input_tokens: number | null
  output_tokens: number | null
  total_tokens: number | null
  attempts: number
  created_at: string
}

export interface SaveSessionResponse {
  session_id: number
  session_public_id: string
  session_name: string
  completed: boolean
  root: SessionInputRow
  generated: SessionInputRow | null
  probe_queries: SessionProbeQueryRow[]
  ai_calls: SessionAiCallRow[]
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
  step3PatentResults: { resultsCount: number; rawItems: Record<string, unknown>[] } | null
  step3ArticleQueries: QueryOptionResult[] | null
  step3ArticleSelectedIndex: number | null
  step3ArticleIterations: number
  step3ArticleResults: { resultsCount: number; rawItems: Record<string, unknown>[] } | null
  // Escolha da Query Final (ver TermSampling.tsx/FinalExploration.tsx) -
  // usados só pra montar a linha de query final (tipo=variante escolhida)
  // quando houver uma. Termos/seleção da Amostragem de Termos em si não são
  // enviados - só a soma das iterações de ambas as etapas.
  step4PatentIterations: number
  step4PatentQueries: Record<FinalQueryVariant, QueryOptionResult> | null
  step4PatentSelectedVariant: FinalQueryVariant | null
  step4PatentQueryIterations: number
  step4PatentResults: { resultsCount: number } | null
  step4ArticleIterations: number
  step4ArticleQueries: Record<FinalQueryVariant, QueryOptionResult> | null
  step4ArticleSelectedVariant: FinalQueryVariant | null
  step4ArticleQueryIterations: number
  step4ArticleResults: { resultsCount: number } | null
  aiCallLog: AiUsage[]
}

export interface SaveSessionPayload {
  root: SessionInputRootPayload
  generated: SessionInputGeneratedPayload | null
  probe_queries: SessionProbeQueryPayload[]
  ai_calls: AiUsage[]
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

  // `iterations` da linha de probe soma as duas etapas que ainda acontecem
  // dentro da Exploração Inicial: regeneração da própria query probe
  // (Step3, "Gerar outras") + reextração de termos (Amostragem de Termos,
  // "Gerar novos" - substep dessa mesma etapa, sempre roda antes da query
  // final existir).
  const patentQuery = buildProbeQueryPayload(
    formState.step3SelectedIndex !== null ? formState.step3Queries?.[formState.step3SelectedIndex] : undefined,
    'ops',
    formState.step3Iterations + formState.step4PatentIterations,
    formState.step3PatentResults?.resultsCount ?? null,
    formState.step3PatentResults?.rawItems ?? [],
  )
  const articleQuery = buildProbeQueryPayload(
    formState.step3ArticleSelectedIndex !== null
      ? formState.step3ArticleQueries?.[formState.step3ArticleSelectedIndex]
      : undefined,
    'scopus',
    formState.step3ArticleIterations + formState.step4ArticleIterations,
    formState.step3ArticleResults?.resultsCount ?? null,
    formState.step3ArticleResults?.rawItems ?? [],
  )

  // Linha da query final escolhida (Escolha da Query Final), auto-
  // relacionada à linha de probe da mesma fonte - null se o usuário ainda
  // não chegou a escolher uma variante. `iterations` aqui é só a
  // regeneração dessa variante ("Gerar outras" na Escolha da Query Final) -
  // a reextração de termos já foi contabilizada na linha de probe acima.
  const patentFinalQuery = buildProbeQueryPayload(
    formState.step4PatentSelectedVariant !== null
      ? formState.step4PatentQueries?.[formState.step4PatentSelectedVariant]
      : undefined,
    'ops',
    formState.step4PatentQueryIterations,
    formState.step4PatentResults?.resultsCount ?? null,
    [],
    formState.step4PatentSelectedVariant,
  )
  const articleFinalQuery = buildProbeQueryPayload(
    formState.step4ArticleSelectedVariant !== null
      ? formState.step4ArticleQueries?.[formState.step4ArticleSelectedVariant]
      : undefined,
    'scopus',
    formState.step4ArticleQueryIterations,
    formState.step4ArticleResults?.resultsCount ?? null,
    [],
    formState.step4ArticleSelectedVariant,
  )

  return {
    root: mapInputToSessionInputRoot(formState.input),
    generated,
    probe_queries: [patentQuery, articleQuery, patentFinalQuery, articleFinalQuery].filter(
      (q): q is SessionProbeQueryPayload => q !== null
    ),
    ai_calls: formState.aiCallLog,
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
