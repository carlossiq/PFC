import { useState } from 'react'
import { X, Play, Loader2 } from 'lucide-react'
import { Button } from '../Button'
import { SectionHeader } from '../SectionHeader'
import { FloatingLabelInput } from '../FloatingLabelInput'
import { Modal } from '../Modal'
import { useFormStore } from '../../stores/useFormStore'
import { useProspectingStore } from '../../stores/useProspectingStore'
import { buildSaveSessionPayload, saveSession } from '../../services/sessionInput'
import {
  AI_SECTION_LABELS,
  AI_SECTION_ORDER,
  buildStaticSections,
  computeSectionRagContext,
  generateSectionText,
  assembleReport,
  type AiSectionKey,
  type SectionGenerateOverrides,
  type SignatureBlockInput,
  type SignaturesFormInput,
} from '../../services/report'
import {
  adminReferenceError,
  bibliographyError,
  signerFuncaoError,
  signerNameError,
  signerPostoError,
  textFieldError,
} from '../../utils/reportFormValidation'

type SectionRunStatus = 'pending' | 'rag' | 'generating' | 'done' | 'error'

interface AiSectionState {
  status: SectionRunStatus
  text: string | null
  error: string | null
}

interface StaticSectionState {
  status: SectionRunStatus
  metodologia: string | null
  referenciasBibliograficas: string[] | null
  databasesDetected: string[]
  error: string | null
}

const STATUS_LABELS: Record<SectionRunStatus, string> = {
  pending: 'Pendente',
  rag: 'Calculando contexto (RAG)...',
  generating: 'Gerando texto...',
  done: 'Pronto',
  error: 'Falhou',
}

const STATUS_CLASSES: Record<SectionRunStatus, string> = {
  pending: 'text-gray-500 bg-gray-100',
  rag: 'text-blue-600 bg-blue-50',
  generating: 'text-blue-600 bg-blue-50',
  done: 'text-[#0f9448] bg-[#0f9448]/10',
  error: 'text-red-600 bg-red-50',
}

function errorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  return err instanceof Error ? err.message : fallback
}

