import { useState } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { useProbeQuerySection } from '../../hooks/useProbeQuerySection'
import { ProbeQuerySectionView } from '../ProbeQuerySectionView'
import { Button } from '../Button'
import { SectionHeader } from '../SectionHeader'
import { PROBE_FIELDS_BY_API } from '../../constants/probeFields'
import { STEPS } from '../../constants/steps'
import { runProbeSearch } from '../../services/probeQuery'

interface Step3Props {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

export function Step3({ step, substep, onBack, onNext }: Step3Props) {
  const {
    input,
    step2SelectedTheme,
    step3Queries,
    setStep3Queries,
    updateStep3QueryAt,
    step3SelectedIndex,
    setStep3SelectedIndex,
    step3GeneratedForIntake,
    incrementStep3Iterations,
    resetStep3Iterations,
    step3ArticleQueries,
    setStep3ArticleQueries,
    updateStep3ArticleQueryAt,
    step3ArticleSelectedIndex,
    setStep3ArticleSelectedIndex,
    step3ArticleGeneratedForIntake,
    incrementStep3ArticleIterations,
    resetStep3ArticleIterations,
    step3PatentResults,
    step3PatentResultsQuery,
    setStep3PatentResults,
    step3ArticleResults,
    step3ArticleResultsQuery,
    setStep3ArticleResults,
  } = useFormStore()

  const [isConfirming, setIsConfirming] = useState(false)
  const [confirmError, setConfirmError] = useState<string | null>(null)

  const patentSection = useProbeQuerySection({
    step,
    substep,
    api: 'ops',
    fieldOrder: PROBE_FIELDS_BY_API.ops.order,
    input,
    step2SelectedTheme,
    slice: {
      queries: step3Queries,
      setQueries: setStep3Queries,
      updateQueryAt: updateStep3QueryAt,
      selectedIndex: step3SelectedIndex,
      setSelectedIndex: setStep3SelectedIndex,
      generatedForIntake: step3GeneratedForIntake,
      incrementIterations: incrementStep3Iterations,
      resetIterations: resetStep3Iterations,
    },
  })

  const articleSection = useProbeQuerySection({
    step,
    substep,
    api: 'scopus',
    fieldOrder: PROBE_FIELDS_BY_API.scopus.order,
    input,
    step2SelectedTheme,
    slice: {
      queries: step3ArticleQueries,
      setQueries: setStep3ArticleQueries,
      updateQueryAt: updateStep3ArticleQueryAt,
      selectedIndex: step3ArticleSelectedIndex,
      setSelectedIndex: setStep3ArticleSelectedIndex,
      generatedForIntake: step3ArticleGeneratedForIntake,
      incrementIterations: incrementStep3ArticleIterations,
      resetIterations: resetStep3ArticleIterations,
    },
  })

  if (step !== STEPS.INITIAL_EXPLORATION || substep !== null) return null

  const isBusy = patentSection.isBusy || articleSection.isBusy
  const canProceed = !!patentSection.selected?.success && !!articleSection.selected?.success

  // Roda a busca real (OPS + Scopus) com as queries selecionadas antes de
  // avançar pra "Resultados Iniciais" - não persiste nada no banco ainda,
  // só guarda o resultado na store pra tela seguinte exibir e, mais tarde,
  // pro botão de finalizar preencher session_probe_query.result_count.
  // Se a query selecionada não mudou desde a última busca (ex: usuário só
  // voltou de "Resultados Iniciais" sem alterar nada), reaproveita o
  // resultado já buscado em vez de bater na API de novo.
  async function handleConfirm() {
    if (!canProceed) return

    const patentQuerySignature = JSON.stringify(patentSection.selected!.query)
    const articleQuerySignature = JSON.stringify(articleSection.selected!.query)
    const needsPatentSearch = !step3PatentResults || step3PatentResultsQuery !== patentQuerySignature
    const needsArticleSearch = !step3ArticleResults || step3ArticleResultsQuery !== articleQuerySignature

    if (!needsPatentSearch && !needsArticleSearch) {
      onNext()
      return
    }

    setIsConfirming(true)
    setConfirmError(null)

    const [patentOutcome, articleOutcome] = await Promise.allSettled([
      needsPatentSearch ? runProbeSearch(patentSection.selected!.query!, 'ops') : Promise.resolve(null),
      needsArticleSearch ? runProbeSearch(articleSection.selected!.query!, 'scopus') : Promise.resolve(null),
    ])

    if (patentOutcome.status === 'rejected' || articleOutcome.status === 'rejected') {
      const label = patentOutcome.status === 'rejected' ? 'patentes' : 'artigos'
      setConfirmError(`Falha ao buscar resultados de ${label}. Tente novamente.`)
      setIsConfirming(false)
      return
    }

    if (needsPatentSearch && patentOutcome.value) {
      setStep3PatentResults(patentOutcome.value, patentQuerySignature)
    }
    if (needsArticleSearch && articleOutcome.value) {
      setStep3ArticleResults(articleOutcome.value, articleQuerySignature)
    }
    setIsConfirming(false)
    onNext()
  }

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <SectionHeader
        title="Escolha qual query utilizaremos para a Exploração Final"
        description="Tentativas independentes de uma busca focada (poucos resultados, alta relevância), tanto de patentes quanto de artigos, geradas automaticamente a partir dos parâmetros enviados no passo anterior."
      />
     
        <ProbeQuerySectionView
          title="Queries iniciais geradas por IA"
          tooltip="Estamos na Exploração Inicial: aqui geramos queries pra uma busca restrita de patentes, só pra encontrar um primeiro conjunto de documentos de referência. Esses documentos serão analisados, e é a partir dessa análise que montamos a query final - mais ampla - da etapa de Exploração Final, que faz a busca completa de verdade."
          cardsSectionLabel="Opções para patentes"
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

        <ProbeQuerySectionView
          title="Queries iniciais geradas por IA"
          tooltip="Mesma ideia da seção de patentes, mas pra artigos científicos: uma busca restrita no Scopus pra achar um primeiro conjunto de artigos de referência, que serão analisados antes da busca final, mais ampla."
          cardsSectionLabel="Opções para artigos"
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

      {confirmError && (
        <p className="mt-2 text-sm text-red-600 font-medium">{confirmError}</p>
      )}

      <div className="mt-2 pt-4 border-t border-gray-200 flex gap-4">
        <Button fullWidth variant="secondary" onClick={onBack} disabled={isBusy || isConfirming}>
          Voltar
        </Button>

        <Button fullWidth onClick={handleConfirm} disabled={isBusy || isConfirming || !canProceed}>
          {isConfirming ? 'Buscando resultados...' : 'Próximo'}
        </Button>
      </div>
    </div>
  )
}
