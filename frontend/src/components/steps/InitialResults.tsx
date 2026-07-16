import { useState } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { buildSaveSessionPayload, saveSession } from '../../services/sessionInput'
import { ProbeResultsPanel } from '../ProbeResultsPanel'
import { STEPS } from '../../constants/steps'

interface InitialResultsProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

export function InitialResults({ step, substep, onBack, onNext }: InitialResultsProps) {
  const { step3PatentResults, step3ArticleResults, setSessionId, aiCallsInFlight } = useFormStore()

  const [expandedPanel, setExpandedPanel] = useState<'patent' | 'article' | null>(null)

  const [isFinalizing, setIsFinalizing] = useState(false)
  const [finalizeResult, setFinalizeResult] = useState<string | null>(null)
  const [finalizeError, setFinalizeError] = useState<string | null>(null)

  if (step !== STEPS.INITIAL_EXPLORATION || substep !== 0) return null

  // Marca a sessão como concluída (completed=true). Os steps seguintes
  // (Exploração Final, Geração do Relatório) ainda são placeholder
  
  async function handleFinalize() {
    setIsFinalizing(true)
    setFinalizeError(null)
    setFinalizeResult(null)
    try {
      const formState = useFormStore.getState()
      const payload = buildSaveSessionPayload(formState, true)
      const result = await saveSession(formState.sessionId, formState.sessionName, payload)
      setSessionId(result.session_id, result.session_public_id)
      // Evita reenviar (e duplicar) as mesmas chamadas de IA num próximo save.
      useFormStore.getState().clearAiCallLog()
      setFinalizeResult(
        `Sessão ${result.session_public_id} finalizada (session_id=${result.session_id}, root_input_id=${result.root.id}${
          result.generated ? `, generated_input_id=${result.generated.id}, iterations=${result.generated.iterations}` : ''
        })`
      )
    } catch (err) {
      console.error('Falha ao finalizar sessão:', err)
      setFinalizeError('Não foi possível finalizar a sessão. Tente novamente.')
    } finally {
      setIsFinalizing(false)
    }
  }

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <h3 className="text-lg font-semibold text-gray-900 mb-1">Resultados Iniciais</h3>
      <p className="text-xs text-gray-500 mb-4">
        Resultado da busca real com as queries escolhidas no passo anterior - patentes (OPS) à
        esquerda, artigos (Scopus) à direita.
      </p>

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

      {finalizeResult && (
        <p className="mb-4 text-sm text-[#0f9448] font-medium">{finalizeResult}</p>
      )}
      {finalizeError && (
        <p className="mb-4 text-sm text-red-600 font-medium">{finalizeError}</p>
      )}

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
        <button
          type="button"
          onClick={handleFinalize}
          disabled={isFinalizing || aiCallsInFlight > 0}
          className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          {isFinalizing ? 'Finalizando...' : 'Finalizar Sessão'}
        </button>
      </div>
    </div>
  )
}
