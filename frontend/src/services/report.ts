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
  // Só preenchido pras curvas S - quantos anos a parte tracejada projeta
  // além do último ano observado (ver PatentSCurveRequest/ArticleSCurveRequest).
  projectionYears: number | null
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
  projection_years?: number | null
} | undefined): GeneratedChart | null {
  if (!raw) return null
  return {
    filename: raw.filename,
    imageBase64: raw.image_base64,
    chart: raw.chart,
    documentType: raw.document_type,
    projectionYears: raw.projection_years ?? null,
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
  projectionYears: number
): Promise<SCurveResult> {
  const { data } = await apiClient.post(`/report/${sessionId}/graphics`, {
    patents_by_year: patentsByYear,
    projection_years: projectionYears,
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
  projectionYears: number
): Promise<SCurveResult> {
  const { data } = await apiClient.post(`/report/${sessionId}/article-s-curve`, {
    articles_by_year: articlesByYear,
    projection_years: projectionYears,
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

// Gera o heatmap top-10 (grid 5x2) a partir de uma distribuição
// label->contagem já agregada pelo chamador (ex.: `cpc`/`areaOfStudy` do
// resultado da inferência estatística, ver services/inference.ts) - mesmo
// componente serve pra CPC de patentes ou área de estudo de artigos, só
// trocando `title`/`documentType`. Rota já existe no backend desde a
// curva S, mas sem consumidor no front até agora.
export async function generateTop10Heatmap(
  sessionId: number,
  top10: Record<string, number>,
  title: string,
  documentType: 'patent' | 'article'
): Promise<GeneratedChart | null> {
  const { data } = await apiClient.post(`/report/${sessionId}/top10-heatmap`, {
    top10,
    title,
    document_type: documentType,
  })
  if (!data.success) {
    throw new Error(data.message || 'Falha ao gerar o heatmap top-10.')
  }
  return mapChart(data.data.chart)
}

// Gera o gráfico de barra horizontal top-K a partir de uma distribuição
// nome->contagem já agregada pelo chamador (ex.: `depositants`/`institutions`
// do resultado da inferência estatística) - `chartType` é explícito porque
// mais de uma distribuição desse formato pode existir pro mesmo
// `documentType` (ver TopEntitiesRequest no backend).
export async function generateTopEntitiesChart(
  sessionId: number,
  entityCounts: Record<string, number>,
  title: string,
  documentType: 'patent' | 'article',
  chartType: string
): Promise<GeneratedChart | null> {
  const { data } = await apiClient.post(`/report/${sessionId}/top-entities`, {
    entity_counts: entityCounts,
    title,
    document_type: documentType,
    chart_type: chartType,
  })
  if (!data.success) {
    throw new Error(data.message || 'Falha ao gerar o gráfico de top entidades.')
  }
  return mapChart(data.data.chart)
}

// Gera o gráfico de barras de documentos por ano (patente OU artigo) a
// partir do mesmo `patentsByYear`/`articlesByYear` que a busca final (ou a
// inferência estatística) já devolve.
export async function generateYearlyVolumeChart(
  sessionId: number,
  documentType: 'patent' | 'article',
  yearlyCounts: Record<string, number>
): Promise<GeneratedChart | null> {
  const { data } = await apiClient.post(`/report/${sessionId}/yearly-volume`, {
    document_type: documentType,
    yearly_counts: yearlyCounts,
  })
  if (!data.success) {
    throw new Error(data.message || 'Falha ao gerar o gráfico de histórico anual.')
  }
  return mapChart(data.data.chart)
}

// Busca um gráfico já persistido pra query final ATUAL de `fonte` (ver
// SessionChart no backend), sem gerar/subir outro - null se a sessão ainda
// não tem query final dessa fonte, nenhum gráfico desse tipo foi gerado
// ainda, ou o download do storage falhou no backend (melhor-esforço).
// Usado tanto por useFinalSCurve.ts (evita re-render/re-upload quando nada
// mudou desde a última geração) quanto pelo card de sessão na busca (ver
// SessionCard em Workflow.tsx), pra exibir uma curva S já gerada.
export async function getExistingChart(
  sessionId: number,
  fonte: 'ops' | 'scopus',
  chartType: string
): Promise<GeneratedChart | null> {
  const { data } = await apiClient.get(`/report/${sessionId}/existing-chart`, {
    params: { fonte, chart_type: chartType },
  })
  if (!data.success) {
    throw new Error(data.message || 'Falha ao buscar o gráfico já gerado.')
  }
  return mapChart(data.data.chart)
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

// ---------------------------------------------------------------------
// Geração do relatório REPTEC/AGITEC (checklist de seções + montagem do
// .tex + compilação de PDF) - espelha app/adapters/driving/http/report_document_router.py.
// ---------------------------------------------------------------------

// Espelha ReportWriterService.AI_SECTIONS (chat_service.py não expõe isso
// por rota, então é mantido em sincronia manualmente aqui) - ordem em que o
// checklist gera/exibe as 7 seções de IA.
export type AiSectionKey =
  | 'finalidade'
  | 'objetivo'
  | 'introducao'
  | 'informacoes_cientificas'
  | 'informacoes_tecnologicas'
  | 'tendencias_ciclo_vida'
  | 'conclusao'

export const AI_SECTION_ORDER: AiSectionKey[] = [
  'finalidade',
  'objetivo',
  'introducao',
  'informacoes_cientificas',
  'informacoes_tecnologicas',
  'tendencias_ciclo_vida',
  'conclusao',
]

export const AI_SECTION_LABELS: Record<AiSectionKey, string> = {
  finalidade: 'Finalidade',
  objetivo: 'Objetivo',
  introducao: 'Introdução',
  informacoes_cientificas: 'Resultados — Informações Científicas',
  informacoes_tecnologicas: 'Resultados — Informações Tecnológicas',
  tendencias_ciclo_vida: 'Resultados — Tendências e Ciclo de Vida',
  conclusao: 'Conclusão',
}

export async function computeSectionRagContext(sessionId: number, sectionKey: AiSectionKey): Promise<string> {
  const { data } = await apiClient.post(`/report/${sessionId}/sections/${sectionKey}/rag`)
  if (!data.success) throw new Error(data.message || `Falha ao calcular o contexto de RAG (${sectionKey}).`)
  return data.data.rag_context
}

// Estatísticas agregadas que o front já tem em memória (step4PatentResults/
// step4ArticleResults + a curva S recalculada na hora, ver
// ReportGeneration.tsx) - só existe porque os documentos da busca FINAL
// nunca são persistidos no banco (diferente dos da probe), então o backend
// sozinho não tem como calcular isso (ver SectionGenerateRequest). Só as
// 3 seções de Resultados usam algum desses campos.
export interface SectionGenerateOverrides {
  articleCount?: number
  topJournals?: string[]
  topFields?: string[]
  patentCount?: number
  topApplicants?: string[]
  topCpcCodes?: string[]
  sCurvePhase?: string
  growthRate?: string
  peakYear?: number
}

export async function generateSectionText(
  sessionId: number,
  sectionKey: AiSectionKey,
  overrides?: SectionGenerateOverrides
): Promise<string> {
  const { data } = await apiClient.post(`/report/${sessionId}/sections/${sectionKey}/generate`, {
    article_count: overrides?.articleCount ?? null,
    top_journals: overrides?.topJournals ?? [],
    top_fields: overrides?.topFields ?? [],
    patent_count: overrides?.patentCount ?? null,
    top_applicants: overrides?.topApplicants ?? [],
    top_cpc_codes: overrides?.topCpcCodes ?? [],
    s_curve_phase: overrides?.sCurvePhase ?? null,
    growth_rate: overrides?.growthRate ?? null,
    peak_year: overrides?.peakYear ?? null,
  })
  if (!data.success) throw new Error(data.message || `Falha ao gerar o texto da seção (${sectionKey}).`)
  return data.data.generated_text
}

export interface SignatureBlockInput {
  nome: string
  postoFuncao: string
}

// Cada papel aceita 1+ assinantes - ReportGeneration.tsx sempre manda pelo
// menos um item por papel (não deixa remover o último).
export interface SignaturesFormInput {
  elaboradoPor: SignatureBlockInput[]
  revisadoPor: SignatureBlockInput[]
  aprovadoPor: SignatureBlockInput[]
}

function mapSignatureBlocks(blocks: SignatureBlockInput[]) {
  return blocks.map((b) => ({ nome: b.nome, posto_funcao: b.postoFuncao }))
}

function mapSignaturesToPayload(sig?: SignaturesFormInput) {
  if (!sig) return undefined
  return {
    elaborado_por: mapSignatureBlocks(sig.elaboradoPor),
    revisado_por: mapSignatureBlocks(sig.revisadoPor),
    aprovado_por: mapSignatureBlocks(sig.aprovadoPor),
  }
}

export interface StaticSectionsPayload {
  numero: string
  ano: string
  referenciasAdministrativas: string[]
  referenciasBibliograficasAdicionais: string[]
  // Bases ADICIONAIS às auto-detectadas pelo backend a partir da fonte real
  // da busca final dessa sessão - normalmente fica vazio.
  databases?: string[]
  assinaturas?: SignaturesFormInput
  // Ano efetivamente usado na busca (ver step4PatentQuery/ArticleQuery.year_range
  // no front) - SessionInput.year_from/year_to (Step1) fica quase sempre
  // null, o ano é escolhido por query, não no wizard inteiro.
  periodStart?: number | null
  periodEnd?: number | null
}

export interface StaticSectionsResult {
  metodologia: string
  referenciasAdministrativas: string[]
  referenciasBibliograficas: string[]
  databasesDetected: string[]
}

export async function buildStaticSections(
  sessionId: number,
  payload: StaticSectionsPayload
): Promise<StaticSectionsResult> {
  const { data } = await apiClient.post(`/report/${sessionId}/sections/static`, {
    numero: payload.numero,
    ano: payload.ano,
    referencias_administrativas: payload.referenciasAdministrativas,
    referencias_bibliograficas_adicionais: payload.referenciasBibliograficasAdicionais,
    databases: payload.databases ?? [],
    assinaturas: mapSignaturesToPayload(payload.assinaturas),
    period_start: payload.periodStart ?? null,
    period_end: payload.periodEnd ?? null,
  })
  if (!data.success) throw new Error(data.message || 'Falha ao montar as seções estáticas.')
  return {
    metodologia: data.data.metodologia,
    referenciasAdministrativas: data.data.referencias_administrativas,
    referenciasBibliograficas: data.data.referencias_bibliograficas,
    databasesDetected: data.data.databases_detected ?? [],
  }
}

// Quadro de busca (query final + contagem) da seção Resultados - montado a
// partir do que o front já tem em memória (step4PatentQuery/step4ArticleQuery
// + step4*Results), sem round-trip novo ao backend.
export interface QuadroBusca {
  patenteQuery?: string | null
  patenteCount?: number | null
  artigoQuery?: string | null
  artigoCount?: number | null
}

export interface AssemblePayload {
  numero: string
  ano: string
  tema: string
  referenciasAdministrativas: string[]
  assinaturas?: SignaturesFormInput
  quadroBusca?: QuadroBusca
}

export interface AssembleResult {
  texObjectKey: string
  texContent: string
  sectionsMissing: string[]
  chartsMissing: string[]
}

export async function assembleReport(sessionId: number, payload: AssemblePayload): Promise<AssembleResult> {
  const { data } = await apiClient.post(`/report/${sessionId}/assemble`, {
    numero: payload.numero,
    ano: payload.ano,
    tema: payload.tema,
    referencias_administrativas: payload.referenciasAdministrativas,
    assinaturas: mapSignaturesToPayload(payload.assinaturas),
    quadro_busca: payload.quadroBusca
      ? {
          patente_query: payload.quadroBusca.patenteQuery ?? null,
          patente_count: payload.quadroBusca.patenteCount ?? null,
          artigo_query: payload.quadroBusca.artigoQuery ?? null,
          artigo_count: payload.quadroBusca.artigoCount ?? null,
        }
      : null,
  })
  if (!data.success) throw new Error(data.message || 'Falha ao montar o relatório.')
  return {
    texObjectKey: data.data.tex_object_key,
    texContent: data.data.tex_content,
    sectionsMissing: data.data.sections_missing ?? [],
    chartsMissing: data.data.charts_missing ?? [],
  }
}

// Remonta o .tex do zero reaproveitando os dados da capa da última
// montagem bem-sucedida (ver SessionReport.assemble_payload) - existe pra
// recuperar uma sessão já finalizada de um bug/ajuste no template ou nos
// dados (ex.: correção de LaTeX, gráfico que sumiu do MinIO) sem reabrir o
// wizard de pesquisa. Sobrescreve qualquer edição manual feita no `.tex`
// desde a última montagem.
export async function reassembleReport(sessionId: number): Promise<AssembleResult> {
  const { data } = await apiClient.post(`/report/${sessionId}/reassemble`)
  if (!data.success) throw new Error(data.message || 'Falha ao remontar o relatório.')
  return {
    texObjectKey: data.data.tex_object_key,
    texContent: data.data.tex_content,
    sectionsMissing: data.data.sections_missing ?? [],
    chartsMissing: data.data.charts_missing ?? [],
  }
}

export interface CompilePdfResult {
  success: boolean
  pdfObjectKey: string | null
  pdfBase64: string | null
  log: string | null
}

// `texContent`, quando informado, sobrescreve o `.tex` persistido ANTES de
// compilar - obrigatório passar o texto atual do editor (ver
// ReportDocumentEditor.tsx), senão o backend compila a última versão
// MONTADA (/assemble), ignorando qualquer edição feita depois.
export async function compileReportPdf(sessionId: number, texContent?: string): Promise<CompilePdfResult> {
  const { data } = await apiClient.post(`/report/${sessionId}/compile-pdf`, {
    tex_content: texContent ?? null,
  })
  if (!data.success) throw new Error(data.message || 'Falha ao compilar o PDF.')
  return {
    success: data.data.success,
    pdfObjectKey: data.data.pdf_object_key ?? null,
    pdfBase64: data.data.pdf_base64 ?? null,
    log: data.data.log ?? null,
  }
}

export interface ReportSectionStatus {
  sectionKey: string
  status: string
  generatedText: string | null
}

export interface ReportDocumentState {
  hasReport: boolean
  reportStatus: string | null
  texObjectKey: string | null
  texContent: string | null
  pdfAvailable: boolean
  sections: ReportSectionStatus[]
}

// Estado atual do relatório dessa sessão - usado tanto pra retomar o
// checklist (ReportStep.tsx decide se pula direto pra tela de documento)
// quanto pra reabrir uma sessão já finalizada (SessionCard "Ver Relatório").
export async function getReportDocument(sessionId: number): Promise<ReportDocumentState> {
  const { data } = await apiClient.get(`/report/${sessionId}/document`)
  if (!data.success) throw new Error(data.message || 'Falha ao buscar o estado do relatório.')
  const raw = data.data
  return {
    hasReport: raw.has_report,
    reportStatus: raw.report_status ?? null,
    texObjectKey: raw.tex_object_key ?? null,
    texContent: raw.tex_content ?? null,
    pdfAvailable: raw.pdf_available,
    sections: (raw.sections ?? []).map(
      (s: { section_key: string; status: string; generated_text: string | null }) => ({
        sectionKey: s.section_key,
        status: s.status,
        generatedText: s.generated_text,
      })
    ),
  }
}

export interface ReportChart {
  filename: string
  imageBase64: string
  chartType: string
  documentType: string
  caption: string
}

// Gráficos já gerados pra busca final dessa sessão, com o PNG em base64 -
// alimenta o painel lateral de imagens da tela de edição do .tex.
export async function getReportCharts(sessionId: number): Promise<ReportChart[]> {
  const { data } = await apiClient.get(`/report/${sessionId}/charts`)
  if (!data.success) throw new Error(data.message || 'Falha ao buscar os gráficos do relatório.')
  return (data.data.charts ?? []).map(
    (c: { filename: string; image_base64: string; chart_type: string; document_type: string; caption: string }) => ({
      filename: c.filename,
      imageBase64: c.image_base64,
      chartType: c.chart_type,
      documentType: c.document_type,
      caption: c.caption,
    })
  )
}

// Baixa o PDF já compilado (persistido por /compile-pdf) - usado por
// "Visualizar PDF" ao reabrir uma sessão sem precisar recompilar.
export async function getReportPdfBase64(sessionId: number): Promise<string> {
  const { data } = await apiClient.get(`/report/${sessionId}/pdf`)
  if (!data.success) throw new Error(data.message || 'Falha ao buscar o PDF compilado.')
  return data.data.pdf_base64
}

// Abre o PDF (já em base64, em memória) numa nova aba - mesmo padrão de
// downloadReportChart, mas sem forçar download (o navegador decide, geralmente
// exibindo o PDF inline). A URL do blob não é revogada aqui de propósito: a
// nova aba ainda pode estar carregando o conteúdo quando esta função retorna.
export function openReportPdf(pdfBase64: string): void {
  const byteChars = atob(pdfBase64)
  const bytes = new Uint8Array(byteChars.length)
  for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i)
  const blob = new Blob([bytes], { type: 'application/pdf' })
  const objectUrl = URL.createObjectURL(blob)
  window.open(objectUrl, '_blank')
}

