import { apiClient } from './api'

export interface ParamInitPayload {
  tema: string
  descricao: string | null
  area_estudo: string | null
  keywords: string[] | null
}

export interface ParamInitResponseData {
  id: number
  tema: string
  descricao: string | null
  area_estudo: string | null
  keywords: string[] | null
}

interface FormInput {
  theme: string
  description: string | null
  keywords: string | null
  studyArea: string | null
}

// Converte o shape do useFormStore.input para o payload esperado pelo endpoint /param-init,
// fazendo o split de keywords (string separada por vírgula) em uma lista sem vazios.
export function mapInputToParamInitPayload(input: FormInput): ParamInitPayload {
  const keywordsArray = input.keywords
    ? input.keywords.split(',').map((k) => k.trim()).filter(Boolean)
    : null

  return {
    tema: input.theme,
    descricao: input.description || null,
    area_estudo: input.studyArea || null,
    keywords: keywordsArray && keywordsArray.length > 0 ? keywordsArray : null,
  }
}

export async function upsertParamInit(
  existingId: number | null,
  payload: ParamInitPayload,
): Promise<ParamInitResponseData> {
  if (existingId) {
    try {
      const { data } = await apiClient.put(`/param-init/${existingId}`, payload)
      return data.data
    } catch (err: any) {
      // Tupla pode ter sido apagada (ex: race com o beacon do pagehide) - cria uma nova.
      if (err?.response?.status !== 404) throw err
    }
  }

  const { data } = await apiClient.post('/param-init', payload)
  return data.data
}

export async function deleteParamInit(id: number): Promise<void> {
  await apiClient.delete(`/param-init/${id}`)
}

// navigator.sendBeacon só suporta POST com corpo (sem DELETE, sem headers customizados),
// por isso usamos o endpoint /discard dedicado para o caso de fechar/atualizar a aba.
export function deleteParamInitViaBeacon(id: number): void {
  const url = `${apiClient.defaults.baseURL}/param-init/${id}/discard`
  const blob = new Blob([JSON.stringify({})], { type: 'application/json' })
  navigator.sendBeacon(url, blob)
}
