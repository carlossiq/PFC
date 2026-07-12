import { useState, useEffect, useCallback, useRef } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import {
  generateProbeQueriesMulti,
  rebuildProbeQuery,
} from '../../services/probeQuery'
import type { StructuredQueryFields } from '../../services/probeQuery'
import { resolveIntakePayload } from '../../services/refineTopic'
import { LoadingScreen } from '../LoadingScreen'
import { FloatingLabelInput } from '../FloatingLabelInput'
import { Tooltip } from '../Tooltip'
import { CandidatePickerLayout, selectableCardClass, toCsv, parseCsv } from '../CandidatePicker'
import { STEPS } from '../../constants/steps'

interface Step3Props {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

const FIELD_LABELS: Record<keyof StructuredQueryFields, string> = {
  title: 'Title',
  abstract: 'Abstract',
  claims: 'Claims',
  ipc: 'IPC',
  cpc: 'CPC',
  applicant: 'Applicant',
  inventor: 'Inventor',
  year: 'Year',
}

// applicant/inventor/claims/cpc ficam de fora: são filtros restritivos ou
// específicos demais pra uma exploração inicial (mais ampla) - fazem mais
// sentido só na busca final. Se a IA gerar algo nesses campos mesmo assim, o
// valor é preservado (não exibido/editável aqui, mas também não é apagado ao
// salvar uma edição).
const FIELD_ORDER: (keyof StructuredQueryFields)[] = [
  'title', 'abstract', 'ipc', 'year',
]

const emptyFields: StructuredQueryFields = {
  title: [], abstract: [], claims: [], ipc: [], cpc: [], applicant: [], inventor: [], year: [],
}

// A API da IA (Gemini/Anthropic) pode devolver mensagens de erro brutas e
// longas (ex: 429 com detalhes de quota) — resume pros casos conhecidos em
// vez de despejar o texto cru no card.
function friendlyErrorMessage(error?: string): string {
  if (!error) return 'Falha ao gerar esta opção.'
  if (/429|quota|rate.?limit/i.test(error)) {
    return 'Limite de requisições da IA atingido no momento. Tente novamente em instantes.'
  }
  return error.length > 140 ? `${error.slice(0, 140)}…` : error
}

export function Step3({ step, substep, onBack, onNext }: Step3Props) {
  const {
    input,
    step2SelectedTheme,
    step3Queries,
    setStep3Queries,
    updateStep3QueryAt,
    step3SelectedIndex,
    setStep3SelectedIndex,
    step3GeneratedForIntake,
    incrementStep3Iterations,
  } = useFormStore()

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isRebuilding, setIsRebuilding] = useState(false)
  const [rebuildError, setRebuildError] = useState<string | null>(null)

  const requestIdRef = useRef(0)
  // Trava síncrona contra o double-invoke do StrictMode em dev: como o Step3
  // nunca desmonta (Workflow.tsx sempre o renderiza, só alterna `return null`
  // internamente), um ref "já rodei uma vez" não pode ser usado aqui - ele
  // nunca resetaria, e uma nova regeneração legítima (parâmetro mudou) ficaria
  // presa. Em vez disso, essa trava só bloqueia uma segunda chamada disparada
  // *durante* a mesma geração em andamento.
  const isGeneratingRef = useRef(false)

  // Assinatura do intake (tema/descrição/keywords resolvido) que seria usado
  // AGORA pra gerar queries - comparada com step3GeneratedForIntake pra saber
  // se as queries existentes ainda são válidas pro parâmetro atual.
  const currentIntakeSignature = JSON.stringify(resolveIntakePayload(input, step2SelectedTheme))

