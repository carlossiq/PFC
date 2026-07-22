import { useState, useEffect, useCallback, useRef } from 'react'
import { extractTerms, toTermItems, selectDocsForAnalysis } from '../services/finalQuery'
import type { ExtractedTerm } from '../services/finalQuery'
import type { ProbeSearchResult } from '../services/probeQuery'
import type { ProbeApi } from '../constants/probeFields'
import { STEPS } from '../constants/steps'
import { useFormStore } from '../stores/useFormStore'
import { useAutoDismiss } from './useAutoDismiss'

// Cada seção de amostragem de termos (patentes/OPS, artigos/Scopus) guarda
// seu próprio estado num slice separado do useFormStore - mesmo desenho de
// useProbeQuerySection.ts pra queries do Step3.
export interface TermSamplingSlice {
  terms: ExtractedTerm[] | null
  termsForQuery: string | null
  selectedTerms: string[]
  setTerms: (terms: ExtractedTerm[], forQuery: string | null) => void
  toggleTerm: (term: string) => void
}

interface UseTermSamplingParams {
  step: number
  substep: number | null
  api: ProbeApi
  probeResults: ProbeSearchResult | null
  probeResultsQuery: string | null
  slice: TermSamplingSlice
}

// Encapsula a extração de termos de uma fonte (uma chamada a
// /chat/extract-terms sobre os títulos/abstracts já buscados no Step3) -
// extrai automaticamente ao entrar no substep "Amostragem de Termos" ou
// quando os resultados da probe mudam. Não tem botão de "gerar novos": a
// extração é NLP determinístico (spaCy + KeyBERT + TF-IDF, sem IA nem
// aleatoriedade) - pros mesmos documentos, rodar de novo sempre devolve
// exatamente os mesmos termos. `retryExtraction` só existe pra tentar de
// novo depois de uma falha (erro de rede/API), não pra buscar resultados
// diferentes.
export function useTermSampling({
  step,
  substep,
  api,
  probeResults,
  probeResultsQuery,
  slice,
}: UseTermSamplingParams) {
  const { terms, termsForQuery, selectedTerms, setTerms, toggleTerm } = slice
  const addAiUsage = useFormStore((state) => state.addAiUsage)
  const beginAiCall = useFormStore((state) => state.beginAiCall)
  const endAiCall = useFormStore((state) => state.endAiCall)

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useAutoDismiss(error, () => setError(null))

  const requestIdRef = useRef(0)
  const isGeneratingRef = useRef(false)

  const hasDocs = (probeResults?.rawItems.length ?? 0) > 0

  const runExtraction = useCallback(async () => {
    if (!probeResults) return
    const requestId = ++requestIdRef.current
    setIsLoading(true)
    setError(null)
    beginAiCall()
    try {
      const sample = selectDocsForAnalysis(probeResults.rawItems, api)
      const items = toTermItems(sample, api)
      const { terms: results, aiUsage } = await extractTerms(items)
      if (requestIdRef.current !== requestId) return
      addAiUsage(aiUsage)
      setTerms(results, probeResultsQuery)
    } catch (err) {
      if (requestIdRef.current !== requestId) return
      console.error(`Falha ao extrair termos (${api}):`, err)
      setError('Não foi possível extrair os termos. Tente novamente.')
    } finally {
      if (requestIdRef.current === requestId) setIsLoading(false)
      endAiCall()
    }
  }, [probeResults, probeResultsQuery, api, setTerms, addAiUsage, beginAiCall, endAiCall])

  useEffect(() => {
    if (step !== STEPS.INITIAL_EXPLORATION || substep !== 1) return
    if (!hasDocs) return
    if (isGeneratingRef.current) return
    const needsExtraction = !terms || termsForQuery !== probeResultsQuery
    if (needsExtraction) {
      isGeneratingRef.current = true
      runExtraction().finally(() => {
        isGeneratingRef.current = false
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, substep, hasDocs, termsForQuery, probeResultsQuery, terms])

  return {
    terms,
    selectedTerms,
    toggleTerm,
    isLoading,
    error,
    hasDocs,
    retryExtraction: runExtraction,
  }
}
