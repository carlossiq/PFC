interface OutrosStepsProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

export function OutrosSteps({ step, substep, onBack, onNext }: OutrosStepsProps) {
  if (step === 0) return null

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
