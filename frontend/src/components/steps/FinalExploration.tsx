import { useState } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { useFinalQuerySection } from '../../hooks/useFinalQuerySection'
import { runFinalSearch } from '../../services/finalQuery'
import { ProbeQuerySectionView } from '../ProbeQuerySectionView'
import { PROBE_FIELDS_BY_API } from '../../constants/probeFields'
import { STEPS } from '../../constants/steps'

const VARIANT_CARD_LABELS = ['Específica', 'Balanceada', 'Ampla']

interface FinalExplorationProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

// Tela principal da "Exploração Final" (Passo 3): escolha entre as 3
// variantes de query final (specific/balanced/generic) já geradas no substep
// anterior (Amostragem de Termos) - mesma estrutura visual (lista + painel de
// detalhe/edição) do Step3.tsx pra Exploração Inicial, via
// ProbeQuerySectionView/useFinalQuerySection.
export function FinalExploration({ step, substep, onBack, onNext }: FinalExplorationProps) {
  const {
    input,
    step2SelectedTheme,
    step4PatentTerms,
    step4PatentSelectedTerms,
    step4PatentQueries,
    setStep4PatentQueries,
    step4PatentSelectedVariant,
    setStep4PatentSelectedVariant,
    updateStep4PatentQueryVariant,
    incrementStep4PatentQueryIterations,
    resetStep4PatentQueryIterations,
    step4ArticleTerms,
    step4ArticleSelectedTerms,
    step4ArticleQueries,
    setStep4ArticleQueries,
    step4ArticleSelectedVariant,
    setStep4ArticleSelectedVariant,
    updateStep4ArticleQueryVariant,
    incrementStep4ArticleQueryIterations,
    resetStep4ArticleQueryIterations,
    setStep4PatentResults,
    setStep4ArticleResults,
  } = useFormStore()

  const [isConfirming, setIsConfirming] = useState(false)
  const [confirmError, setConfirmError] = useState<string | null>(null)

  const hasPatentQueries = step4PatentQueries !== null
  const hasArticleQueries = step4ArticleQueries !== null

  const patentSection = useFinalQuerySection({
    api: 'ops',
    fieldOrder: PROBE_FIELDS_BY_API.ops.order,
    input,
    step2SelectedTheme,
    extractedTerms: (step4PatentTerms ?? []).filter((t) => step4PatentSelectedTerms.includes(t.term)),
    slice: {
      queries: step4PatentQueries,
      setQueries: setStep4PatentQueries,
      updateQueryVariant: updateStep4PatentQueryVariant,
      selectedVariant: step4PatentSelectedVariant,
      setSelectedVariant: setStep4PatentSelectedVariant,
      incrementIterations: incrementStep4PatentQueryIterations,
      resetIterations: resetStep4PatentQueryIterations,
    },
  })

  const articleSection = useFinalQuerySection({
    api: 'scopus',
    fieldOrder: PROBE_FIELDS_BY_API.scopus.order,
    input,
    step2SelectedTheme,
    extractedTerms: (step4ArticleTerms ?? []).filter((t) => step4ArticleSelectedTerms.includes(t.term)),
    slice: {
      queries: step4ArticleQueries,
      setQueries: setStep4ArticleQueries,
      updateQueryVariant: updateStep4ArticleQueryVariant,
      selectedVariant: step4ArticleSelectedVariant,
      setSelectedVariant: setStep4ArticleSelectedVariant,
      incrementIterations: incrementStep4ArticleQueryIterations,
      resetIterations: resetStep4ArticleQueryIterations,
    },
  })

  if (step !== STEPS.FINAL_EXPLORATION || substep !== null) return null

  const isBusy = patentSection.isBusy || articleSection.isBusy
  const canConfirm =
    (hasPatentQueries || hasArticleQueries) &&
    (!hasPatentQueries || !!patentSection.selected?.success) &&
    (!hasArticleQueries || !!articleSection.selected?.success)

  async function handleConfirm() {
    if (!canConfirm) return
    setIsConfirming(true)
    setConfirmError(null)
    try {
      const [patentOutcome, articleOutcome] = await Promise.allSettled([
        hasPatentQueries && patentSection.selected?.success
          ? runFinalSearch(patentSection.selected.query!, 'ops')
          : Promise.resolve(null),
        hasArticleQueries && articleSection.selected?.success
          ? runFinalSearch(articleSection.selected.query!, 'scopus')
          : Promise.resolve(null),
      ])

      if (patentOutcome.status === 'rejected' || articleOutcome.status === 'rejected') {
        setConfirmError('Falha ao buscar os resultados finais. Tente novamente.')
        return
      }

      if (patentOutcome.value) setStep4PatentResults(patentOutcome.value)
      if (articleOutcome.value) setStep4ArticleResults(articleOutcome.value)
      onNext()
    } finally {
      setIsConfirming(false)
    }
  }

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <h3 className="text-lg font-semibold text-gray-900 mb-1">Escolha a query final</h3>
      <p className="text-xs text-gray-500 mb-4">
        3 variantes geradas a partir dos termos marcados na Amostragem de Termos - da mais restrita
        (Específica) à mais ampla (Ampla).
      </p>

      {hasPatentQueries && (
        <ProbeQuerySectionView
          title="Query final de patentes (OPS)"
          tooltip="3 variantes da query final de patentes, geradas a partir dos termos marcados na Amostragem de Termos: Específica usa só os termos de maior pontuação (alta precisão), Balanceada mistura pontuações intermediárias, e Ampla usa todos os termos marcados (alta cobertura)."
          cardsSectionLabel="Variantes da query final"
          cardLabels={VARIANT_CARD_LABELS}
          fieldOrder={PROBE_FIELDS_BY_API.ops.order}
          fieldLabels={PROBE_FIELDS_BY_API.ops.labels}
          queries={patentSection.queries}
          selectedIndex={patentSection.selectedIndex}
          setSelectedIndex={patentSection.setSelectedIndex}
          selected={patentSection.selected}
          isLoading={patentSection.isLoading}
          error={patentSection.error}
          isRebuilding={patentSection.isRebuilding}
          rebuildError={patentSection.rebuildError}
          isBusy={patentSection.isBusy}
          isEditing={patentSection.isEditing}
          editFields={patentSection.editFields}
          setEditFields={patentSection.setEditFields}
          onRetry={patentSection.handleRetry}
          onStartEdit={patentSection.handleStartEdit}
          onCancelEdit={patentSection.handleCancelEdit}
          onSaveEdit={patentSection.handleSaveEdit}
        />
      )}

      {hasArticleQueries && (
        <ProbeQuerySectionView
          title="Query final de artigos (Scopus)"
          tooltip="3 variantes da query final de artigos, geradas a partir dos termos marcados na Amostragem de Termos: Específica usa só os termos de maior pontuação (alta precisão), Balanceada mistura pontuações intermediárias, e Ampla usa todos os termos marcados (alta cobertura)."
          cardsSectionLabel="Variantes da query final"
          cardLabels={VARIANT_CARD_LABELS}
          fieldOrder={PROBE_FIELDS_BY_API.scopus.order}
          fieldLabels={PROBE_FIELDS_BY_API.scopus.labels}
          queries={articleSection.queries}
          selectedIndex={articleSection.selectedIndex}
          setSelectedIndex={articleSection.setSelectedIndex}
          selected={articleSection.selected}
          isLoading={articleSection.isLoading}
          error={articleSection.error}
          isRebuilding={articleSection.isRebuilding}
          rebuildError={articleSection.rebuildError}
          isBusy={articleSection.isBusy}
          isEditing={articleSection.isEditing}
          editFields={articleSection.editFields}
          setEditFields={articleSection.setEditFields}
          onRetry={articleSection.handleRetry}
          onStartEdit={articleSection.handleStartEdit}
          onCancelEdit={articleSection.handleCancelEdit}
          onSaveEdit={articleSection.handleSaveEdit}
        />
      )}

      {confirmError && <p className="mt-2 text-sm text-red-600 font-medium">{confirmError}</p>}

      <div className="mt-2 pt-4 border-t border-gray-200 flex gap-4">
        <button
          type="button"
          onClick={onBack}
          disabled={isBusy || isConfirming}
          className="flex-1 bg-gray-400 hover:bg-gray-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          Voltar
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={!canConfirm || isBusy || isConfirming}
          className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          {isConfirming ? 'Buscando resultados...' : 'Confirmar e buscar'}
        </button>
      </div>
    </div>
  )
}
