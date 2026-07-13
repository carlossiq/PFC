import { FloatingLabelInput } from './FloatingLabelInput'

interface StatusFilterConfig<T extends string> {
  options: { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
}

interface SessionSearchFilterProps<T extends string> {
  value: string
  onChange: (value: string) => void
  statusFilter?: StatusFilterConfig<T>
}

export function SessionSearchFilter<T extends string = string>({
  value,
  onChange,
  statusFilter,
}: SessionSearchFilterProps<T>) {
  return (
    <div className="mb-6 flex flex-wrap items-end gap-4">
      <div className="flex-1 min-w-[280px] max-w-md">
        <FloatingLabelInput
          label="Buscar por tema"
          name="sessionThemeQuery"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Ex: Drones, IA em Saúde..."
        />
      </div>

      {statusFilter && (
        <div className="flex h-10 items-center rounded-xl border border-gray-200 bg-white p-1 shadow-sm">
          {statusFilter.options.map((option) => {
            const selected = statusFilter.value === option.value

            return (
              <button
                key={option.value}
                type="button"
                onClick={() => statusFilter.onChange(option.value)}
                className={`
                  flex h-full items-center rounded-lg px-4
                  text-sm font-medium transition-all duration-200
                  ${
                    selected
                      ? 'bg-[#0f9448] text-white shadow-sm'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }
                `}
              >
                {option.label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}