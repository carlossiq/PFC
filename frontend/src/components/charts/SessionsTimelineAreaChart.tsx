import { useEffect, useRef, useState } from 'react'
import type { ResearchSessionSummary } from '../../services/researchSession'
import {
  CHART_AREA_FILL_OPACITY, CHART_AXIS_LABEL_TEXT, CHART_AXIS_TICK_TEXT, CHART_BASELINE,
  CHART_GRID_LINE, CHART_HEIGHT, CHART_SESSIONS_OPENED, CHART_SESSIONS_OPENED_HOVER,
  CHART_STATUS_COMPLETED, CHART_TIMESERIES_DAYS,
} from '../../constants/charts'

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

// Passo "redondo" pro eixo Y - mesma lógica de IterationsBarChart.tsx.
function niceStep(maxValue: number, targetTicks = 4): number {
  const rawStep = Math.max(maxValue, 1) / targetTicks
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const residual = rawStep / magnitude
  const niceResidual = residual <= 1 ? 1 : residual <= 2 ? 2 : residual <= 5 ? 5 : 10
  return Math.max(1, niceResidual * magnitude)
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

// Sessões em andamento x concluídas por dia, últimos 30 dias - gráfico de
// linha sombreado (área), duas séries independentes (cada uma na sua própria
// data - ver buildDayBuckets) numa única escala (as duas são "contagem de
// sessões"). Único gráfico de linha/área do app até agora - segue a mesma
// anatomia dos gráficos de barra (ResizeObserver, margin fixo, grid manual,
// tooltip via div absoluto), mas com hover de crosshair único (compartilhado
// pelas duas séries) em vez de hover por barra.
export function SessionsTimelineAreaChart({ sessions }: SessionsTimelineAreaChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const chartWrapperRef = useRef<HTMLDivElement>(null)
  const [measuredWidth, setMeasuredWidth] = useState(800)

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

  if (sessions.length === 0) {
    return (
      <div className="rounded-xl border-2 border-gray-200 bg-white shadow-sm p-6 w-full">
        <h3 className="font-bold text-base text-gray-900 mb-1">Sessões em andamento x concluídas (últimos 30 dias)</h3>
        <p className="text-sm text-gray-500">
          Nenhuma sessão encontrada ainda - inicie uma prospecção pra ver estatísticas aqui.
        </p>
      </div>
    )
  }

  const days = buildDayBuckets(sessions)

  const width = measuredWidth
  const height = CHART_HEIGHT
  const margin = { top: 28, right: 16, bottom: 44, left: 34 }
  const plotWidth = width - margin.left - margin.right
  const plotHeight = height - margin.top - margin.bottom
  const baselineY = margin.top + plotHeight

  const rawMax = Math.max(...days.map((d) => Math.max(d.pending, d.completed)), 0)
  const step = niceStep(rawMax)
  const axisMax = Math.max(step, Math.ceil(rawMax / step) * step)
  const ticks: number[] = []
  for (let t = 0; t <= axisMax + 1e-9; t += step) ticks.push(Math.round(t))

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

  return (
    <div className="rounded-xl border-2 border-gray-200 bg-white shadow-sm p-6 w-full">
      <div className="mb-2">
        <h3 className="font-bold text-base text-gray-900">Sessões em andamento x concluídas (últimos 30 dias)</h3>
        <p className="text-xs text-gray-500 mt-1">
          Em andamento: sessões abertas naquele dia que ainda não foram concluídas. Concluídas: sessões
          finalizadas naquele dia (data real de conclusão) - sessões concluídas antes dessa métrica existir
          não aparecem aqui.
        </p>
      </div>

      <div className="flex items-center gap-4 text-xs text-gray-600 mb-2">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 rounded-full" style={{ backgroundColor: CHART_SESSIONS_OPENED }} />
          Em andamento
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 rounded-full" style={{ backgroundColor: CHART_STATUS_COMPLETED }} />
          Concluídas
        </span>
      </div>

      <div ref={chartWrapperRef} className="relative w-full" style={{ height: CHART_HEIGHT }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height={CHART_HEIGHT}
          role="img"
          aria-label="Gráfico de área: sessões em andamento e concluídas por dia, últimos 30 dias"
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

          {/* Duas séries independentes - concluídas (verde) desenhada por
              cima da em andamento (laranja) só pra o traço "positivo" ficar
              visível nos pontos onde as duas se cruzam. */}
          <path d={areaPath(pendingPoints, baselineY)} fill={CHART_SESSIONS_OPENED} fillOpacity={CHART_AREA_FILL_OPACITY} stroke="none" />
          <path d={smoothPath(pendingPoints)} fill="none" stroke={CHART_SESSIONS_OPENED} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

          <path d={areaPath(completedPoints, baselineY)} fill={CHART_STATUS_COMPLETED} fillOpacity={CHART_AREA_FILL_OPACITY} stroke="none" />
          <path d={smoothPath(completedPoints)} fill="none" stroke={CHART_STATUS_COMPLETED} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

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

          <line x1={margin.left} x2={width - margin.right} y1={baselineY} y2={baselineY} stroke={CHART_BASELINE} strokeWidth={1} />

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

          {hoveredDay && (
            <>
              <line x1={hoveredX} x2={hoveredX} y1={margin.top} y2={baselineY} stroke={CHART_BASELINE} strokeWidth={1} strokeDasharray="3,3" />
              <circle cx={hoveredX} cy={yFor(hoveredDay.pending)} r={4} fill={CHART_SESSIONS_OPENED_HOVER} stroke="white" strokeWidth={2} />
              <circle cx={hoveredX} cy={yFor(hoveredDay.completed)} r={4} fill={CHART_STATUS_COMPLETED} stroke="white" strokeWidth={2} />
            </>
          )}
        </svg>

        {hoveredDay && (
          <div
            className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg bg-gray-900 text-white text-xs px-3 py-2 shadow-lg whitespace-nowrap"
            style={{
              left: `${(hoveredX / width) * 100}%`,
              top: `${(Math.min(yFor(hoveredDay.pending), yFor(hoveredDay.completed)) / height) * 100}%`,
              marginTop: '-8px',
            }}
          >
            <p className="font-semibold">{hoveredDay.date.toLocaleDateString('pt-BR')}</p>
            <p className="text-gray-300">Em andamento: {hoveredDay.pending}</p>
            <p className="text-gray-300">Concluídas: {hoveredDay.completed}</p>
          </div>
        )}
      </div>
    </div>
  )
}