  const generateQueries = useCallback(async () => {
    const requestId = ++requestIdRef.current
    setIsLoading(true)
    setError(null)
    try {
      const queries = await generateProbeQueriesMulti(input, step2SelectedTheme)
      if (requestIdRef.current !== requestId) return
      setStep3Queries(queries, currentIntakeSignature)
      const firstSuccessIndex = queries.findIndex((q) => q.success)
      setStep3SelectedIndex(firstSuccessIndex !== -1 ? firstSuccessIndex : 0)
    } catch (err) {
      if (requestIdRef.current !== requestId) return
      console.error('Falha ao gerar queries com IA:', err)
      setError('Não foi possível gerar as queries com IA. Tente novamente.')
    } finally {
      if (requestIdRef.current === requestId) setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, step2SelectedTheme, setStep3Queries, setStep3SelectedIndex])

  useEffect(() => {
    if (step !== STEPS.INITIAL_EXPLORATION || substep !== null) return
    if (isGeneratingRef.current) return
    const needsRegeneration = !step3Queries || step3GeneratedForIntake !== currentIntakeSignature
    if (needsRegeneration) {
      isGeneratingRef.current = true
      generateQueries().finally(() => {
        isGeneratingRef.current = false
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, substep, step3GeneratedForIntake, currentIntakeSignature, step3Queries])

  const [isEditing, setIsEditing] = useState(false)
  const [editFields, setEditFields] = useState<Record<keyof StructuredQueryFields, string>>({
    title: '', abstract: '', claims: '', ipc: '', cpc: '', applicant: '', inventor: '', year: '',
  })

  useEffect(() => {
    setIsEditing(false)
    setRebuildError(null)
  }, [step3SelectedIndex])

  if (step !== STEPS.INITIAL_EXPLORATION || substep !== null) return null

  const handleRetry = () => {
    incrementStep3Iterations()
    generateQueries()
  }

  const selected = step3SelectedIndex !== null ? step3Queries?.[step3SelectedIndex] : undefined
  const isBusy = isLoading || isRebuilding

  function handleStartEdit() {
    const fields = selected?.fields ?? emptyFields
    setEditFields({
      title: toCsv(fields.title),
      abstract: toCsv(fields.abstract),
      claims: toCsv(fields.claims),
      ipc: toCsv(fields.ipc),
      cpc: toCsv(fields.cpc),
      applicant: toCsv(fields.applicant),
      inventor: toCsv(fields.inventor),
      year: toCsv(fields.year),
    })
    setIsEditing(true)
  }

  function handleCancelEdit() {
    setIsEditing(false)
  }

  async function handleSaveEdit() {
    if (step3SelectedIndex === null) return
    const parsed: StructuredQueryFields = {
      title: parseCsv(editFields.title),
      abstract: parseCsv(editFields.abstract),
      claims: parseCsv(editFields.claims),
      ipc: parseCsv(editFields.ipc),
      cpc: parseCsv(editFields.cpc),
      applicant: parseCsv(editFields.applicant),
      inventor: parseCsv(editFields.inventor),
      year: parseCsv(editFields.year),
    }

    setIsRebuilding(true)
    setRebuildError(null)
    try {
      const result = await rebuildProbeQuery(parsed)
      updateStep3QueryAt(step3SelectedIndex, result)
      setIsEditing(false)
    } catch (err) {
      console.error('Falha ao reconstruir query:', err)
      setRebuildError('Não foi possível reconstruir a query. Tente novamente.')
    } finally {
      setIsRebuilding(false)
    }
  }

  const leftPane = (
    <>
      <div className="flex items-center gap-1.5 mb-2">
        <p className="text-xs font-semibold text-black uppercase tracking-wide">
          Queries iniciais geradas por IA
        </p>
        <Tooltip
          position="right"
          label="Estamos na Exploração Inicial: aqui geramos queries pra uma busca restrita, só pra encontrar um primeiro conjunto de documentos de referência. Esses documentos serão analisados, e é a partir dessa análise que montamos a query final - mais ampla - da etapa de Exploração Final, que faz a busca completa de verdade."
        >
          <span className="w-4 h-4 flex items-center justify-center rounded-full border border-gray-400 text-gray-500 text-[10px] font-bold leading-none cursor-help">
            ?
          </span>
        </Tooltip>
      </div>
      <p className="text-xs text-gray-500 mb-3">
        {step3Queries?.length ?? 2} tentativas independentes de uma busca focada (poucos
        resultados, alta relevância), geradas automaticamente a partir dos parâmetros
        enviados.
      </p>

      {isLoading && <LoadingScreen message="Gerando queries com IA..." />}

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

      {!isLoading && !error && step3Queries && (
        <>
          <p className="text-xs font-semibold text-black uppercase tracking-wide mb-2">
            Queries de busca para patentes
          </p>
          <div className="grid gap-3">
            {step3Queries.map((result, index) => (
              <button
                key={index}
                onClick={() => setStep3SelectedIndex(index)}
                disabled={!result.success}
                className={`${selectableCardClass(step3SelectedIndex === index, 'w-full')} ${!result.success ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <h4 className="font-semibold text-sm text-gray-900 mb-1">
                  Opção {index + 1}
                </h4>
                {!result.success && (
                  <p className="text-xs text-red-600">{friendlyErrorMessage(result.error)}</p>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </>
  )

  const rightPane = (
    <>
      {selected && selected.success && (
        <p className="text-xs font-semibold text-black uppercase tracking-wide mb-2">
          Detalhes da query selecionada
        </p>
      )}

      {selected && selected.success && !isEditing && (
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
          </div>

          {rebuildError && (
            <div className="mx-2 mb-3 p-3 rounded-lg border-2 border-red-200 bg-red-50">
              <p className="text-sm text-red-700">{rebuildError}</p>
            </div>
          )}

          <div className="space-y-5 mt-1 mx-1">
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600 font-medium mb-1">Query (CQL)</p>
              <p className="text-sm font-mono text-gray-900 break-all">
                {selected.query?.query}
              </p>
            </div>

            {FIELD_ORDER.filter((f) => f !== 'year' && (selected.fields?.[f]?.length ?? 0) > 0).map((f) => (
              <div key={f} className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-600 font-medium mb-1">{FIELD_LABELS[f]}</p>
                <p className="text-sm font-semibold text-gray-900">
                  {selected.fields![f].join(', ')}
                </p>
              </div>
            ))}

            {/* Year sempre aparece, mesmo sem edição - mostra o padrão do
                backend quando o campo está vazio, deixando claro que a busca
                não é irrestrita por data. */}
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600 font-medium mb-1">{FIELD_LABELS.year}</p>
              <p className="text-sm font-semibold text-gray-900">
                {selected.fields?.year && selected.fields.year.length > 0
                  ? selected.fields.year.join(', ')
                  : selected.year_range
                    ? `${selected.year_range.from} - ${selected.year_range.to} (padrão)`
                    : '—'}
              </p>
            </div>

            {selected.complexity && (
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-600 font-medium mb-1">Complexidade</p>
                <p className="text-sm font-semibold text-gray-900">
                  {selected.complexity.level} ({selected.complexity.score.toFixed(1)}/100)
                </p>
              </div>
            )}

            {selected.warning && (
              <p className="text-xs text-amber-600">{selected.warning}</p>
            )}
          </div>
        </>
      )}

      {selected && selected.success && isEditing && (
        <div className="space-y-4 mt-1 mx-1">
          {FIELD_ORDER.map((f) => (
            <FloatingLabelInput
              key={f}
              label={FIELD_LABELS[f]}
              name={`edit-${f}`}
              value={editFields[f]}
              onChange={(e) => setEditFields((prev) => ({ ...prev, [f]: e.target.value }))}
              placeholder={f === 'year' ? 'ex: 2020 ou 2015, 2020 (intervalo)' : 'separados por vírgula'}
            />
          ))}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={handleCancelEdit}
              disabled={isRebuilding}
              className="flex-1 bg-gray-400 hover:bg-gray-500 disabled:opacity-60 text-white text-sm font-semibold py-2 px-4 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleSaveEdit}
              disabled={isRebuilding}
              className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] disabled:opacity-60 text-white text-sm font-semibold py-2 px-4 rounded-lg transition-colors"
            >
              {isRebuilding ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </div>
      )}
    </>
  )

  return (
    <div className="w-full flex flex-col h-full">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Escolha qual query utilizaremos
      </h3>

      <CandidatePickerLayout hasSelection={step3SelectedIndex !== null} left={leftPane} right={rightPane} />

      <div className="mt-6 pt-4 border-t border-gray-200 flex gap-4">
        <button
          onClick={onBack}
          disabled={isBusy}
          className="flex-1 bg-gray-400 hover:bg-gray-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
        >
          Voltar
        </button>

        <button
          onClick={onNext}
          disabled={isBusy || !selected?.success}
          className="flex-1 font-semibold py-2 px-4 rounded-lg text-white transition-colors duration-300 bg-[#0f9448] hover:bg-[#0d843f] disabled:opacity-60 disabled:cursor-not-allowed"
        >
          Próximo
        </button>

        <button
          onClick={handleRetry}
          disabled={isBusy}
          className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
        >
          {isLoading ? 'Gerando...' : 'Gerar outras'}
        </button>
      </div>
    </div>
  )
}
