import { apiClient } from './api'
import { resolveIntakePayload } from './refineTopic'
import type { FormInput, ThemeInput } from './refineTopic'
import type { ProbeApi } from '../constants/probeFields'
import type { AiUsage } from './aiUsage'

// Genérico porque os campos variam por API (patente: title/abstract/ipc/year;
// artigo: title/abstract/field_of_study/year) — ver PROBE_FIELDS_BY_API em
// constants/probeFields.ts, que define quais chaves aparecem na UI.
export type StructuredQueryFields = Record<string, string[]>

export interface QueryComplexity {
  score: number
  level: string
  warnings: string[]
  recommendations: string[]
}

export interface YearRange {
  from: number
  to: number
}

export interface QueryOptionResult {
  success: boolean
  // OPS retorna {query,range,format}; Scopus retorna {query,count,start,sort,
  // view} — só `query` (a string de busca) é comum aos dois e de fato
  // exibida na UI hoje.
  query?: { query: string } & Record<string, unknown>
  fields?: StructuredQueryFields
  complexity?: QueryComplexity
  // Intervalo de anos usado na busca quando o campo "year" está vazio (padrão
  // configurado no backend, ex: 2010-2026) — mostrado no detalhe da query
  // mesmo sem edição, pra deixar claro que a busca não é irrestrita.
  year_range?: YearRange
  warning?: string
  error?: string
}

// Chama a LLM (via backend) para gerar N tentativas independentes de query em modo
// probe, direto do tema/descrição/keywords do usuário — seja o input cru do Step1
// ("Gerar Query") ou o tema refinado/selecionado no Step2 ("Confirm").
// resolveIntakePayload decide qual dos dois usar, unificando o tratamento dos dois
// caminhos. O probe é sempre "específico" por natureza (ver ChatService.
// build_probe_queries_multi) - as N opções não são variantes de precisão/cobertura,
// só tentativas independentes com a mesma instrução.
export interface ProbeQueriesMultiResult {
  queries: QueryOptionResult[]
  aiUsage: AiUsage | null
}

export async function generateProbeQueriesMulti(
  input: FormInput,
  step2SelectedTheme: (ThemeInput & { id: string }) | null,
  api = 'ops'
): Promise<ProbeQueriesMultiResult> {
  const intake = resolveIntakePayload(input, step2SelectedTheme)
  const { data } = await apiClient.post('/chat/probe/queries-multi', intake, { params: { api } })

  if (!data.success) {
    throw new Error(data.message || 'Falha ao gerar queries com IA')
  }

  return {
    queries: data.data.queries,
    aiUsage: data.data?.ai_usage ?? null,
  }
}

// Reconstrói a CQL a partir de campos estruturados editados pelo usuário, sem
// chamar a IA (síncrono e determinístico) — usado ao salvar uma edição no Step3.
export async function rebuildProbeQuery(
  fields: StructuredQueryFields,
  api = 'ops'
): Promise<QueryOptionResult> {
  const { data } = await apiClient.post('/chat/probe/rebuild-query', fields, { params: { api } })

  if (!data.success) {
    throw new Error(data.message || 'Falha ao reconstruir query')
  }

  return data.data
}

export interface ProbeSearchResultItem {
  title: string
  //  autor do artigo (campo
  // "dc:creator") - null se a API não retornou o campo pro item.
  author: string | null
  // Inventor da patente (campo "inventors") - só preenchido pra OPS. 
  inventor: string | null
  // Ano de publicação - OPS: "publication_date" (YYYYMMDD); 
  year: number | null
  // Só preenchido pra OPS (patentes).
  ipcCodes: string[]
  // OPS: país/jurisdição da patente. Scopus: país da primeira afiliação.
  country: string | null
  // Só preenchido pra Scopus (artigos).
  sourceTitle: string | null
}

// Estatísticas agregadas sobre o conjunto de resultados retornado - pensado
// pra dar uma visão geral da cobertura da busca além da contagem crua (ex:
// "achamos 15 patentes, mas de quantas classificações IPC diferentes? de
// que faixa de anos?"), sem precisar abrir cada item individualmente.
export interface ProbeSearchSummary {
  yearMin: number | null
  yearMax: number | null
  distinctYears: number
  // Patentes (OPS)
  distinctIpc: number
  distinctCountries: number
  // Artigos (Scopus)
  distinctSources: number
}

export interface ProbeSearchResult {
  success: boolean
  resultsCount: number
  totalAvailable: number | null
  items: ProbeSearchResultItem[]
  // Dicts crus (não transformados) devolvidos pelo backend - carregados até o
  // save da sessão pra persistir os documentos encontrados em patent/article
  // (ver sessionInput.ts). O mapeamento campo-a-campo pras colunas do banco
  // acontece no backend (NormalizationService), não aqui.
  rawItems: Record<string, unknown>[]
  summary: ProbeSearchSummary
}

// OPS: título vem em "invention_title"; Scopus: "dc:title" (chave crua da
// Elsevier, precisa de acesso por colchete).
export function extractResultTitle(item: Record<string, unknown>, api: ProbeApi): string {
  const raw = api === 'ops' ? item['invention_title'] : item['dc:title']
  return typeof raw === 'string' && raw.trim() ? raw : 'Sem título'
}

// OPS: "applicants" é uma lista (titulares da patente) - junta com vírgula.
// Scopus: "dc:creator" já vem como string única (primeiro autor).
export function extractResultAuthor(item: Record<string, unknown>, api: ProbeApi): string | null {
  if (api === 'ops') {
    const applicants = item['applicants']
    return Array.isArray(applicants) && applicants.length > 0 ? applicants.join(', ') : null
  }
  const creator = item['dc:creator']
  return typeof creator === 'string' && creator.trim() ? creator : null
}

