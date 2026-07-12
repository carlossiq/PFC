import { useState } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { finalizeSession } from '../../services/sessionInput'
import { STEPS } from '../../constants/steps'

interface OutrosStepsProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

export function OutrosSteps({ step, substep, onBack, onNext }: OutrosStepsProps) {
  const { sessionName, input, step2SelectedTheme, step2Iterations } = useFormStore()

  const [isFinalizing, setIsFinalizing] = useState(false)
  const [finalizeResult, setFinalizeResult] = useState<string | null>(null)
  const [finalizeError, setFinalizeError] = useState<string | null>(null)

  // Step0 (Input Inicial) é todo tratado por Step1/Step2. Step1 (Exploração
  // Inicial) tem sua tela "principal" (escolha/edição da query) tratada pelo
  // Step3 quando substep===null; o substep "Resultados Iniciais" ainda não
  // tem tela própria, então cai neste placeholder genérico.
  if (step === STEPS.INPUT) return null
  if (step === STEPS.INITIAL_EXPLORATION && substep === null) return null

  // Botão de teste: os passos 2-4 ainda são placeholder, então isso só serve
  // pra exercitar a rota POST /session-input enquanto o fluxo real de
  // finalização (ao fim da Geração do Relatório) não existe de verdade.
  async function handleFinalize() {
    setIsFinalizing(true)
    setFinalizeError(null)
    setFinalizeResult(null)
    try {
      const wasRefinedByAI = !!step2SelectedTheme && step2SelectedTheme.id !== 'input'
      const generated = wasRefinedByAI
        ? { theme: step2SelectedTheme!.theme, description: step2SelectedTheme!.description || null }
        : null

      const result = await finalizeSession(sessionName, input, generated, step2Iterations)
      setFinalizeResult(
        `Sessão ${result.session_public_id} criada (session_id=${result.session_id}, root_input_id=${result.root.id}${
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
    <div>
      <h2 className="text-2xl font-bold mb-4">
        Passo {step + 1}
        {substep !== null && ` - Subnó ${substep + 1}`}
      </h2>
      <p className="mb-6">Conteúdo do passo em construção</p>

      {finalizeResult && (
        <p className="mb-4 text-sm text-[#0f9448] font-medium">{finalizeResult}</p>
      )}
      {finalizeError && (
        <p className="mb-4 text-sm text-red-600 font-medium">{finalizeError}</p>
      )}

      <div className="flex gap-4">
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
          disabled={isFinalizing}
          className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          {isFinalizing ? 'Finalizando...' : 'Finalizar Sessão (teste)'}
        </button>
      </div>
    </div>
  )
}
