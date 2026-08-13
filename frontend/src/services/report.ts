import { apiClient } from './api'

// Espelha schemas/report.py:GeneratedChart - o PNG vem embutido em base64
// na própria resposta (ver ReportService._generate_s_curve_in_memory), nada
// é salvo em disco - se o usuário sair da sessão sem baixar, o gráfico se
// perde, sem deixar arquivo órfão.
export interface GeneratedChart {
  filename: string
  imageBase64: string
  chart: string
  documentType: string
}

export interface SCurveFitQuality {
  rSquared: number
  reliable: boolean
  warning: string | null
}

// Espelha schemas/report.py:SCurveFit - ver app/core/services/s_curve.py
// para o significado de cada campo (modelo logístico de Fisher-Pry).
export interface SCurveFit {
  K: number
  r: number
  t0: number
  gpYear: number
  mpYear: number
  spYear: number
  currentSaturation: number
  yearsObserved: number[]
  cumulativeObserved: number[]
  fitQuality: SCurveFitQuality
}

export interface SCurveResult {
  chart: GeneratedChart | null
  fit: SCurveFit | null
}

function mapChart(raw: {
  filename: string
  image_base64: string
  chart: string
  document_type: string
} | undefined): GeneratedChart | null {
  if (!raw) return null
  return {
    filename: raw.filename,
    imageBase64: raw.image_base64,
    chart: raw.chart,
    documentType: raw.document_type,
  }
}

function mapFit(raw: {
  K: number
  r: number
  t0: number
  gp_year: number
  mp_year: number
  sp_year: number
  current_saturation: number
  years_observed: number[]
  cumulative_observed: number[]
  fit_quality: { r_squared: number; reliable: boolean; warning?: string | null }
} | null | undefined): SCurveFit | null {
  if (!raw) return null
  return {
    K: raw.K,
    r: raw.r,
    t0: raw.t0,
    gpYear: raw.gp_year,
    mpYear: raw.mp_year,
    spYear: raw.sp_year,
    currentSaturation: raw.current_saturation,
    yearsObserved: raw.years_observed,
    cumulativeObserved: raw.cumulative_observed,
    fitQuality: {
      rSquared: raw.fit_quality.r_squared,
      reliable: raw.fit_quality.reliable,
      warning: raw.fit_quality.warning ?? null,
    },
  }
}

// Gera a curva S de patentes a partir do patentsByYear que
// /chat/final/search já devolve para a fonte OPS - não depende de
// documentos persistidos no banco, só da sessão já existir (ver
// PatentSCurveRequest em schemas/report.py). `chart` vem null quando o
// ajuste não converge (ex: menos de 2 anos distintos, série ainda muito
// inicial) - ver SCurveFitError. Essa rota (`/graphics`) também roda o
// report completo da sessão (top depositantes/CPC/etc a partir do banco),
// por isso o chart de patente vem dentro de `charts`/`patent_s_curve_fit`,
// diferente da rota de artigo (ver generateArticleSCurve).
export async function generatePatentSCurve(
  sessionId: number,
  patentsByYear: Record<string, number>,
  projectionEndYear?: number
): Promise<SCurveResult> {
  const { data } = await apiClient.post(`/report/${sessionId}/graphics`, {
    patents_by_year: patentsByYear,
    projection_end_year: projectionEndYear ?? null,
  })
  if (!data.success) {
    throw new Error(data.message || 'Falha ao gerar a curva S de patentes.')
  }
  const result = data.data
  const rawChart = (result.charts ?? []).find(
    (c: { chart: string; document_type: string }) => c.chart === 's_curve' && c.document_type === 'patent'
  )

  return {
    chart: mapChart(rawChart),
    fit: mapFit(result.patent_s_curve_fit),
  }
}

// Equivalente a generatePatentSCurve, pro lado artigos (Scopus) - a partir
// do articlesByYear que /chat/final/search já devolve pra essa fonte. Rota
// própria (`/article-s-curve`), sem o report completo da sessão junto (ver
// ArticleSCurveResponse em schemas/report.py e o docstring da rota em
// report_router.py pro motivo).
export async function generateArticleSCurve(
  sessionId: number,
  articlesByYear: Record<string, number>,
  projectionEndYear?: number
): Promise<SCurveResult> {
  const { data } = await apiClient.post(`/report/${sessionId}/article-s-curve`, {
    articles_by_year: articlesByYear,
    projection_end_year: projectionEndYear ?? null,
  })
  if (!data.success) {
    throw new Error(data.message || 'Falha ao gerar a curva S de artigos.')
  }
  const result = data.data

  return {
    chart: mapChart(result.chart),
    fit: mapFit(result.fit),
  }
}

// Data URI pronta pro <img src> - o PNG já veio inteiro em base64 na
// resposta de generatePatentSCurve/generateArticleSCurve, então não há
// nenhum arquivo pra buscar.
export function chartDataUrl(chart: GeneratedChart): string {
  return `data:image/png;base64,${chart.imageBase64}`
}

// Dispara o download do PNG a partir do base64 já em memória (sem round
// trip de rede - o gráfico nunca foi salvo em disco no servidor, então não
// há URL nenhuma pra buscar) via um <a> temporário apontando pra um blob.
export function downloadReportChart(chart: GeneratedChart): void {
  const byteChars = atob(chart.imageBase64)
  const bytes = new Uint8Array(byteChars.length)
  for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i)
  const blob = new Blob([bytes], { type: 'image/png' })

  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = chart.filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}
