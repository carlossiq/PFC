import { FloatingLabelInput } from '../FloatingLabelInput'
import { Button } from '../Button'
import { SectionHeader } from '../SectionHeader'
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
  isSaving?: boolean
  onFormChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void
  onRefinirParametros: () => void
  onGerar: () => void
  // Indica que já existe um resultado (parâmetros/query) gerado e válido pro
  // input atual - troca o texto do botão pra deixar claro que o clique só
  // navega, sem chamar a IA de novo (ver Workflow.tsx).
  refineAlreadyGenerated: boolean
  queryAlreadyGenerated: boolean
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
  isSaving,
  onFormChange,
  onRefinirParametros,
  onGerar,
  refineAlreadyGenerated,
  queryAlreadyGenerated,
  onCancel,
  onBack,
  onNext,
}: Step1Props) {

  if (step !== 0) return null

  if (substep === 0) {
    return (
      <Step2
        formData={formData}
        isSaving={isSaving}
        onBack={onBack}
        onNext={onNext}
      />
    )
  }

  return (
    <div className="w-full">
      <SectionHeader
        title="Parâmetros da Prospecção"
        description="Preencha o tema e os detalhes da sua pesquisa - só o tema é obrigatório para avançar ou salvar o progresso."
      />

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
          <p className="text-gray-500 text-xs mt-1">
            Separe as keywords por vírgulas
          </p>
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
          <Button fullWidth onClick={onRefinirParametros} disabled={isSaving}>
            {refineAlreadyGenerated ? 'Ver parâmetros' : 'Refinar parâmetros'}
          </Button>
          <Button fullWidth onClick={onGerar} disabled={isSaving}>
            {isSaving ? 'Gerando...' : queryAlreadyGenerated ? 'Avançar' : 'Gerar Query'}
          </Button>
          <Button fullWidth variant="secondary" onClick={onCancel} disabled={isSaving}>
            Cancelar
          </Button>
        </div>
      </form>
    </div>
  )
}
