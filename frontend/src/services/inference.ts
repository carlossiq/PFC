import { apiClient } from './api'
import type { OpsFinalAggregateResult, ScopusFinalAggregateResult } from './finalQuery'

// Espelha schemas/inference.py:Top10Block - `top10` é a estabilidade de
// ranking (bootstrap, 0-1), `counts` é a contagem bruta enriquecida (todas
// as categorias/entidades observadas, não só o top-10) - o que um gráfico
// de verdade (barra ou heatmap) precisa pra mostrar números reais.
export interface Top10Block {
  top10: Record<string, number>
  counts: Record<string, number>
}

// Espelha schemas/inference.py:StatisticalInferenceResponse. Os campos do
// lado que não corresponde a `api` vêm sempre null (ver
// StatisticalInferenceService.run).
export interface StatisticalInferenceResult {
  api: 'ops' | 'scopus'
  score: number
  iterationsUsed: number
  elapsedSeconds: number
  stoppedReason: string
  cpc: Top10Block | null
  depositants: Top10Block | null
  areaOfStudy: Top10Block | null
  institutions: Top10Block | null
  patentsByYear: Record<string, number> | null
  articlesByYear: Record<string, number> | null
}

function mapTop10Block(raw: { top10: Record<string, number>; counts: Record<string, number> } | null | undefined): Top10Block | null {
  if (!raw) return null
  return { top10: raw.top10, counts: raw.counts }
}

function mapResult(raw: {
  api: 'ops' | 'scopus'
  score: number
  iterations_used: number
  elapsed_seconds: number
  stopped_reason: string
  cpc?: { top10: Record<string, number>; counts: Record<string, number> } | null
  depositants?: { top10: Record<string, number>; counts: Record<string, number> } | null
  area_of_study?: { top10: Record<string, number>; counts: Record<string, number> } | null
  institutions?: { top10: Record<string, number>; counts: Record<string, number> } | null
  patents_by_year?: Record<string, number> | null
  articles_by_year?: Record<string, number> | null
}): StatisticalInferenceResult {
  return {
    api: raw.api,
    score: raw.score,
    iterationsUsed: raw.iterations_used,
    elapsedSeconds: raw.elapsed_seconds,
    stoppedReason: raw.stopped_reason,
    cpc: mapTop10Block(raw.cpc),
    depositants: mapTop10Block(raw.depositants),
    areaOfStudy: mapTop10Block(raw.area_of_study),
    institutions: mapTop10Block(raw.institutions),
    patentsByYear: raw.patents_by_year ?? null,
    articlesByYear: raw.articles_by_year ?? null,
  }
}

// Roda a inferência estatística (enriquecimento + estatísticas, ver
// StatisticalInferenceService) sobre o compilado agregado que
// runFinalSearch(..., 'ops') já devolveu - não depende de documentos
// persistidos no banco, é a fonte de dado usada por useChartCreation.ts
// pros gráficos de "Criação de Gráficos" (top depositantes, CPC, histórico).
export async function runPatentStatisticalInference(
  query: { query: string } & Record<string, unknown>,
  finalSearchResult: OpsFinalAggregateResult,
  theme: string
): Promise<StatisticalInferenceResult> {
  const { data } = await apiClient.post('/inference/final-search', {
    api: 'ops',
    query,
    final_search_result: {
      depositants: finalSearchResult.depositants,
      cpc: finalSearchResult.cpc,
      title: finalSearchResult.title,
      patents_by_year: finalSearchResult.patentsByYear,
    },
    theme,
  })
  if (!data.success) {
    throw new Error(data.message || 'Falha ao rodar a inferência estatística de patentes.')
  }
  return mapResult(data.data)
}

// Equivalente a runPatentStatisticalInference, pro lado artigos (Scopus).
export async function runArticleStatisticalInference(
  query: { query: string } & Record<string, unknown>,
  finalSearchResult: ScopusFinalAggregateResult,
  theme: string
): Promise<StatisticalInferenceResult> {
  const { data } = await apiClient.post('/inference/final-search', {
    api: 'scopus',
    query,
    final_search_result: {
      institutions: finalSearchResult.institutions,
      area_of_study: finalSearchResult.areaOfStudy,
      title: finalSearchResult.title,
      articles_by_year: finalSearchResult.articlesByYear,
    },
    theme,
  })
  if (!data.success) {
    throw new Error(data.message || 'Falha ao rodar a inferência estatística de artigos.')
  }
  return mapResult(data.data)
}
