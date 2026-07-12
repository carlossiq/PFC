import { apiClient } from './api'
import { resolveIntakePayload } from './refineTopic'
import type { FormInput, ThemeInput } from './refineTopic'

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
export async function generateProbeQueriesMulti(
  input: FormInput,
  step2SelectedTheme: (ThemeInput & { id: string }) | null,
  api = 'ops'
): Promise<QueryOptionResult[]> {
  const intake = resolveIntakePayload(input, step2SelectedTheme)
  const { data } = await apiClient.post('/chat/probe/queries-multi', intake, { params: { api } })

  if (!data.success) {
    throw new Error(data.message || 'Falha ao gerar queries com IA')
  }

  return data.data.queries
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
