import { useState } from 'react'
import { STEPS } from '../../constants/steps'
import { TABS } from '../../constants/tabs'
import { useFormStore } from '../../stores/useFormStore'
import { useWorkflowStore } from '../../stores/useWorkflowStore'
import { useProspectingStore } from '../../stores/useProspectingStore'
import { useHistoryStore } from '../../stores/useHistoryStore'
import { buildSaveSessionPayload, saveSession } from '../../services/sessionInput'
import { Button } from '../Button'
import { SectionHeader } from '../SectionHeader'

interface OutrosStepsProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

export function OutrosSteps({ step, substep, onBack, onNext }: OutrosStepsProps) {
  const { aiCallsInFlight, setSessionId } = useFormStore()
  const [isFinalizing, setIsFinalizing] = useState(false)
  const [finalizeError, setFinalizeError] = useState<string | null>(null)

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

  // Marca a sessão como concluída (completed=true) e tira o usuário do
  // wizard - só sessão pendente pode ser reaberta/reeditada (ver
  // SessionCard.tsx - "Continuar pesquisa" nem aparece pra sessão
  // completed), então uma vez finalizada não faz sentido deixar continuar
  // navegando (e salvando progresso) numa sessão já concluída.
  async function handleFinalize() {
    setIsFinalizing(true)
    setFinalizeError(null)
    try {
      const formState = useFormStore.getState()
      const payload = buildSaveSessionPayload(formState, true)
      const result = await saveSession(formState.sessionId, formState.sessionName, payload)
      setSessionId(result.session_id, result.session_public_id)
      useFormStore.getState().clearAiCallLog()
      useProspectingStore.getState().reset()
      useHistoryStore.getState().reset()
      useFormStore.getState().reset()
      useWorkflowStore.getState().setTab(TABS.SEARCH)
    } catch (err) {
      console.error('Falha ao finalizar sessão:', err)
      setFinalizeError('Não foi possível finalizar a sessão. Tente novamente.')
    } finally {
      setIsFinalizing(false)
    }
  }

  const isReportStep = step === STEPS.REPORT

  return (
    <div>
      <SectionHeader
        title={
          <>
            Passo {step + 1}
            {substep !== null && ` - Subnó ${substep + 1}`}
          </>
        }
        description="Conteúdo do passo em construção"
      />

      {isReportStep && finalizeError && (
        <p className="mb-4 text-sm text-red-600 font-medium">{finalizeError}</p>
      )}

      <div className="flex gap-4">
        <Button fullWidth variant="secondary" onClick={onBack}>
          Voltar
        </Button>
        <Button fullWidth onClick={onNext}>
          Próximo
        </Button>
        {isReportStep && (
          <Button
            fullWidth
            variant="accent"
            onClick={handleFinalize}
            disabled={isFinalizing || aiCallsInFlight > 0}
          >
            {isFinalizing ? 'Finalizando...' : 'Finalizar Sessão'}
          </Button>
        )}
      </div>
    </div>
  )
}
