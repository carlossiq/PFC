import { FloatingLabelInput } from './FloatingLabelInput'

interface SessionSearchFilterProps {
  value: string
  onChange: (value: string) => void
}

// Campo de filtro por tema, usado na página de busca de sessões. Mantido
// separado da página em si pra ser reutilizável (ex: se outra tela precisar
// do mesmo filtro) e pra não misturar lógica de busca/paginação com o
// controle de UI do input.
export function SessionSearchFilter({ value, onChange }: SessionSearchFilterProps) {
  return (
    <div className="max-w-md mb-6">
      <FloatingLabelInput
        label="Buscar por tema"
        name="sessionThemeQuery"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Ex: Drones, IA em Saúde..."
      />
    </div>
  )
}
