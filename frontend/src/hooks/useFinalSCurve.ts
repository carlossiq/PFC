import { useEffect, useRef, useState } from 'react'
import { useFormStore } from '../stores/useFormStore'
import { buildSaveSessionPayload, saveSession } from '../services/sessionInput'
import { generatePatentSCurve, generateArticleSCurve, chartDataUrl, downloadReportChart } from '../services/report'
import type { GeneratedChart, SCurveFit } from '../services/report'
import { useAutoDismiss } from './useAutoDismiss'

export type SCurveKind = 'patent' | 'article'

// Quantos anos projetar à frente do último ano observado, por padrão -
// vira a parte tracejada do gráfico (ver project_s_curve em s_curve.py),
// desenhada só quando a curva convergiu com confiança o suficiente pra
// extrapolar.
const DEFAULT_PROJECTION_YEARS = 5

function lastObservedYear(yearlyByYear: Record<string, number>): number {
  return Math.max(...Object.keys(yearlyByYear).map(Number))
}

// Gera a curva S a partir do
// patentsByYear/articlesByYear já devolvido pela busca final e mantém em
// cache - não regera a cada re-render, só
// quando o resultado da busca final muda de fato O PNG vem embutido em base64 na resposta
// A rota de geração ainda exige que a sessão já exista no banco (ver
// PatentSCurveRequest/ArticleSCurveRequest em schemas/report.py); se o
// usuário ainda não salvou/finalizou nada, cria a sessão agora (mesmo
// payload de "Salvar progresso") só pra obter o id.
export function useFinalSCurve(kind: SCurveKind, yearlyByYear: Record<string, number> | null) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chart, setChart] = useState<GeneratedChart | null>(null)
  const [fit, setFit] = useState<SCurveFit | null>(null)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  useAutoDismiss(error, () => setError(null))
  useAutoDismiss(downloadError, () => setDownloadError(null))

  const generatedForRef = useRef<string | null>(null)
  // Contador de requisição (não um boolean `cancelled` capturado por
  // closure) - em StrictMode (dev), o React dispara este efeito 2x de
  // propósito (monta → limpa → monta de novo) pra pegar efeitos mal
  // escritos. Um `cancelled` setado na função de limpeza da 1ª execução
  // cancelaria PARA SEMPRE a única chamada que de fato rodou, enquanto a 2ª
  // execução (a que fica) já veria `generatedForRef` preenchido e desistiria
  // sem tentar de novo - travando o spinner pra sempre. Comparar contra o
  // valor ATUAL do ref (não uma cópia congelada) evita isso. Mesmo padrão
  // de requestIdRef em useProbeQuerySection.ts.
  const requestIdRef = useRef(0)
  const hasData = !!yearlyByYear && Object.keys(yearlyByYear).length > 0
  const signature = hasData ? `${kind}:${JSON.stringify(yearlyByYear)}` : null

  useEffect(() => {
    if (!signature || !yearlyByYear) return
    if (generatedForRef.current === signature) return

    const requestId = ++requestIdRef.current
    generatedForRef.current = signature
    setIsLoading(true)
    setError(null)

    async function run() {
      try {
        let sessionId = useFormStore.getState().sessionId
        if (sessionId === null) {
          const formState = useFormStore.getState()
          const payload = buildSaveSessionPayload(formState, false)
          const result = await saveSession(null, formState.sessionName, payload)
          useFormStore.getState().setSessionId(result.session_id, result.session_public_id)
          sessionId = result.session_id
        }

        const projectionEndYear = lastObservedYear(yearlyByYear!) + DEFAULT_PROJECTION_YEARS
        const result =
          kind === 'patent'
            ? await generatePatentSCurve(sessionId, yearlyByYear!, projectionEndYear)
            : await generateArticleSCurve(sessionId, yearlyByYear!, projectionEndYear)
        if (requestIdRef.current !== requestId) return
        setChart(result.chart)
        setFit(result.fit)
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
  }, [signature, yearlyByYear, kind])

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
  }
}
