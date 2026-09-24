import { useEffect, useRef, useState } from 'react'
import { useFormStore } from '../stores/useFormStore'
import { useProspectingStore } from '../stores/useProspectingStore'
import { buildSaveSessionPayload, saveSession } from '../services/sessionInput'
import {
  generatePatentSCurve,
  generateArticleSCurve,
  getExistingChart,
  chartDataUrl,
  downloadReportChart,
} from '../services/report'
import type { GeneratedChart, SCurveFit } from '../services/report'
import { useAutoDismiss } from './useAutoDismiss'

export type SCurveKind = 'patent' | 'article'

// Quantos anos projetar à frente do último ano observado, por padrão -
// vira a parte tracejada do gráfico (ver project_s_curve em s_curve.py),
// desenhada só quando a curva convergiu com confiança o suficiente pra
// extrapolar. Só o valor inicial antes de qualquer geração/consulta - o
// usuário pode mudar (ver projectionYearsInput/applyProjectionYears
// abaixo), e o valor escolhido fica salvo (SessionChart.projection_years).
const DEFAULT_PROJECTION_YEARS = 5

// Gera a curva S a partir do
// patentsByYear/articlesByYear já devolvido pela busca final e mantém em
// cache - não regera a cada re-render, só
// quando o resultado da busca final muda de fato O PNG vem embutido em base64 na resposta
// Salva a sessão (mesmo payload de "Salvar progresso") sempre antes de
// pedir o gráfico - não só quando ainda não existe sessionId - porque o
// backend agora vincula o gráfico à linha de query final salva no banco
// (ver SessionChart/session_probe_query), que precisa estar em dia. Isso é
// seguro mesmo numa sessão já existente porque montar o .tex (ver
// ReportGeneration.tsx) já tira o usuário do wizard - nunca dá pra chegar
// aqui com uma sessão já concluída pra reabrir sem querer.
export function useFinalSCurve(kind: SCurveKind, yearlyByYear: Record<string, number> | null) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chart, setChart] = useState<GeneratedChart | null>(null)
  const [fit, setFit] = useState<SCurveFit | null>(null)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  // O que o usuário está digitando no campo "Anos para projetar" - separado
  // de `chart` de propósito: mudar esse número não regera nada sozinho, só
  // quando o botão "Atualizar" chama applyProjectionYears (ver abaixo).
  const [projectionYearsInput, setProjectionYearsInput] = useState(DEFAULT_PROJECTION_YEARS)
  const [isApplyingProjection, setIsApplyingProjection] = useState(false)

  useAutoDismiss(error, () => setError(null))
  useAutoDismiss(downloadError, () => setDownloadError(null))

  const generatedForRef = useRef<string | null>(null)

  const requestIdRef = useRef(0)
  const hasData = !!yearlyByYear && Object.keys(yearlyByYear).length > 0
  const signature = hasData ? `${kind}:${JSON.stringify(yearlyByYear)}` : null
  const fonte = kind === 'patent' ? 'ops' : 'scopus'

  useEffect(() => {
    if (!signature || !yearlyByYear) return
    if (generatedForRef.current === signature) return

    const requestId = ++requestIdRef.current
    generatedForRef.current = signature
    setIsLoading(true)
    setError(null)

    async function run() {
      try {
        const formState = useFormStore.getState()
        const { step, substep } = useProspectingStore.getState()
        const payload = buildSaveSessionPayload(formState, false, step, substep)
        const saveResult = await saveSession(formState.sessionId, formState.sessionName, payload)
        useFormStore.getState().setSessionId(saveResult.session_id, saveResult.session_public_id)
        useFormStore.getState().setLastSavedSignature(JSON.stringify(payload))
        const sessionId = saveResult.session_id

        // Se a query final dessa fonte já tem uma curva S salva (ver
        // SessionChart no backend), mostra ela em vez de gerar/subir outra
        // à toa - o save acima garante que essa checagem reflete o estado
        // atual (trocar de variante já invalida/apaga o gráfico salvo, ver
        // session_persistence.py).
        const existing = await getExistingChart(sessionId, fonte, 's_curve', true)
        if (requestIdRef.current !== requestId) return
        if (existing) {
          setChart(existing)
          setFit(null)
          setProjectionYearsInput(existing.projectionYears ?? DEFAULT_PROJECTION_YEARS)
          return
        }

        const result =
          kind === 'patent'
            ? await generatePatentSCurve(sessionId, yearlyByYear!, DEFAULT_PROJECTION_YEARS)
            : await generateArticleSCurve(sessionId, yearlyByYear!, DEFAULT_PROJECTION_YEARS)
        if (requestIdRef.current !== requestId) return
        setChart(result.chart)
        setFit(result.fit)
        setProjectionYearsInput(result.chart?.projectionYears ?? DEFAULT_PROJECTION_YEARS)
      } catch (err) {
        if (requestIdRef.current !== requestId) return
        console.error(`Falha ao gerar a curva S de ${kind === 'patent' ? 'patentes' : 'artigos'}:`, err)
        generatedForRef.current = null
        setError('Não foi possível gerar o gráfico da curva S. Tente novamente.')
      } finally {
        if (requestIdRef.current === requestId) setIsLoading(false)
      }
    }

    run()
  }, [signature, yearlyByYear, kind, fonte])

  // Regera a curva S com o valor de `projectionYearsInput` atual - chamado
  // explicitamente pelo botão "Atualizar" (não pelo efeito automático
  // acima), então ignora getExistingChart de propósito: aqui o usuário está
  // pedindo uma mudança, não checando se já existe uma versão salva. O
  // gráfico novo sobrescreve o mesmo objeto/linha de sempre (mesma chave
  // determinística em ReportService._upload_chart), então fica salvo com o
  // valor novo.
  async function applyProjectionYears() {
    if (!yearlyByYear) return
    const sessionId = useFormStore.getState().sessionId
    if (sessionId === null) return

    const requestId = ++requestIdRef.current
    setIsApplyingProjection(true)
    setError(null)
    try {
      const result =
        kind === 'patent'
          ? await generatePatentSCurve(sessionId, yearlyByYear, projectionYearsInput)
          : await generateArticleSCurve(sessionId, yearlyByYear, projectionYearsInput)
      if (requestIdRef.current !== requestId) return
      setChart(result.chart)
      setFit(result.fit)
    } catch (err) {
      if (requestIdRef.current !== requestId) return
      console.error(
        `Falha ao atualizar a projeção da curva S de ${kind === 'patent' ? 'patentes' : 'artigos'}:`,
        err
      )
      setError('Não foi possível atualizar a projeção. Tente novamente.')
    } finally {
      if (requestIdRef.current === requestId) setIsApplyingProjection(false)
    }
  }

  function handleDownload() {
    if (!chart) return
    setDownloadError(null)
    try {
      downloadReportChart(chart)
    } catch (err) {
      console.error('Falha ao baixar o gráfico da curva S:', err)
      setDownloadError('Não foi possível baixar o gráfico. Tente novamente.')
    }
  }

  return {
    hasData,
    isLoading,
    error,
    chart,
    fit,
    chartUrl: chart ? chartDataUrl(chart) : null,
    downloadError,
    handleDownload,
    projectionYearsInput,
    setProjectionYearsInput,
    applyProjectionYears,
    isApplyingProjection,
  }
}
