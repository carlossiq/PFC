import { apiClient } from './api'

export interface RefineTopicCandidate {
  theme: string
  description?: string | null
  area_of_study?: string | null
  keywords?: string[] | null
}

interface FormInput {
  theme: string
  description: string | null
  keywords: string | null
  studyArea: string | null
}

// Converte o shape do useFormStore.input para o InputIntake esperado por /chat/refine-topic.
// studyArea é um campo de texto livre (não uma lista real), por isso vai como string única
// em area_of_study, igual ao já feito em mapInputToParamInitPayload.
function mapInputToIntakePayload(input: FormInput) {
  const keywordsArray = input.keywords
    ? input.keywords.split(',').map((k) => k.trim()).filter(Boolean)
    : null

  return {
    theme: input.theme,
    description: input.description || null,
    area_of_study: input.studyArea || null,
    keywords: keywordsArray && keywordsArray.length > 0 ? keywordsArray : null,
  }
}

// Chama a LLM (via backend) para gerar 4 variações mais específicas do tema informado.
export async function refineTopic(input: FormInput): Promise<RefineTopicCandidate[]> {
  const payload = mapInputToIntakePayload(input)
  const { data } = await apiClient.post('/chat/refine-topic', payload)

  if (!data.success) {
    throw new Error(data.message || 'Falha ao gerar parâmetros com IA')
  }

  return data.data?.candidates ?? []
}
