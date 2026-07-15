import { useEffect, useRef, useState } from 'react'
import type { ResearchSessionSummary } from '../../services/researchSession'
import {
  CHART_AXIS_LABEL_TEXT, CHART_AXIS_TICK_TEXT, CHART_BASELINE, CHART_GRID_LINE, CHART_HEIGHT,
  CHART_STATUS_COMPLETED, CHART_STATUS_COMPLETED_HOVER, CHART_STATUS_PENDING, CHART_STATUS_PENDING_HOVER,
  CHART_VALUE_LABEL_TEXT,
} from '../../constants/charts'

interface StatusBar {
  key: 'completed' | 'pending'
  label: string
  count: number
  percent: number
  color: string
  hoverColor: string
}

// Coluna com topo arredondado (4px) e base quadrada, nascendo da baseline -
// mesmo path usado no IterationsBarChart, pra manter a mesma "anatomia" de
// barra em todos os gráficos da página de estatísticas.
function roundedTopBarPath(x: number, y: number, w: number, h: number, r: number): string {
  if (h <= 0) return ''
  const radius = Math.min(r, w / 2, h)
  if (radius <= 0) return `M${x},${y + h} L${x},${y} L${x + w},${y} L${x + w},${y + h} Z`
  return `M${x},${y + h} L${x},${y + radius} Q${x},${y} ${x + radius},${y} L${x + w - radius},${y} Q${x + w},${y} ${x + w},${y + radius} L${x + w},${y + h} Z`
}

interface SessionStatusBarChartProps {
  sessions: ResearchSessionSummary[]
}

