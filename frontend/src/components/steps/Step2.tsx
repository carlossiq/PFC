import { useEffect, useState, useCallback, useRef } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { refineTopic, specifyTopic } from '../../services/refineTopic'
import { LoadingScreen } from '../LoadingScreen'
import { FloatingLabelInput } from '../FloatingLabelInput'
import { Tooltip } from '../Tooltip'

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
  const {
    input,
    step2SelectedTheme,
    setStep2SelectedTheme,
    setGenerated,
    step2Candidates: candidates,
    setStep2Candidates: setCandidates,
    shouldRegenerateStep2,
    setShouldRegenerateStep2,
    incrementStep2Iterations,
  } = useFormStore()

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Evita que uma chamada antiga (ex: o double-invoke do StrictMode em dev,
  // ou um clique duplo em "Generate Others") sobrescreva o resultado de uma
  // chamada mais recente quando ambas resolverem fora de ordem.
  const requestIdRef = useRef(0)

  const generateCandidates = useCallback(async () => {
    const requestId = ++requestIdRef.current
    setIsLoading(true)
    setError(null)
    try {
      const results = await refineTopic(input)
      if (requestIdRef.current !== requestId) return
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
      if (requestIdRef.current !== requestId) return
      console.error('Falha ao gerar parâmetros com IA:', err)
      setError('Não foi possível gerar parâmetros com IA. Tente novamente.')
      setCandidates([])
    } finally {
      if (requestIdRef.current === requestId) setIsLoading(false)
    }
  }, [input, setCandidates])

  // Guarda contra o double-invoke do StrictMode em dev, e contra regenerar os
  // parâmetros toda vez que o componente remonta (ex: ao navegar para outro
  // step e voltar). Só gera de novo se for a primeira vez da sessão ou se
  // shouldRegenerateStep2 foi setado explicitamente (clique em "Refinar
  // parâmetros" no Step1).
  const hasCheckedOnMountRef = useRef(false)

  useEffect(() => {
    if (hasCheckedOnMountRef.current) return
    hasCheckedOnMountRef.current = true
    if (shouldRegenerateStep2 || candidates.length === 0) {
      setShouldRegenerateStep2(false)
      generateCandidates()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleRetry = () => {
    incrementStep2Iterations()
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

  const [isEditingSelected, setIsEditingSelected] = useState(false)
  const [editTheme, setEditTheme] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editKeywords, setEditKeywords] = useState('')
  const [editStudyArea, setEditStudyArea] = useState('')

  const [isSpecifying, setIsSpecifying] = useState(false)
  const [specifyError, setSpecifyError] = useState<string | null>(null)

  // Sair do modo de edição e limpar erro de especificação ao trocar de card
  // selecionado, pra não misturar estado de um card com os campos de outro.
  useEffect(() => {
    setIsEditingSelected(false)
    setSpecifyError(null)
  }, [selectedData.id])

  function handleStartEdit() {
    setEditTheme(selectedData.theme)
    setEditDescription(selectedData.description)
    setEditKeywords(selectedData.keywords?.join(', ') ?? '')
    setEditStudyArea(selectedData.studyArea?.join(', ') ?? '')
    setIsEditingSelected(true)
  }

  function handleCancelEdit() {
    setIsEditingSelected(false)
  }

  function handleSaveEdit() {
    const updated: Theme = {
      ...selectedData,
      theme: editTheme.trim() || selectedData.theme,
      description: editDescription.trim(),
      keywords: editKeywords.trim()
        ? editKeywords.split(',').map((k) => k.trim()).filter(Boolean)
        : undefined,
      studyArea: editStudyArea.trim()
        ? editStudyArea.split(',').map((a) => a.trim()).filter(Boolean)
        : undefined,
    }
    setStep2SelectedTheme(updated)
    setCandidates(candidates.map((c) => (c.id === updated.id ? updated : c)))
    setIsEditingSelected(false)
  }

  // Pede pra IA aprofundar o tema atualmente selecionado numa versão mais
  // específica do mesmo assunto. Reenvia sempre o selectedData corrente, então
  // clicar de novo aprofunda a partir do resultado anterior (progressivo).
  async function handleSpecify() {
    incrementStep2Iterations()
    setIsSpecifying(true)
    setSpecifyError(null)
    try {
      const result = await specifyTopic(selectedData)
      const updated: Theme = {
        ...selectedData,
        theme: result.theme,
        description: result.description ?? selectedData.description,
      }
      setStep2SelectedTheme(updated)
      setCandidates(candidates.map((c) => (c.id === updated.id ? updated : c)))
    } catch (err) {
      console.error('Falha ao especificar o tema com IA:', err)
      setSpecifyError('Não foi possível especificar o tema com IA. Tente novamente.')
    } finally {
      setIsSpecifying(false)
    }
  }

  const isBusy = isSaving || isLoading || isSpecifying

  const cardClass = (themeId: string) => `
    py-2 px-3 rounded-lg border-2 text-left bg-white shadow-sm
    transition-all duration-300 ease-in-out
    ${
      selectedData?.id === themeId
        ? 'border-[#0f9448] ring-2 ring-[#0f9448]/10 border-2'
        : 'border-gray-200 hover:border-[#0f9448]'
    }
  `

  return (
    <div className="w-full flex flex-col h-full">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Escolha qual parâmetro utilizaremos
      </h3>

      <div className="flex-1 flex gap-6 overflow-hidden">
        <div
          className={`
            bg-gray-100 rounded-xl border border-gray-200 p-4 overflow-y-auto
            transition-all duration-500 ease-in-out
            ${selectedData ? 'w-1/2' : 'w-full'}
          `}
        >
          <p className="text-xs font-semibold text-black uppercase tracking-wide mb-2">
            Parâmetro inicial
          </p>
          <p className="text-xs text-gray-500 mb-3">
            O tema (e demais campos) exatamente como você preencheu no passo anterior.
          </p>

          <div
            className={`
              grid gap-3 transition-all duration-500 ease-in-out
              ${selectedData ? 'grid-cols-1' : 'grid-cols-2'}
            `}
          >
            <button
              key={persistedTheme.id}
              onClick={() => handleSelectTheme(persistedTheme)}
              className={cardClass(persistedTheme.id)}
            >
              <h4 className="font-semibold text-sm text-gray-900 mb-1">
                {persistedTheme.theme}
              </h4>
            </button>
          </div>

          <p className="text-xs font-semibold text-black uppercase tracking-wide mt-6 mb-2">
            Parâmetros gerados por IA
          </p>
          <p className="text-xs text-gray-500 mb-3">
            4 variações mais específicas do seu tema, geradas automaticamente.
          </p>

          {isLoading && (
            <LoadingScreen message="Gerando parâmetros com IA..." />
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
                grid gap-3 transition-all duration-500 ease-in-out
                ${selectedData ? 'grid-cols-1' : 'grid-cols-2'}
              `}
            >
              {candidates.map((theme) => (
                <button
                  key={theme.id}
                  onClick={() => handleSelectTheme(theme)}
                  className={cardClass(theme.id)}
                >
                  <h4 className="font-semibold text-sm text-gray-900 mb-1">
                    {theme.theme}
                  </h4>
                </button>
              ))}
            </div>
          )}
        </div>

        <div
          className={`
            bg-gray-100 rounded-xl border border-gray-200 p-4 overflow-y-auto
            transition-all duration-500 ease-in-out
            ${
              selectedData
                ? 'w-1/2 opacity-100 translate-x-0'
                : 'w-0 opacity-0 translate-x-4 p-0 border-transparent pointer-events-none'
            }
          `}
        >
          {selectedData && (
            <p className="text-xs font-semibold text-black uppercase tracking-wide mb-2">
              Detalhes do parâmetro selecionado
            </p>
          )}

          {selectedData && isSpecifying && (
            <LoadingScreen message="Especificando tema com IA..." />
          )}

          {selectedData && !isSpecifying && !isEditingSelected && (
            <>
              <div className="flex justify-end gap-4 mb-2 p-2">
                  <button
                  type="button"
                  onClick={handleStartEdit}
                  disabled={isBusy}
                  className="text-xs p-4 font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  Editar
                </button>
                <div className="flex items-center ">
                  <Tooltip
                    position="top"
                    label="Quanto maior a especificação, mais afunilado o resultado. Pode gerar uma consulta que retorne poucos ou nenhum resultado."
                  >
                    <button
                      type="button"
                      onClick={handleSpecify}
                      disabled={isBusy}
                      className="text-xs p-4 font-semibold text-white bg-green-600 rounded-lg hover:bg-[#0d843f] disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      Especificar
                    </button>
                  </Tooltip>
                </div>
              
              </div>

              {specifyError && (
                <div className="mx-2 mb-3 p-3 rounded-lg border-2 border-red-200 bg-red-50">
                  <p className="text-sm text-red-700 mb-2">{specifyError}</p>
                  <button
                    type="button"
                    onClick={handleSpecify}
                    className="text-sm font-semibold text-[#0f9448] hover:text-[#0d843f]"
                  >
                    Tentar novamente
                  </button>
                </div>
              )}

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

          {selectedData && isEditingSelected && (
            <div className="space-y-4 mt-1 mx-1">
              <FloatingLabelInput
                label="Theme"
                name="editTheme"
                value={editTheme}
                onChange={(e) => setEditTheme(e.target.value)}
              />
              <FloatingLabelInput
                label="Description"
                name="editDescription"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                isTextarea
                rows={3}
              />
              <FloatingLabelInput
                label="Keywords"
                name="editKeywords"
                value={editKeywords}
                onChange={(e) => setEditKeywords(e.target.value)}
                placeholder="separadas por vírgula"
              />
              <FloatingLabelInput
                label="Study Area"
                name="editStudyArea"
                value={editStudyArea}
                onChange={(e) => setEditStudyArea(e.target.value)}
                placeholder="separadas por vírgula"
              />

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  className="flex-1 bg-gray-400 hover:bg-gray-500 text-white text-sm font-semibold py-2 px-4 rounded-lg transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleSaveEdit}
                  className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] text-white text-sm font-semibold py-2 px-4 rounded-lg transition-colors"
                >
                  Salvar
                </button>
              </div>
            </div>
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
