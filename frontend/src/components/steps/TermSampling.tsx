import { useState } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { useTermSampling } from '../../hooks/useTermSampling'
import { generateFinalQuery, buildFinalQuerySelectionSignature } from '../../services/finalQuery'
import type { ExtractedTerm, FinalQueryVariant } from '../../services/finalQuery'
import { FINAL_QUERY_VARIANTS, FINAL_QUERY_VARIANT_LABELS } from '../../constants/finalQueryVariants'
import { selectableCardClass } from '../CandidatePicker'
import { LoadingScreen } from '../LoadingScreen'
import { Tooltip } from '../Tooltip'
import { Button } from '../Button'
import { SectionHeader } from '../SectionHeader'
import { STEPS } from '../../constants/steps'
import { useAutoDismiss } from '../../hooks/useAutoDismiss'
import { friendlyErrorMessage } from '../../hooks/useProbeQuerySection'

const SCORE_TOOLTIP =
  'Pontuação de relevância do termo (0 a 1), combinando ' +
  'importância estatística (frequência do termo nos documentos) ' +
  'e semântica (o quanto o termo captura o assunto do título/abstract ' +
  ')'

const VARIANT_SELECT_TOOLTIP =
  'Tipo da query final a gerar '+
  'Específica busca mais restrita e ' +
  'precisa; Balanceada  equilíbrio entre ' +
  'precisão e cobertura; Ampla ' +
  ' maior cobertura.'

interface TermChecklistProps {
  title: string
  hasDocs: boolean
  terms: ExtractedTerm[] | null
  selectedTerms: string[]
  isLoading: boolean
  error: string | null
  onToggle: (term: string) => void
  onRetry: () => void
  onSelectAll: () => void
  onDeselectAll: () => void
  selectedVariant: FinalQueryVariant
  onVariantChange: (variant: FinalQueryVariant) => void
}

