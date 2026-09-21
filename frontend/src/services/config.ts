import { apiClient } from './api'

// Espelha app/core/domain/config_types.py::AppSettingValue (mascarado se
// is_secret) - ver PLANO_MIGRACAO_CONFIG_BANCO.md.
export interface AppSetting {
  key: string
  value: string
  value_type: 'float' | 'int' | 'bool' | 'str'
  category: string
  is_secret: boolean
  min_value: number | null
  max_value: number | null
  step: number | null
  label: string | null
  description: string | null
  // Valor do seed inicial ("recomendado") - null pra settings secretas, ver
  // db/config_seed.py.
  default_value: string | null
}

export async function listSettings(): Promise<AppSetting[]> {
  const { data } = await apiClient.get('/config/settings')
  return data.data
}

export async function updateSetting(key: string, value: string): Promise<AppSetting> {
  const { data } = await apiClient.put(`/config/settings/${key}`, { value })
  return data.data
}

// --- Seleção de API de busca (patent/scholarly) ---

export interface SearchApiOption {
  code: string
  display_name: string
}

export interface SearchApiState {
  selections: Record<string, string>
  options: Record<string, SearchApiOption[]>
}

export async function getSearchApis(): Promise<SearchApiState> {
  const { data } = await apiClient.get('/config/search-apis')
  return data.data
}

export async function setSearchApi(family: string, activeProviderCode: string): Promise<{ message?: string }> {
  const { data } = await apiClient.put(`/config/search-apis/${family}`, { active_provider_code: activeProviderCode })
  return { message: data.message }
}

// --- Providers/configs de IA ---

export interface LLMProviderInfo {
  display_name: string
  requires_api_key: boolean
  requires_base_url: boolean
}

export async function listLLMProviders(): Promise<Record<string, LLMProviderInfo>> {
  const { data } = await apiClient.get('/config/llm/providers')
  return data.data
}

export interface LLMProviderConfig {
  id: number
  provider_code: string
  model: string
  api_key: string
  base_url: string
}

export async function listLLMConfigs(): Promise<LLMProviderConfig[]> {
  const { data } = await apiClient.get('/config/llm/configs')
  return data.data
}

export async function createLLMConfig(input: {
  provider_code: string
  model: string
  api_key?: string
  base_url?: string
}): Promise<LLMProviderConfig> {
  const { data } = await apiClient.post('/config/llm/configs', input)
  return data.data
}

export async function updateLLMConfig(
  id: number,
  input: { provider_code: string; model: string; api_key?: string; base_url?: string }
): Promise<LLMProviderConfig> {
  const { data } = await apiClient.put(`/config/llm/configs/${id}`, input)
  return data.data
}

export async function deleteLLMConfig(id: number): Promise<void> {
  await apiClient.delete(`/config/llm/configs/${id}`)
}

// --- Seleção de IA por call site ---

export const CALL_SITE_LABELS: Record<string, string> = {
  theme_candidates: 'Geração de temas candidatos',
  probe_query: 'Geração de query (probe)',
  final_query: 'Geração de query final',
  report_writing: 'Redação do relatório',
}

export interface CallSitesState {
  call_sites: string[]
  bindings: Record<string, number>
  configs: LLMProviderConfig[]
}

export async function getCallSites(): Promise<CallSitesState> {
  const { data } = await apiClient.get('/config/llm/call-sites')
  return data.data
}

export async function setCallSiteConfig(callSite: string, configId: number): Promise<void> {
  await apiClient.put(`/config/llm/call-sites/${callSite}`, { config_id: configId })
}

// --- Imagem de capa do relatório (símbolo/logo, ver
// app/core/services/report_cover_image.py) ---

export interface ReportCoverImage {
  hasImage: boolean
  imageBase64: string | null
}

// Espelha REPORT_COVER_IMAGE_TARGET_SIZE em
// app/core/services/report_cover_image.py - a moldura de recorte/zoom
// (ver ImageCropModal.tsx) usa a mesma proporção, então o que o usuário
// enquadra ali já é exatamente o tamanho final.
export const REPORT_COVER_IMAGE_TARGET_SIZE: [number, number] = [600, 848]

function mapReportCoverImage(raw: { has_image: boolean; image_base64?: string | null }): ReportCoverImage {
  return { hasImage: raw.has_image, imageBase64: raw.image_base64 ?? null }
}

export async function getReportCoverImage(): Promise<ReportCoverImage> {
  const { data } = await apiClient.get('/config/report-cover-image')
  return mapReportCoverImage(data.data)
}

// `Content-Type: undefined` remove o header JSON default do apiClient pra
// essa chamada - sem isso, o transformRequest do axios vê o Content-Type
// "application/json" já presente e converte o FormData pra uma string JSON
// em vez de mandar como multipart de verdade (ver axios/lib/defaults). Sem
// header nenhum, o próprio navegador seta "multipart/form-data" com o
// boundary correto ao enviar um FormData via XHR/fetch.
// `file` já vem recortado/redimensionado pro tamanho final (ver
// ImageCropModal.tsx) - por isso aceita Blob, não só File (canvas.toBlob
// devolve um Blob puro, sem nome).
export async function uploadReportCoverImage(file: Blob, filename = 'capa_relatorio.png'): Promise<ReportCoverImage> {
  const formData = new FormData()
  formData.append('file', file, filename)
  const { data } = await apiClient.post('/config/report-cover-image', formData, {
    headers: { 'Content-Type': undefined },
  })
  return mapReportCoverImage(data.data)
}

export async function deleteReportCoverImage(): Promise<void> {
  await apiClient.delete('/config/report-cover-image')
}
