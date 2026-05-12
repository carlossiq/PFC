import { useEffect } from 'react'
import { useFormStore } from '../../stores/useFormStore'

interface Theme {
  id: string
  theme: string
  description: string
  keywords?: string[]
  studyArea?: string[]
}

const themes1: Theme[] = [
  {
    id: 'ai-health',
    theme: 'AI in Healthcare',
    description: 'Artificial Intelligence applied to diagnosis and treatment',
    keywords: ['machine learning', 'diagnosis', 'healthcare'],
    studyArea: ['healthcare', 'medicine'],
  },
  {
    id: 'blockchain',
    theme: 'Blockchain',
    description: 'Distributed ledger and cryptography technologies',
    keywords: ['cryptocurrencies', 'smart contracts', 'security'],
    studyArea: ['finance', 'supply chain'],
  },
  {
    id: 'climate-tech',
    theme: 'ClimaTech',
    description: 'Technologies for sustainabilitdy and climate',
    keywords: ['renewable energy', 'environmental monitoring', 'sustainability'],
    studyArea: ['environment', 'energy'],
  },
  {
    id: 'quantum',
    theme: 'Quantum Computing',
    description: 'Quantum computers and algorithms',
    keywords: ['qubits', 'quantum algorithms', 'simulation'],
    studyArea: ['computing', 'physics'],
  },
]

const themes2: Theme[] = [
  {
    id: 'cybersecurity',
    theme: 'Cybersecurity',
    description: 'Protection of systems and data from cyber threats',
    keywords: ['network security', 'encryption', 'threat detection'],
    studyArea: ['security', 'information technology'],
  },
  {
    id: 'vr-ar',
    theme: 'VR/AR',
    description: 'Virtual and Augmented Reality technologies',
    keywords: ['virtual reality', 'augmented reality', 'mixed reality'],
    studyArea: ['entertainment', 'education'],
  },
  {
    id: 'autonomous-vehicles',
    theme: 'Autonomous Vehicles',
    description: 'Self-driving cars and autonomous transportation',
    keywords: ['self-driving cars', 'autonomous drones', 'transportation'],
    studyArea: ['automotive', 'transportation'],
  },
  {
    id: 'space-tech',
    theme: 'Space Technology',
    description: 'Technologies for space exploration and satellite systems',
    keywords: ['space exploration', 'satellites', 'space technology'],
    studyArea: ['aerospace', 'astronomy'],
  },
]

interface Step2Props {
  formData: {
    theme: string
    description: string | null
    keywords: string | null
    studyArea: string | null
  }
  onBack: () => void
  onNext: () => void
}

