import { useState } from 'react'
import type { ResearchSessionSummary } from '../../services/researchSession'
import {
  CHART_AREA_FILL_OPACITY, CHART_AXIS_LABEL_TEXT, CHART_BASELINE, CHART_HEIGHT, CHART_MARGIN,
  CHART_SESSIONS_OPENED, CHART_SESSIONS_OPENED_HOVER, CHART_STATUS_COMPLETED, CHART_TIMESERIES_DAYS,
} from '../../constants/charts'
import { ChartAxisGrid } from './ChartAxisGrid'
import { ChartCard } from './ChartCard'
import { buildNiceTicks } from './chartGeometry'
import { ChartTooltip } from './ChartTooltip'
import { useChartWidth } from '../../hooks/useChartWidth'

interface DayBucket {
  key: string
  date: Date
  pending: number
  completed: number
}

interface Point {
  x: number
  y: number
}

function startOfLocalDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function toDayKey(date: Date): string {
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

// Últimos CHART_TIMESERIES_DAYS dias (incluindo hoje), zero-preenchidos antes
// de percorrer as sessões - dias sem sessão aparecem como 0, não somem da
// linha. As duas séries são independentes, cada uma na sua própria data:
// "pending" bucket pelo dia de ABERTURA (created_at) das sessões que ainda
// não foram concluídas; "completed" bucket pelo dia de CONCLUSÃO real
// (completed_at, setado uma vez quando a sessão é finalizada). Sessões
// concluídas antes dessa coluna existir (completed_at nulo) não entram na
// série "completed" - não temos como saber quando foram finalizadas.
function buildDayBuckets(sessions: ResearchSessionSummary[]): DayBucket[] {
  const today = startOfLocalDay(new Date())
  const days: DayBucket[] = []
  for (let i = CHART_TIMESERIES_DAYS - 1; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)
    days.push({ key: toDayKey(date), date, pending: 0, completed: 0 })
  }

  const indexByKey = new Map(days.map((d, idx) => [d.key, idx]))

  for (const session of sessions) {
    if (!session.completed) {
      const createdDay = startOfLocalDay(new Date(session.created_at))
      const idx = indexByKey.get(toDayKey(createdDay))
      if (idx !== undefined) days[idx].pending += 1
    } else if (session.completed_at) {
      const completedDay = startOfLocalDay(new Date(session.completed_at))
      const idx = indexByKey.get(toDayKey(completedDay))
      if (idx !== undefined) days[idx].completed += 1
    }
  }

  return days
}

// Spline cúbica monotônica (Fritsch-Carlson) - ao contrário de uma suavização
// por pontos médios, a curva passa exatamente por cada ponto de dado (um dia
// com valor 1 fica exatamente na marca de 1 do eixo); ao contrário de
// Catmull-Rom, a tangente de cada ponto é zerada em extremos locais (pico ou
// vale) e reescalada quando necessário pra nunca ultrapassar o mín/máx dos
// pontos vizinhos - por isso não "estoura" abaixo de 0 perto de dias zerados
// vizinhos de um pico isolado.
function smoothPath(points: Point[]): string {
  const n = points.length
  if (n < 3) return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')

  const dx: number[] = []
  const secant: number[] = []
  for (let i = 0; i < n - 1; i++) {
    dx.push(points[i + 1].x - points[i].x)
    secant.push((points[i + 1].y - points[i].y) / dx[i])
  }

  const tangent: number[] = new Array(n)
  tangent[0] = secant[0]
  tangent[n - 1] = secant[n - 2]
  for (let i = 1; i < n - 1; i++) {
    const sameSign = secant[i - 1] !== 0 && secant[i] !== 0 && (secant[i - 1] > 0) === (secant[i] > 0)
    tangent[i] = sameSign ? (secant[i - 1] + secant[i]) / 2 : 0
  }

  for (let i = 0; i < n - 1; i++) {
    if (secant[i] === 0) {
      tangent[i] = 0
      tangent[i + 1] = 0
      continue
    }
    const alpha = tangent[i] / secant[i]
    const beta = tangent[i + 1] / secant[i]
    const sumSq = alpha * alpha + beta * beta
    if (sumSq > 9) {
      const tau = 3 / Math.sqrt(sumSq)
      tangent[i] = tau * alpha * secant[i]
      tangent[i + 1] = tau * beta * secant[i]
    }
  }

  let d = `M${points[0].x},${points[0].y}`
  for (let i = 0; i < n - 1; i++) {
    const p0 = points[i]
    const p1 = points[i + 1]
    const cp1x = p0.x + dx[i] / 3
    const cp1y = p0.y + (tangent[i] * dx[i]) / 3
    const cp2x = p1.x - dx[i] / 3
    const cp2y = p1.y - (tangent[i + 1] * dx[i]) / 3
    d += ` C${cp1x},${cp1y} ${cp2x},${cp2y} ${p1.x},${p1.y}`
  }
  return d
}

