import { apiClient } from './api'

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
}

// Finaliza a sessão: envia o nome da sessão, o input raiz (Step1) e, se houve
// refinamento por IA, o tema escolhido para seguir adiante + o total de
// iterações acumuladas. Cria research_session + a cadeia de session_input no
// backend numa tacada só.
export async function finalizeSession(
  name: string,
  root: FormInput,
  generated: GeneratedTheme | null,
  iterations: number,
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
  })
  return data.data
}
