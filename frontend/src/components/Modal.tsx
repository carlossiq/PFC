import { FloatingLabelInput } from './FloatingLabelInput'

interface ModalInputProps {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  error?: boolean
  errorMessage?: string
}

interface ModalProps {
  isOpen: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
  isDangerous?: boolean
  // Campo de input opcional dentro do modal (padrão: sem input, só confirm/cancel).
  input?: ModalInputProps
}

export function Modal({
  isOpen,
  title,
  message,
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  onConfirm,
  onCancel,
  isDangerous = false,
  input,
}: ModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full mx-4">
        <h2 className="text-lg font-bold text-gray-900 mb-2">{title}</h2>
        <p className={`text-gray-600 ${input ? 'mb-4' : 'mb-6'}`}>{message}</p>

        {input && (
          <div className="mb-6">
            <FloatingLabelInput
              label={input.label}
              name="modal-input"
              value={input.value}
              onChange={(e) => input.onChange(e.target.value)}
              placeholder={input.placeholder}
              error={input.error}
            />
            {input.error && input.errorMessage && (
              <p className="text-red-500 text-xs mt-1">{input.errorMessage}</p>
            )}
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors font-medium"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-white rounded-lg transition-colors font-medium ${
              isDangerous
                ? 'bg-red-500 hover:bg-red-600'
                : 'bg-[#0f9448] hover:bg-[#0d843f]'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
