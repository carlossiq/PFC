import { useEffect, useRef, useState } from 'react'
import { ChevronLeft, Download, ExternalLink, FilePlus2, Loader2, Plus, Trash2, X } from 'lucide-react'
import { Button } from '../Button'
import { Tooltip } from '../Tooltip'
import { LoadingScreen } from '../LoadingScreen'
import { Modal } from '../Modal'
import { useFormStore } from '../../stores/useFormStore'
import { useProspectingStore } from '../../stores/useProspectingStore'
import { useHistoryStore } from '../../stores/useHistoryStore'
import { useWorkflowStore } from '../../stores/useWorkflowStore'
import { useReportImagesPanelStore } from '../../stores/useReportImagesPanelStore'
import { TABS } from '../../constants/tabs'
import {
  compileReportPdf,
  deleteReportAttachment,
  downloadReportBundle,
  downloadReportImage,
  getReportCharts,
  getReportDocument,
  getReportPdfBase64,
  openReportImage,
  openReportPdf,
  reassembleReport,
  reviewReportTex,
  uploadReportAttachment,
  type ReportChart,
} from '../../services/report'
import { applyEdits, shiftOffset, type TextEdit } from '../../utils/reviewApply'
import { ReviewPanel, type ReviewIssueItem, type ReviewSuggestionItem } from './ReviewPanel'

function errorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
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

// Anexo não tem título próprio (o nome do arquivo não serve de título de
// figura) - entra um texto provisório pro usuário trocar no próprio .tex.
const ATTACHMENT_CAPTION_PLACEHOLDER = 'Título da figura'

