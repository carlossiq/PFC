import { useState } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { useTermSampling } from '../../hooks/useTermSampling'
import { generateFinalQueriesMulti } from '../../services/finalQuery'
import type { ExtractedTerm } from '../../services/finalQuery'
import { selectableCardClass } from '../CandidatePicker'
import { LoadingScreen } from '../LoadingScreen'
import { Tooltip } from '../Tooltip'
import { STEPS } from '../../constants/steps'

const SCORE_TOOLTIP =
  'Pontuação de relevância do termo (0 a 1), calculada pela IA combinando ' +
  'importância estatística (frequência do termo nos documentos) ' +
  'e semântica (o quanto o termo captura o assunto do título/abstract ' +
  ') - quanto maior, mais relevante o termo é considerado ' +
  'pro tema pesquisado.'

interface TermChecklistProps {
  title: string
  hasDocs: boolean
  terms: ExtractedTerm[] | null
  selectedTerms: string[]
  isLoading: boolean
  error: string | null
  onToggle: (term: string) => void
  onRegenerate: () => void
}

// Uma coluna da amostragem de termos (patentes/OPS ou artigos/Scopus):
// checklist ordenado por score (já vem ordenado do backend), nada marcado
// por padrão, e um botão pra reextrair (conta como iteração) abaixo do card
// - mesmo padrão visual do "Gerar outras" em ProbeQuerySectionView.tsx.
function TermChecklist({
  title,
  hasDocs,
  terms,
  selectedTerms,
  isLoading,
  error,
  onToggle,
  onRegenerate,
}: TermChecklistProps) {
  return (
    <div className="flex flex-col">
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="font-semibold text-sm text-gray-900">{title}</h4>
          <Tooltip position="left" label={SCORE_TOOLTIP}>
            <span className="text-xs font-mono text-gray-400 cursor-help">Score</span>
          </Tooltip>
        </div>

        {!hasDocs && <p className="text-sm text-gray-500">Sem documentos encontrados nesta fonte.</p>}

        {hasDocs && isLoading && <LoadingScreen message="Extraindo termos com IA..." />}

        {hasDocs && !isLoading && error && (
          <div className="p-4 rounded-lg border-2 border-red-200 bg-red-50">
            <p className="text-sm text-red-700 mb-2">{error}</p>
            <button
              type="button"
              onClick={onRegenerate}
              className="text-sm font-semibold text-[#0f9448] hover:text-[#0d843f]"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {hasDocs && !isLoading && !error && terms && (
          <ul className="space-y-1 max-h-64 overflow-y-auto">
            {terms.map((t) => (
              <li key={t.term}>
                <label className={`${selectableCardClass(selectedTerms.includes(t.term))} w-full flex items-center gap-2 cursor-pointer`}>
                  <input
                    type="checkbox"
                    checked={selectedTerms.includes(t.term)}
                    onChange={() => onToggle(t.term)}
                    className="shrink-0"
                  />
                  <span className="flex-1 text-sm text-gray-900">{t.term}</span>
                  <span className="text-xs font-mono text-gray-400 shrink-0">{t.score.toFixed(2)}</span>
                </label>
              </li>
            ))}
            {terms.length === 0 && <p className="text-sm text-gray-500">Nenhum termo relevante encontrado.</p>}
          </ul>
        )}
      </div>

      {hasDocs && (
        <div className="mt-3 shrink-0">
          <button
            type="button"
            onClick={onRegenerate}
            disabled={isLoading}
            className="bg-[#0f9448] hover:bg-[#0d843f] disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300 text-sm"
          >
            {isLoading ? 'Gerando...' : 'Gerar novos'}
          </button>
        </div>
      )}
    </div>
  )
}

interface TermSamplingProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

// Substep "Amostragem de Termos" da Exploração Inicial: mostra os termos
// extraídos dos documentos da probe (patentes + artigos) pro usuário marcar
// manualmente quais quer levar pra construção da query final. "Gerar Query"
// já dispara a geração das 3 variantes (specific/balanced/generic) com os
// termos marcados e avança pro substep seguinte (escolha da query, em
// FinalExploration.tsx) - mesmo padrão de Step3.tsx, que roda a busca real
// antes de avançar pra "Resultados Iniciais".
export function TermSampling({ step, substep, onBack, onNext }: TermSamplingProps) {
  const {
    input,
    step2SelectedTheme,
    step3PatentResults,
    step3PatentResultsQuery,
    step3ArticleResults,
    step3ArticleResultsQuery,
    step4PatentTerms,
    step4PatentTermsForQuery,
    step4PatentSelectedTerms,
    setStep4PatentTerms,
    toggleStep4PatentTerm,
    incrementStep4PatentIterations,
    resetStep4PatentIterations,
    step4ArticleTerms,
    step4ArticleTermsForQuery,
    step4ArticleSelectedTerms,
    setStep4ArticleTerms,
    toggleStep4ArticleTerm,
    incrementStep4ArticleIterations,
    resetStep4ArticleIterations,
    setStep4PatentQueries,
    resetStep4PatentQueryIterations,
    setStep4ArticleQueries,
    resetStep4ArticleQueryIterations,
    addAiUsage,
  } = useFormStore()

  const patentTerms = useTermSampling({
    step,
    substep,
    api: 'ops',
    probeResults: step3PatentResults,
    probeResultsQuery: step3PatentResultsQuery,
    slice: {
      terms: step4PatentTerms,
      termsForQuery: step4PatentTermsForQuery,
      selectedTerms: step4PatentSelectedTerms,
      setTerms: setStep4PatentTerms,
      toggleTerm: toggleStep4PatentTerm,
      incrementIterations: incrementStep4PatentIterations,
      resetIterations: resetStep4PatentIterations,
    },
  })

  const articleTerms = useTermSampling({
    step,
    substep,
    api: 'scopus',
    probeResults: step3ArticleResults,
    probeResultsQuery: step3ArticleResultsQuery,
    slice: {
      terms: step4ArticleTerms,
      termsForQuery: step4ArticleTermsForQuery,
      selectedTerms: step4ArticleSelectedTerms,
      setTerms: setStep4ArticleTerms,
      toggleTerm: toggleStep4ArticleTerm,
      incrementIterations: incrementStep4ArticleIterations,
      resetIterations: resetStep4ArticleIterations,
    },
  })

  const [isBuildingQueries, setIsBuildingQueries] = useState(false)
  const [buildQueriesError, setBuildQueriesError] = useState<string | null>(null)

  if (step !== STEPS.INITIAL_EXPLORATION || substep !== 1) return null

  const patentTermsReady = !patentTerms.hasDocs || step4PatentSelectedTerms.length > 0
  const articleTermsReady = !articleTerms.hasDocs || step4ArticleSelectedTerms.length > 0
  const canBuildQueries =
    (patentTerms.hasDocs || articleTerms.hasDocs) && patentTermsReady && articleTermsReady

  async function handleBuildQueries() {
    if (!canBuildQueries) return
    setIsBuildingQueries(true)
    setBuildQueriesError(null)
    try {
      const [patentOutcome, articleOutcome] = await Promise.allSettled([
        patentTerms.hasDocs
          ? generateFinalQueriesMulti(
              input,
              step2SelectedTheme,
              step4PatentTerms!.filter((t) => step4PatentSelectedTerms.includes(t.term)),
              'ops'
            )
          : Promise.resolve(null),
        articleTerms.hasDocs
          ? generateFinalQueriesMulti(
              input,
              step2SelectedTheme,
              step4ArticleTerms!.filter((t) => step4ArticleSelectedTerms.includes(t.term)),
              'scopus'
            )
          : Promise.resolve(null),
      ])

      if (patentOutcome.status === 'rejected' || articleOutcome.status === 'rejected') {
        setBuildQueriesError('Falha ao gerar a query final com IA. Tente novamente.')
        return
      }

      if (patentOutcome.value) {
        addAiUsage(patentOutcome.value.aiUsage)
        setStep4PatentQueries(patentOutcome.value.queries)
        resetStep4PatentQueryIterations()
      }
      if (articleOutcome.value) {
        addAiUsage(articleOutcome.value.aiUsage)
        setStep4ArticleQueries(articleOutcome.value.queries)
        resetStep4ArticleQueryIterations()
      }
      onNext()
    } finally {
      setIsBuildingQueries(false)
    }
  }

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <h3 className="text-lg font-semibold text-gray-900 mb-1">Amostragem de Termos</h3>
      <p className="text-xs text-gray-500 mb-4">
        Termos extraídos pela IA a partir dos títulos/abstracts das patentes e artigos encontrados na
        Exploração Inicial, ordenados do maior pro menor score. Marque os termos que quer usar na
        construção da query final.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
        <TermChecklist
          title="Termos de patentes (OPS)"
          hasDocs={patentTerms.hasDocs}
          terms={patentTerms.terms}
          selectedTerms={patentTerms.selectedTerms}
          isLoading={patentTerms.isLoading}
          error={patentTerms.error}
          onToggle={patentTerms.toggleTerm}
          onRegenerate={patentTerms.handleRegenerate}
        />
        <TermChecklist
          title="Termos de artigos (Scopus)"
          hasDocs={articleTerms.hasDocs}
          terms={articleTerms.terms}
          selectedTerms={articleTerms.selectedTerms}
          isLoading={articleTerms.isLoading}
          error={articleTerms.error}
          onToggle={articleTerms.toggleTerm}
          onRegenerate={articleTerms.handleRegenerate}
        />
      </div>

      {buildQueriesError && <p className="mb-4 text-sm text-red-600 font-medium">{buildQueriesError}</p>}

      <div className="mt-2 pt-4 border-t border-gray-200 flex gap-4">
        <button
          type="button"
          onClick={onBack}
          disabled={isBuildingQueries}
          className="flex-1 bg-gray-400 hover:bg-gray-500 disabled:opacity-60 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          Voltar
        </button>
        <button
          type="button"
          onClick={handleBuildQueries}
          disabled={!canBuildQueries || isBuildingQueries}
          className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          {isBuildingQueries ? 'Gerando query...' : 'Gerar Query Final'}
        </button>
      </div>
    </div>
  )
}