// Só a OPS retorna o inventor por item (campo "inventors") - diferente de
// "applicants" (titular/assignee), que é quem detém a patente, não quem
// de fato inventou.
export function extractResultInventor(item: Record<string, unknown>, api: ProbeApi): string | null {
  if (api !== 'ops') return null
  const inventors = item['inventors']
  return Array.isArray(inventors) && inventors.length > 0 ? inventors.join(', ') : null
}

// OPS: "publication_date" vem como "YYYYMMDD" (ver _extract_biblio_fields no
// backend). Scopus: "prism:coverDate" vem como "YYYY-MM-DD". Nos dois casos
// os primeiros 4 caracteres são o ano.
export function extractResultYear(item: Record<string, unknown>, api: ProbeApi): number | null {
  const raw = api === 'ops' ? item['publication_date'] : item['prism:coverDate']
  if (typeof raw !== 'string' || raw.length < 4) return null
  const year = parseInt(raw.slice(0, 4), 10)
  return Number.isFinite(year) ? year : null
}

// Só a OPS retorna classificação IPC por item (campo "ipc_classifications").
export function extractIpcCodes(item: Record<string, unknown>, api: ProbeApi): string[] {
  if (api !== 'ops') return []
  const raw = item['ipc_classifications']
  return Array.isArray(raw) ? raw.filter((v): v is string => typeof v === 'string' && v.trim() !== '') : []
}

// OPS: país/jurisdição de publicação da patente (campo "country"), um valor
// só por item. Scopus não expõe um "país do artigo" - só países de afiliação
// dos autores (campo "affiliation", cada entrada com "affiliation-country");
// usamos o país da primeira afiliação, mesmo modelo "um valor por item" da
// OPS, o bastante pra alimentar a mesma estatística de países distintos.
// "affiliation" vem como array normalmente, mas a Scopus devolve um objeto
// solto (não envolto em array) quando há só 1 afiliação.
export function extractResultCountry(item: Record<string, unknown>, api: ProbeApi): string | null {
  if (api === 'ops') {
    const raw = item['country']
    return typeof raw === 'string' && raw.trim() ? raw : null
  }

  const raw = item['affiliation']
  const affiliations = Array.isArray(raw) ? raw : raw ? [raw] : []
  for (const aff of affiliations) {
    if (aff && typeof aff === 'object') {
      const country = (aff as Record<string, unknown>)['affiliation-country']
      if (typeof country === 'string' && country.trim()) return country
    }
  }
  return null
}

// Só o Scopus retorna o nome da revista/fonte por item (campo
// "prism:publicationName") - equivalente mais próximo de "categoria" que
// a busca de artigo devolve por item (a Scopus Search API não devolve a
// área de assunto do artigo, só a que foi usada como filtro na query).
export function extractSourceTitle(item: Record<string, unknown>, api: ProbeApi): string | null {
  if (api !== 'scopus') return null
  const raw = item['prism:publicationName']
  return typeof raw === 'string' && raw.trim() ? raw : null
}

function summarizeItems(items: ProbeSearchResultItem[]): ProbeSearchSummary {
  const years = items.map((i) => i.year).filter((y): y is number => y !== null)
  const ipcSet = new Set(items.flatMap((i) => i.ipcCodes))
  const countrySet = new Set(items.map((i) => i.country).filter((c): c is string => c !== null))
  const sourceSet = new Set(items.map((i) => i.sourceTitle).filter((s): s is string => s !== null))

  return {
    yearMin: years.length > 0 ? Math.min(...years) : null,
    yearMax: years.length > 0 ? Math.max(...years) : null,
    distinctYears: new Set(years).size,
    distinctIpc: ipcSet.size,
    distinctCountries: countrySet.size,
    distinctSources: sourceSet.size,
  }
}

// Constrói um ProbeSearchResult a partir de dicts crus (title/author/ipc/etc
// por chave específica de cada API) - usado tanto pela busca real quanto pra
// reconstruir os resultados de uma sessão retomada (ver sessionHydration.ts),
// a partir dos documentos persistidos em patent/article.
export function buildProbeSearchResult(
  rawItems: Record<string, unknown>[],
  api: ProbeApi,
  totalAvailable: number | null = null,
): ProbeSearchResult {
  const items = rawItems.map((r) => ({
    title: extractResultTitle(r, api),
    author: extractResultAuthor(r, api),
    inventor: extractResultInventor(r, api),
    year: extractResultYear(r, api),
    ipcCodes: extractIpcCodes(r, api),
    country: extractResultCountry(r, api),
    sourceTitle: extractSourceTitle(r, api),
  }))
  return {
    success: true,
    resultsCount: items.length,
    totalAvailable,
    items,
    rawItems,
    summary: summarizeItems(items),
  }
}

// Roda a busca real (OPS ou Scopus) com a query já montada no Step3 - é a
// mesma query devolvida por generateProbeQueriesMulti/rebuildProbeQuery
// (campo `query` de QueryOptionResult). O backend pede topK+5 como buffer
// ao adapter mas não corta de volta pra topK, então resultsCount/items.length
// pode vir até topK+5 - não assumir um teto exato de topK.
export async function runProbeSearch(
  query: { query: string } & Record<string, unknown>,
  api: ProbeApi,
  topK = 10
): Promise<ProbeSearchResult> {
  const { data } = await apiClient.post('/chat/probe/search', query, { params: { api, top_k: topK } })
  if (!data.success) {
    throw new Error(data.data?.error || data.message || 'Falha ao buscar resultados.')
  }
  const result = data.data
  const results: Record<string, unknown>[] = result.results ?? []
  return {
    ...buildProbeSearchResult(results, api, result.total_available ?? null),
    success: result.success,
    resultsCount: result.results_count,
  }
}
