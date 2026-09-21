import { useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import { Button } from '../Button'
import { Tooltip } from '../Tooltip'
import { LoadingScreen } from '../LoadingScreen'
import { Modal } from '../Modal'
import { useFormStore } from '../../stores/useFormStore'
import { useProspectingStore } from '../../stores/useProspectingStore'
import { useHistoryStore } from '../../stores/useHistoryStore'
import { useWorkflowStore } from '../../stores/useWorkflowStore'
import { TABS } from '../../constants/tabs'
import {
  compileReportPdf,
  getReportCharts,
  getReportDocument,
  getReportPdfBase64,
  openReportPdf,
  reassembleReport,
  type ReportChart,
} from '../../services/report'

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback
}

// Espelha app/core/services/report_writer_service.py::escape_latex - a
// legenda vem pronta pra exibição na UI (não teria porquê já vir escapada
// do backend, ver ReportChartItem), então quem monta o snippet de LaTeX
// (só aqui) escapa por conta própria antes de inserir no editor.
const LATEX_ESCAPE_MAP: Record<string, string> = {
  '\\': '\\textbackslash{}',
  '{': '\\{',
  '}': '\\}',
  $: '\\$',
  '&': '\\&',
  '%': '\\%',
  '#': '\\#',
  _: '\\_',
  '~': '\\textasciitilde{}',
  '^': '\\textasciicircum{}',
}

