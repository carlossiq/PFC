import { apiClient } from './api'
import { resolveIntakePayload } from './refineTopic'
import type { FormInput, ThemeInput } from './refineTopic'
import type { ProbeApi } from '../constants/probeFields'
import type { AiUsage } from './aiUsage'
import { extractResultTitle, extractResultYear, buildProbeSearchResult } from './probeQuery'
import type { QueryOptionResult, ProbeSearchResult, ProbeSearchResultItem, StructuredQueryFields } from './probeQuery'
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

// Quantos documentos (dos até 30 buscados na probe, ver runProbeSearch) de
// fato entram na extração de termos - o custo do ranking de termos cresce
// mais rápido que o nº de documentos (ver TermExtractor no backend: BM25F é
// O(candidatos × docs), C-value é O(candidatos²)), então analisar um volume
// muito maior que isso ficaria caro. 30 dobra a amostra anterior (15) - testado
// empiricamente em ~13-15 docs a ~3s de processamento NLP puro, folga
// razoável antes de precisar reavaliar o custo de novo.
const ANALYSIS_SAMPLE_SIZE = 30

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

// `score` é o final_rrf_score bruto devolvido pelo backend (soma de dois
// termos RRF 1/(k+rank), k=60) - sem normalização, vive sempre num range
// matemático estreito (~0.018-0.033, ver TESTE_EXTRACAO_TERMOS_BM25F_RRF.md).
// Não é comparável a uma escala 0-1 "de verdade", mas É comparável entre
// termos de uma mesma extração (mesmo lote).
export interface ExtractedTerm {
  term: string
  score: number
  frequency: number
}

export interface ExtractTermsResult {
  terms: ExtractedTerm[]
  aiUsage: AiUsage | null
}

// Roda a extração de termos (spaCy + KeyBERT + TF-IDF, processamento NLP
// local - não é uma chamada de IA, sem tokens de LLM). `scoreThreshold`
// (final_rrf_score mínimo, escala RRF ~0.018-0.033) é opcional - omitido,
// o backend usa settings.term_extraction_score_threshold.
export async function extractTerms(
  items: { title: string; abstract: string }[],
  originalParams: Record<string, unknown> = {},
  scoreThreshold?: number
): Promise<ExtractTermsResult> {
  const { data } = await apiClient.post(
    '/chat/extract-terms',
    { items, original_params: originalParams },
    { params: scoreThreshold !== undefined ? { score_threshold: scoreThreshold } : {} }
  )

  if (!data.success) {
    throw new Error(data.data?.error || data.message || 'Falha ao extrair termos.')
  }

  const rawTerms: { term: string; final_rrf_score: number; frequency: number }[] = data.data.terms ?? []
  return {
    terms: rawTerms.map((t) => ({ term: t.term, score: t.final_rrf_score, frequency: t.frequency })),
    aiUsage: data.data?.ai_usage ?? null,
  }
}

export interface FinalQueryResult {
  query: QueryOptionResult
  aiUsage: AiUsage | null
}

// Assinatura do que determina o conteúdo da query final gerada (termos
// marcados + tipo escolhido) - usada tanto por TermSampling.tsx (decidir se
// "Gerar Query Final" pode reaproveitar a query já gerada, em vez de chamar
// a IA de novo) quanto por sessionHydration.ts (reconstruir essa mesma
// assinatura a partir de uma sessão salva, pro mesmo cache funcionar logo
// após retomar a sessão). Ordena os termos porque a seleção (Set de toggles)
// não tem ordem estável - duas seleções com os mesmos termos em ordem
// diferente devem contar como a mesma assinatura.
export function buildFinalQuerySelectionSignature(selectedTerms: string[], variant: FinalQueryVariant): string {
  return JSON.stringify({ terms: [...selectedTerms].sort(), variant })
}

