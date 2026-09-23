import { useState, useEffect } from 'react'
import { generateFinalQuery, validateFinalQuery } from '../services/finalQuery'
import type { FinalQueryVariant, ExtractedTerm } from '../services/finalQuery'
import type { QueryOptionResult } from '../services/probeQuery'
import type { FormInput, ThemeInput } from '../services/refineTopic'
import type { ProbeApi } from '../constants/probeFields'
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
  variant: FinalQueryVariant
  input: FormInput
  step2SelectedTheme: (ThemeInput & { id: string }) | null
  extractedTerms: ExtractedTerm[]
  slice: FinalQuerySlice
  // Códigos IPC reais da busca probe (só faz sentido pra 'ops') - ver
  // finalQuery.ts::computeTopIpcCodes. Omitido/vazio pro lado artigos.
  probeClassificationCodes?: string[]
}

// Encapsula revisão/edição/regeneração da única query final de uma fonte -
// o tipo (specific/balanced/generic) já foi escolhido antes de chegar aqui,
// então não gera nada ao montar (a query já vem pronta de
// TermSampling.tsx). "Gerar de novo" regenera com o mesmo tipo (conta como
// iteração); a edição é texto livre da query inteira, validada via
// validateFinalQuery (síncrono, sem IA, só recalcula complexidade).
export function useFinalQuerySection({
  api,
  variant,
  input,
  step2SelectedTheme,
  extractedTerms,
  slice,
  probeClassificationCodes = [],
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
        api,
        probeClassificationCodes
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
  // Texto livre da query inteira (AND/OR/parênteses etc.) - substitui a
  // edição por campos estruturados (title/abstract/ipc/...) separados, que
  // obrigava a reconstruir a CQL via query builder e não permitia mexer na
  // estrutura booleana em si.
  const [editQueryText, setEditQueryText] = useState('')

  useEffect(() => {
    setIsEditing(false)
    setRebuildError(null)
  }, [query])

  const isBusy = isRegenerating || isRebuilding

  function handleStartEdit() {
    setEditQueryText(query?.query?.query ?? '')
    setIsEditing(true)
  }

  function handleCancelEdit() {
    setIsEditing(false)
  }

  async function handleSaveEdit() {
    if (!editQueryText.trim()) {
      setRebuildError('A query não pode ficar vazia.')
      return
    }

    setIsRebuilding(true)
    setRebuildError(null)
    try {
      const result = await validateFinalQuery(editQueryText, api)
      // `fields` vem re-extraído do texto editado pelo backend (ver
      // query_field_extractor.py) e substitui o breakdown inteiro -
      // updateQuery faz merge raso, então o `?? {}` garante que campos
      // removidos na edição não sobrevivam com valores antigos.
      updateQuery({ ...result, fields: result.fields ?? {} })
      setIsEditing(false)
    } catch (err) {
      console.error(`Falha ao validar query final (${api}):`, err)
      setRebuildError(
        friendlyErrorMessage(err instanceof Error ? err.message : undefined, 'Não foi possível salvar a query. Tente novamente.')
      )
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
    editQueryText,
    setEditQueryText,
    handleRegenerate,
    handleStartEdit,
    handleCancelEdit,
    handleSaveEdit,
  }
}
