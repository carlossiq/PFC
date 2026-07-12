import { apiClient } from './api'

export interface RefineTopicCandidate {
  theme: string
  description?: string | null
  area_of_study?: string | null
  keywords?: string[] | null
}

export interface FormInput {
  theme: string
  description: string | null
  keywords: string | null
  studyArea: string | null
}

// Converte o shape do useFormStore.input para o InputIntake esperado por /chat/refine-topic.
// studyArea é um campo de texto livre (não uma lista real), por isso vai como string única
// em area_of_study, igual ao já feito em mapInputToSessionInputRoot.
export function mapInputToIntakePayload(input: FormInput) {
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

export interface ThemeInput {
  theme: string
  description: string
  keywords?: string[]
  studyArea?: string[]
}

// Converte um tema já selecionado (shape usado em Step2.tsx) para o InputIntake
// esperado por /chat/specify-topic. Aqui keywords/studyArea já são arrays (diferente
// de mapInputToIntakePayload, que parte de strings separadas por vírgula do Step1).
export function mapThemeToIntakePayload(theme: ThemeInput) {
  return {
    theme: theme.theme,
    description: theme.description || null,
    area_of_study: theme.studyArea && theme.studyArea.length > 0 ? theme.studyArea.join(', ') : null,
    keywords: theme.keywords && theme.keywords.length > 0 ? theme.keywords : null,
  }
}

// Decide se o intake enviado à IA deve vir do tema selecionado/refinado no
// Step2 (id !== 'input', ou seja, uma variação gerada por IA ou editada) ou
// do input cru do Step1 (quando o usuário pula o refinamento, ex: "Gerar
// Query"). Mesma lógica de decisão já usada em OutrosSteps.handleFinalize.
export function resolveIntakePayload(
  input: FormInput,
  step2SelectedTheme: (ThemeInput & { id: string }) | null
) {
  const wasRefinedByAI = !!step2SelectedTheme && step2SelectedTheme.id !== 'input'
  return wasRefinedByAI ? mapThemeToIntakePayload(step2SelectedTheme!) : mapInputToIntakePayload(input)
}

// Chama a LLM (via backend) para aprofundar um único tema já selecionado em uma
// versão mais específica/estreita do mesmo assunto (ao contrário de refineTopic,
// que gera 4 variações diversas).
export async function specifyTopic(theme: ThemeInput): Promise<RefineTopicCandidate> {
  const payload = mapThemeToIntakePayload(theme)
  const { data } = await apiClient.post('/chat/specify-topic', payload)

  if (!data.success) {
    throw new Error(data.message || 'Falha ao especificar o tema com IA')
  }

  return data.data
}
