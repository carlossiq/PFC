import { useEffect, useState } from 'react'
import { SelectField } from '../SelectField'
import { Button } from '../Button'
import {
  CALL_SITE_LABELS,
  createLLMConfig,
  deleteLLMConfig,
  getCallSites,
  listLLMConfigs,
  listLLMProviders,
  setCallSiteConfig,
  updateLLMConfig,
} from '../../services/config'
import type { CallSitesState, LLMProviderConfig, LLMProviderInfo } from '../../services/config'

function configLabel(config: LLMProviderConfig, providers: Record<string, LLMProviderInfo>): string {
  const providerName = providers[config.provider_code]?.display_name ?? config.provider_code
  const suffix = config.base_url ? ` @ ${config.base_url}` : ''
  return `${providerName}: ${config.model}${suffix}`
}

// Gerencia as "instâncias" de IA (llm_provider_configs - qualquer combinação
// de provider/model/api_key/base_url) e qual delas cada uma das 4 chamadas
// de IA do programa usa (llm_call_site_bindings). Adicionar um provider novo
// no futuro (ver app/adapters/driven/llm/provider_registry.py) aparece aqui
// automaticamente via GET /config/llm/providers, sem mudar este componente.
export function LLMPanel() {
  const [providers, setProviders] = useState<Record<string, LLMProviderInfo> | null>(null)
  const [configs, setConfigs] = useState<LLMProviderConfig[] | null>(null)
  const [callSites, setCallSites] = useState<CallSitesState | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [newProviderCode, setNewProviderCode] = useState('')
  const [newModel, setNewModel] = useState('')
  const [newApiKey, setNewApiKey] = useState('')
  const [newBaseUrl, setNewBaseUrl] = useState('')
  const [creating, setCreating] = useState(false)

  async function refresh() {
    try {
      const [providersData, configsData, callSitesData] = await Promise.all([
        listLLMProviders(),
        listLLMConfigs(),
        getCallSites(),
      ])
      setProviders(providersData)
      setConfigs(configsData)
      setCallSites(callSitesData)
      if (!newProviderCode) {
        const firstCode = Object.keys(providersData)[0]
        if (firstCode) setNewProviderCode(firstCode)
      }
    } catch {
      setError('Não foi possível carregar a configuração de IA.')
    }
  }

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleCreate() {
    if (!newProviderCode || !newModel.trim()) return
    setCreating(true)
    try {
      await createLLMConfig({
        provider_code: newProviderCode,
        model: newModel.trim(),
        api_key: newApiKey,
        base_url: newBaseUrl,
      })
      setNewModel('')
      setNewApiKey('')
      setNewBaseUrl('')
      await refresh()
    } catch {
      setError('Não foi possível criar essa configuração (talvez já exista uma igual).')
    } finally {
      setCreating(false)
    }
  }

  async function handleFieldCommit(config: LLMProviderConfig, field: 'model' | 'api_key' | 'base_url', value: string) {
    if (value === config[field]) return
    try {
      await updateLLMConfig(config.id, { ...config, [field]: value })
      await refresh()
    } catch {
      setError('Não foi possível salvar a alteração.')
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteLLMConfig(id)
      await refresh()
    } catch {
      setError('Não foi possível remover essa configuração.')
    }
  }

  async function handleCallSiteChange(callSite: string, configId: number) {
    try {
      await setCallSiteConfig(callSite, configId)
      await refresh()
    } catch {
      setError('Não foi possível trocar a IA usada por essa chamada.')
    }
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!providers || !configs || !callSites) return <p className="text-sm text-gray-500">Carregando...</p>

  const selectedProviderInfo = providers[newProviderCode]

  return (
    <div className="space-y-6">
      <section>
        <h4 className="text-sm font-semibold text-gray-900 mb-2">Qual IA cada chamada usa</h4>
        <div className="space-y-3">
          {callSites.call_sites.map((callSite) => (
            <div key={callSite} className="rounded-lg border border-gray-200 bg-white p-3">
              <SelectField
                label={CALL_SITE_LABELS[callSite] ?? callSite}
                value={String(callSites.bindings[callSite] ?? '')}
                options={configs.map((c) => ({ value: String(c.id), label: configLabel(c, providers) }))}
                onChange={(value) => handleCallSiteChange(callSite, Number(value))}
              />
            </div>
          ))}
        </div>
      </section>

      <section>
        <h4 className="text-sm font-semibold text-gray-900 mb-2">Configurações de IA salvas</h4>
        <div className="space-y-2">
          {configs.map((config) => (
            <div key={config.id} className="rounded-lg border border-gray-200 bg-white p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase text-[#0f9448]">
                  {providers[config.provider_code]?.display_name ?? config.provider_code}
                </span>
                <button
                  type="button"
                  onClick={() => handleDelete(config.id)}
                  aria-label="Remover configuração"
                  className="w-6 h-6 flex items-center justify-center rounded-full text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <input
                  defaultValue={config.model}
                  placeholder="model"
                  onBlur={(e) => handleFieldCommit(config, 'model', e.target.value)}
                  className="text-sm border border-gray-300 rounded-md px-2 py-1 text-gray-900"
                />
                {providers[config.provider_code]?.requires_base_url && (
                  <input
                    defaultValue={config.base_url}
                    placeholder="base_url"
                    onBlur={(e) => handleFieldCommit(config, 'base_url', e.target.value)}
                    className="text-sm border border-gray-300 rounded-md px-2 py-1 text-gray-900"
                  />
                )}
                {providers[config.provider_code]?.requires_api_key && (
                  <input
                    type="password"
                    defaultValue={config.api_key}
                    placeholder="api_key"
                    onBlur={(e) => handleFieldCommit(config, 'api_key', e.target.value)}
                    className="text-sm border border-gray-300 rounded-md px-2 py-1 text-gray-900"
                  />
                )}
              </div>
            </div>
          ))}
          {configs.length === 0 && <p className="text-sm text-gray-500">Nenhuma configuração ainda.</p>}
        </div>
      </section>

      <section>
        <h4 className="text-sm font-semibold text-gray-900 mb-2">Adicionar nova configuração</h4>
        <div className="rounded-lg border border-gray-200 bg-white p-3 space-y-2">
          <SelectField
            label="Provider"
            value={newProviderCode}
            options={Object.entries(providers).map(([code, info]) => ({ value: code, label: info.display_name }))}
            onChange={setNewProviderCode}
          />
          <input
            value={newModel}
            onChange={(e) => setNewModel(e.target.value)}
            placeholder="model (ex: gemini-2.5-flash)"
            className="w-full text-sm border border-gray-300 rounded-md px-2 py-1.5 text-gray-900"
          />
          {selectedProviderInfo?.requires_base_url && (
            <input
              value={newBaseUrl}
              onChange={(e) => setNewBaseUrl(e.target.value)}
              placeholder="base_url (ex: http://localhost:11434)"
              className="w-full text-sm border border-gray-300 rounded-md px-2 py-1.5 text-gray-900"
            />
          )}
          {selectedProviderInfo?.requires_api_key && (
            <input
              type="password"
              value={newApiKey}
              onChange={(e) => setNewApiKey(e.target.value)}
              placeholder="api_key"
              className="w-full text-sm border border-gray-300 rounded-md px-2 py-1.5 text-gray-900"
            />
          )}
          <Button onClick={handleCreate} disabled={creating || !newModel.trim()}>
            Adicionar
          </Button>
        </div>
      </section>
    </div>
  )
}
