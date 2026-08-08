import { apiClient } from './api'
import { resolveIntakePayload } from './refineTopic'
import type { FormInput, ThemeInput } from './refineTopic'
import type { ProbeApi } from '../constants/probeFields'
import type { AiUsage } from './aiUsage'
import { extractResultTitle, extractResultYear, buildProbeSearchResult } from './probeQuery'
import type { QueryOptionResult, ProbeSearchResult, StructuredQueryFields } from './probeQuery'
import { FINAL_QUERY_VARIANTS } from '../constants/finalQueryVariants'
import type { FinalQueryVariant } from '../constants/finalQueryVariants'

export type { FinalQueryVariant }
export { FINAL_QUERY_VARIANTS }

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
// LLM)
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

export interface FinalQueryResult {
  query: QueryOptionResult
  aiUsage: AiUsage | null
}

// Gera só a variante escolhida (specific/balanced/generic) da query final
export async function generateFinalQuery(
  input: FormInput,
  step2SelectedTheme: (ThemeInput & { id: string }) | null,
  extractedTerms: ExtractedTerm[],
  variant: FinalQueryVariant,
  api: ProbeApi
): Promise<FinalQueryResult> {
  const intake = resolveIntakePayload(input, step2SelectedTheme)
  const { data } = await apiClient.post(
    '/chat/final/query-variant',
    { intake, extracted_terms: extractedTerms },
    { params: { variant, api } }
  )

  if (!data.success) {
    throw new Error(data.message || 'Falha ao gerar a query final com IA')
  }

  return {
    query: data.data,
    aiUsage: data.data?.ai_usage ?? null,
  }
}

// Reconstrói a CQL de UMA variante final a partir de campos estruturados
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

// Compilado agregado devolvido pela busca final da OPS (patentes) - a rota
// não devolve mais a lista bruta de documentos pro lado OPS (ver
// ChatService.run_final_search no backend), só esses 4 agregados. Um
// redesenho de UI pra exibi-los (gráficos de depositantes/CPC/ano) fica pra
// depois - por ora só evita quebrar a chamada e o save de sessão (que só
// usa `resultsCount`, ver sessionInput.ts).
export interface OpsFinalAggregateResult {
  success: boolean
  resultsCount: number
  depositants: Record<string, number>
  cpc: Record<string, number>
  title: string[]
  patentsByYear: Record<string, number>
}

// Roda a busca final real com a query escolhida entre as variantes geradas.
// OPS: devolve o compilado agregado (depositants/cpc/title/patentsByYear).
// Scopus: mantém o mesmo shape de resultado da probe search (lista bruta de
// itens) - a agregação equivalente à da OPS ainda não foi feita pro Scopus.
export async function runFinalSearch(
  query: { query: string } & Record<string, unknown>,
  api: 'ops',
  yearFrom: number,
  yearTo: number,
  maxResults?: number
): Promise<OpsFinalAggregateResult>
export async function runFinalSearch(
  query: { query: string } & Record<string, unknown>,
  api: 'scopus',
  yearFrom: number,
  yearTo: number,
  maxResults?: number
): Promise<ProbeSearchResult>
export async function runFinalSearch(
  query: { query: string } & Record<string, unknown>,
  api: ProbeApi,
  yearFrom: number,
  yearTo: number,
  maxResults = 500
): Promise<ProbeSearchResult | OpsFinalAggregateResult> {
  const { data } = await apiClient.post('/chat/final/search', query, {
    params: { api, year_from: yearFrom, year_to: yearTo, max_results: maxResults },
  })
  if (!data.success) {
    throw new Error(data.data?.error || data.message || 'Falha ao buscar resultados finais.')
  }
  const result = data.data

  if (api === 'ops') {
    const title: string[] = result.title ?? []
    return {
      success: result.success,
      resultsCount: title.length,
      depositants: result.depositants ?? {},
      cpc: result.cpc ?? {},
      title,
      patentsByYear: result.patents_by_year ?? {},
    }
  }

  const results: Record<string, unknown>[] = result.results ?? []
  return {
    ...buildProbeSearchResult(results, api, result.total_available ?? null),
    success: result.success,
    resultsCount: result.results_count,
  }
}
