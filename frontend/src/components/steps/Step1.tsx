import { FloatingLabelInput } from '../FloatingLabelInput'
import { Step2 } from './Step2'

interface Step1Props {
  step: number
  substep: number | null
  formData: {
    theme: string
    description: string | null
    keywords: string | null
    studyArea: string | null
  }
  temaError: boolean
  hasAttempted: boolean
  onFormChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void
  onRefinirParametros: () => void
  onGerar: () => void
  onCancel: () => void
  onBack: () => void
  onNext: () => void
}

export function Step1({
  step,
  substep,
  formData,
  temaError,
  hasAttempted,
  onFormChange,
  onRefinirParametros,
  onGerar,
  onCancel,
  onBack,
  onNext,
}: Step1Props) {

  if (step !== 0) return null

  if (substep === 0) {
    return (
      <Step2
        formData={formData}
        onBack={onBack}
        onNext={onNext}
      />
    )
  }

  return (
    <div className="w-full">
      <form className="space-y-6">
        <div>
          <FloatingLabelInput
            label="Tema"
            name="theme"
            value={formData.theme}
            onChange={onFormChange}
            placeholder="Ex: Inteligência Artificial em Saúde"
            error={temaError}
          />
          {hasAttempted && temaError && (
            <p className="text-red-500 text-xs mt-1">Tema é obrigatório</p>
          )}
        </div>

        <div>
          <FloatingLabelInput
            label="Descrição"
            name="description"
            value={formData.description || ''}
            onChange={onFormChange}
            placeholder="Descreva seu projeto ou área de interesse"
            isTextarea
            rows={4}
          />
        </div>

        <div>
          <FloatingLabelInput
            label="Keywords"
            name="keywords"
            value={formData.keywords || ''}
            onChange={onFormChange}
            placeholder="machine learning, diagnóstico, saúde"
          />
        </div>

        <div>
          <FloatingLabelInput
            label="Área de Estudo"
            name="studyArea"
            value={formData.studyArea || ''}
            onChange={onFormChange}
            placeholder="Ex: Healthcare, Finance, ou G06F, A61B"
          />
        </div>

        <div className="flex gap-4 pt-0">
          <button
            type="button"
            onClick={onRefinirParametros}
            className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] text-white font-semibold py-2 px-4 rounded-lg transition-colors"
          >
            Refinar parâmetros
          </button>
          <button
            type="button"
            onClick={onGerar}
            className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] text-white font-semibold py-2 px-4 rounded-lg transition-colors"
          >
            Gerar Query
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 bg-gray-400 hover:bg-gray-500 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
