import { useFormStore } from '../../stores/useFormStore'
import { useProbeQuerySection } from '../../hooks/useProbeQuerySection'
import { ProbeQuerySectionView } from '../ProbeQuerySectionView'
import { PROBE_FIELDS_BY_API } from '../../constants/probeFields'
import { STEPS } from '../../constants/steps'

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
    step3ArticleQueries,
    setStep3ArticleQueries,
    updateStep3ArticleQueryAt,
    step3ArticleSelectedIndex,
    setStep3ArticleSelectedIndex,
    step3ArticleGeneratedForIntake,
    incrementStep3ArticleIterations,
  } = useFormStore()

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
    },
  })

  if (step !== STEPS.INITIAL_EXPLORATION || substep !== null) return null

  const isBusy = patentSection.isBusy || articleSection.isBusy
  const canProceed = !!patentSection.selected?.success && !!articleSection.selected?.success

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <h3 className="text-lg font-semibold text-gray-900 mb-1">
        Escolha qual query utilizaremos para a Exploração Final
      </h3>
      <p className="text-xs text-gray-500 mb-4">
        Tentativas independentes de uma busca focada (poucos resultados, alta relevância), tanto de patentes quanto de artigos,
        geradas automaticamente a partir dos parâmetros enviados no passo anterior.
      </p>
     
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

      <div className="mt-2 pt-4 border-t border-gray-200 flex gap-4">
        <button
          onClick={onBack}
          disabled={isBusy}
          className="flex-1 bg-gray-400 hover:bg-gray-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
        >
          Voltar
        </button>

        <button
          onClick={onNext}
          disabled={isBusy || !canProceed}
          className="flex-1 font-semibold py-2 px-4 rounded-lg text-white transition-colors duration-300 bg-[#0f9448] hover:bg-[#0d843f] disabled:opacity-60 disabled:cursor-not-allowed"
        >
          Próximo
        </button>
      </div>
    </div>
  )
}
