import { Tooltip } from './Tooltip'

interface InfoTooltipProps {
  description: string
  defaultValue?: string | null
}

// Ícone de interrogação cinza claro, inscrito num círculo - ao passar o
// mouse, mostra a janela flutuante (Tooltip.tsx) explicando o que aquele
// campo faz e as consequências de aumentar/diminuir demais. Sempre
// acrescenta "Valor recomendado" quando o backend manda um default_value
// (nunca vem pra settings secretas - ver AppSettingValue.default_value).
export function InfoTooltip({ description, defaultValue }: InfoTooltipProps) {
  const label = defaultValue ? `${description}\n\nValor recomendado: ${defaultValue}` : description

  return (
    <Tooltip position="top" label={label}>
      <span className="w-4 h-4 flex items-center justify-center rounded-full border border-gray-300 text-gray-400 text-[10px] font-bold leading-none cursor-help shrink-0 hover:border-gray-400 hover:text-gray-500">
        ?
      </span>
    </Tooltip>
  )
}
