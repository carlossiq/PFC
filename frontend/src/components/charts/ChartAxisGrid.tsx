import { CHART_AXIS_TICK_TEXT, CHART_BASELINE, CHART_GRID_LINE, CHART_MARGIN } from '../../constants/charts'

interface ChartAxisGridProps {
  margin?: typeof CHART_MARGIN
  width: number
  baselineY: number
  ticks: number[]
  yFor: (value: number) => number
  tickFormat?: (value: number) => string
}

// Grade horizontal + rótulos do eixo Y + linha de base - mesmo eixo em todo
// gráfico numérico da página (colunas, histograma, área), só variando os
// ticks e o formato do rótulo.
export function ChartAxisGrid({
  margin = CHART_MARGIN,
  width,
  baselineY,
  ticks,
  yFor,
  tickFormat = (v) => String(v),
}: ChartAxisGridProps) {
  return (
    <>
      {ticks.map((t) => {
        const y = yFor(t)
        return (
          <g key={t}>
            <line x1={margin.left} x2={width - margin.right} y1={y} y2={y} stroke={CHART_GRID_LINE} strokeWidth={1} />
            <text x={margin.left - 8} y={y} textAnchor="end" dominantBaseline="middle" fill={CHART_AXIS_TICK_TEXT} fontSize={11}>
              {tickFormat(t)}
            </text>
          </g>
        )
      })}

      <line x1={margin.left} x2={width - margin.right} y1={baselineY} y2={baselineY} stroke={CHART_BASELINE} strokeWidth={1} />
    </>
  )
}
