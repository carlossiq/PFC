import { useState, useEffect } from 'react'
import {
  generateFinalQueriesMulti,
  rebuildFinalQuery,
  FINAL_QUERY_VARIANTS,
} from '../services/finalQuery'
import type { FinalQueryVariant, ExtractedTerm } from '../services/finalQuery'
import type { QueryOptionResult, StructuredQueryFields } from '../services/probeQuery'
import type { FormInput, ThemeInput } from '../services/refineTopic'
import type { ProbeApi } from '../constants/probeFields'
import { toCsv, parseCsv } from '../components/CandidatePicker'
import { friendlyErrorMessage } from './useProbeQuerySection'
import { useFormStore } from '../stores/useFormStore'

// Slice de uma fonte (patentes/OPS ou artigos/Scopus) na tela de escolha da
// query final - mesmo papel de ProbeQuerySlice em useProbeQuerySection.ts,
// só que indexado por variante (specific/balanced/generic) em vez de posição
// no array, já que aqui cada posição tem um significado fixo.
export interface FinalQuerySlice {
  queries: Record<FinalQueryVariant, QueryOptionResult> | null
  setQueries: (queries: Record<FinalQueryVariant, QueryOptionResult> | null) => void
  updateQueryVariant: (variant: FinalQueryVariant, patch: Partial<QueryOptionResult>) => void
  selectedVariant: FinalQueryVariant | null
  setSelectedVariant: (variant: FinalQueryVariant | null) => void
  // Conta cliques em "Gerar outras" (a primeira geração, disparada em
  // TermSampling.tsx ao confirmar a amostragem de termos, não conta - reset
  // acontece lá, mesmo padrão de ProbeQuerySlice.incrementIterations).
  incrementIterations: () => void
  resetIterations: () => void
}

interface UseFinalQuerySectionParams {
  api: ProbeApi
  fieldOrder: readonly string[]
  input: FormInput
  step2SelectedTheme: (ThemeInput & { id: string }) | null
  extractedTerms: ExtractedTerm[]
  slice: FinalQuerySlice
}

// Encapsula escolha/edição/regeneração das 3 variantes de query final de uma
// fonte - mesma estrutura de useProbeQuerySection.ts, adaptada pra um
// conjunto fixo de 3 opções nomeadas em vez de N tentativas intercambiáveis.
// Diferente do probe, não gera nada sozinho ao montar: as queries já vêm
// prontas de TermSampling.tsx (que roda generateFinalQueriesMulti antes de
// navegar pra cá) - "Gerar outras" aqui só regenera as 3 de novo sob demanda.
export function useFinalQuerySection({
  api,
  fieldOrder,
  input,
  step2SelectedTheme,
  extractedTerms,
  slice,
}: UseFinalQuerySectionParams) {
  const {
    queries,
    setQueries,
    updateQueryVariant,
    selectedVariant,
    setSelectedVariant,
    incrementIterations,
  } = slice
  const addAiUsage = useFormStore((state) => state.addAiUsage)
  const beginAiCall = useFormStore((state) => state.beginAiCall)
  const endAiCall = useFormStore((state) => state.endAiCall)

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isRebuilding, setIsRebuilding] = useState(false)
  const [rebuildError, setRebuildError] = useState<string | null>(null)

  const queriesArray = queries ? FINAL_QUERY_VARIANTS.map((v) => queries[v]) : null
  const selectedIndex = selectedVariant !== null ? FINAL_QUERY_VARIANTS.indexOf(selectedVariant) : null

  function setSelectedIndex(index: number | null) {
    setSelectedVariant(index !== null ? FINAL_QUERY_VARIANTS[index] : null)
  }

  async function generateQueries() {
    setIsLoading(true)
    setError(null)
    beginAiCall()
    try {
      const { queries: results, aiUsage } = await generateFinalQueriesMulti(
        input,
        step2SelectedTheme,
        extractedTerms,
        api
      )
      addAiUsage(aiUsage)
      setQueries(results)
    } catch (err) {
      console.error(`Falha ao gerar queries finais (${api}):`, err)
      setError(
        friendlyErrorMessage(
          err instanceof Error ? err.message : undefined,
          'Não foi possível gerar as queries finais com IA. Tente novamente.'
        )
      )
    } finally {
      setIsLoading(false)
      endAiCall()
    }
  }

  function handleRetry() {
    incrementIterations()
    generateQueries()
  }

  const [isEditing, setIsEditing] = useState(false)
  const [editFields, setEditFields] = useState<Record<string, string>>({})

  useEffect(() => {
    setIsEditing(false)
    setRebuildError(null)
  }, [selectedVariant])

  const selected = selectedIndex !== null ? queriesArray?.[selectedIndex] : undefined
  const isBusy = isLoading || isRebuilding

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
    if (selectedVariant === null) return
    const parsed: StructuredQueryFields = {}
    for (const f of fieldOrder) parsed[f] = parseCsv(editFields[f] ?? '')

    setIsRebuilding(true)
    setRebuildError(null)
    try {
      const result = await rebuildFinalQuery(parsed, api)
      updateQueryVariant(selectedVariant, result)
      setIsEditing(false)
    } catch (err) {
      console.error(`Falha ao reconstruir query final (${api}):`, err)
      setRebuildError('Não foi possível reconstruir a query. Tente novamente.')
    } finally {
      setIsRebuilding(false)
    }
  }

  return {
    queries: queriesArray,
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
