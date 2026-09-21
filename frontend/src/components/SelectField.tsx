interface SelectOption {
  value: string
  label: string
}

interface SelectFieldProps {
  label: string
  value: string
  options: SelectOption[]
  onChange: (value: string) => void
  disabled?: boolean
}

// Campo de seleção nativo (mostra as opções ao clicar) - usado pra escolhas
// exclusivas tipo "qual API de patente está ativa" ou "qual config de IA
// esse call site usa". Salva imediatamente ao escolher (onChange).
export function SelectField({ label, value, options, onChange, disabled = false }: SelectFieldProps) {
  return (
    <div className="flex items-center justify-between gap-3">
      <label className="text-sm font-medium text-gray-800 shrink-0">{label}</label>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 max-w-xs text-sm border border-gray-300 rounded-md px-2 py-1.5 text-gray-900 bg-white disabled:opacity-60 disabled:bg-gray-100"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