export function Step2({ formData, onBack, onNext }: Step2Props) {
  const { input, step2SelectedTheme, setStep2SelectedTheme, step2ThemeSet, setStep2ThemeSet, setGenerated } = useFormStore()

  const themes = step2ThemeSet === 1 ? themes1 : themes2

  const handleRetry = () => {
    setStep2ThemeSet(step2ThemeSet === 1 ? 2 : 1)
  }

  const persistedTheme: Theme = {
    id: 'input',
    theme: input.theme || formData.theme,
    description: input.description || formData.description || '',
    keywords: input.keywords
      ? input.keywords.split(',').map((k) => k.trim())
      : formData.keywords
        ? formData.keywords.split(',').map((k) => k.trim())
        : undefined,
    studyArea: input.studyArea
      ? input.studyArea.split(',').map((a) => a.trim())
      : formData.studyArea
        ? formData.studyArea.split(',').map((a) => a.trim())
        : undefined,
  }

  // Inicializar com tema persistido se ainda não há seleção
  useEffect(() => {
    if (!step2SelectedTheme) {
      setStep2SelectedTheme(persistedTheme)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step2SelectedTheme, setStep2SelectedTheme])

  const selectedData = step2SelectedTheme || persistedTheme

  useEffect(() => {
    setGenerated({
      theme: selectedData.theme,
      description: selectedData.description,
      keywords: selectedData.keywords ?? null,
      studyArea: selectedData.studyArea ?? null,
    })
  }, [selectedData, setGenerated])

  function handleSelectTheme(theme: Theme) {
    // Permite seleção de um tema diferente do atual
    if (selectedData.id !== theme.id) {
      setStep2SelectedTheme(theme)
    }
  }

  const cardClass = (themeId: string) => `
    py-2 px-4 rounded-lg border-2 text-left bg-gray-100 shadow-sm
    transition-all duration-300 ease-in-out
    ${
      selectedData?.id === themeId
        ? 'border-[#0f9448] ring-2 ring-[#0f9448]/10 border-2'
        : 'border-gray-100 hover:border-[#0f9448]'
    }
  `

  return (
    <div className="w-full flex flex-col h-full">
      <div className="flex-1 flex gap-6 overflow-hidden">
        <div
          className={`
            transition-all duration-500 ease-in-out
            ${selectedData ? 'w-1/2' : 'w-full'}
          `}
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Initial Parameters
          </h3>

          <div
            className={`
              grid gap-4 transition-all duration-500 ease-in-out
              ${selectedData ? 'grid-cols-1' : 'grid-cols-2'}
            `}
          >
            <button
              key={persistedTheme.id}
              onClick={() => handleSelectTheme(persistedTheme)}
              className={cardClass(persistedTheme.id)}
            >
              <h4 className="font-semibold text-gray-900 mb-1">
                {persistedTheme.theme}
              </h4>
            </button>
          </div>

          <h3 className="text-lg font-semibold text-gray-900 mt-6 mb-4">
            Generated Parameters
          </h3>

          <div
            className={`
              grid gap-4 transition-all duration-500 ease-in-out
              ${selectedData ? 'grid-cols-1' : 'grid-cols-2'}
            `}
          >
            {themes.map((theme) => (
              <button
                key={theme.id}
                onClick={() => handleSelectTheme(theme)}
                className={cardClass(theme.id)}
              >
                <h4 className="font-semibold text-gray-900 mb-1">
                  {theme.theme}
                </h4>
              </button>
            ))}
          </div>
        </div>

        <div
          className={`
            bg-gray-100 rounded-xl border border-gray-200 p-4 overflow-y-auto mt-10.5 mb-16.5 mx-4
            transition-all duration-500 ease-in-out
            ${
              selectedData
                ? 'w-1/2 opacity-100 translate-x-0'
                : 'w-0 opacity-0 translate-x-4 p-0 border-transparent pointer-events-none'
            }
          `}
        >
          {selectedData && (
            <>
              <div className="space-y-5 mt-1 mx-1">
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-600 font-medium mb-1">
                    Theme
                  </p>
                  <p className="text-sm font-semibold text-gray-900">
                    {selectedData.theme}
                  </p>
                </div>

                {selectedData.description && (
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600 font-medium mb-1">
                      Description
                    </p>
                    <p className="text-sm font-semibold text-gray-900">
                      {selectedData.description}
                    </p>
                  </div>
                )}

                {selectedData.keywords && selectedData.keywords.length > 0 && (
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600 font-medium mb-1">
                      Keywords
                    </p>
                    <p className="text-sm font-semibold text-gray-900">
                      {selectedData.keywords.join(', ')}
                    </p>
                  </div>
                )}

                {selectedData.studyArea && selectedData.studyArea.length > 0 && (
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600 font-medium mb-1">
                      Study Area
                    </p>
                    <p className="text-sm font-semibold text-gray-900">
                      {selectedData.studyArea.join(', ')}
                    </p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200 flex gap-4">
        <button
          onClick={onBack}
          className="flex-1 bg-gray-400 hover:bg-gray-500 text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
        >
          Back
        </button>

        <button
          onClick={onNext}
          className="flex-1 font-semibold py-2 px-4 rounded-lg text-white transition-colors duration-300 bg-[#0f9448] hover:bg-[#0d843f]"
        >
          Confirm
        </button>

        <button
          onClick={handleRetry}
          className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
        >
          Generate Others
        </button>
      </div>
    </div>
  )
}