import { apiClient } from './api'
import { resolveIntakePayload } from './refineTopic'
import type { FormInput, ThemeInput } from './refineTopic'
import type { ProbeApi } from '../constants/probeFields'
import type { AiUsage } from './aiUsage'
import { extractResultTitle, extractResultYear, buildProbeSearchResult } from './probeQuery'
import type { QueryOptionResult, ProbeSearchResult, StructuredQueryFields } from './probeQuery'

// OPS: abstract vem solto na chave "abstract". Scopus: "dc:description"
// (só preenchido depois do enriquecimento via OpenAlex no backend - ver
// ChatService._enrich_scopus_abstracts). Mesmo mapeamento usado no lado
// inverso em session_probe_documents.py:115-143.
export function extractAbstract(item: Record<string, unknown>, api: ProbeApi): string {
  const raw = api === 'ops' ? item['abstract'] : item['dc:description']
  return typeof raw === 'string' ? raw : ''
}

// Quantos documentos (dos até 20 buscados na probe) de fato entram na
// extração de termos - o custo do ranking de termos cresce muito mais rápido
// que o nº de documentos (ver TermExtractor no backend), então analisar todos
// os buscados é desnecessariamente caro. 15 mantém uma amostra generosa sem
// pagar esse custo.
const ANALYSIS_SAMPLE_SIZE = 15

function hasTitleAndAbstract(item: Record<string, unknown>, api: ProbeApi): boolean {
  const title = api === 'ops' ? item['invention_title'] : item['dc:title']
  return typeof title === 'string' && title.trim() !== '' && extractAbstract(item, api).trim() !== ''
}

// Distribui `total` vagas proporcionalmente ao tamanho de cada grupo (método
// dos maiores restos - mesmo princípio usado em sistemas eleitorais
// proporcionais), garantindo que a soma bata exato com `total` sem nenhuma
// quota passar do tamanho real do grupo. Determinístico pra uma mesma
// entrada (empates no resto são resolvidos pela ordem original dos grupos).
function proportionalQuotas(groupSizes: number[], total: number): number[] {
  const sumSizes = groupSizes.reduce((a, b) => a + b, 0)
  if (sumSizes <= total) return groupSizes.slice()

  const floors = groupSizes.map((size) => Math.floor((size / sumSizes) * total))
  let remaining = total - floors.reduce((a, b) => a + b, 0)

  const byRemainder = groupSizes
    .map((size, i) => ({ i, remainder: (size / sumSizes) * total - floors[i] }))
    .sort((a, b) => b.remainder - a.remainder)

  const quotas = [...floors]
  for (const { i } of byRemainder) {
    if (remaining <= 0) break
    if (quotas[i] < groupSizes[i]) {
      quotas[i] += 1
      remaining -= 1
    }
  }
  return quotas
}

// Seleciona uma amostra determinística dos documentos já buscados na probe
// pra alimentar a extração de termos - descarta os sem título/abstract (não
// contribuem com nada pro extract_terms) e mantém proporção entre os anos
// distintos presentes, em vez de simplesmente pegar os N primeiros.
export function selectDocsForAnalysis(
  rawItems: Record<string, unknown>[],
  api: ProbeApi,
  sampleSize = ANALYSIS_SAMPLE_SIZE
): Record<string, unknown>[] {
  const withContent = rawItems.filter((item) => hasTitleAndAbstract(item, api))
  if (withContent.length <= sampleSize) return withContent

  const byYear = new Map<number | null, Record<string, unknown>[]>()
  for (const item of withContent) {
    const year = extractResultYear(item, api)
    const bucket = byYear.get(year)
    if (bucket) bucket.push(item)
    else byYear.set(year, [item])
  }

  const years = [...byYear.keys()]
  const quotas = proportionalQuotas(
    years.map((year) => byYear.get(year)!.length),
    sampleSize
  )

  return years.flatMap((year, i) => byYear.get(year)!.slice(0, quotas[i]))
}

// Monta os itens genéricos {title, abstract} que /chat/extract-terms espera,
// a partir dos rawItems crus (OPS/Scopus) já guardados em step3PatentResults/
// step3ArticleResults.
export function toTermItems(
  rawItems: Record<string, unknown>[],
  api: ProbeApi
): { title: string; abstract: string }[] {
  return rawItems.map((item) => ({
    title: extractResultTitle(item, api),
    abstract: extractAbstract(item, api),
  }))
}