// Top-N códigos IPC observados de verdade nos itens da busca probe (só faz
// sentido pra patentes - Scopus não tem IPC/CPC) - mandados pra IA como a
// ÚNICA fonte de códigos que ela pode usar na query final (ver
// final_system_prompt.md, seção PROBE-DISCOVERED CLASSIFICATION CODES),
// evitando o código inventar classificação do nada.
export function computeTopIpcCodes(items: ProbeSearchResultItem[] | undefined, limit = 8): string[] {
  if (!items || items.length === 0) return []
  const counts = new Map<string, number>()
  for (const item of items) {
    for (const code of item.ipcCodes ?? []) {
      if (!code) continue
      counts.set(code, (counts.get(code) ?? 0) + 1)
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([code]) => code)
}

// Gera só a variante escolhida (specific/balanced/generic) da query final
export async function generateFinalQuery(
  input: FormInput,
  step2SelectedTheme: (ThemeInput & { id: string }) | null,
  extractedTerms: ExtractedTerm[],
  variant: FinalQueryVariant,
  api: ProbeApi,
  probeClassificationCodes: string[] = []
): Promise<FinalQueryResult> {
  const intake = resolveIntakePayload(input, step2SelectedTheme)
  const { data } = await apiClient.post(
    '/chat/final/query-variant',
    { intake, extracted_terms: extractedTerms, probe_classification_codes: probeClassificationCodes },
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

// Valida uma query final editada como texto livre (a caixa única de edição
// em FinalExploration.tsx) - não reconstrói nada a partir de campos
// estruturados, só computa complexidade/warnings pro texto que o usuário
// digitou (AND/OR/parênteses etc., igual pra patentes e artigos).
export async function validateFinalQuery(query: string, api: ProbeApi = 'ops'): Promise<QueryOptionResult> {
  const { data } = await apiClient.post('/chat/final/validate-query', { query }, { params: { api } })

  if (!data.success) {
    throw new Error(data.message || 'Falha ao validar query')
  }

  return data.data
}

// Compilado agregado devolvido pela busca final da OPS (patentes) - a rota
// não devolve mais uma lista de documentos pra exibição direta (ver
// ChatService.run_final_search no backend), só esses agregados. Um
// redesenho de UI pra exibi-los (gráficos de depositantes/CPC/ano) fica pra
// depois. `rawItems` é a exceção: itens crus (title/abstract/inventors/...)
// não pra exibição, só pra persistir/alimentar o RAG do relatório (ver
// buildProbeQueryPayload em sessionInput.ts) - por isso não vira nenhum
// campo "amigável" aqui, só repassado como veio do backend.
export interface OpsFinalAggregateResult {
  success: boolean
  // Tamanho da AMOSTRA baixada/analisada (itens com título) - usado pra
  // saber se há dados; o total que a base encontrou é `totalCount`.
  resultsCount: number
  // Total REAL de patentes que a base encontrou pra query (é o número do
  // Quadro de busca e do texto do relatório, como no REPTEC).
  totalCount: number
  depositants: Record<string, number>
  cpc: Record<string, number>
  title: string[]
  patentsByYear: Record<string, number>
  rawItems: Record<string, unknown>[]
}

// Equivalente a OpsFinalAggregateResult, pro Scopus (artigos) - mesmo
// motivo de existir. areaOfStudy usa o nome completo da área ASJC (ex:
// "Medicine"), não a sigla (ex: "MEDI") - já resolvido no backend.
// `rawItems` aqui já vem enriquecido com abstract via OpenAlex (ver
// ChatService._enrich_scopus_abstracts), quando disponível.
export interface ScopusFinalAggregateResult {
  success: boolean
  // Ver OpsFinalAggregateResult: amostra x total real.
  resultsCount: number
  totalCount: number
  institutions: Record<string, number>
  areaOfStudy: Record<string, number>
  title: string[]
  articlesByYear: Record<string, number>
  rawItems: Record<string, unknown>[]
}

// Roda a busca final real com a query escolhida entre as variantes geradas.
// Total real da busca; sem ele (resposta antiga), soma a série anual; em
// último caso, o tamanho da amostra.
function totalFrom(total: number | null | undefined, byYear: Record<string, number> | undefined, sample: number): number {
  if (typeof total === 'number' && total > 0) return total
  const summed = Object.values(byYear ?? {}).reduce((sum, n) => sum + n, 0)
  return summed > 0 ? summed : sample
}

// OPS: devolve o compilado agregado (depositants/cpc/title/patentsByYear).
// Scopus: devolve o compilado agregado equivalente
// (institutions/areaOfStudy/title/articlesByYear) - mesmo esquema da OPS.
// Demais APIs (lens_patent/lens_scholarly/openalex) mantêm o shape de
// resultado da probe search (lista bruta de itens).
export async function runFinalSearch(
  query: { query: string } & Record<string, unknown>,
  api: 'ops',
  yearFrom: number,
  yearTo: number
): Promise<OpsFinalAggregateResult>
export async function runFinalSearch(
  query: { query: string } & Record<string, unknown>,
  api: 'scopus',
  yearFrom: number,
  yearTo: number
): Promise<ScopusFinalAggregateResult>
export async function runFinalSearch(
  query: { query: string } & Record<string, unknown>,
  api: ProbeApi,
  yearFrom: number,
  yearTo: number
): Promise<ProbeSearchResult>
export async function runFinalSearch(
  query: { query: string } & Record<string, unknown>,
  api: ProbeApi,
  yearFrom: number,
  yearTo: number
): Promise<ProbeSearchResult | OpsFinalAggregateResult | ScopusFinalAggregateResult> {
  // iteration não é exposto aqui - a UI sempre usa o default (0) do backend
  // (ver ChatService.run_final_search); parâmetro existe pro futuro módulo
  // de inferência estatística chamar a mesma rota HTTP diretamente.
  const { data } = await apiClient.post('/chat/final/search', query, {
    params: { api, year_from: yearFrom, year_to: yearTo },
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
      totalCount: totalFrom(result.total_count, result.patents_by_year, title.length),
      depositants: result.depositants ?? {},
      cpc: result.cpc ?? {},
      title,
      patentsByYear: result.patents_by_year ?? {},
      rawItems: result.raw_items ?? [],
    }
  }

  if (api === 'scopus') {
    const title: string[] = result.title ?? []
    return {
      success: result.success,
      resultsCount: title.length,
      totalCount: totalFrom(result.total_count, result.articles_by_year, title.length),
      institutions: result.institutions ?? {},
      areaOfStudy: result.area_of_study ?? {},
      title,
      articlesByYear: result.articles_by_year ?? {},
      rawItems: result.raw_items ?? [],
    }
  }

  const results: Record<string, unknown>[] = result.results ?? []
  return {
    ...buildProbeSearchResult(results, api, result.total_available ?? null),
    success: result.success,
    resultsCount: result.results_count,
  }
}
