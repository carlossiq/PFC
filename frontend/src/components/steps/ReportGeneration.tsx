import { useState } from 'react'
import { X } from 'lucide-react'
import { Button } from '../Button'
import { SectionHeader } from '../SectionHeader'
import { FloatingLabelInput } from '../FloatingLabelInput'
import { Modal } from '../Modal'
import { useFormStore } from '../../stores/useFormStore'
import { buildSaveSessionPayload, saveSession } from '../../services/sessionInput'
import {
  AI_SECTION_LABELS,
  AI_SECTION_ORDER,
  buildStaticSections,
  computeSectionRagContext,
  generateSectionText,
  generatePatentSCurve,
  generateArticleSCurve,
  assembleReport,
  type AiSectionKey,
  type SectionGenerateOverrides,
  type SignatureBlockInput,
  type SignaturesFormInput,
} from '../../services/report'

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
  return err instanceof Error ? err.message : fallback
}

// Top-N chaves de um Record<string, number> (contagem), ordem decrescente -
// usado pra extrair "top depositantes"/"top CPC"/"top área de estudo" dos
// agregados que o front já tem em memória (step4PatentResults/step4ArticleResults,
// ver useFormStore.ts) e mandar como override pro backend (ver
// SectionGenerateOverrides) - sem isso as seções de Resultados sempre geram
// texto genérico, já que os documentos da busca FINAL nunca são persistidos
// no banco (só os da probe).
function topNKeys(counts: Record<string, number> | undefined, n = 5): string[] {
  if (!counts) return []
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([key]) => key)
}

// Estágio do ciclo de vida (Ernst, 1997 - o mesmo boilerplate de
// Metodologia já cita isso) a partir da saturação atual do ajuste
// logístico da curva S (0-1).
function deriveSCurvePhase(currentSaturation: number): string {
  if (currentSaturation < 0.25) return 'Emergente'
  if (currentSaturation < 0.6) return 'Crescimento'
  if (currentSaturation < 0.9) return 'Maturidade'
  return 'Saturação'
}