export interface ExtractedTerm {
  term: string
  score: number
  frequency: number
}

export interface ExtractTermsResult {
  terms: ExtractedTerm[]
  aiUsage: AiUsage | null
}

// Roda a extração de termos (KeyBERT + TF-IDF, IA interna - sem tokens de
// LLM) sobre os títulos/abstracts de um conjunto de documentos da probe.
// Termos já vêm ordenados por score decrescente (ver
// TermExtractor.extract_and_rank_terms no backend).
export async function extractTerms(
  items: { title: string; abstract: string }[],
  originalParams: Record<string, unknown> = {},
  topK = 20
): Promise<ExtractTermsResult> {
  const { data } = await apiClient.post(
    '/chat/extract-terms',
    { items, original_params: originalParams },
    { params: { top_k: topK } }
  )

  if (!data.success) {
    throw new Error(data.data?.error || data.message || 'Falha ao extrair termos.')
  }

  return {
    terms: data.data.terms ?? [],
    aiUsage: data.data?.ai_usage ?? null,
  }
}

export type FinalQueryVariant = 'specific' | 'balanced' | 'generic'

export const FINAL_QUERY_VARIANTS: FinalQueryVariant[] = ['specific', 'balanced', 'generic']

export interface FinalQueriesMultiResult {
  // Diferente da probe (N tentativas independentes e intercambiáveis),
  // aqui cada variante tem um significado próprio (precisão x cobertura) -
  // por isso mantemos as chaves specific/balanced/generic em vez de
  // achatar num array, pra UI poder rotular cada opção.
  queries: Record<FinalQueryVariant, QueryOptionResult>
  aiUsage: AiUsage | null
}

// Gera as 3 variantes (specific/balanced/generic) da query final via IA,
// usando só os termos que o usuário marcou na amostragem de termos.
export async function generateFinalQueriesMulti(
  input: FormInput,
  step2SelectedTheme: (ThemeInput & { id: string }) | null,
  extractedTerms: ExtractedTerm[],
  api: ProbeApi
): Promise<FinalQueriesMultiResult> {
  const intake = resolveIntakePayload(input, step2SelectedTheme)
  const { data } = await apiClient.post(
    '/chat/final/queries-multi',
    { intake, extracted_terms: extractedTerms },
    { params: { api } }
  )

  if (!data.success) {
    throw new Error(data.message || 'Falha ao gerar queries finais com IA')
  }

  return {
    queries: data.data?.queries ?? {},
    aiUsage: data.data?.ai_usage ?? null,
  }
}

// Reconstrói a CQL de UMA variante final a partir de campos estruturados
// editados pelo usuário, sem chamar a IA (síncrono e determinístico) - usado
// ao salvar uma edição em FinalExploration.tsx. Mesma ideia de
// rebuildProbeQuery (probeQuery.ts), só que contra /chat/final/rebuild-query
// (o backend monta a query em modo "final", não "probe").
export async function rebuildFinalQuery(
  fields: StructuredQueryFields,
  api: ProbeApi = 'ops'
): Promise<QueryOptionResult> {
  const { data } = await apiClient.post('/chat/final/rebuild-query', fields, { params: { api } })

  if (!data.success) {
    throw new Error(data.message || 'Falha ao reconstruir query')
  }

  return data.data
}

// Roda a busca final real (OPS ou Scopus) com a query escolhida entre as
// variantes geradas - mesmo shape de resultado da probe search.
export async function runFinalSearch(
  query: { query: string } & Record<string, unknown>,
  api: ProbeApi,
  maxResults = 500
): Promise<ProbeSearchResult> {
  const { data } = await apiClient.post('/chat/final/search', query, {
    params: { api, max_results: maxResults },
  })
  if (!data.success) {
    throw new Error(data.data?.error || data.message || 'Falha ao buscar resultados finais.')
  }
  const result = data.data
  const results: Record<string, unknown>[] = result.results ?? []
  return {
    ...buildProbeSearchResult(results, api, result.total_available ?? null),
    success: result.success,
    resultsCount: result.results_count,
  }
}
