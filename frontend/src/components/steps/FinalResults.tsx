import { useState } from 'react'
import { FileText } from 'lucide-react'
import { useFormStore } from '../../stores/useFormStore'
import { ProbeResultsPanel } from '../ProbeResultsPanel'
import { Button } from '../Button'
import { SectionHeader } from '../SectionHeader'
import { STEPS } from '../../constants/steps'
import { PANEL_ACCENT } from '../../constants/probePanelAccent'
import type { OpsFinalAggregateResult } from '../../services/finalQuery'

// Painel de patentes (OPS) da busca final - a rota devolve um compilado
// agregado (depositants/cpc/title/patentsByYear), não mais uma lista de
// documentos (ver OpsFinalAggregateResult), então não dá mais pra reusar
// ProbeResultsPanel (que espera ProbeSearchResult) pro lado OPS aqui. Uma
// visualização completa (gráficos) fica pra depois - por ora só um resumo
// simples dos agregados, sem quebrar a tela.
function OpsFinalAggregatePanel({
  title,
  results,
}: {
  title: string
  results: OpsFinalAggregateResult | null
}) {
  const accent = PANEL_ACCENT.ops
  const depositantsCount = results ? Object.keys(results.depositants).length : 0
  const cpcCount = results ? Object.keys(results.cpc).length : 0

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${accent.icon}`}>
            <FileText size={16} />
          </span>
          <h4 className="font-semibold text-sm text-gray-900 truncate">{title}</h4>
        </div>
        {results && (
          <div className="text-right shrink-0">
            <div className="text-lg font-bold text-gray-900 leading-none">{results.resultsCount}</div>
          </div>
        )}
      </div>

      {results === null && <p className="text-sm text-gray-500">Ainda não buscado.</p>}

      {results !== null && results.resultsCount === 0 && (
        <p className="text-sm text-gray-500">Nenhum resultado encontrado pra essa query.</p>
      )}

      {results !== null && results.resultsCount > 0 && (
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="rounded-md bg-gray-50 p-2">
            <div className="text-xs text-gray-500">Depositantes distintos</div>
            <div className="font-semibold text-gray-900">{depositantsCount}</div>
          </div>
          <div className="rounded-md bg-gray-50 p-2">
            <div className="text-xs text-gray-500">Classificações CPC distintas</div>
            <div className="font-semibold text-gray-900">{cpcCount}</div>
          </div>
        </div>
      )}
    </div>
  )
}

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

  const [expandedPanel, setExpandedPanel] = useState<'article' | null>(null)

  if (step !== STEPS.FINAL_EXPLORATION || substep !== 0) return null

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <SectionHeader
        title="Resultados da Busca Final"
        description="Resultado da busca real com a query final escolhida no passo anterior - patentes (OPS) à esquerda, artigos (Scopus) à direita."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
        <OpsFinalAggregatePanel title="Patentes (OPS)" results={step4PatentResults} />
        <ProbeResultsPanel
          title="Artigos (Scopus)"
          api="scopus"
          results={step4ArticleResults}
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
