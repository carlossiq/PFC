interface ConfirmButtonProps {
  visible: boolean
  onConfirm: () => void
  disabled?: boolean
}

// Botão redondo com check no meio, ao lado de campos de texto - fica
// invisível/inerte até o campo ser editado (visible=true), aí fica
// clicável; ao clicar, o chamador salva e volta a passar visible=false,
// fazendo o botão sumir de novo (transição suave via opacity).
export function ConfirmButton({ visible, onConfirm, disabled = false }: ConfirmButtonProps) {
  return (
    <button
      type="button"
      onClick={onConfirm}
      disabled={!visible || disabled}
      aria-label="Confirmar alteração"
      className={`
        shrink-0 w-7 h-7 rounded-full flex items-center justify-center
        bg-[#0f9448] text-white transition-opacity duration-200
        ${visible ? 'opacity-100 cursor-pointer hover:bg-[#0d843f]' : 'opacity-0 pointer-events-none'}
      `}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12" />
      </svg>
    </button>
  )
}
