import { useState } from 'react'
import { LLMPanel } from './settings/LLMPanel'
import { SearchApiPanel } from './settings/SearchApiPanel'
import { SettingsCategoryPanel } from './settings/SettingsCategoryPanel'
import { ReportCoverImagePanel } from './settings/ReportCoverImagePanel'

// Sub-abas da tela de Configurações - cada uma carrega só o que precisa
// (ver SettingsCategoryPanel/SearchApiPanel/LLMPanel), evitando uma lista
// enorme única de ~35 campos. Categorias batem com as usadas em
// db/config_seed.py::_SETTINGS_SEED (campo `category` de AppSetting).
const TABS = [
  { id: 'ia', label: 'Inteligência Artificial' },
  { id: 'busca', label: 'Busca' },
  { id: 'extracao', label: 'Extração de Termos' },
  { id: 'relevancia', label: 'Relevância & Qualidade' },
  { id: 'inferencia', label: 'Inferência Estatística' },
  { id: 'geral', label: 'Geral' },
] as const

type TabId = (typeof TABS)[number]['id']

export function ConfiguracoesTab() {
  const [activeTab, setActiveTab] = useState<TabId>('ia')

  return (
    <div className="w-full">
      <h2 className="text-2xl font-bold mb-1">Configurações</h2>
      <p className="text-sm text-gray-500 mb-6">
        Alterações são salvas automaticamente ao adicionar/editar/selecionar - não existe botão de salvar.
      </p>

      <div className="border-b border-gray-200 mb-6 overflow-x-auto">
        <nav className="flex gap-1 -mb-px min-w-max">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'border-[#0f9448] text-[#0f9448]'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="max-w-2xl">
        {activeTab === 'ia' && <LLMPanel />}
        {activeTab === 'busca' && (
          <div className="space-y-6">
            <SearchApiPanel />
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-2">Parâmetros de busca e credenciais</h4>
              <SettingsCategoryPanel categories={['search', 'external_api']} />
            </div>
          </div>
        )}
        {activeTab === 'extracao' && <SettingsCategoryPanel categories={['term_extraction']} />}
        {activeTab === 'relevancia' && <SettingsCategoryPanel categories={['relevance', 'fuzzy_matching']} />}
        {activeTab === 'inferencia' && <SettingsCategoryPanel categories={['statistical_inference']} />}
        {activeTab === 'geral' && (
          <div className="space-y-6">
            <ReportCoverImagePanel />
            <SettingsCategoryPanel categories={['general']} />
          </div>
        )}
      </div>
    </div>
  )
}