function escapeLatex(text: string): string {
  return text.replace(/[\\{}$&%#_~^]/g, (ch) => LATEX_ESCAPE_MAP[ch])
}

function chartFigureSnippet(chart: ReportChart): string {
  const caption = escapeLatex(chart.caption)
  return `\n\\begin{figure}[h]\n  \\centering\n  \\includegraphics[width=0.85\\textwidth]{${chart.filename}}\n  \\caption{${caption}}\n\\end{figure}\n`
}

interface ReportDocumentEditorProps {
  sessionId: number
  // Preenchido quando essa tela é montada logo após /assemble (o front já
  // tem o .tex em mãos, sem precisar de round-trip) - null faz o
  // componente buscar via GET /document (caso de reabrir uma sessão já
  // finalizada, ver `standalone`).
  initialTexContent: string | null
  // true = aberto via "Ver Relatório" no card de uma sessão já finalizada
  // (SearchPage.tsx), fora do wizard - "Fechar" só chama onExit, sem tocar
  // em nenhum store do wizard. false (padrão) = alcançado dentro do wizard
  // logo após montar o .tex (ReportStep.tsx) - mostra "Concluir e voltar
  // para Pesquisa" em vez de "Fechar", que reseta os stores do wizard.
  standalone?: boolean
  onExit?: () => void
}

export function ReportDocumentEditor({
  sessionId,
  initialTexContent,
  standalone = false,
  onExit,
}: ReportDocumentEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const [isLoadingDoc, setIsLoadingDoc] = useState(initialTexContent === null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [texText, setTexText] = useState(initialTexContent ?? '')
  const [lastCompiledText, setLastCompiledText] = useState<string | null>(null)
  const [pdfAvailable, setPdfAvailable] = useState(false)

  const [charts, setCharts] = useState<ReportChart[]>([])
  const [isPanelOpen, setIsPanelOpen] = useState(true)

  const [isCompiling, setIsCompiling] = useState(false)
  const [compileError, setCompileError] = useState<string | null>(null)
  const [compileSuccessMessage, setCompileSuccessMessage] = useState<string | null>(null)
  const [isLoadingPdf, setIsLoadingPdf] = useState(false)
  const successTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (successTimeoutRef.current) clearTimeout(successTimeoutRef.current)
    }
  }, [])

  const [showReassembleConfirm, setShowReassembleConfirm] = useState(false)
  const [isReassembling, setIsReassembling] = useState(false)

  // Só busca o estado do documento quando `initialTexContent` não veio
  // pronto (reabrindo uma sessão já finalizada) - logo após montar (.tex
  // recém gerado), o front já tem tudo em mãos e nunca foi compilado ainda.
  useEffect(() => {
    if (initialTexContent !== null) return
    let cancelled = false
    setIsLoadingDoc(true)
    getReportDocument(sessionId)
      .then((doc) => {
        if (cancelled) return
        setTexText(doc.texContent ?? '')
        setPdfAvailable(doc.pdfAvailable)
        // Se já existe PDF compilado, o `.tex` persistido é presumivelmente
        // o que gerou esse PDF (nenhuma edição pendente ainda nesta sessão
        // do browser) - "Compilar" só reabilita se o usuário editar a partir daqui.
        setLastCompiledText(doc.pdfAvailable ? doc.texContent : null)
      })
      .catch((err) => {
        console.error('Falha ao buscar o relatório da sessão:', err)
        if (!cancelled) setLoadError(errorMessage(err, 'Não foi possível carregar o relatório desta sessão.'))
      })
      .finally(() => {
        if (!cancelled) setIsLoadingDoc(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  useEffect(() => {
    let cancelled = false
    getReportCharts(sessionId)
      .then((list) => {
        if (!cancelled) setCharts(list)
      })
      .catch((err) => console.error('Falha ao buscar os gráficos do relatório:', err))
    return () => {
      cancelled = true
    }
  }, [sessionId])

  const canCompile = !isLoadingDoc && texText !== lastCompiledText

  function insertChartSnippet(chart: ReportChart) {
    const snippet = chartFigureSnippet(chart)
    const textarea = textareaRef.current
    if (!textarea) {
      setTexText((t) => t + snippet)
      return
    }
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    setTexText((t) => t.slice(0, start) + snippet + t.slice(end))
    requestAnimationFrame(() => {
      textarea.focus()
      const pos = start + snippet.length
      textarea.setSelectionRange(pos, pos)
    })
  }

  async function handleCompile() {
    setIsCompiling(true)
    setCompileError(null)
    setCompileSuccessMessage(null)
    try {
      const result = await compileReportPdf(sessionId, texText)
      if (!result.success) {
        setCompileError(result.log || 'Falha desconhecida na compilação do PDF.')
        return
      }
      setLastCompiledText(texText)
      setPdfAvailable(true)
      setCompileSuccessMessage('PDF compilado com sucesso!')
      if (successTimeoutRef.current) clearTimeout(successTimeoutRef.current)
      successTimeoutRef.current = setTimeout(() => setCompileSuccessMessage(null), 6000)
    } catch (err) {
      console.error('Falha ao compilar o PDF:', err)
      setCompileError(errorMessage(err, 'Falha ao compilar o PDF.'))
    } finally {
      setIsCompiling(false)
    }
  }

  async function handleViewPdf() {
    setIsLoadingPdf(true)
    try {
      const base64 = await getReportPdfBase64(sessionId)
      openReportPdf(base64)
    } catch (err) {
      console.error('Falha ao abrir o PDF compilado:', err)
      setCompileError(errorMessage(err, 'Não foi possível abrir o PDF.'))
    } finally {
      setIsLoadingPdf(false)
    }
  }

  async function handleConfirmReassemble() {
    setShowReassembleConfirm(false)
    setIsReassembling(true)
    setCompileError(null)
    try {
      const result = await reassembleReport(sessionId)
      setTexText(result.texContent)
      setLastCompiledText(null)
    } catch (err) {
      console.error('Falha ao remontar o relatório:', err)
      setCompileError(errorMessage(err, 'Não foi possível remontar o relatório.'))
    } finally {
      setIsReassembling(false)
    }
  }

  function handleExit() {
    if (standalone) {
      onExit?.()
      return
    }
    // Ponto de saída normal do wizard pra uma sessão já finalizada (ver
    // ReportGeneration.tsx - `completed=true` já foi salvo no momento de
    // montar o .tex) - mesmo reset que handleFinalize fazia antes em
    // OutrosSteps.tsx, só que sem salvar de novo (nada mudou no lado da
    // pesquisa desde então).
    useProspectingStore.getState().reset()
    useHistoryStore.getState().reset()
    useFormStore.getState().reset()
    useWorkflowStore.getState().setTab(TABS.SEARCH)
  }

  if (isLoadingDoc) {
    return <LoadingScreen message="Carregando o relatório..." />
  }

  if (loadError) {
    return <p className="text-sm text-red-600 font-medium">{loadError}</p>
  }

  return (
    <div className="w-full h-full flex flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 pb-3 mb-3">
        <h2 className="text-lg font-bold text-gray-900">Documento do Relatório</h2>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant={canCompile && !isCompiling ? 'primary' : 'secondary'}
            onClick={handleCompile}
            disabled={!canCompile || isCompiling}
            type="button"
          >
            {isCompiling ? 'Compilando...' : 'Compilar'}
          </Button>
          <Button
            size="sm"
            variant={pdfAvailable && !isLoadingPdf ? 'primary' : 'secondary'}
            onClick={handleViewPdf}
            disabled={!pdfAvailable || isLoadingPdf}
            type="button"
          >
            {isLoadingPdf ? 'Abrindo...' : 'Visualizar PDF'}
          </Button>
          <Tooltip label="Revisão automática de erros de compilação por IA - ainda não implementada." position="bottom">
            <span>
              <Button size="sm" variant="secondary" disabled type="button">
                Revisão de erros por IA
              </Button>
            </span>
          </Tooltip>
          <Tooltip
            label="Remonta o .tex do zero a partir das seções/gráficos/capa atuais - útil se um bug ou ajuste no relatório impedir a compilação. Substitui qualquer edição manual feita aqui."
            position="bottom"
          >
            <span>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setShowReassembleConfirm(true)}
                disabled={isReassembling}
                type="button"
              >
                {isReassembling ? 'Remontando...' : 'Remontar .tex'}
              </Button>
            </span>
          </Tooltip>
          <Button size="sm" variant="accent" onClick={handleExit} type="button">
            {standalone ? 'Fechar' : 'Concluir e voltar para Pesquisa'}
          </Button>
        </div>
      </div>

      <Modal
        isOpen={showReassembleConfirm}
        title="Remontar o documento?"
        message="Isso substitui o texto atual do .tex por uma versão remontada do zero (mesmos dados da capa, seções e gráficos atuais) - qualquer edição manual feita aqui desde a última montagem será perdida."
        confirmText="Remontar"
        cancelText="Cancelar"
        onConfirm={handleConfirmReassemble}
        onCancel={() => setShowReassembleConfirm(false)}
        isDangerous
      />

      {compileSuccessMessage && (
        <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-[#0f9448]/30 bg-[#0f9448]/10 px-3 py-2">
          <p className="text-sm font-semibold text-[#0f9448]">{compileSuccessMessage}</p>
          <button
            type="button"
            onClick={() => setCompileSuccessMessage(null)}
            className="shrink-0 text-[#0f9448] hover:text-[#0d843f]"
            aria-label="Fechar aviso"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {compileError && (
        <div className="mb-3 rounded-lg border border-red-300 bg-red-50 p-3">
          <div className="flex items-center justify-between gap-3 mb-1">
            <p className="text-sm font-semibold text-red-700">Falha na compilação do PDF</p>
            <button
              type="button"
              onClick={() => navigator.clipboard.writeText(compileError)}
              className="text-xs font-medium text-red-700 hover:text-red-900 underline shrink-0"
            >
              Copiar log completo
            </button>
          </div>
          <pre className="text-xs text-red-700 whitespace-pre-wrap max-h-96 overflow-y-auto">{compileError}</pre>
        </div>
      )}

      <div className="flex-1 flex gap-3 min-h-0">
        <div
          className={`shrink-0 border border-gray-200 rounded-lg bg-white overflow-hidden transition-all duration-200 ${
            isPanelOpen ? 'w-56' : 'w-9'
          }`}
        >
          <button
            type="button"
            onClick={() => setIsPanelOpen((v) => !v)}
            className="w-full flex items-center justify-center gap-1 py-2 text-gray-500 hover:text-gray-700 hover:bg-gray-50 border-b border-gray-200"
            aria-label={isPanelOpen ? 'Recolher imagens' : 'Expandir imagens'}
          >
            {isPanelOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
            {isPanelOpen && <span className="text-xs font-medium">Imagens</span>}
          </button>
          {isPanelOpen && (
            <div className="p-2 space-y-2 overflow-y-auto" style={{ maxHeight: 'calc(100% - 2.25rem)' }}>
              {charts.length === 0 && (
                <p className="text-xs text-gray-400 px-1">Nenhum gráfico disponível para esta sessão.</p>
              )}
              {charts.map((chart) => (
                <button
                  key={chart.filename}
                  type="button"
                  onClick={() => insertChartSnippet(chart)}
                  title={`Inserir ${chart.caption} no cursor`}
                  className="w-full text-left rounded-md border border-gray-200 hover:border-[#0f9448] transition-colors overflow-hidden"
                >
                  <img
                    src={`data:image/png;base64,${chart.imageBase64}`}
                    alt={chart.caption}
                    className="w-full block"
                  />
                  <p className="text-[10px] text-gray-600 px-1.5 py-1 truncate">{chart.caption}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="relative flex-1 min-h-[60vh]">
          <textarea
            ref={textareaRef}
            value={texText}
            onChange={(e) => setTexText(e.target.value)}
            spellCheck={false}
            disabled={isCompiling}
            className="w-full h-full rounded-lg border border-gray-300 bg-gray-50 p-4 font-mono text-xs text-gray-900 leading-relaxed focus:outline-none focus:border-[#0f9448] focus:ring-1 focus:ring-[#0f9448] resize-none disabled:opacity-70"
          />
          {isCompiling && (
            <div className="absolute inset-0 rounded-lg bg-white/70 backdrop-blur-[1px] flex items-center justify-center">
              <LoadingScreen message="Compilando PDF..." />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
