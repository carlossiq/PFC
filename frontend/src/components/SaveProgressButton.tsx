import { useState } from 'react'
import { Save } from 'lucide-react'
import { Tooltip } from './Tooltip'
import { useFormStore } from '../stores/useFormStore'
import { useProspectingStore } from '../stores/useProspectingStore'
import { useSidebarStore } from '../stores/useSidebarStore'
import { buildSaveSessionPayload, saveSession } from '../services/sessionInput'

// Ícone de disquete na sidebar (abaixo do toggle de collapse, logo abaixo
// do logo no Navbar acima) - só renderizado pelo Sidebar quando `locked`
// (modo de prospecção ativo, ver useSidebarStore/Workflow.tsx). Salva o que
// estiver preenchido no form store até o momento com completed=false
// (sessão fica "Pendente" até o usuário finalizar) - só fica clicável
// quando há alguma alteração desde o último save (compara a assinatura do
// payload atual contra lastSavedSignature, mesmo idioma já usado em
// step2GeneratedForInput/step3GeneratedForIntake).
export function SaveProgressButton() {
  const { collapsed } = useSidebarStore()
  const formState = useFormStore()
  const { step, substep } = useProspectingStore()
  const [isSaving, setIsSaving] = useState(false)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const payload = buildSaveSessionPayload(formState, false, step, substep)
  const hasChanges = JSON.stringify(payload) !== formState.lastSavedSignature
  const disabled = !hasChanges || !formState.input.theme.trim() || formState.aiCallsInFlight > 0 || isSaving

  async function handleClick() {
    setIsSaving(true)
    setFeedback(null)
    try {
      const result = await saveSession(formState.sessionId, formState.sessionName, payload)
      useFormStore.getState().setSessionId(result.session_id, result.session_public_id)
      useFormStore.getState().setLastSavedSignature(JSON.stringify(payload))
      useFormStore.getState().clearAiCallLog()
      setFeedback({ type: 'success', message: 'Progresso salvo.' })
    } catch (err) {
      console.error('Falha ao salvar progresso:', err)
      setFeedback({ type: 'error', message: 'Não foi possível salvar. Tente novamente.' })
    } finally {
      setIsSaving(false)
    }
  }

  const button = (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      aria-label="Salvar progresso"
      className="pointer-events-auto shrink-0 w-9 h-9 rounded-sm flex items-center justify-center text-white transition-colors enabled:hover:bg-[#0d843f] disabled:opacity-40"
    >
      <Save size={25}/>
    </button>
  )

  return (
    <div className={`flex flex-col items-center gap-1 mb-4 ${collapsed ? '' : 'self-start'}`}>
      {collapsed ? <Tooltip label={isSaving ? 'Salvando...' : 'Salvar progresso'}>{button}</Tooltip> : button}
      {!collapsed && feedback && (
        <p className={`text-xs font-medium text-center ${feedback.type === 'success' ? 'text-[#27e27a]' : 'text-red-400'}`}>
          {feedback.message}
        </p>
      )}
    </div>
  )
}
