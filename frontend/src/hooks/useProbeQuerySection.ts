import { useState, useEffect, useCallback, useRef } from 'react'
import {
  generateProbeQueriesMulti,
  rebuildProbeQuery,
} from '../services/probeQuery'
import type { QueryOptionResult, StructuredQueryFields } from '../services/probeQuery'
import { resolveIntakePayload } from '../services/refineTopic'
import type { FormInput, ThemeInput } from '../services/refineTopic'
import type { ProbeApi } from '../constants/probeFields'
import { toCsv, parseCsv } from '../components/CandidatePicker'
import { STEPS } from '../constants/steps'

// A API da IA (Gemini/Anthropic) pode devolver mensagens de erro brutas e
// longas (ex: 429 com detalhes de quota) — resume pros casos conhecidos em
// vez de despejar o texto cru na tela.
export function friendlyErrorMessage(error?: string, fallback = 'Falha ao gerar esta opção.'): string {
  if (!error) return fallback
  if (/429|quota|rate.?limit/i.test(error)) {
    return 'Limite de requisições da IA atingido no momento. Tente novamente em instantes.'
  }
  return error.length > 140 ? `${error.slice(0, 140)}…` : error
}

// O backend anexa esse warning (chat_service.py: _build_query_with_retry)
// quando nenhuma tentativa ficou dentro do limite de complexidade e ele
// devolve a menos complexa mesmo assim - a mensagem original é técnica
// ("Query complexity (75.0/100) exceeds limit (60) after 3 attempts...");
// aqui a resumimos pro usuário sem jargão.
export function friendlyWarningMessage(warning?: string): string | undefined {
  if (!warning) return undefined
  if (/complexity.*exceeds limit/i.test(warning)) {
    return 'Essa busca ainda ficou um pouco complexa — entre as tentativas que fizemos, usamos a de menor complexidade.'
  }
  return warning
}

// Cada seção de query (patentes/OPS, artigos/Scopus) guarda seu próprio
// estado num slice separado do useFormStore - o hook não assume nomes fixos
// de campo, só recebe os getters/setters já resolvidos pelo chamador.
export interface ProbeQuerySlice {
  queries: QueryOptionResult[] | null
  setQueries: (queries: QueryOptionResult[], generatedForIntake: string) => void
  updateQueryAt: (index: number, patch: Partial<QueryOptionResult>) => void
  selectedIndex: number | null
  setSelectedIndex: (index: number | null) => void
  generatedForIntake: string | null
  incrementIterations: () => void
}

interface UseProbeQuerySectionParams {
  step: number
  substep: number | null
  api: ProbeApi
  fieldOrder: readonly string[]
  input: FormInput
  step2SelectedTheme: (ThemeInput & { id: string }) | null
  slice: ProbeQuerySlice
}

// Encapsula geração/edição de uma seção de query do Step3 (uma por API).
// Usado duas vezes em Step3.tsx (ops e scopus), cada chamada lendo/escrevendo
// o slice de store correspondente - a lógica de regeneração (comparação de
// assinatura do intake) e edição de campos é idêntica pras duas, só muda a
// API e os campos editáveis.
export function useProbeQuerySection({
  step,
  substep,
  api,
  fieldOrder,
  input,
  step2SelectedTheme,
  slice,
}: UseProbeQuerySectionParams) {
  const { queries, setQueries, updateQueryAt, selectedIndex, setSelectedIndex, generatedForIntake, incrementIterations } = slice

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isRebuilding, setIsRebuilding] = useState(false)
  const [rebuildError, setRebuildError] = useState<string | null>(null)

  const requestIdRef = useRef(0)
  // Trava síncrona contra o double-invoke do StrictMode em dev: como o Step3
  // nunca desmonta, um ref "já rodei uma vez" não pode ser usado aqui - ele
  // nunca resetaria, e uma nova regeneração legítima (parâmetro mudou)
  // ficaria presa. Em vez disso, essa trava só bloqueia uma segunda chamada
  // disparada *durante* a mesma geração em andamento.
  const isGeneratingRef = useRef(false)

  // Assinatura do intake que seria usado AGORA pra gerar queries - comparada
  // com generatedForIntake pra saber se as queries existentes ainda são
  // válidas pro parâmetro atual.
  const currentIntakeSignature = JSON.stringify(resolveIntakePayload(input, step2SelectedTheme))

  const generateQueries = useCallback(async () => {
    const requestId = ++requestIdRef.current
    setIsLoading(true)
    setError(null)
    try {
      const results = await generateProbeQueriesMulti(input, step2SelectedTheme, api)
      if (requestIdRef.current !== requestId) return
      setQueries(results, currentIntakeSignature)
      const firstSuccessIndex = results.findIndex((q) => q.success)
      setSelectedIndex(firstSuccessIndex !== -1 ? firstSuccessIndex : 0)
    } catch (err) {
      if (requestIdRef.current !== requestId) return
      console.error(`Falha ao gerar queries com IA (${api}):`, err)
      setError(
        friendlyErrorMessage(
          err instanceof Error ? err.message : undefined,
          'Não foi possível gerar as queries com IA. Tente novamente.'
        )
      )
    } finally {
      if (requestIdRef.current === requestId) setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, step2SelectedTheme, api, setQueries, setSelectedIndex])

  useEffect(() => {
    if (step !== STEPS.INITIAL_EXPLORATION || substep !== null) return
    if (isGeneratingRef.current) return
    const needsRegeneration = !queries || generatedForIntake !== currentIntakeSignature
    if (needsRegeneration) {
      isGeneratingRef.current = true
      generateQueries().finally(() => {
        isGeneratingRef.current = false
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, substep, generatedForIntake, currentIntakeSignature, queries])

  const [isEditing, setIsEditing] = useState(false)
  const [editFields, setEditFields] = useState<Record<string, string>>({})

  useEffect(() => {
    setIsEditing(false)
    setRebuildError(null)
  }, [selectedIndex])

  const selected = selectedIndex !== null ? queries?.[selectedIndex] : undefined
  const isBusy = isLoading || isRebuilding

  function handleRetry() {
    incrementIterations()
    generateQueries()
  }

  function handleStartEdit() {
    const fields: StructuredQueryFields = selected?.fields ?? {}
    const next: Record<string, string> = {}
    for (const f of fieldOrder) next[f] = toCsv(fields[f])
    setEditFields(next)
    setIsEditing(true)
  }

  function handleCancelEdit() {
    setIsEditing(false)
  }

  async function handleSaveEdit() {
    if (selectedIndex === null) return
    const parsed: StructuredQueryFields = {}
    for (const f of fieldOrder) parsed[f] = parseCsv(editFields[f] ?? '')

    setIsRebuilding(true)
    setRebuildError(null)
    try {
      const result = await rebuildProbeQuery(parsed, api)
      updateQueryAt(selectedIndex, result)
      setIsEditing(false)
    } catch (err) {
      console.error(`Falha ao reconstruir query (${api}):`, err)
      setRebuildError('Não foi possível reconstruir a query. Tente novamente.')
    } finally {
      setIsRebuilding(false)
    }
  }

  return {
    queries,
    selectedIndex,
    setSelectedIndex,
    selected,
    isLoading,
    error,
    isRebuilding,
    rebuildError,
    isBusy,
    isEditing,
    editFields,
    setEditFields,
    handleRetry,
    handleStartEdit,
    handleCancelEdit,
    handleSaveEdit,
  }
}
