import { useState } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { ProbeResultsPanel } from '../ProbeResultsPanel'
import { Button } from '../Button'
import { SectionHeader } from '../SectionHeader'
import { STEPS } from '../../constants/steps'

interface InitialResultsProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

export function InitialResults({ step, substep, onBack, onNext }: InitialResultsProps) {
  const { step3PatentResults, step3ArticleResults } = useFormStore()

  const [expandedPanel, setExpandedPanel] = useState<'patent' | 'article' | null>(null)

  if (step !== STEPS.INITIAL_EXPLORATION || substep !== 0) return null

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <SectionHeader
        title="Resultados Iniciais"
        description="Resultado da busca real com as queries escolhidas no passo anterior - patentes (OPS) à esquerda, artigos (Scopus) à direita."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
        <ProbeResultsPanel
          title="Patentes (OPS)"
          api="ops"
          results={step3PatentResults}
          isExpanded={expandedPanel === 'patent'}
          onToggle={() => setExpandedPanel((prev) => (prev === 'patent' ? null : 'patent'))}
        />
        <ProbeResultsPanel
          title="Artigos (Scopus)"
          api="scopus"
          results={step3ArticleResults}
          isExpanded={expandedPanel === 'article'}
          onToggle={() => setExpandedPanel((prev) => (prev === 'article' ? null : 'article'))}
        />
      </div>

      <div className="mt-2 pt-4 border-t border-gray-200 flex gap-4">
        <Button fullWidth variant="secondary" onClick={onBack}>
          Voltar
        </Button>
        <Button fullWidth onClick={onNext}>
          Próximo
        </Button>
      </div>
    </div>
  )
}
