import { useState } from 'react'
import { Toggle } from './Toggle'

interface ModelItem {
  id: string
  name: string
  enabled: boolean
}

interface ModelCategory {
  id: string
  label: string
  items: ModelItem[]
}

interface ModelGroup {
  id: string
  title: string
  categories: ModelCategory[]
}

const modelGroups: ModelGroup[] = [
  {
    id: 'ia-models',
    title: 'Modelos de IA disponíveis',
    categories: [
      {
        id: 'remota',
        label: 'Remota',
        items: [
          { id: 'gemini', name: 'Gemini 2.5', enabled: true },
          { id: 'gpt4', name: 'GPT-4', enabled: false },
        ],
      },
      {
        id: 'local',
        label: 'Local',
        items: [
          { id: 'ollama', name: 'Ollama', enabled: false },
          { id: 'llama2', name: 'Llama 2', enabled: true },
        ],
      },
    ],
  },
  {
    id: 'prospection-models',
    title: 'Modelos de prospecção',
    categories: [
      {
        id: 'patents',
        label: 'Patentes',
        items: [{ id: 'lens-patents', name: 'LENS Patents', enabled: true },
                {id: 'ops', name: 'OPS', enabled: false},
        ],
      },
      {
        id: 'articles',
        label: 'Artigos',
        items: [{ id: 'scopus', name: 'Scopus', enabled: true }],
      },
    ],
  },
]

export function ConfiguracoesTab() {
  const [selectedModels, setSelectedModels] = useState<Map<string, string>>(() => {
    const selected = new Map<string, string>()
    modelGroups.forEach((group) => {
      group.categories.forEach((category) => {
        const enabledItem = category.items.find((item) => item.enabled)
        if (enabledItem) {
          selected.set(category.id, enabledItem.id)
        }
      })
    })
    return selected
  })

  const selectModel = (categoryId: string, modelId: string) => {
    const newSelected = new Map(selectedModels)
    newSelected.set(categoryId, modelId)
    setSelectedModels(newSelected)
  }

  return (
    <div className="w-full">
      <h2 className="text-2xl font-bold mb-6">Configurações</h2>

      <div className="space-y-6">
        {modelGroups.map((group) => (
          <div key={group.id}>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">{group.title}</h3>

            <div className="ml-4 space-y-4">
              {group.categories.map((category) => (
                <div key={category.id}>
                  <p className="text-base font-medium text-gray-700 mb-2">{category.label}</p>

                  <div className="ml-4 space-y-2">
                    {category.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-700"
                      >
                        <Toggle
                          enabled={selectedModels.get(category.id) === item.id}
                          onChange={() => selectModel(category.id, item.id)}
                        />
                        <span className="text-sm font-medium">{item.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