function areaPath(points: Point[], baselineY: number): string {
  const first = points[0]
  const last = points[points.length - 1]
  return `${smoothPath(points)} L${last.x},${baselineY} L${first.x},${baselineY} Z`
}

interface SessionsTimelineAreaChartProps {
  sessions: ResearchSessionSummary[]
}

type SeriesKey = 'pending' | 'completed'

const SERIES: { key: SeriesKey; label: string; color: string }[] = [
  { key: 'pending', label: 'Em andamento', color: CHART_SESSIONS_OPENED },
  { key: 'completed', label: 'Concluídas', color: CHART_STATUS_COMPLETED },
]

// Sessões em andamento x concluídas por dia, últimos 30 dias - gráfico de
// linha sombreado (área), duas séries independentes (cada uma na sua própria
// data - ver buildDayBuckets) numa única escala (as duas são "contagem de
// sessões"). Único gráfico de linha/área do app até agora - segue a mesma
// anatomia dos gráficos de barra (ChartCard, ChartAxisGrid, ChartTooltip),
// mas com hover de crosshair único (compartilhado pelas duas séries) em vez
// de hover por barra. A legenda funciona como filtro clicável (mesmo padrão
// da "Rosca — filtrar por clique" da galeria de referência): clicar
// esconde/mostra a série, ambas visíveis por padrão - o eixo Y é
// recalculado a partir de `visibleSeries` a cada render, nunca fixo.
export function SessionsTimelineAreaChart({ sessions }: SessionsTimelineAreaChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const [visibleSeries, setVisibleSeries] = useState<Record<SeriesKey, boolean>>({ pending: true, completed: true })
  const { ref: chartWrapperRef, width: measuredWidth } = useChartWidth(800)

  if (sessions.length === 0) {
    return <ChartCard title="Sessões em andamento x concluídas (últimos 30 dias)" isEmpty />
  }

  function toggleSeries(key: SeriesKey) {
    setVisibleSeries((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const days = buildDayBuckets(sessions)

  const width = measuredWidth
  const height = CHART_HEIGHT
  const margin = CHART_MARGIN
  const plotWidth = width - margin.left - margin.right
  const plotHeight = height - margin.top - margin.bottom
  const baselineY = margin.top + plotHeight

  const rawMax = Math.max(
    ...days.map((d) => Math.max(visibleSeries.pending ? d.pending : 0, visibleSeries.completed ? d.completed : 0)),
    0,
  )
  const { axisMax, ticks } = buildNiceTicks(rawMax)

  const band = plotWidth / CHART_TIMESERIES_DAYS

  function xFor(i: number): number {
    return margin.left + i * band + band / 2
  }

  function yFor(value: number): number {
    return margin.top + plotHeight - (axisMax === 0 ? 0 : (value / axisMax) * plotHeight)
  }

  const pendingPoints = days.map((d, i) => ({ x: xFor(i), y: yFor(d.pending) }))
  const completedPoints = days.map((d, i) => ({ x: xFor(i), y: yFor(d.completed) }))

  // Rotula só a cada 5 dias + hoje - rotular os 30 pontos lotaria o eixo.
  const labelIndices = [0, 5, 10, 15, 20, 25, CHART_TIMESERIES_DAYS - 1]

  const hoveredDay = hoveredIndex !== null ? days[hoveredIndex] : null
  const hoveredX = hoveredIndex !== null ? xFor(hoveredIndex) : 0
  const visibleHoveredValues = hoveredDay
    ? SERIES.filter((s) => visibleSeries[s.key]).map((s) => ({ ...s, value: hoveredDay[s.key] }))
    : []

  const legend = (
    <>
      {SERIES.map((s) => {
        const active = visibleSeries[s.key]
        return (
          <button
            key={s.key}
            type="button"
            role="checkbox"
            aria-checked={active}
            onClick={() => toggleSeries(s.key)}
            className={`flex items-center gap-1.5 rounded px-1 py-0.5 -mx-1 cursor-pointer transition-colors hover:bg-gray-100 ${active ? '' : 'opacity-40'}`}
          >
            <span className="w-3 h-0.5 rounded-full" style={{ backgroundColor: s.color }} />
            {s.label}
          </button>
        )
      })}
    </>
  )

  return (
    <ChartCard
      title="Sessões em andamento x concluídas (últimos 30 dias)"
      description="Em andamento: sessões abertas naquele dia que ainda não foram concluídas. Concluídas: sessões finalizadas naquele dia (data real de conclusão) - sessões concluídas antes dessa métrica existir não aparecem aqui."
      legend={legend}
    >
      <div ref={chartWrapperRef} className="relative w-full" style={{ height: CHART_HEIGHT }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height={CHART_HEIGHT}
          role="img"
          aria-label="Gráfico de área: sessões em andamento e concluídas por dia, últimos 30 dias"
        >
          <ChartAxisGrid margin={margin} width={width} baselineY={baselineY} ticks={ticks} yFor={yFor} />

          {/* Duas séries independentes - concluídas (verde) desenhada por
              cima da em andamento (laranja) só pra o traço "positivo" ficar
              visível nos pontos onde as duas se cruzam. Série oculta pela
              legenda simplesmente não entra no SVG (nunca só "apagada" via
              opacidade - o eixo Y já foi recalculado sem ela). */}
          {visibleSeries.pending && (
            <>
              <path d={areaPath(pendingPoints, baselineY)} fill={CHART_SESSIONS_OPENED} fillOpacity={CHART_AREA_FILL_OPACITY} stroke="none" />
              <path d={smoothPath(pendingPoints)} fill="none" stroke={CHART_SESSIONS_OPENED} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            </>
          )}

          {visibleSeries.completed && (
            <>
              <path d={areaPath(completedPoints, baselineY)} fill={CHART_STATUS_COMPLETED} fillOpacity={CHART_AREA_FILL_OPACITY} stroke="none" />
              <path d={smoothPath(completedPoints)} fill="none" stroke={CHART_STATUS_COMPLETED} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            </>
          )}

          {labelIndices.map((i) => (
            <text
              key={i}
              x={xFor(i)}
              y={margin.top + plotHeight + 18}
              textAnchor="middle"
              fill={CHART_AXIS_LABEL_TEXT}
              fontSize={11}
            >
              {days[i].date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}
            </text>
          ))}

          {/* Hit targets - uma banda invisível por dia, mesmo idioma dos
              gráficos de barra, controla o crosshair único das duas séries. */}
          {days.map((d, i) => (
            <rect
              key={d.key}
              x={margin.left + i * band}
              y={margin.top}
              width={band}
              height={plotHeight}
              fill="transparent"
              tabIndex={0}
              role="img"
              aria-label={`${d.date.toLocaleDateString('pt-BR')}: ${d.pending} em andamento, ${d.completed} concluídas`}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex((prev) => (prev === i ? null : prev))}
              onFocus={() => setHoveredIndex(i)}
              onBlur={() => setHoveredIndex((prev) => (prev === i ? null : prev))}
              className="cursor-pointer outline-none"
            />
          ))}

          {hoveredDay && visibleHoveredValues.length > 0 && (
            <>
              <line x1={hoveredX} x2={hoveredX} y1={margin.top} y2={baselineY} stroke={CHART_BASELINE} strokeWidth={1} strokeDasharray="3,3" />
              {visibleSeries.pending && (
                <circle cx={hoveredX} cy={yFor(hoveredDay.pending)} r={4} fill={CHART_SESSIONS_OPENED_HOVER} stroke="white" strokeWidth={2} />
              )}
              {visibleSeries.completed && (
                <circle cx={hoveredX} cy={yFor(hoveredDay.completed)} r={4} fill={CHART_STATUS_COMPLETED} stroke="white" strokeWidth={2} />
              )}
            </>
          )}
        </svg>

        {hoveredDay && visibleHoveredValues.length > 0 && (
          <ChartTooltip
            leftPct={(hoveredX / width) * 100}
            topPct={(Math.min(...visibleHoveredValues.map((s) => yFor(s.value))) / height) * 100}
          >
            <p className="font-semibold">{hoveredDay.date.toLocaleDateString('pt-BR')}</p>
            {visibleHoveredValues.map((s) => (
              <p key={s.key} className="text-gray-300">
                {s.label}: {s.value}
              </p>
            ))}
          </ChartTooltip>
        )}
      </div>
    </ChartCard>
  )
}
