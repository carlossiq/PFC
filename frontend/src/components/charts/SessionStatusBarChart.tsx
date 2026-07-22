import { useState } from 'react'
import type { ResearchSessionSummary } from '../../services/researchSession'
import {
  CHART_AXIS_LABEL_TEXT, CHART_HEIGHT, CHART_MARGIN, CHART_STATUS_COMPLETED, CHART_STATUS_COMPLETED_HOVER,
  CHART_STATUS_PENDING, CHART_STATUS_PENDING_HOVER, CHART_VALUE_LABEL_TEXT,
} from '../../constants/charts'
import { ChartAxisGrid } from './ChartAxisGrid'
import { ChartCard } from './ChartCard'
import { roundedTopBarPath } from './chartGeometry'
import { ChartTooltip } from './ChartTooltip'
import { useChartWidth } from '../../hooks/useChartWidth'

interface StatusBar {
  key: 'completed' | 'pending'
  label: string
  count: number
  percent: number
  color: string
  hoverColor: string
}

interface SessionStatusBarChartProps {
  sessions: ResearchSessionSummary[]
}

// Barras "Pendente" x "Concluída" em % do total de sessões - eixo Y sempre
// 0-100% (não um histograma de valores abertos como IterationsBarChart), só
// 2 categorias fixas, por isso barras bem mais largas que o outro gráfico.
export function SessionStatusBarChart({ sessions }: SessionStatusBarChartProps) {
  const [hoveredKey, setHoveredKey] = useState<StatusBar['key'] | null>(null)
  const { ref: chartWrapperRef, width: measuredWidth } = useChartWidth(400)

  const total = sessions.length

  if (total === 0) {
    return <ChartCard title="Sessões Concluídas x Pendentes" isEmpty width="half" />
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
  const margin = CHART_MARGIN
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
    <ChartCard
      title="Sessões pendentes x concluídas"
      description={`${total} ${total === 1 ? 'sessão no total' : 'sessões no total'} - proporção que já foi finalizada.`}
      width="half"
    >
      <div ref={chartWrapperRef} className="relative w-full" style={{ height: CHART_HEIGHT }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height={CHART_HEIGHT}
          role="img"
          aria-label={`Gráfico de colunas: ${completedCount} de ${total} sessões concluídas (${completedPercent}%), ${pendingCount} pendentes`}
        >
          <ChartAxisGrid margin={margin} width={width} baselineY={margin.top + plotHeight} ticks={ticks} yFor={yFor} tickFormat={(t) => `${t}%`} />

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
        </svg>

        {hovered && (
          <ChartTooltip leftPct={((margin.left + hoveredIndex * band + band / 2) / width) * 100} topPct={(yFor(hovered.percent) / height) * 100}>
            <p className="font-semibold">
              {hovered.count} {hovered.count === 1 ? 'sessão' : 'sessões'}
            </p>
            <p className="text-gray-300">{hovered.percent}% do total</p>
          </ChartTooltip>
        )}
      </div>
    </ChartCard>
  )
}