function ListEditor({
  label,
  items,
  onChange,
  placeholder,
  error = false,
  validate,
}: {
  label: string
  items: string[]
  onChange: (items: string[]) => void
  placeholder: string
  error?: boolean
  // Devolve a mensagem de erro do item (ou null) - item inválido não entra
  // na lista (ver utils/reportFormValidation.ts).
  validate?: (item: string) => string | null
}) {
  const [draft, setDraft] = useState('')
  const [draftError, setDraftError] = useState<string | null>(null)

  function add() {
    const trimmed = draft.trim()
    if (!trimmed) return
    const itemError = validate?.(trimmed) ?? null
    if (itemError) {
      setDraftError(itemError)
      return
    }
    onChange([...items, trimmed])
    setDraft('')
    setDraftError(null)
  }

  return (
    <div>
      <p className="text-xs text-gray-600 font-medium mb-1">{label}</p>
      <div className="flex gap-2 mb-2">
        <input
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value)
            setDraftError(null)
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              add()
            }
          }}
          placeholder={placeholder}
          className={`flex-1 h-9 px-3 rounded-lg border text-sm focus:outline-none focus:ring-1 ${
            error || draftError
              ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:border-[#0f9448] focus:ring-[#0f9448]'
          }`}
        />
        <Button size="sm" variant="secondary" onClick={add} type="button">
          Adicionar
        </Button>
      </div>
      {draftError && <p className="text-red-500 text-xs -mt-1 mb-2">{draftError}</p>}
      {error && items.length === 0 && <p className="text-red-500 text-xs -mt-1 mb-2">Campo obrigatório.</p>}
      {items.length > 0 && (
        <ul className="space-y-1">
          {items.map((item, i) => (
            <li
              key={i}
              className="flex items-center justify-between gap-2 bg-gray-50 rounded-md px-3 py-1.5 text-sm text-gray-800"
            >
              <span className="break-all">{item}</span>
              <button
                type="button"
                onClick={() => onChange(items.filter((_, idx) => idx !== i))}
                className="shrink-0 text-gray-400 hover:text-red-600 transition-colors"
                aria-label="Remover"
              >
                <X size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// Lista de assinantes de um papel (Elaborado/Revisado/Aprovado por) - 1+
// blocos nome / posto-graduação / função (sai como "NOME – POSTO" e a
// função embaixo, como no REPTEC), com "+ Adicionar" e um X por bloco (some
// quando só resta um - esse nunca pode ser removido).
function SignatureListEditor({
  title,
  values,
  onChange,
  error = false,
}: {
  title: string
  values: SignatureBlockInput[]
  onChange: (values: SignatureBlockInput[]) => void
  error?: boolean
}) {
  function updateAt(index: number, patch: Partial<SignatureBlockInput>) {
    onChange(values.map((v, i) => (i === index ? { ...v, ...patch } : v)))
  }

  return (
    <div className={error ? 'rounded-lg border border-red-500 p-2' : ''}>
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs text-gray-600 font-medium">{title}</p>
        <button
          type="button"
          onClick={() => onChange([...values, { nome: '', posto: '', funcao: '' }])}
          className="text-xs font-semibold text-[#0f9448] hover:text-[#0d843f]"
        >
          + Adicionar
        </button>
      </div>
      {error && (
        <p className="text-red-500 text-xs mb-2">Pelo menos um assinante (nome, posto/graduação e função) é obrigatório.</p>
      )}
      <div className="space-y-2">
        {values.map((value, index) => (
          <div key={index} className="flex items-start gap-2">
            <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr_2fr] gap-3 flex-1">
              <div>
                <FloatingLabelInput
                  label="Nome"
                  name={`${title}-nome-${index}`}
                  value={value.nome}
                  onChange={(e) => updateAt(index, { nome: e.target.value })}
                  placeholder="Ex.: RICARDO WAGNER AMORIM GUIMARÃES"
                  error={!!signerNameError(value.nome)}
                />
                {signerNameError(value.nome) && (
                  <p className="text-red-500 text-xs mt-1">{signerNameError(value.nome)}</p>
                )}
              </div>
              <div>
                <FloatingLabelInput
                  label="Posto/Graduação"
                  name={`${title}-posto-${index}`}
                  value={value.posto}
                  onChange={(e) => updateAt(index, { posto: e.target.value })}
                  placeholder="Ex.: TC"
                  error={!!signerPostoError(value.posto)}
                />
                {signerPostoError(value.posto) && (
                  <p className="text-red-500 text-xs mt-1">{signerPostoError(value.posto)}</p>
                )}
              </div>
              <div>
                <FloatingLabelInput
                  label="Função"
                  name={`${title}-funcao-${index}`}
                  value={value.funcao}
                  onChange={(e) => updateAt(index, { funcao: e.target.value })}
                  placeholder="Ex.: Adj da Seção de Informações Tecnológicas"
                  error={!!signerFuncaoError(value)}
                />
                {signerFuncaoError(value) && (
                  <p className="text-red-500 text-xs mt-1">{signerFuncaoError(value)}</p>
                )}
              </div>
            </div>
            {values.length > 1 && (
              <button
                type="button"
                onClick={() => onChange(values.filter((_, i) => i !== index))}
                className="shrink-0 mt-2.5 text-gray-400 hover:text-red-600 transition-colors"
                aria-label="Remover assinante"
              >
                <X size={16} />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function SectionRow({
  label,
  state,
  onRegenerate,
  disabled,
}: {
  label: string
  state: { status: SectionRunStatus; error: string | null; text: string | null }
  onRegenerate: () => void
  disabled: boolean
}) {
  const busy = state.status === 'rag' || state.status === 'generating'
  const actionLabel = state.status === 'pending' ? 'Gerar' : 'Gerar novamente'
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <h4 className="font-semibold text-sm text-gray-900">{label}</h4>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-semibold rounded-full px-2 py-0.5 ${STATUS_CLASSES[state.status]}`}>
            {STATUS_LABELS[state.status]}
          </span>
          <button
            type="button"
            onClick={onRegenerate}
            disabled={disabled || busy}
            aria-label={actionLabel}
            title={actionLabel}
            className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-[#0f9448] text-white transition-colors hover:bg-[#0d843f] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-[#0f9448]"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Play size={14} fill="white" />}
          </button>
        </div>
      </div>
      {state.error && <p className="text-xs text-red-600 mb-2">{state.error}</p>}
      {state.text && (
        <p className="text-sm text-gray-700 whitespace-pre-wrap max-h-40 overflow-y-auto">{state.text}</p>
      )}
    </div>
  )
}

interface ReportGenerationProps {
  sessionId: number
  onBack: () => void
  onAssembled: (texContent: string) => void
}

const EMPTY_SIGNATURE_LIST: SignatureBlockInput[] = [{ nome: '', posto: '', funcao: '' }]

export function ReportGeneration({ sessionId, onBack, onAssembled }: ReportGenerationProps) {
  const [numero, setNumero] = useState('')
  const [ano, setAno] = useState(String(new Date().getFullYear()))
  const [referenciasAdministrativas, setReferenciasAdministrativas] = useState<string[]>([])
  const [referenciasBibliograficasAdicionais, setReferenciasBibliograficasAdicionais] = useState<string[]>([])
  // Finalidade = frase fixa com o destinatário; Objetivo opcional (vazio =
  // gerado por IA); local = linha "Rio de Janeiro, <data>." das assinaturas.
  const [destinatario, setDestinatario] = useState('')
  const [objetivo, setObjetivo] = useState('')
  const [local, setLocal] = useState('Rio de Janeiro')
  const [signatures, setSignatures] = useState<SignaturesFormInput>({
    elaboradoPor: EMPTY_SIGNATURE_LIST,
    revisadoPor: EMPTY_SIGNATURE_LIST,
    aprovadoPor: EMPTY_SIGNATURE_LIST,
  })

  const [staticState, setStaticState] = useState<StaticSectionState>({
    status: 'pending',
    metodologia: null,
    referenciasBibliograficas: null,
    databasesDetected: [],
    error: null,
  })
  const [aiSections, setAiSections] = useState<Record<AiSectionKey, AiSectionState>>(() => {
    const initial = {} as Record<AiSectionKey, AiSectionState>
    for (const key of AI_SECTION_ORDER) {
      initial[key] = { status: 'pending', text: null, error: null }
    }
    return initial
  })
  const [isGenerating, setIsGenerating] = useState(false)

  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [isAssembling, setIsAssembling] = useState(false)
  const [assembleError, setAssembleError] = useState<string | null>(null)
  const [hasAttemptedAssemble, setHasAttemptedAssemble] = useState(false)

  const allSectionsDone =
    staticState.status === 'done' && AI_SECTION_ORDER.every((key) => aiSections[key].status === 'done')
  const hasStarted = staticState.status !== 'pending' || AI_SECTION_ORDER.some((key) => aiSections[key].status !== 'pending')

  // Campos sempre obrigatórios pro relatório (ver Metodologia/Referências e
  // a capa do .tex) - a borda vermelha só aparece depois de uma tentativa de
  // clicar em "Montar .tex" com algo faltando (hasAttemptedAssemble), não já
  // na entrada da tela. O botão continua sempre clicável (ver
  // handleAssembleClick) - clicar com campo faltando apenas revela os erros,
  // sem abrir o modal de confirmação.
  const numeroError = !numero.trim()
  const anoError = !ano.trim()
  const referenciasAdministrativasError = referenciasAdministrativas.length === 0
  const elaboradoPorError = !signatures.elaboradoPor.some((s) => s.nome.trim() && s.posto.trim() && s.funcao.trim())
  const destinatarioError = !destinatario.trim() || !!textFieldError(destinatario)
  const objetivoError = !!textFieldError(objetivo, 5)
  const localError = !local.trim()
  const signatureFieldErrors = [...signatures.elaboradoPor, ...signatures.revisadoPor, ...signatures.aprovadoPor].some(
    (s) => !!signerNameError(s.nome) || !!signerPostoError(s.posto) || !!signerFuncaoError(s)
  )
  const hasRequiredFieldErrors =
    numeroError ||
    anoError ||
    referenciasAdministrativasError ||
    elaboradoPorError ||
    destinatarioError ||
    objetivoError ||
    localError ||
    signatureFieldErrors
  const showDestinatarioError = hasAttemptedAssemble && destinatarioError
  const showLocalError = hasAttemptedAssemble && localError
  const hasUserObjetivo = !!objetivo.trim()
  const showNumeroError = hasAttemptedAssemble && numeroError
  const showAnoError = hasAttemptedAssemble && anoError
  const showReferenciasAdministrativasError = hasAttemptedAssemble && referenciasAdministrativasError
  const showElaboradoPorError = hasAttemptedAssemble && elaboradoPorError

  function currentTema(): string {
    const formState = useFormStore.getState()
    return formState.step2SelectedTheme?.theme || formState.input.theme
  }

  function buildSignaturesPayload(): SignaturesFormInput {
    return signatures
  }

  // Período efetivamente usado na busca - SessionInput.year_from/year_to
  // (Step1) fica quase sempre null (o ano é escolhido por query, não numa
  // etapa global do wizard), então usamos o year_range da query final de
  // patente (ou artigo, se a de patente não tiver) que o front já tem em mãos.
  function resolvePeriod(): { periodStart: number | null; periodEnd: number | null } {
    const formState = useFormStore.getState()
    const range = formState.step4PatentQuery?.year_range ?? formState.step4ArticleQuery?.year_range
    return { periodStart: range?.from ?? null, periodEnd: range?.to ?? null }
  }

  // Totais de resultados da busca final - os únicos fatos que não ficam no
  // banco (resumos dos gráficos, estágio do ciclo de vida e CPC oficial o
  // backend lê do que já está persistido).
  function buildSectionOverrides(): SectionGenerateOverrides {
    const formState = useFormStore.getState()
    return {
      articleCount: (formState.step4ArticleResults?.totalCount ?? formState.step4ArticleResults?.resultsCount),
      patentCount: (formState.step4PatentResults?.totalCount ?? formState.step4PatentResults?.resultsCount),
    }
  }

  async function runStatic(): Promise<boolean> {
    setStaticState((s) => ({ ...s, status: 'generating', error: null }))
    try {
      const { periodStart, periodEnd } = resolvePeriod()
      const result = await buildStaticSections(sessionId, {
        numero,
        ano,
        referenciasAdministrativas,
        referenciasBibliograficasAdicionais,
        assinaturas: buildSignaturesPayload(),
        periodStart,
        periodEnd,
        tema: currentTema(),
        destinatario,
        objetivo,
      })
      // Objetivo escrito pelo usuário já foi gravado pelas seções estáticas
      // - a seção de IA "objetivo" não roda.
      if (hasUserObjetivo) {
        setAiSections((s) => ({ ...s, objetivo: { status: 'done', text: objetivo.trim(), error: null } }))
      }
      setStaticState({
        status: 'done',
        metodologia: result.metodologia,
        referenciasBibliograficas: result.referenciasBibliograficas,
        databasesDetected: result.databasesDetected,
        error: null,
      })
      return true
    } catch (err) {
      setStaticState((s) => ({ ...s, status: 'error', error: errorMessage(err, 'Falha ao montar as seções estáticas.') }))
      return false
    }
  }

  async function runAiSection(key: AiSectionKey): Promise<boolean> {
    setAiSections((s) => ({ ...s, [key]: { status: 'rag', text: null, error: null } }))
    try {
      await computeSectionRagContext(sessionId, key)
    } catch (err) {
      setAiSections((s) => ({ ...s, [key]: { status: 'error', text: null, error: errorMessage(err, 'Falha ao calcular o contexto.') } }))
      return false
    }
    setAiSections((s) => ({ ...s, [key]: { ...s[key], status: 'generating' } }))
    try {
      const text = await generateSectionText(sessionId, key, buildSectionOverrides())
      setAiSections((s) => ({ ...s, [key]: { status: 'done', text, error: null } }))
      return true
    } catch (err) {
      setAiSections((s) => ({ ...s, [key]: { status: 'error', text: null, error: errorMessage(err, 'Falha ao gerar o texto.') } }))
      return false
    }
  }

  async function runPipeline() {
    if (isGenerating) return
    // Mesmos campos obrigatórios da montagem - as seções estáticas (Finalidade,
    // Objetivo do usuário, referências) já dependem deles.
    if (hasRequiredFieldErrors) {
      setHasAttemptedAssemble(true)
      return
    }
    setIsGenerating(true)
    if (staticState.status !== 'done') {
      const ok = await runStatic()
      if (!ok) {
        setIsGenerating(false)
        return
      }
    }
    for (const key of AI_SECTION_ORDER) {
      if (aiSections[key].status === 'done') continue
      if (key === 'objetivo' && hasUserObjetivo) continue
      const ok = await runAiSection(key)
      if (!ok) {
        setIsGenerating(false)
        return
      }
    }
    setIsGenerating(false)
  }

  function handleAssembleClick() {
    if (hasRequiredFieldErrors) {
      setHasAttemptedAssemble(true)
      return
    }
    setShowConfirmModal(true)
  }

  async function handleConfirmAssemble() {
    setShowConfirmModal(false)
    setIsAssembling(true)
    setAssembleError(null)
    try {
      const formState = useFormStore.getState()
      const tema = currentTema()
      const quadroBusca = {
        patenteQuery: formState.step4PatentQuery?.query?.query ?? null,
        patenteCount: (formState.step4PatentResults?.totalCount ?? formState.step4PatentResults?.resultsCount) ?? null,
        artigoQuery: formState.step4ArticleQuery?.query?.query ?? null,
        artigoCount: (formState.step4ArticleResults?.totalCount ?? formState.step4ArticleResults?.resultsCount) ?? null,
      }
      const result = await assembleReport(sessionId, {
        numero,
        ano,
        tema,
        referenciasAdministrativas,
        assinaturas: buildSignaturesPayload(),
        quadroBusca,
        local,
      })
      const { step: currentStep, substep: currentSubstep } = useProspectingStore.getState()
      const payload = buildSaveSessionPayload(formState, true, currentStep, currentSubstep)
      const saveResult = await saveSession(formState.sessionId, formState.sessionName, payload)
      useFormStore.getState().setSessionId(saveResult.session_id, saveResult.session_public_id)
      useFormStore.getState().setLastSavedSignature(JSON.stringify(payload))
      useFormStore.getState().clearAiCallLog()
      onAssembled(result.texContent)
    } catch (err) {
      console.error('Falha ao montar o relatório:', err)
      setAssembleError(errorMessage(err, 'Não foi possível montar o relatório. Tente novamente.'))
    } finally {
      setIsAssembling(false)
    }
  }

  return (
    <div>
      <SectionHeader
        title="Geração do Relatório"
        description="Preencha os metadados do REPTEC, gere as seções do relatório e, quando todas estiverem prontas, monte o documento final."
      />

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4 mb-6 space-y-4">
        <h4 className="font-semibold text-sm text-gray-900">Metadados do REPTEC</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <FloatingLabelInput label="Número" name="reptec-numero" value={numero} onChange={(e) => setNumero(e.target.value)} placeholder="Ex.: 001" error={showNumeroError} />
            {showNumeroError && <p className="text-red-500 text-xs mt-1">Campo obrigatório.</p>}
          </div>
          <div>
            <FloatingLabelInput label="Ano" name="reptec-ano" value={ano} onChange={(e) => setAno(e.target.value)} placeholder="Ex.: 2026" error={showAnoError} />
            {showAnoError && <p className="text-red-500 text-xs mt-1">Campo obrigatório.</p>}
          </div>
        </div>

        <ListEditor
          label="Referências administrativas"
          items={referenciasAdministrativas}
          onChange={setReferenciasAdministrativas}
          placeholder="Ex.: DIEx Nº 115-A3/DCT de 6 de janeiro de 2023"
          error={showReferenciasAdministrativasError}
          validate={adminReferenceError}
        />

        <ListEditor
          label="Referências bibliográficas adicionais"
          items={referenciasBibliograficasAdicionais}
          onChange={setReferenciasBibliograficasAdicionais}
          placeholder="Ex.: SILVA, J. Título da obra. Editora, 2020."
          validate={bibliographyError}
        />

        <div>
          <FloatingLabelInput
            label="Destinatário (Finalidade)"
            name="reptec-destinatario"
            value={destinatario}
            onChange={(e) => setDestinatario(e.target.value)}
            placeholder="Ex.: Indústria de Material Bélico do Brasil (IMBEL)"
            error={showDestinatarioError}
          />
          <p className="text-xs text-gray-500 mt-1">
            Finalidade: "Apresentar o relatório de Prospecção Tecnológica sobre o tema a fim de fornecer informações de
            tendências e ciclo de vida da tecnologia para <strong>{destinatario.trim() || '[destinatário]'}</strong>."
          </p>
          {showDestinatarioError && <p className="text-red-500 text-xs mt-1">Informe para quem é o relatório.</p>}
        </div>

        <div>
          <FloatingLabelInput
            label="Objetivo (opcional)"
            name="reptec-objetivo"
            value={objetivo}
            onChange={(e) => setObjetivo(e.target.value)}
            placeholder="Ex.: O presente trabalho consiste em realizar um estudo de prospecção tecnológica sobre ... como subsídio para ..."
            isTextarea
            rows={3}
            error={objetivoError}
          />
          <p className="text-xs text-gray-500 mt-1">
            {objetivoError
              ? 'Texto inválido - escreva ao menos uma frase.'
              : 'Deixe em branco para a IA redigir um parágrafo curto a partir do tema.'}
          </p>
        </div>

        <div>
          <FloatingLabelInput
            label="Local (linha antes das assinaturas)"
            name="reptec-local"
            value={local}
            onChange={(e) => setLocal(e.target.value)}
            placeholder="Ex.: Rio de Janeiro"
            error={showLocalError}
          />
          {showLocalError && <p className="text-red-500 text-xs mt-1">Campo obrigatório.</p>}
        </div>

        {staticState.databasesDetected.length > 0 && (
          <p className="text-xs text-gray-500">
            Bases de dados detectadas automaticamente: <strong>{staticState.databasesDetected.join(', ')}</strong>
          </p>
        )}

        <div className="space-y-4">
          <p className="text-xs text-gray-600 font-medium">Assinaturas</p>
          <SignatureListEditor
            title="Elaborado por"
            values={signatures.elaboradoPor}
            onChange={(v) => setSignatures((s) => ({ ...s, elaboradoPor: v }))}
            error={showElaboradoPorError}
          />
          <SignatureListEditor
            title="Revisado por"
            values={signatures.revisadoPor}
            onChange={(v) => setSignatures((s) => ({ ...s, revisadoPor: v }))}
          />
          <SignatureListEditor
            title="Aprovado por"
            values={signatures.aprovadoPor}
            onChange={(v) => setSignatures((s) => ({ ...s, aprovadoPor: v }))}
          />
        </div>
      </div>

      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-sm text-gray-900">Seções do relatório</h4>
        <Button size="sm" onClick={runPipeline} disabled={isGenerating || allSectionsDone} type="button">
          {isGenerating ? 'Gerando...' : hasStarted ? 'Continuar geração' : 'Gerar Seções'}
        </Button>
      </div>

      <div className="space-y-3 mb-6">
        <SectionRow
          label="Finalidade, Metodologia e Referências Bibliográficas"
          state={{
            status: staticState.status,
            error: staticState.error,
            text: staticState.metodologia,
          }}
          onRegenerate={() => runStatic()}
          disabled={isGenerating}
        />
        {AI_SECTION_ORDER.map((key) => (
          <SectionRow
            key={key}
            label={AI_SECTION_LABELS[key]}
            state={aiSections[key]}
            onRegenerate={() => runAiSection(key)}
            disabled={isGenerating}
          />
        ))}
      </div>

      {assembleError && <p className="mb-4 text-sm text-red-600 font-medium">{assembleError}</p>}

      <div className="flex gap-4">
        <Button fullWidth variant="secondary" onClick={onBack} type="button">
          Voltar
        </Button>
        <Button
          fullWidth
          variant="accent"
          onClick={handleAssembleClick}
          disabled={!allSectionsDone || isAssembling}
          type="button"
        >
          {isAssembling ? 'Montando...' : 'Montar .tex'}
        </Button>
      </div>

      <Modal
        isOpen={showConfirmModal}
        title="Montar o relatório final?"
        message="A partir daqui não será mais possível voltar a editar a pesquisa desta sessão - só o texto do relatório. Deseja continuar?"
        confirmText="Sim, montar"
        cancelText="Não"
        onConfirm={handleConfirmAssemble}
        onCancel={() => setShowConfirmModal(false)}
      />
    </div>
  )
}