// Mesmo formato das figuras montadas pelo template (título "Figura N:"
// acima, "Fonte: O autor." abaixo, centralizada) - usa o macro \figura
// quando o .tex já o define (montado com o template atual); documentos
// montados antes dele ganham o bloco equivalente por extenso.
function chartFigureSnippet(chart: ReportChart, texText: string): string {
  const caption = escapeLatex(chart.origin === 'attachment' ? ATTACHMENT_CAPTION_PLACEHOLDER : chart.caption)
  // Heatmaps (CPC/áreas de estudo) são Quadro no REPTEC, não Figura - ver
  // FIGURE_SPECS em app/core/services/report_figures.py.
  if (chart.chartType === 'top10_heatmap' && texText.includes('\\newcommand{\\quadroimg}')) {
    return `\n\\quadroimg{${caption}}{${chart.filename}}\n`
  }
  if (texText.includes('\\newcommand{\\figura}')) {
    return `\n\\figura{${caption}}{${chart.filename}}\n`
  }
  return `\n\\begin{figure}[h]\n  \\centering\n  \\caption{${caption}}\n  \\includegraphics[width=0.85\\textwidth]{${chart.filename}}\\par\n  {\\small Fonte: O autor.}\n\\end{figure}\n`
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
  // Rastreia se o textarea já recebeu foco de verdade nesta visita - sem
  // isso, clicar numa miniatura de gráfico ANTES de clicar no textarea usa
  // selectionStart/selectionEnd = 0 (valor padrão de um textarea nunca
  // focado), inserindo o \begin{figure} antes até do \documentclass e
  // quebrando a compilação ("Environment figure undefined" - o pdflatex
  // nem chega a processar a classe do documento). Ver insertChartSnippet.
  const hasFocusedTextareaRef = useRef(false)

  const [isLoadingDoc, setIsLoadingDoc] = useState(initialTexContent === null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [texText, setTexText] = useState(initialTexContent ?? '')
  const [lastCompiledText, setLastCompiledText] = useState<string | null>(null)
  const [pdfAvailable, setPdfAvailable] = useState(false)

  const [charts, setCharts] = useState<ReportChart[]>([])
  const isPanelOpen = useReportImagesPanelStore((s) => s.isOpen)
  const setIsPanelOpen = useReportImagesPanelStore((s) => s.setOpen)

  // Avisa a Sidebar que o editor está na tela (mostra o botão de imagem só
  // enquanto isso for verdade).
  useEffect(() => {
    const { setEditorMounted } = useReportImagesPanelStore.getState()
    setEditorMounted(true)
    return () => setEditorMounted(false)
  }, [])
  // Miniatura com o menu de ações aberto (pelo filename) - null = nenhum.
  const [menuFor, setMenuFor] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<ReportChart | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [imageError, setImageError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  // Fecha o menu de ações ao clicar em qualquer lugar fora do painel.
  useEffect(() => {
    if (menuFor === null) return
    function handleMouseDown(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) setMenuFor(null)
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [menuFor])

  const [isCompiling, setIsCompiling] = useState(false)
  const [compileError, setCompileError] = useState<string | null>(null)
  // Revisão do documento (ver ReviewPanel.tsx / report_review.py).
  const [isReviewOpen, setIsReviewOpen] = useState(false)
  const [reviewing, setReviewing] = useState<'basic' | 'ai' | null>(null)
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [reviewIssues, setReviewIssues] = useState<ReviewIssueItem[]>([])
  const [reviewSuggestions, setReviewSuggestions] = useState<ReviewSuggestionItem[]>([])
  const [reviewScope, setReviewScope] = useState<string[]>([])
  const [reviewWarnings, setReviewWarnings] = useState<string[]>([])
  const [reviewStaleIds, setReviewStaleIds] = useState<Set<string>>(() => new Set())
  const [hasAiReview, setHasAiReview] = useState(false)
  // Muda a cada revisão concluída - recria o painel (key), zerando as
  // seleções feitas sobre as sugestões da rodada anterior.
  const [reviewRun, setReviewRun] = useState(0)
  const [compileSuccessMessage, setCompileSuccessMessage] = useState<string | null>(null)
  const [isLoadingPdf, setIsLoadingPdf] = useState(false)
  const [isDownloadingBundle, setIsDownloadingBundle] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
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

  // Ponto de inserção seguro quando não há uma posição de cursor real
  // (textarea nunca focado) - antes de `\end{document}`, pra cair dentro
  // do corpo do documento (o final puro e simples do arquivo ficaria
  // depois de `\end{document}`, onde o LaTeX ignora tudo silenciosamente
  // - o gráfico nunca apareceria no PDF, sem nenhum erro de compilação
  // pra avisar).
  function fallbackInsertionIndex(t: string): number {
    const endDocIdx = t.lastIndexOf('\\end{document}')
    return endDocIdx === -1 ? t.length : endDocIdx
  }

  // Foca e posiciona o cursor em `pos` SEM mexer na rolagem: trocar o
  // `value` do textarea (re-render do React) joga o cursor pro fim do texto,
  // e um focus() comum rola até ele - a tela pulava pro fim do documento a
  // cada imagem inserida. preventScroll + restaurar o scrollTop salvo antes
  // da troca mantém o usuário exatamente onde estava.
  function placeCaretKeepingScroll(textarea: HTMLTextAreaElement, pos: number, scrollTop: number) {
    requestAnimationFrame(() => {
      textarea.focus({ preventScroll: true })
      textarea.setSelectionRange(pos, pos)
      textarea.scrollTop = scrollTop
    })
  }

  function insertChartSnippet(chart: ReportChart) {
    const snippet = chartFigureSnippet(chart, texText)
    const textarea = textareaRef.current
    const scrollTop = textarea?.scrollTop ?? 0
    if (!textarea || !hasFocusedTextareaRef.current) {
      const at = fallbackInsertionIndex(texText)
      setTexText((t) => t.slice(0, at) + snippet + t.slice(at))
      // Cursor logo após o snippet inserido, pra que a PRÓXIMA inserção (ou
      // digitação) já use a posição real do cursor em vez de cair de novo
      // no fallback.
      if (textarea) placeCaretKeepingScroll(textarea, at + snippet.length, scrollTop)
      return
    }
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    setTexText((t) => t.slice(0, start) + snippet + t.slice(end))
    placeCaretKeepingScroll(textarea, start + snippet.length, scrollTop)
  }

  // --- Revisão (LaTeX + ortografia/acentuação/concordância) -------------

  async function runReview(includeAi: boolean) {
    const snapshot = texText
    setReviewing(includeAi ? 'ai' : 'basic')
    setIsReviewOpen(true)
    setReviewError(null)
    try {
      const result = await reviewReportTex(sessionId, snapshot, { compileLog: compileError, includeAi })
      setReviewIssues(
        result.latexIssues.map((issue, i) => ({
          ...issue,
          id: `l-${i}`,
          original: issue.offset === null ? '' : snapshot.slice(issue.offset, issue.offset + issue.length),
        }))
      )
      setReviewSuggestions(result.suggestions.map((s, i) => ({ ...s, id: `s-${i}` })))
      setReviewScope(result.scopeSections)
      setReviewWarnings(result.warnings)
      setReviewStaleIds(new Set())
      setHasAiReview(includeAi)
      setReviewRun((n) => n + 1)
    } catch (err) {
      console.error('Falha na revisão do documento:', err)
      setReviewError(errorMessage(err, 'Não foi possível revisar o documento.'))
    } finally {
      setReviewing(null)
    }
  }

  // Aplica as correções aprovadas SEM mexer na rolagem, remove as aplicadas
  // do painel e reposiciona as que sobraram (as posições mudam quando uma
  // correção antes delas troca o tamanho do texto). Correção cujo trecho
  // mudou de lugar desde a revisão não é aplicada - fica "desatualizada".
  function applyReviewEdits(edits: TextEdit[]) {
    const textarea = textareaRef.current
    const scrollTop = textarea?.scrollTop ?? 0
    const result = applyEdits(texText, edits)
    const applied = new Set(result.applied)
    setTexText(result.text)
    setReviewSuggestions((list) =>
      list.filter((s) => !applied.has(s.id)).map((s) => ({ ...s, offset: shiftOffset(s.offset, result.shifts) }))
    )
    setReviewIssues((list) =>
      list
        .filter((issue) => !applied.has(issue.id))
        .map((issue) => (issue.offset === null ? issue : { ...issue, offset: shiftOffset(issue.offset, result.shifts) }))
    )
    if (result.stale.length > 0) setReviewStaleIds((current) => new Set([...current, ...result.stale]))
    if (textarea) {
      requestAnimationFrame(() => {
        textarea.scrollTop = scrollTop
      })
    }
  }

  // Seleciona o trecho no .tex e rola até ele.
  function goToOffset(offset: number, length: number) {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.focus()
    textarea.setSelectionRange(offset, offset + length)
    // Rola pra que o trecho fique mais ou menos no meio da área visível.
    const lineHeight = parseFloat(getComputedStyle(textarea).lineHeight) || 18
    const line = texText.slice(0, offset).split('\n').length - 1
    textarea.scrollTop = Math.max(0, line * lineHeight - textarea.clientHeight / 2)
  }

  async function handleUploadAttachment(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    // Limpa o input já - sem isso, escolher o MESMO arquivo de novo (ex.:
    // depois de excluí-lo) não dispara onChange.
    e.target.value = ''
    if (!file) return
    setIsUploading(true)
    setImageError(null)
    try {
      const attachment = await uploadReportAttachment(sessionId, file)
      setCharts((list) => [...list, attachment])
    } catch (err) {
      console.error('Falha ao enviar anexo:', err)
      setImageError(errorMessage(err, 'Não foi possível enviar a imagem.'))
    } finally {
      setIsUploading(false)
    }
  }

  async function handleConfirmDelete() {
    const chart = pendingDelete
    setPendingDelete(null)
    if (!chart) return
    setImageError(null)
    try {
      await deleteReportAttachment(sessionId, chart.filename)
      setCharts((list) => list.filter((c) => c.filename !== chart.filename))
    } catch (err) {
      console.error('Falha ao excluir anexo:', err)
      setImageError(errorMessage(err, 'Não foi possível excluir a imagem.'))
    }
  }

  function renderImageCard(chart: ReportChart) {
    const isMenuOpen = menuFor === chart.filename
    const canDelete = chart.origin === 'attachment'
    const menuItemClass =
      'w-full flex items-center gap-1.5 px-2 py-1.5 text-left text-[11px] text-gray-700 hover:bg-gray-100 disabled:text-gray-300 disabled:hover:bg-transparent disabled:cursor-not-allowed'
    return (
      <div key={chart.filename} className="relative">
        <button
          type="button"
          onClick={() => setMenuFor(isMenuOpen ? null : chart.filename)}
          title={chart.caption}
          className={`w-full text-left rounded-md border transition-colors overflow-hidden ${
            isMenuOpen ? 'border-[#0f9448]' : 'border-gray-200 hover:border-[#0f9448]'
          }`}
        >
          <img src={`data:image/png;base64,${chart.imageBase64}`} alt={chart.caption} className="w-full block" />
          <p className="text-[10px] text-gray-600 px-1.5 py-1 truncate">{chart.caption}</p>
        </button>
        {isMenuOpen && (
          <div className="absolute left-1 right-1 top-full z-10 mt-1 rounded-md border border-gray-200 bg-white shadow-lg py-1">
            <button
              type="button"
              className={menuItemClass}
              onClick={() => {
                setMenuFor(null)
                insertChartSnippet(chart)
              }}
            >
              <FilePlus2 size={12} /> Adicionar ao .tex
            </button>
            <button
              type="button"
              className={menuItemClass}
              onClick={() => {
                setMenuFor(null)
                openReportImage(chart)
              }}
            >
              <ExternalLink size={12} /> Abrir em nova aba
            </button>
            <button
              type="button"
              className={menuItemClass}
              onClick={() => {
                setMenuFor(null)
                downloadReportImage(chart)
              }}
            >
              <Download size={12} /> Download
            </button>
            <button
              type="button"
              className={`${menuItemClass} ${canDelete ? 'text-red-600 hover:bg-red-50' : ''}`}
              disabled={!canDelete}
              title={canDelete ? undefined : 'Gráficos gerados pelo sistema não podem ser excluídos.'}
              onClick={() => {
                setMenuFor(null)
                setPendingDelete(chart)
              }}
            >
              <Trash2 size={12} /> Excluir
            </button>
          </div>
        )}
      </div>
    )
  }

  const generatedCharts = charts.filter((c) => c.origin === 'generated')
  const attachments = charts.filter((c) => c.origin === 'attachment')

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

  async function handleDownloadBundle() {
    setIsDownloadingBundle(true)
    setDownloadError(null)
    try {
      await downloadReportBundle(sessionId, texText)
    } catch (err) {
      console.error('Falha ao baixar o .zip do relatório:', err)
      setDownloadError(errorMessage(err, 'Não foi possível baixar o .zip do relatório.'))
    } finally {
      setIsDownloadingBundle(false)
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
          <Tooltip label="Baixar .zip com o .tex atual e as imagens usadas no relatório" position="bottom">
            <button
              type="button"
              onClick={handleDownloadBundle}
              disabled={isDownloadingBundle || isLoadingDoc}
              aria-label="Baixar .zip com o .tex e as imagens"
              className="h-8 w-8 flex items-center justify-center rounded-md border border-gray-300 text-gray-600 hover:border-[#0f9448] hover:text-[#0f9448] disabled:opacity-50 disabled:hover:border-gray-300 disabled:hover:text-gray-600"
            >
              {isDownloadingBundle ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            </button>
          </Tooltip>
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
          <Tooltip
            label="Verifica problemas de LaTeX no documento e sugere correções de ortografia, acentuação e concordância nas seções geradas por IA e nos trechos que você editou. Nada é alterado sem sua aprovação."
            position="bottom"
          >
            <span>
              <Button
                size="sm"
                variant={isReviewOpen ? 'primary' : 'secondary'}
                onClick={() => runReview(false)}
                disabled={reviewing !== null || isLoadingDoc}
                type="button"
              >
                {reviewing ? 'Revisando...' : 'Revisão'}
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
        isOpen={pendingDelete !== null}
        title="Excluir imagem?"
        message={
          pendingDelete && texText.includes(pendingDelete.filename)
            ? `"${pendingDelete.filename}" ainda é usada no .tex - remova a referência do documento antes de compilar, senão a compilação vai falhar (arquivo não encontrado).`
            : `"${pendingDelete?.filename ?? ''}" será excluída permanentemente.`
        }
        confirmText="Excluir"
        cancelText="Cancelar"
        onConfirm={handleConfirmDelete}
        onCancel={() => setPendingDelete(null)}
        isDangerous
      />

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

      {downloadError && (
        <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-red-300 bg-red-50 px-3 py-2">
          <p className="text-sm text-red-700">{downloadError}</p>
          <button
            type="button"
            onClick={() => setDownloadError(null)}
            className="shrink-0 text-red-700 hover:text-red-900"
            aria-label="Fechar aviso"
          >
            <X size={14} />
          </button>
        </div>
      )}

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
        {/* Fechado = some por completo (sem faixa recolhida) - reabre pelo
            botão de imagem da Sidebar (ReportImagesToggleButton.tsx). */}
        {isPanelOpen && (
          <div ref={panelRef} className="shrink-0 w-56 border border-gray-200 rounded-lg bg-white overflow-hidden">
            <button
              type="button"
              onClick={() => setIsPanelOpen(false)}
              className="w-full flex items-center justify-center gap-1 py-2 text-gray-500 hover:text-gray-700 hover:bg-gray-50 border-b border-gray-200"
              aria-label="Recolher imagens"
            >
              <ChevronLeft size={16} />
              <span className="text-xs font-medium">Imagens</span>
            </button>
            <div className="p-2 space-y-2 overflow-y-auto" style={{ maxHeight: 'calc(100% - 2.25rem)' }}>
              {imageError && (
                <div className="flex items-start justify-between gap-1 rounded-md border border-red-200 bg-red-50 px-2 py-1">
                  <p className="text-[10px] text-red-700">{imageError}</p>
                  <button
                    type="button"
                    onClick={() => setImageError(null)}
                    className="shrink-0 text-red-700"
                    aria-label="Fechar aviso"
                  >
                    <X size={10} />
                  </button>
                </div>
              )}

              <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 px-1">Gráficos</p>
              {generatedCharts.length === 0 && (
                <p className="text-xs text-gray-400 px-1">Nenhum gráfico disponível para esta sessão.</p>
              )}
              {generatedCharts.map(renderImageCard)}

              <div className="flex items-center justify-between border-t border-gray-200 pt-2 px-1">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Anexos</p>
                <Tooltip label="Adicionar imagem (PNG ou JPG)" position="right">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                    className="w-5 h-5 flex items-center justify-center rounded-full border border-gray-300 text-gray-600 hover:border-[#0f9448] hover:text-[#0f9448] disabled:opacity-50"
                    aria-label="Adicionar imagem"
                  >
                    <Plus size={12} />
                  </button>
                </Tooltip>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg"
                  className="hidden"
                  onChange={handleUploadAttachment}
                />
              </div>
              {isUploading && <p className="text-xs text-gray-400 px-1">Enviando...</p>}
              {!isUploading && attachments.length === 0 && <p className="text-xs text-gray-400 px-1">Nenhum anexo.</p>}
              {attachments.map(renderImageCard)}
            </div>
          </div>
        )}

        <div className="relative flex-1 min-h-[60vh]">
          <textarea
            ref={textareaRef}
            value={texText}
            onChange={(e) => setTexText(e.target.value)}
            onFocus={() => {
              hasFocusedTextareaRef.current = true
            }}
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

        {isReviewOpen && (
          <ReviewPanel
            key={reviewRun}
            issues={reviewIssues}
            suggestions={reviewSuggestions}
            scopeSections={reviewScope}
            warnings={reviewError ? [reviewError, ...reviewWarnings] : reviewWarnings}
            staleIds={reviewStaleIds}
            hasAiResults={hasAiReview}
            isReviewing={reviewing === 'basic'}
            isReviewingAi={reviewing === 'ai'}
            onClose={() => setIsReviewOpen(false)}
            onRerun={() => runReview(false)}
            onRunAi={() => runReview(true)}
            onGoTo={goToOffset}
            onApply={applyReviewEdits}
          />
        )}
      </div>
    </div>
  )
}
