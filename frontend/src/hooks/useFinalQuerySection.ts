import { useState, useEffect } from 'react'
import { generateFinalQuery, rebuildFinalQuery } from '../services/finalQuery'
import type { FinalQueryVariant, ExtractedTerm } from '../services/finalQuery'
import type { QueryOptionResult, StructuredQueryFields } from '../services/probeQuery'
import type { FormInput, ThemeInput } from '../services/refineTopic'
import type { ProbeApi } from '../constants/probeFields'
import { toCsv, parseCsv } from '../components/CandidatePicker'
import { friendlyErrorMessage } from './useProbeQuerySection'
import { useFormStore } from '../stores/useFormStore'
import { useAutoDismiss } from './useAutoDismiss'

// Slice de uma fonte (patentes/OPS ou artigos/Scopus) na tela de revisão da
// query final - só 1 query (o tipo já foi escolhido antes, em
// TermSampling.tsx), não mais uma lista de 3 pra escolher.
export interface FinalQuerySlice {
  query: QueryOptionResult | null
  setQuery: (query: QueryOptionResult | null) => void
  updateQuery: (patch: Partial<QueryOptionResult>) => void
  incrementIterations: () => void
}

interface UseFinalQuerySectionParams {
  api: ProbeApi
  fieldOrder: readonly string[]
  variant: FinalQueryVariant
  input: FormInput
  step2SelectedTheme: (ThemeInput & { id: string }) | null
  extractedTerms: ExtractedTerm[]
  slice: FinalQuerySlice
}

// Encapsula revisão/edição/regeneração da única query final de uma fonte -
// o tipo (specific/balanced/generic) já foi escolhido antes de chegar aqui,
// então não gera nada ao montar (a query já vem pronta de
// TermSampling.tsx). "Gerar de novo" regenera com o mesmo tipo (conta como
// iteração); a edição usa rebuildFinalQuery (síncrono, sem IA), mesmo
// padrão de useProbeQuerySection.ts.
export function useFinalQuerySection({
  api,
  fieldOrder,
  variant,
  input,
  step2SelectedTheme,
  extractedTerms,
  slice,
}: UseFinalQuerySectionParams) {
  const { query, setQuery, updateQuery, incrementIterations } = slice
  const addAiUsage = useFormStore((state) => state.addAiUsage)
  const beginAiCall = useFormStore((state) => state.beginAiCall)
  const endAiCall = useFormStore((state) => state.endAiCall)

  const [isRegenerating, setIsRegenerating] = useState(false)
  const [regenerateError, setRegenerateError] = useState<string | null>(null)
  const [isRebuilding, setIsRebuilding] = useState(false)
  const [rebuildError, setRebuildError] = useState<string | null>(null)

  useAutoDismiss(regenerateError, () => setRegenerateError(null))
  useAutoDismiss(rebuildError, () => setRebuildError(null))

  async function handleRegenerate() {
    incrementIterations()
    setIsRegenerating(true)
    setRegenerateError(null)
    beginAiCall()
    try {
      const { query: result, aiUsage } = await generateFinalQuery(
        input,
        step2SelectedTheme,
        extractedTerms,
        variant,
        api
      )
      addAiUsage(aiUsage)
      setQuery(result)
    } catch (err) {
      console.error(`Falha ao gerar query final (${api}):`, err)
      setRegenerateError(
        friendlyErrorMessage(
          err instanceof Error ? err.message : undefined,
          'Não foi possível gerar a query final com IA. Tente novamente.'
        )
      )
    } finally {
      setIsRegenerating(false)
      endAiCall()
    }
  }

  const [isEditing, setIsEditing] = useState(false)
  const [editFields, setEditFields] = useState<Record<string, string>>({})

  useEffect(() => {
    setIsEditing(false)
    setRebuildError(null)
  }, [query])

  const isBusy = isRegenerating || isRebuilding

  function handleStartEdit() {
    const fields: StructuredQueryFields = query?.fields ?? {}
    const next: Record<string, string> = {}
    for (const f of fieldOrder) {
      // Year geralmente vem vazio do LLM (nenhum dos prompts pede um ano
      // específico) - a query já aplica o intervalo padrão de qualquer
      // jeito (year_range), então pré-preenche o campo de edição com esse
      // padrão em vez de deixar em branco, pra não parecer que "sumiu".
      if (f === 'year' && (!fields.year || fields.year.length === 0) && query?.year_range) {
        next[f] = `${query.year_range.from}, ${query.year_range.to}`
      } else {
        next[f] = toCsv(fields[f])
      }
    }
    setEditFields(next)
    setIsEditing(true)
  }

  function handleCancelEdit() {
    setIsEditing(false)
  }

  async function handleSaveEdit() {
    const parsed: StructuredQueryFields = {}
    for (const f of fieldOrder) parsed[f] = parseCsv(editFields[f] ?? '')

    setIsRebuilding(true)
    setRebuildError(null)
    try {
      const result = await rebuildFinalQuery(parsed, api)
      updateQuery(result)
      setIsEditing(false)
    } catch (err) {
      console.error(`Falha ao reconstruir query final (${api}):`, err)
      setRebuildError('Não foi possível reconstruir a query. Tente novamente.')
    } finally {
      setIsRebuilding(false)
    }
  }

  return {
    query,
    isRegenerating,
    regenerateError,
    isRebuilding,
    rebuildError,
    isBusy,
    isEditing,
    editFields,
    setEditFields,
    handleRegenerate,
    handleStartEdit,
    handleCancelEdit,
    handleSaveEdit,
  }
}
