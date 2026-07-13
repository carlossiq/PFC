import { Tooltip } from './Tooltip'

// Card autocontido de estatística, usado nos painéis de Resultados Iniciais
// (patentes/artigos) - sempre o mesmo formato: título, valor em destaque,
// um "?" opcional que explica o que a estatística significa (ex: Acesso
// Aberto), e um comentário opcional embaixo.
export function StatTile({
  label,
  value,
  sub,
  tooltip,
}: {
  label: string
  value: string | number
  sub?: string
  tooltip?: string
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-2.5 flex flex-col gap-1 min-w-0">
      <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
        {label}
        {tooltip && (
          <Tooltip position="top" label={tooltip}>
            <span className="w-3.5 h-3.5 flex items-center justify-center rounded-full border border-gray-400 text-gray-500 text-[9px] font-bold leading-none cursor-help">
              ?
            </span>
          </Tooltip>
        )}
      </span>
      <span className="text-lg font-bold text-gray-900 leading-none truncate">{value}</span>
      {sub && <span className="text-[11px] text-gray-500 truncate">{sub}</span>}
    </div>
  )
}
