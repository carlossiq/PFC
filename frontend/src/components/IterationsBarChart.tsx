import { useEffect, useRef, useState } from 'react'
import { getSessionTotalIterations, type ResearchSessionSummary } from '../services/researchSession'
import {
  CHART_AXIS_LABEL_TEXT, CHART_AXIS_TICK_TEXT, CHART_BASELINE, CHART_BRAND_GREEN,
  CHART_BRAND_GREEN_HOVER, CHART_GRID_LINE, CHART_HEIGHT, CHART_MAX_BUCKETS, CHART_VALUE_LABEL_TEXT,
} from '../constants/charts'

interface Bucket {
  key: string
  label: string
  from: number
  to: number
  count: number
}

// Passo "redondo" pro eixo Y 
function niceStep(maxValue: number, targetTicks = 4): number {
  const rawStep = Math.max(maxValue, 1) / targetTicks
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const residual = rawStep / magnitude
  const niceResidual = residual <= 1 ? 1 : residual <= 2 ? 2 : residual <= 5 ? 5 : 10
  return Math.max(1, niceResidual * magnitude)
}

// Agrupa as sessões pelo total de iterações: um bucket por valor exato
// (0, 1, 2, ...) enquanto couber em CHART_MAX_BUCKETS;
function buildBuckets(values: number[]): Bucket[] {
  if (values.length === 0) return []
  const max = Math.max(...values)
  const distinctCount = max + 1

  const buckets: Bucket[] = []
  if (distinctCount <= CHART_MAX_BUCKETS) {
    for (let v = 0; v <= max; v++) {
      buckets.push({ key: String(v), label: String(v), from: v, to: v, count: 0 })
    }
  } else {
    const binSize = Math.ceil(distinctCount / CHART_MAX_BUCKETS)
    for (let from = 0; from <= max; from += binSize) {
      const to = Math.min(from + binSize - 1, max)
      buckets.push({ key: `${from}-${to}`, label: from === to ? String(from) : `${from}-${to}`, from, to, count: 0 })
    }
  }

  for (const value of values) {
    const bucket = buckets.find((b) => value >= b.from && value <= b.to)
    if (bucket) bucket.count += 1
  }
  return buckets
}

// Coluna com topo arredondado (4px) e base quadrada, nascendo da baseline -
// spec de "Bar / column" do design system (mark cresce de uma única baseline).
function roundedTopBarPath(x: number, y: number, w: number, h: number, r: number): string {
  if (h <= 0) return ''
  const radius = Math.min(r, w / 2, h)
  if (radius <= 0) return `M${x},${y + h} L${x},${y} L${x + w},${y} L${x + w},${y + h} Z`
  return `M${x},${y + h} L${x},${y + radius} Q${x},${y} ${x + radius},${y} L${x + w - radius},${y} Q${x + w},${y} ${x + w},${y + radius} L${x + w},${y + h} Z`
}

interface IterationsBarChartProps {
  sessions: ResearchSessionSummary[]
}

