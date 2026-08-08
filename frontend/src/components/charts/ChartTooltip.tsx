import type { ReactNode } from 'react'

interface ChartTooltipProps {
  /** Posição do ponto de referência em % da largura/altura do viewBox. */
  leftPct: number
  topPct: number
  children: ReactNode
}

// Tooltip flutuante padrão dos gráficos SVG - mesmo balão escuro ancorado
// acima do ponto/barra em hover, em todos os gráficos da página.
export function ChartTooltip({ leftPct, topPct, children }: ChartTooltipProps) {
  return (
    <div
      className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg bg-gray-900 text-white text-xs px-3 py-2 shadow-lg whitespace-nowrap"
      style={{ left: `${leftPct}%`, top: `${topPct}%`, marginTop: '-8px' }}
    >
      {children}
    </div>
  )
}
