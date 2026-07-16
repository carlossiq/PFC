import { STEPS } from '../../constants/steps'

interface OutrosStepsProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

export function OutrosSteps({ step, substep, onBack, onNext }: OutrosStepsProps) {
  // Step0 (Input Inicial) é todo tratado por Step1/Step2. Step1 (Exploração
  // Inicial) tem sua tela "principal" (escolha/edição da query) tratada pelo
  // Step3 quando substep===null, o substep 0 "Resultados Iniciais" tratado
  // pelo InitialResults, e o substep 1 "Amostragem de Termos" tratado pelo
  // TermSampling. Step2 (Exploração Final) segue o mesmo padrão:
  // FinalExploration (substep===null) e FinalResults (substep===0). Passos
  // além disso ainda não têm tela própria, então caem neste placeholder
  // genérico.
  if (step === STEPS.INPUT) return null
  if (step === STEPS.INITIAL_EXPLORATION && substep === null) return null
  if (step === STEPS.INITIAL_EXPLORATION && substep === 0) return null
  if (step === STEPS.INITIAL_EXPLORATION && substep === 1) return null
  if (step === STEPS.FINAL_EXPLORATION && substep === null) return null
  if (step === STEPS.FINAL_EXPLORATION && substep === 0) return null

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">
        Passo {step + 1}
        {substep !== null && ` - Subnó ${substep + 1}`}
      </h2>
      <p className="mb-6">Conteúdo do passo em construção</p>

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
      </div>
    </div>
  )
}