function ListEditor({
  label,
  items,
  onChange,
  placeholder,
}: {
  label: string
  items: string[]
  onChange: (items: string[]) => void
  placeholder: string
}) {
  const [draft, setDraft] = useState('')

  function add() {
    const trimmed = draft.trim()
    if (!trimmed) return
    onChange([...items, trimmed])
    setDraft('')
  }

  return (
    <div>
      <p className="text-xs text-gray-600 font-medium mb-1">{label}</p>
      <div className="flex gap-2 mb-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              add()
            }
          }}
          placeholder={placeholder}
          className="flex-1 h-9 px-3 rounded-lg border border-gray-300 text-sm focus:outline-none focus:border-[#0f9448] focus:ring-1 focus:ring-[#0f9448]"
        />
        <Button size="sm" variant="secondary" onClick={add} type="button">
          Adicionar
        </Button>
      </div>
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
// blocos nome/posto, com "+ Adicionar" e um X por bloco (some quando só
// resta um - esse nunca pode ser removido).
function SignatureListEditor({
  title,
  values,
  onChange,
}: {
  title: string
  values: SignatureBlockInput[]
  onChange: (values: SignatureBlockInput[]) => void
}) {
  function updateAt(index: number, patch: Partial<SignatureBlockInput>) {
    onChange(values.map((v, i) => (i === index ? { ...v, ...patch } : v)))
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs text-gray-600 font-medium">{title}</p>
        <button
          type="button"
          onClick={() => onChange([...values, { nome: '', postoFuncao: '' }])}
          className="text-xs font-semibold text-[#0f9448] hover:text-[#0d843f]"
        >
          + Adicionar
        </button>
      </div>
      <div className="space-y-2">
        {values.map((value, index) => (
          <div key={index} className="flex items-start gap-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 flex-1">
              <FloatingLabelInput
                label="Nome"
                name={`${title}-nome-${index}`}
                value={value.nome}
                onChange={(e) => updateAt(index, { nome: e.target.value })}
              />
              <FloatingLabelInput
                label="Posto/Função"
                name={`${title}-posto-${index}`}
                value={value.postoFuncao}
                onChange={(e) => updateAt(index, { postoFuncao: e.target.value })}
              />
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
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <h4 className="font-semibold text-sm text-gray-900">{label}</h4>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-semibold rounded-full px-2 py-0.5 ${STATUS_CLASSES[state.status]}`}>
            {STATUS_LABELS[state.status]}
          </span>
          <Button size="xs" variant="secondary" onClick={onRegenerate} disabled={disabled || busy} type="button">
            {state.status === 'pending' ? 'Gerar' : 'Gerar novamente'}
          </Button>
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

const EMPTY_SIGNATURE_LIST: SignatureBlockInput[] = [{ nome: '', postoFuncao: '' }]

export function ReportGeneration({ sessionId, onBack, onAssembled }: ReportGenerationProps) {
  const [numero, setNumero] = useState('')
  const [ano, setAno] = useState(String(new Date().getFullYear()))
  const [referenciasAdministrativas, setReferenciasAdministrativas] = useState<string[]>([])
  const [referenciasBibliograficasAdicionais, setReferenciasBibliograficasAdicionais] = useState<string[]>([])
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

  const allSectionsDone =
    staticState.status === 'done' && AI_SECTION_ORDER.every((key) => aiSections[key].status === 'done')
  const hasStarted = staticState.status !== 'pending' || AI_SECTION_ORDER.some((key) => aiSections[key].status !== 'pending')

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

  // Estatísticas agregadas que o front já tem em memória pra alimentar as 3
  // seções de Resultados - ver docstring de SectionGenerateOverrides (só
  // existe porque os documentos da busca final nunca são persistidos no
  // banco). "tendencias_ciclo_vida" precisa recalcular a curva S na hora
  // (a mesma rota que FinalResults.tsx já usa) porque o ajuste (fase,
  // saturação, ano de pico) não é persistido em lugar nenhum, só o PNG.
  async function buildSectionOverrides(key: AiSectionKey): Promise<SectionGenerateOverrides | undefined> {
    const formState = useFormStore.getState()

    if (key === 'informacoes_cientificas') {
      return {
        articleCount: formState.step4ArticleResults?.resultsCount,
        topFields: topNKeys(formState.step4ArticleResults?.areaOfStudy),
      }
    }

    if (key === 'informacoes_tecnologicas') {
      return {
        patentCount: formState.step4PatentResults?.resultsCount,
        topApplicants: topNKeys(formState.step4PatentResults?.depositants),
        topCpcCodes: topNKeys(formState.step4PatentResults?.cpc),
      }
    }

    if (key === 'tendencias_ciclo_vida') {
      try {
        const patentsByYear = formState.step4PatentResults?.patentsByYear
        if (patentsByYear && Object.keys(patentsByYear).length >= 2) {
          const { fit } = await generatePatentSCurve(sessionId, patentsByYear, 5)
          if (fit) {
            return {
              sCurvePhase: deriveSCurvePhase(fit.currentSaturation),
              growthRate: fit.r.toFixed(3),
              peakYear: Math.round(fit.mpYear),
            }
          }
        }
        const articlesByYear = formState.step4ArticleResults?.articlesByYear
        if (articlesByYear && Object.keys(articlesByYear).length >= 2) {
          const { fit } = await generateArticleSCurve(sessionId, articlesByYear, 5)
          if (fit) {
            return {
              sCurvePhase: deriveSCurvePhase(fit.currentSaturation),
              growthRate: fit.r.toFixed(3),
              peakYear: Math.round(fit.mpYear),
            }
          }
        }
      } catch (err) {
        console.warn('Falha ao calcular a curva S para o prompt de Tendências e Ciclo de Vida:', err)
      }
      return undefined
    }

    return undefined
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
      })
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
      const overrides = await buildSectionOverrides(key)
      const text = await generateSectionText(sessionId, key, overrides)
      setAiSections((s) => ({ ...s, [key]: { status: 'done', text, error: null } }))
      return true
    } catch (err) {
      setAiSections((s) => ({ ...s, [key]: { status: 'error', text: null, error: errorMessage(err, 'Falha ao gerar o texto.') } }))
      return false
    }
  }

  async function runPipeline() {
    if (isGenerating) return
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
      const ok = await runAiSection(key)
      if (!ok) {
        setIsGenerating(false)
        return
      }
    }
    setIsGenerating(false)
  }

  async function handleConfirmAssemble() {
    setShowConfirmModal(false)
    setIsAssembling(true)
    setAssembleError(null)
    try {
      const formState = useFormStore.getState()
      const tema = formState.step2SelectedTheme?.theme || formState.input.theme
      const quadroBusca = {
        patenteQuery: formState.step4PatentQuery?.query?.query ?? null,
        patenteCount: formState.step4PatentResults?.resultsCount ?? null,
        artigoQuery: formState.step4ArticleQuery?.query?.query ?? null,
        artigoCount: formState.step4ArticleResults?.resultsCount ?? null,
      }
      const result = await assembleReport(sessionId, {
        numero,
        ano,
        tema,
        referenciasAdministrativas,
        assinaturas: buildSignaturesPayload(),
        quadroBusca,
      })
      const payload = buildSaveSessionPayload(formState, true)
      const saveResult = await saveSession(formState.sessionId, formState.sessionName, payload)
      useFormStore.getState().setSessionId(saveResult.session_id, saveResult.session_public_id)
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
          <FloatingLabelInput label="Número" name="reptec-numero" value={numero} onChange={(e) => setNumero(e.target.value)} placeholder="Ex.: 001" />
          <FloatingLabelInput label="Ano" name="reptec-ano" value={ano} onChange={(e) => setAno(e.target.value)} placeholder="Ex.: 2026" />
        </div>

        <ListEditor
          label="Referências administrativas"
          items={referenciasAdministrativas}
          onChange={setReferenciasAdministrativas}
          placeholder="Ex.: DIEx Nº 115-A3/DCT de 6 de janeiro de 2023"
        />

        <ListEditor
          label="Referências bibliográficas adicionais"
          items={referenciasBibliograficasAdicionais}
          onChange={setReferenciasBibliograficasAdicionais}
          placeholder="Referência no formato ABNT"
        />

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
          {isGenerating ? 'Gerando...' : hasStarted ? 'Continuar geração' : 'Gerar Relatório'}
        </Button>
      </div>

      <div className="space-y-3 mb-6">
        <SectionRow
          label="Metodologia e Referências Bibliográficas"
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
          onClick={() => setShowConfirmModal(true)}
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
