import { apiClient } from './api'
import { resolveIntakePayload } from './refineTopic'
import type { FormInput, ThemeInput } from './refineTopic'

export interface StructuredQueryFields {
  title: string[]
  abstract: string[]
  claims: string[]
  ipc: string[]
  cpc: string[]
  applicant: string[]
  inventor: string[]
  year: string[]
}

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
  query?: { query: string; range: string; format: string }
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
