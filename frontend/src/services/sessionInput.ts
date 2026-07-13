import { apiClient } from './api'
import type { QueryOptionResult } from './probeQuery'

export interface SessionInputRootPayload {
  theme: string
  description: string | null
  area_of_study: string | null
  keywords: string[] | null
  year_from: number | null
  year_to: number | null
}

export interface SessionInputGeneratedPayload {
  theme: string
  description: string | null
  iterations: number
}

interface FormInput {
  theme: string
  description: string | null
  keywords: string | null
  studyArea: string | null
}

interface GeneratedTheme {
  theme: string
  description: string | null
}

// Converte o shape do useFormStore.input para o payload raiz esperado pelo
// endpoint /session-input, fazendo o split de keywords (string separada por
// vírgula) em uma lista sem vazios.
export function mapInputToSessionInputRoot(input: FormInput): SessionInputRootPayload {
  const keywordsArray = input.keywords
    ? input.keywords.split(',').map((k) => k.trim()).filter(Boolean)
    : null

  return {
    theme: input.theme,
    description: input.description || null,
    area_of_study: input.studyArea || null,
    keywords: keywordsArray && keywordsArray.length > 0 ? keywordsArray : null,
    year_from: null,
    year_to: null,
  }
}

export interface SessionProbeQueryPayload {
  fonte: 'ops' | 'scopus'
  query_text: string
  fields: Record<string, string[]> | null
  year_from: number | null
  year_to: number | null
  complexity_score: number | null
  complexity_level: string | null
  iterations: number
  result_count: number | null
}

// Monta o payload de uma query do Step3 pronta pra enviar no finalize, a
// partir da opção selecionada numa seção (patente ou artigo). `iterations`
// é o contador interno da store (0-based: 0 = gerada uma vez, sem retry) -
// aqui vira o valor de negócio "nº de vezes que a query foi gerada" (1+).
// `resultCount` vem da busca real já rodada no Step3 (ver runProbeSearch),
// null se por algum motivo não tiver rodado ainda.
// Retorna null se não há uma seleção válida (nada gerado, ou a tentativa
// selecionada falhou) - mesma condição usada no `canProceed` do Step3.
export function buildProbeQueryPayload(
  selected: QueryOptionResult | undefined,
  fonte: 'ops' | 'scopus',
  iterations: number,
  resultCount: number | null = null,
): SessionProbeQueryPayload | null {
  if (!selected?.success) return null
  return {
    fonte,
    query_text: selected.query?.query ?? '',
    fields: selected.fields ?? null,
    year_from: selected.year_range?.from ?? null,
    year_to: selected.year_range?.to ?? null,
    complexity_score: selected.complexity?.score ?? null,
    complexity_level: selected.complexity?.level ?? null,
    iterations: iterations + 1,
    result_count: resultCount,
  }
}

export interface SessionProbeQueryRow extends SessionProbeQueryPayload {
  id: number
  session_id: number
}

export interface SessionInputRow {
  id: number
  session_id: number
  parent_id: number | null
  theme: string
  description: string | null
  area_of_study: string | null
  keywords: string[] | null
  year_from: number | null
  year_to: number | null
  iterations: number
}

export interface FinalizeSessionResponse {
  session_id: number
  session_public_id: string
  session_name: string
  root: SessionInputRow
  generated: SessionInputRow | null
  probe_queries: SessionProbeQueryRow[]
}

// Finaliza a sessão: envia o nome da sessão, o input raiz (Step1), se houve
// refinamento por IA o tema escolhido para seguir adiante + o total de
// iterações acumuladas, e as queries do Step3 selecionadas (patente/artigo).
// Cria research_session + a cadeia de session_input + as linhas de
// session_probe_query no backend numa tacada só.
export async function finalizeSession(
  name: string,
  root: FormInput,
  generated: GeneratedTheme | null,
  iterations: number,
  probeQueries: SessionProbeQueryPayload[] = [],
): Promise<FinalizeSessionResponse> {
  const { data } = await apiClient.post('/session-input', {
    name,
    root: mapInputToSessionInputRoot(root),
    generated: generated
      ? {
          theme: generated.theme,
          description: generated.description,
          iterations,
        }
      : null,
    probe_queries: probeQueries,
  })
  return data.data
}
