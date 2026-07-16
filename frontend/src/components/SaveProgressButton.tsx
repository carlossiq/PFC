import { useState } from 'react'

interface SaveProgressButtonProps {
  disabled: boolean
  onSave: () => Promise<void>
}

// Botão fixo no canto superior direito do wizard, visível em qualquer
// step/substep - salva o que estiver preenchido no form store até o momento
// com completed=false (sessão fica "Pendente" até o usuário finalizar).
export function SaveProgressButton({ disabled, onSave }: SaveProgressButtonProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  async function handleClick() {
    setIsSaving(true)
    setFeedback(null)
    try {
      await onSave()
      setFeedback({ type: 'success', message: 'Progresso salvo.' })
    } catch (err) {
      console.error('Falha ao salvar progresso:', err)
      setFeedback({ type: 'error', message: 'Não foi possível salvar. Tente novamente.' })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="absolute top-2 right-4 flex flex-col items-end gap-1 mr-7 ">
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || isSaving}
        className="bg-white border border-[#0f9448] text-[#0f9448] hover:bg-[#0f9448]/10 disabled:opacity-50 disabled:cursor-not-allowed font-semibold text-sm py-1.5 px-4 rounded-lg shadow-sm transition-colors"
      >
        {isSaving ? 'Salvando...' : 'Salvar progresso'}
      </button>
      {feedback && (
        <p className={`text-xs font-medium ${feedback.type === 'success' ? 'text-[#0f9448]' : 'text-red-600'}`}>
          {feedback.message}
        </p>
      )}
    </div>
  )
}