// Uma coluna da amostragem de termos (patentes/OPS ou artigos/Scopus):
// checklist ordenado por score (já vem ordenado do backend), nada marcado
// por padrão. Sem botão de regenerar - a extração é NLP determinístico
// (mesmos documentos sempre produzem os mesmos termos), então só existe
// "Tentar novamente" pra quando a extração falha por erro de rede/API.
function TermChecklist({
  title,
  hasDocs,
  terms,
  selectedTerms,
  isLoading,
  error,
  onToggle,
  onRetry,
  onSelectAll,
  onDeselectAll,
  selectedVariant,
  onVariantChange,
}: TermChecklistProps) {
  const hasTerms = !!terms && terms.length > 0
  const allSelected = hasTerms && selectedTerms.length === terms!.length

  return (
    <div className="flex flex-col">
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="font-semibold text-sm text-gray-900">{title}</h4>
          <Tooltip position="left" label={SCORE_TOOLTIP}>
            <span className="text-xs font-mono text-gray-400 cursor-help">Score</span>
          </Tooltip>
        </div>

        {hasDocs && (
          <div className="flex items-center gap-1.5 mb-3">
            <label className="text-xs font-medium text-gray-600 shrink-0" htmlFor={`variant-${title}`}>
              Tipo de query final:
            </label>
            <select
              id={`variant-${title}`}
              value={selectedVariant}
              onChange={(e) => onVariantChange(e.target.value as FinalQueryVariant)}
              disabled={isLoading}
              className="flex-1 text-sm border border-gray-200 rounded-lg px-2 py-1 text-gray-900 disabled:opacity-60"
            >
              {FINAL_QUERY_VARIANTS.map((variant) => (
                <option key={variant} value={variant}>
                  {FINAL_QUERY_VARIANT_LABELS[variant]}
                </option>
              ))}
            </select>
          </div>
        )}

        {hasDocs && !isLoading && !error && hasTerms && (
          <div className="flex items-center justify-end gap-3 mb-2">
            <button
              type="button"
              onClick={onSelectAll}
              disabled={allSelected}
              className="text-xs font-semibold text-[#0f9448] hover:text-[#0d843f] disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Selecionar todos
            </button>
            <button
              type="button"
              onClick={onDeselectAll}
              disabled={selectedTerms.length === 0}
              className="text-xs font-semibold text-gray-500 hover:text-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Desmarcar todos
            </button>
          </div>
        )}

        {!hasDocs && <p className="text-sm text-gray-500">Sem documentos encontrados nesta fonte.</p>}

        {hasDocs && isLoading && <LoadingScreen message="Extraindo termos..." />}

        {hasDocs && !isLoading && error && (
          <div className="p-4 rounded-lg border-2 border-red-200 bg-red-50">
            <p className="text-sm text-red-700 mb-2">{error}</p>
            <Button variant="link" onClick={onRetry}>
              Tentar novamente
            </Button>
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
// manualmente quais quer levar pra construção da query final, e escolher
// (select) qual tipo de query final quer gerar pra cada fonte. "Gerar Query"
// já dispara a geração só do tipo escolhido (não as 3 variantes) com os
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
    setStep4PatentSelectedTerms,
    step4ArticleTerms,
    step4ArticleTermsForQuery,
    step4ArticleSelectedTerms,
    setStep4ArticleTerms,
    toggleStep4ArticleTerm,
    setStep4ArticleSelectedTerms,
    step4PatentSelectedVariant,
    setStep4PatentSelectedVariant,
    step4PatentQuery,
    step4PatentGeneratedForSelection,
    setStep4PatentQuery,
    resetStep4PatentQueryIterations,
    step4ArticleSelectedVariant,
    setStep4ArticleSelectedVariant,
    step4ArticleQuery,
    step4ArticleGeneratedForSelection,
    setStep4ArticleQuery,
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
    },
  })

  const [isBuildingQueries, setIsBuildingQueries] = useState(false)
  const [buildQueriesError, setBuildQueriesError] = useState<string | null>(null)

  useAutoDismiss(buildQueriesError, () => setBuildQueriesError(null))

  if (step !== STEPS.INITIAL_EXPLORATION || substep !== 1) return null

  const patentTermsReady = !patentTerms.hasDocs || step4PatentSelectedTerms.length > 0
  const articleTermsReady = !articleTerms.hasDocs || step4ArticleSelectedTerms.length > 0
  const canBuildQueries =
    (patentTerms.hasDocs || articleTerms.hasDocs) && patentTermsReady && articleTermsReady

  // Assinatura da seleção atual (termos marcados + tipo escolhido) por
  // fonte - comparada com a assinatura que gerou a query já guardada no
  // store pra decidir se dá pra reaproveitá-la em vez de chamar a IA de
  // novo (mesmo padrão de step3GeneratedForIntake em useProbeQuerySection).
  const currentPatentSignature = buildFinalQuerySelectionSignature(step4PatentSelectedTerms, step4PatentSelectedVariant)
  const currentArticleSignature = buildFinalQuerySelectionSignature(step4ArticleSelectedTerms, step4ArticleSelectedVariant)
  const patentNeedsGeneration =
    patentTerms.hasDocs && (!step4PatentQuery || step4PatentGeneratedForSelection !== currentPatentSignature)
  const articleNeedsGeneration =
    articleTerms.hasDocs && (!step4ArticleQuery || step4ArticleGeneratedForSelection !== currentArticleSignature)

  async function handleBuildQueries() {
    if (!canBuildQueries) return

    // Nada mudou desde a última geração (mesmos termos marcados + mesmo
    // tipo) e já existe uma query pronta pras duas fontes com docs - reusa
    // em vez de chamar a IA de novo.
    if (!patentNeedsGeneration && !articleNeedsGeneration) {
      onNext()
      return
    }

    setIsBuildingQueries(true)
    setBuildQueriesError(null)
    try {
      const [patentOutcome, articleOutcome] = await Promise.allSettled([
        patentNeedsGeneration
          ? generateFinalQuery(
              input,
              step2SelectedTheme,
              step4PatentTerms!.filter((t) => step4PatentSelectedTerms.includes(t.term)),
              step4PatentSelectedVariant,
              'ops'
            )
          : Promise.resolve(null),
        articleNeedsGeneration
          ? generateFinalQuery(
              input,
              step2SelectedTheme,
              step4ArticleTerms!.filter((t) => step4ArticleSelectedTerms.includes(t.term)),
              step4ArticleSelectedVariant,
              'scopus'
            )
          : Promise.resolve(null),
      ])

      if (patentOutcome.status === 'rejected' || articleOutcome.status === 'rejected') {
        console.error('Falha ao gerar a query final:', patentOutcome, articleOutcome)
        const reason = patentOutcome.status === 'rejected' ? patentOutcome.reason : articleOutcome.status === 'rejected' ? articleOutcome.reason : undefined
        const message = reason instanceof Error ? reason.message : undefined
        setBuildQueriesError(friendlyErrorMessage(message, 'Falha ao gerar a query final com IA. Tente novamente.'))
        return
      }

      if (patentOutcome.value) {
        addAiUsage(patentOutcome.value.aiUsage)
        setStep4PatentQuery(patentOutcome.value.query, currentPatentSignature)
        resetStep4PatentQueryIterations()
      }
      if (articleOutcome.value) {
        addAiUsage(articleOutcome.value.aiUsage)
        setStep4ArticleQuery(articleOutcome.value.query, currentArticleSignature)
        resetStep4ArticleQueryIterations()
      }
      onNext()
    } finally {
      setIsBuildingQueries(false)
    }
  }

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <SectionHeader
        title="Amostragem de Termos"
        description="Termos extraídos dos títulos/abstracts das patentes e artigos encontrados na Exploração Inicial, ordenados do maior pro menor score. Marque os termos que quer usar na construção da query final."
      />

      <div className="flex items-center gap-1.5 mb-4">
        <span className="text-xs font-medium text-gray-600">Tipos de query final</span>
        <Tooltip position="right" label={VARIANT_SELECT_TOOLTIP}>
          <span className="w-4 h-4 flex items-center justify-center rounded-full border border-gray-400 text-gray-500 text-[10px] font-bold leading-none cursor-help shrink-0">
            ?
          </span>
        </Tooltip>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
        <TermChecklist
          title="Termos de patentes (OPS)"
          hasDocs={patentTerms.hasDocs}
          terms={patentTerms.terms}
          selectedTerms={patentTerms.selectedTerms}
          isLoading={patentTerms.isLoading}
          error={patentTerms.error}
          onToggle={patentTerms.toggleTerm}
          onRetry={patentTerms.retryExtraction}
          onSelectAll={() => setStep4PatentSelectedTerms((patentTerms.terms ?? []).map((t) => t.term))}
          onDeselectAll={() => setStep4PatentSelectedTerms([])}
          selectedVariant={step4PatentSelectedVariant}
          onVariantChange={setStep4PatentSelectedVariant}
        />
        <TermChecklist
          title="Termos de artigos (Scopus)"
          hasDocs={articleTerms.hasDocs}
          terms={articleTerms.terms}
          selectedTerms={articleTerms.selectedTerms}
          isLoading={articleTerms.isLoading}
          error={articleTerms.error}
          onToggle={articleTerms.toggleTerm}
          onRetry={articleTerms.retryExtraction}
          onSelectAll={() => setStep4ArticleSelectedTerms((articleTerms.terms ?? []).map((t) => t.term))}
          onDeselectAll={() => setStep4ArticleSelectedTerms([])}
          selectedVariant={step4ArticleSelectedVariant}
          onVariantChange={setStep4ArticleSelectedVariant}
        />
      </div>

      {buildQueriesError && <p className="mb-4 text-sm text-red-600 font-medium">{buildQueriesError}</p>}

      <div className="mt-2 pt-4 border-t border-gray-200 flex gap-4">
        <Button fullWidth variant="secondary" onClick={onBack} disabled={isBuildingQueries}>
          Voltar
        </Button>
        <Button fullWidth onClick={handleBuildQueries} disabled={!canBuildQueries || isBuildingQueries}>
          {isBuildingQueries
            ? 'Gerando query...'
            : patentNeedsGeneration || articleNeedsGeneration
              ? 'Gerar Query Final'
              : 'Avançar'}
        </Button>
      </div>
    </div>
  )
}
