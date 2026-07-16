import { useState } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { ProbeResultsPanel } from '../ProbeResultsPanel'
import { STEPS } from '../../constants/steps'

interface FinalResultsProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

// Resultados da busca final real, exibidos depois que o usuário escolhe e
// confirma uma das 3 variantes de query em FinalExploration.tsx - mesmo
// papel que InitialResults.tsx tem pra probe search. substep 0 é o único
// substep de "Exploração Final" (SUBSTEPS.RESULTS_ANALYSIS, ver steps.ts).
export function FinalResults({ step, substep, onBack, onNext }: FinalResultsProps) {
  const { step4PatentResults, step4ArticleResults } = useFormStore()

  const [expandedPanel, setExpandedPanel] = useState<'patent' | 'article' | null>(null)

  if (step !== STEPS.FINAL_EXPLORATION || substep !== 0) return null

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <h3 className="text-lg font-semibold text-gray-900 mb-1">Resultados da Busca Final</h3>
      <p className="text-xs text-gray-500 mb-4">
        Resultado da busca real com a query final escolhida no passo anterior - patentes (OPS) à
        esquerda, artigos (Scopus) à direita.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
        <ProbeResultsPanel
          title="Patentes (OPS)"
          api="ops"
          results={step4PatentResults}
          isExpanded={expandedPanel === 'patent'}
          onToggle={() => setExpandedPanel((prev) => (prev === 'patent' ? null : 'patent'))}
        />
        <ProbeResultsPanel
          title="Artigos (Scopus)"
          api="scopus"
          results={step4ArticleResults}
          isExpanded={expandedPanel === 'article'}
          onToggle={() => setExpandedPanel((prev) => (prev === 'article' ? null : 'article'))}
        />
      </div>

      <div className="mt-2 pt-4 border-t border-gray-200 flex gap-4">
        <button
          type="button"
          onClick={onBack}
          className="flex-1 bg-gray-400 hover:bg-gray-500 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          Voltar
        </button>
        <button
          type="button"
          onClick={onNext}
          className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          Próximo
        </button>
      </div>
    </div>
  )
}
