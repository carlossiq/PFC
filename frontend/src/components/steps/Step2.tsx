import { useEffect, useState, useCallback } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { refineTopic } from '../../services/refineTopic'
import { Loading } from '../Loading'

interface Theme {
  id: string
  theme: string
  description: string
  keywords?: string[]
  studyArea?: string[]
}

interface Step2Props {
  formData: {
    theme: string
    description: string | null
    keywords: string | null
    studyArea: string | null
  }
  isSaving?: boolean
  onBack: () => void
  onNext: () => void
}

export function Step2({ formData, isSaving, onBack, onNext }: Step2Props) {
  const { input, step2SelectedTheme, setStep2SelectedTheme, setGenerated } = useFormStore()

  const [candidates, setCandidates] = useState<Theme[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generateCandidates = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const results = await refineTopic(input)
      setCandidates(
        results.map((candidate, index) => ({
          id: `candidate-${index}`,
          theme: candidate.theme,
          description: candidate.description ?? '',
          keywords: candidate.keywords ?? undefined,
          studyArea: candidate.area_of_study
            ? candidate.area_of_study.split(',').map((a) => a.trim())
            : undefined,
        }))
      )
    } catch (err) {
      console.error('Falha ao gerar parâmetros com IA:', err)
      setError('Não foi possível gerar parâmetros com IA. Tente novamente.')
      setCandidates([])
    } finally {
      setIsLoading(false)
    }
  }, [input])

  useEffect(() => {
    generateCandidates()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleRetry = () => {
    generateCandidates()
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

  const isBusy = isSaving || isLoading

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

          {isLoading && (
            <div className="min-h-55">
              <Loading message="Generating parameters with AI..." transparent />
            </div>
          )}

          {!isLoading && error && (
            <div className="p-4 rounded-lg border-2 border-red-200 bg-red-50">
              <p className="text-sm text-red-700 mb-2">{error}</p>
              <button
                type="button"
                onClick={handleRetry}
                className="text-sm font-semibold text-[#0f9448] hover:text-[#0d843f]"
              >
                Tentar novamente
              </button>
            </div>
          )}

          {!isLoading && !error && (
            <div
              className={`
                grid gap-4 transition-all duration-500 ease-in-out
                ${selectedData ? 'grid-cols-1' : 'grid-cols-2'}
              `}
            >
              {candidates.map((theme) => (
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
          )}
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
                    <ol className="text-sm font-semibold text-gray-900 list-decimal list-inside space-y-0.5">
                      {selectedData.keywords.map((keyword, index) => (
                        <li key={`${keyword}-${index}`}>{keyword}</li>
                      ))}
                    </ol>
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
          disabled={isBusy}
          className="flex-1 bg-gray-400 hover:bg-gray-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
        >
          Back
        </button>

        <button
          onClick={onNext}
          disabled={isBusy}
          className="flex-1 font-semibold py-2 px-4 rounded-lg text-white transition-colors duration-300 bg-[#0f9448] hover:bg-[#0d843f] disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isSaving ? 'Confirming...' : 'Confirm'}
        </button>

        <button
          onClick={handleRetry}
          disabled={isBusy}
          className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
        >
          {isLoading ? 'Generating...' : 'Generate Others Parameters'}
        </button>
      </div>
    </div>
  )
}