// Histograma "quantas sessões têm X iterações"
export function IterationsBarChart({ sessions }: IterationsBarChartProps) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null)
  const [showTable, setShowTable] = useState(false)
  const chartWrapperRef = useRef<HTMLDivElement>(null)
  const [measuredWidth, setMeasuredWidth] = useState(400)

  // Largura do gráfico segue o container (metade da página, via CSS) 
  useEffect(() => {
    if (showTable) return
    const el = chartWrapperRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width
      if (w) setMeasuredWidth(Math.round(w))
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [showTable])

  const values = sessions.map(getSessionTotalIterations)
  const data = buildBuckets(values).filter((d) => d.count > 0)

  if (data.length === 0) {
    return (
      <div className="rounded-xl border-2 border-gray-200 bg-white shadow-sm p-6 w-1/2">
        <h3 className="font-bold text-base text-gray-900 mb-1">Sessões por total de iterações</h3>
        <p className="text-sm text-gray-500">
          Nenhuma sessão encontrada ainda - inicie uma prospecção pra ver estatísticas aqui.
        </p>
      </div>
    )
  }

  const width = measuredWidth
  const height = CHART_HEIGHT
  const margin = { top: 28, right: 16, bottom: 44, left: 34 }
  const plotWidth = width - margin.left - margin.right
  const plotHeight = height - margin.top - margin.bottom

  const rawMax = Math.max(...data.map((d) => d.count), 0)
  const step = niceStep(rawMax)
  const axisMax = Math.max(step, Math.ceil(rawMax / step) * step)
  const ticks: number[] = []
  for (let t = 0; t <= axisMax + 1e-9; t += step) ticks.push(Math.round(t))

  const band = plotWidth / data.length
  const barWidth = Math.min(28, band * 0.55)
  const maxCount = Math.max(...data.map((d) => d.count))

  function yFor(value: number): number {
    return margin.top + plotHeight - (axisMax === 0 ? 0 : (value / axisMax) * plotHeight)
  }

  const hoveredIndex = data.findIndex((d) => d.key === hoveredKey)
  const hovered = hoveredIndex >= 0 ? data[hoveredIndex] : null

  return (
    <div className="rounded-xl border-2 border-gray-200 bg-white shadow-sm p-6 w-1/2">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="font-bold text-base text-gray-900">Prospecções por total de iterações</h3>
          <p className="text-xs text-gray-500 mt-1">
            Quanta sessões consumiram um certo valor de iterações
            com a IA para gerar os resultados das propecções.
          </p>
        </div>
        <div className="flex gap-1 shrink-0 bg-gray-100 rounded-lg p-1">
          <button
            type="button"
            onClick={() => setShowTable(false)}
            className={`text-xs font-semibold px-2.5 py-1 rounded-md transition-colors ${
              !showTable ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Gráfico
          </button>
          <button
            type="button"
            onClick={() => setShowTable(true)}
            className={`text-xs font-semibold px-2.5 py-1 rounded-md transition-colors ${
              showTable ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Tabela
          </button>
        </div>
      </div>

      {showTable ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wide border-b border-gray-200">
                <th className="py-2 pr-4 font-medium">Sessões</th>
                <th className="py-2 font-medium">Iterações</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.key} className="border-b border-gray-100 last:border-0">
                  <td className="py-2 pr-4 font-medium text-gray-900">{d.count}</td>
                  <td className="py-2 text-gray-700">{d.label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div ref={chartWrapperRef} className="relative w-full" style={{ height: CHART_HEIGHT }}>
          <svg
            viewBox={`0 0 ${width} ${height}`}
            width="100%"
            height={CHART_HEIGHT}
            role="img"
            aria-label="Histograma: número de sessões por total de iterações"
          >
            {ticks.map((t) => {
              const y = yFor(t)
              return (
                <g key={t}>
                  <line x1={margin.left} x2={width - margin.right} y1={y} y2={y} stroke={CHART_GRID_LINE} strokeWidth={1} />
                  <text x={margin.left - 8} y={y} textAnchor="end" dominantBaseline="middle" fill={CHART_AXIS_TICK_TEXT} fontSize={11}>
                    {t}
                  </text>
                </g>
              )
            })}

            {data.map((d, i) => {
              const x = margin.left + i * band + (band - barWidth) / 2
              const barTop = yFor(d.count)
              const barHeight = margin.top + plotHeight - barTop
              const isHovered = d.key === hoveredKey
              const isMax = d.count === maxCount && maxCount > 0

              return (
                <g
                  key={d.key}
                  tabIndex={0}
                  role="img"
                  aria-label={`${d.count} ${d.count === 1 ? 'sessão' : 'sessões'} com ${d.label} iterações`}
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
                    fill={isHovered ? CHART_BRAND_GREEN_HOVER : CHART_BRAND_GREEN}
                    style={{ transition: 'fill 150ms ease, transform 150ms ease' }}
                    transform={isHovered ? 'translate(0,-2)' : undefined}
                  />
                  {isMax && (
                    <text x={x + barWidth / 2} y={barTop - 8} textAnchor="middle" fill={CHART_VALUE_LABEL_TEXT} fontSize={11} fontWeight={600}>
                      {d.count}
                    </text>
                  )}
                  <text
                    x={margin.left + i * band + band / 2}
                    y={margin.top + plotHeight + 18}
                    textAnchor="middle"
                    fill={CHART_AXIS_LABEL_TEXT}
                    fontSize={11}
                  >
                    {d.label}
                  </text>
                </g>
              )
            })}

            <text
              x={margin.left + plotWidth / 2}
              y={height - 4}
              textAnchor="middle"
              fill={CHART_AXIS_TICK_TEXT}
              fontSize={10}
            >
              Total de iterações
            </text>

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
                top: `${(yFor(hovered.count) / height) * 100}%`,
                marginTop: '-8px',
              }}
            >
              <p className="font-semibold">
                {hovered.count} {hovered.count === 1 ? 'sessão' : 'sessões'}
              </p>
              <p className="text-gray-300">{hovered.label} iterações</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