// Barras "Pendente" x "Concluída" em % do total de sessões - eixo Y sempre
// 0-100% (não um histograma de valores abertos como IterationsBarChart), só
// 2 categorias fixas, por isso barras bem mais largas que o outro gráfico.
export function SessionStatusBarChart({ sessions }: SessionStatusBarChartProps) {
  const [hoveredKey, setHoveredKey] = useState<StatusBar['key'] | null>(null)
  const chartWrapperRef = useRef<HTMLDivElement>(null)
  const [measuredWidth, setMeasuredWidth] = useState(400)

  // Largura do gráfico segue o container (metade da página, via CSS)
  useEffect(() => {
    const el = chartWrapperRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width
      if (w) setMeasuredWidth(Math.round(w))
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const total = sessions.length

  if (total === 0) {
    return (
      <div className="rounded-xl border-2 border-gray-200 bg-white shadow-sm p-6 w-1/2">
        <h3 className="font-bold text-base text-gray-900 mb-1">Sessões Concluídas x Pendentes</h3>
        <p className="text-sm text-gray-500">
          Nenhuma sessão encontrada ainda - inicie uma prospecção pra ver estatísticas aqui.
        </p>
      </div>
    )
  }

  const completedCount = sessions.filter((s) => s.completed).length
  const pendingCount = total - completedCount
  const completedPercent = Math.round((completedCount / total) * 100)

  const data: StatusBar[] = [
    {
      key: 'completed',
      label: 'Concluídas',
      count: completedCount,
      percent: completedPercent,
      color: CHART_STATUS_COMPLETED,
      hoverColor: CHART_STATUS_COMPLETED_HOVER,
    },
    {
      key: 'pending',
      label: 'Pendentes',
      count: pendingCount,
      // Complementar a completedPercent (não um segundo round independente) -
      // garante que as duas fatias sempre somem 100%, mesmo com arredondamento.
      percent: 100 - completedPercent,
      color: CHART_STATUS_PENDING,
      hoverColor: CHART_STATUS_PENDING_HOVER,
    },
  ]

  const width = measuredWidth
  const height = CHART_HEIGHT
  const margin = { top: 28, right: 16, bottom: 44, left: 34 }
  const plotWidth = width - margin.left - margin.right
  const plotHeight = height - margin.top - margin.bottom

  const axisMax = 100
  const ticks = [0, 25, 50, 75, 100]

  const band = plotWidth / data.length
  // "Colunas mais gordas" - só 2 categorias, então a barra ocupa boa parte da
  // banda (bem mais que os 55%/28px do histograma de iterações).
  const barWidth = Math.min(140, band * 0.55)

  function yFor(value: number): number {
    return margin.top + plotHeight - (value / axisMax) * plotHeight
  }

  const hoveredIndex = data.findIndex((d) => d.key === hoveredKey)
  const hovered = hoveredIndex >= 0 ? data[hoveredIndex] : null

  return (
    <div className="rounded-xl border-2 border-gray-200 bg-white shadow-sm p-6 w-1/2">
      <div className="mb-4">
        <h3 className="font-bold text-base text-gray-900">Sessões pendentes x concluídas</h3>
        <p className="text-xs text-gray-500 mt-1">
          {total} {total === 1 ? 'sessão no total' : 'sessões no total'} - proporção que já foi finalizada.
        </p>
      </div>

      <div ref={chartWrapperRef} className="relative w-full" style={{ height: CHART_HEIGHT }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height={CHART_HEIGHT}
          role="img"
          aria-label={`Gráfico de colunas: ${completedCount} de ${total} sessões concluídas (${completedPercent}%), ${pendingCount} pendentes`}
        >
          {ticks.map((t) => {
            const y = yFor(t)
            return (
              <g key={t}>
                <line x1={margin.left} x2={width - margin.right} y1={y} y2={y} stroke={CHART_GRID_LINE} strokeWidth={1} />
                <text x={margin.left - 8} y={y} textAnchor="end" dominantBaseline="middle" fill={CHART_AXIS_TICK_TEXT} fontSize={11}>
                  {t}%
                </text>
              </g>
            )
          })}

          {data.map((d, i) => {
            const x = margin.left + i * band + (band - barWidth) / 2
            const barTop = yFor(d.percent)
            const barHeight = margin.top + plotHeight - barTop
            const isHovered = d.key === hoveredKey

            return (
              <g
                key={d.key}
                tabIndex={0}
                role="img"
                aria-label={`${d.label}: ${d.count} ${d.count === 1 ? 'sessão' : 'sessões'} (${d.percent}%)`}
                onMouseEnter={() => setHoveredKey(d.key)}
                onMouseLeave={() => setHoveredKey((prev) => (prev === d.key ? null : prev))}
                onFocus={() => setHoveredKey(d.key)}
                onBlur={() => setHoveredKey((prev) => (prev === d.key ? null : prev))}
                className="cursor-pointer outline-none"
              >
                {/* Hit target maior que a barra visível - a banda inteira */}
                <rect x={margin.left + i * band} y={margin.top} width={band} height={plotHeight} fill="transparent" />
                <path
                  d={roundedTopBarPath(x, barTop, barWidth, barHeight, 4)}
                  fill={isHovered ? d.hoverColor : d.color}
                  style={{ transition: 'fill 150ms ease, transform 150ms ease' }}
                  transform={isHovered ? 'translate(0,-2)' : undefined}
                />
                <text x={x + barWidth / 2} y={barTop - 8} textAnchor="middle" fill={CHART_VALUE_LABEL_TEXT} fontSize={12} fontWeight={600}>
                  {d.percent}%
                </text>
                <text
                  x={margin.left + i * band + band / 2}
                  y={margin.top + plotHeight + 18}
                  textAnchor="middle"
                  fill={CHART_AXIS_LABEL_TEXT}
                  fontSize={11}
                  fontWeight={600}
                >
                  {d.label}
                </text>
              </g>
            )
          })}

          <line
            x1={margin.left}
            x2={width - margin.right}
            y1={margin.top + plotHeight}
            y2={margin.top + plotHeight}
            stroke={CHART_BASELINE}
            strokeWidth={1}
          />
        </svg>

        {hovered && (
          <div
            className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg bg-gray-900 text-white text-xs px-3 py-2 shadow-lg whitespace-nowrap"
            style={{
              left: `${((margin.left + hoveredIndex * band + band / 2) / width) * 100}%`,
              top: `${(yFor(hovered.percent) / height) * 100}%`,
              marginTop: '-8px',
            }}
          >
            <p className="font-semibold">
              {hovered.count} {hovered.count === 1 ? 'sessão' : 'sessões'}
            </p>
            <p className="text-gray-300">{hovered.percent}% do total</p>
          </div>
        )}
      </div>
    </div>
  )
}
