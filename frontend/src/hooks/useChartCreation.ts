import { useEffect, useRef, useState } from 'react'
import { useFormStore } from '../stores/useFormStore'
import { buildSaveSessionPayload, saveSession } from '../services/sessionInput'
import { runPatentStatisticalInference, runArticleStatisticalInference } from '../services/inference'
import {
  generateTopEntitiesChart,
  generateTop10Heatmap,
  generateYearlyVolumeChart,
  getExistingChart,
} from '../services/report'
import type { GeneratedChart } from '../services/report'

type Fonte = 'ops' | 'scopus'

// Gera (ou reaproveita, se já existir - ver getExistingChart) um gráfico
// pra uma (fonte, chart_type) - erro aqui é sempre não-bloqueante (mesma
// filosofia "melhor esforço" do resto do report): loga e segue, nunca
// impede os outros gráficos/estágios de rodar.
async function withExistingCheck(
  sessionId: number,
  fonte: Fonte,
  chartType: string,
  generate: () => Promise<GeneratedChart | null>
): Promise<GeneratedChart | null> {
  try {
    const existing = await getExistingChart(sessionId, fonte, chartType)
    if (existing) return existing
  } catch (err) {
    console.warn(`Falha ao checar gráfico existente ${chartType} (${fonte}), gerando de novo:`, err)
  }
  try {
    return await generate()
  } catch (err) {
    console.error(`Falha ao gerar gráfico ${chartType} (${fonte}):`, err)
    return null
  }
}

// Orquestra a "Criação de Gráficos" (substep 1 de Exploração Final, ver
// steps.ts): roda a inferência estatística (StatisticalInferenceService,
// via services/inference.ts) sobre o compilado da busca final e, com o
// resultado, gera os 3 pares de gráfico que não dependem de documentos
// persistidos no banco (top depositantes/instituições, CPC/área de estudo,
// histórico de patentes/artigos) - a curva S (gerada em FinalResults.tsx,
// substep anterior) já cobre o 4º par.
//
// Dedupe por assinatura (mesmo princípio de useFinalSCurve.ts): só roda de
// novo se os resultados da busca final mudarem (ex.: usuário voltou e
// regenerou a query final) - simplesmente reabrir esta tela não repete o
// trabalho nem reenvia gráficos idênticos pro MinIO.
export function useChartCreation(enabled: boolean) {
  const [stageMessage, setStageMessage] = useState('Preparando...')
  const [isDone, setIsDone] = useState(false)
  const [fatalError, setFatalError] = useState<string | null>(null)

  const { input, step4PatentQuery, step4ArticleQuery, step4PatentResults, step4ArticleResults } = useFormStore()

  const hasPatent = !!step4PatentQuery?.query && !!step4PatentResults && step4PatentResults.resultsCount > 0
  const hasArticle = !!step4ArticleQuery?.query && !!step4ArticleResults && step4ArticleResults.resultsCount > 0
  const signature = `${hasPatent ? JSON.stringify(step4PatentResults) : ''}|${hasArticle ? JSON.stringify(step4ArticleResults) : ''}`

  const doneForRef = useRef<string | null>(null)
  // Marca "já disparado pra essa assinatura" de forma SÍNCRONA, antes de
  // chamar run() - ao contrário de doneForRef (só marcado quando run()
  // termina com sucesso), evita que as duas invocações do efeito que o
  // React 18 StrictMode dispara de propósito em dev (mount->unmount->mount,
  // pra achar bug de limpeza) dupliquem o primeiro await dentro de run()
  // (saveSession) - foi exatamente esse race que gerou o
  // UniqueViolationError em session_probe_query (duas linhas concorrentes
  // pra (session_id, fonte, tipo) igual). Mesmo padrão já usado em
  // useFinalSCurve.ts (generatedForRef, marcado antes do run()).
  const startedForRef = useRef<string | null>(null)
  const requestIdRef = useRef(0)

  async function run() {
    const requestId = ++requestIdRef.current
    setFatalError(null)
    setIsDone(false)

    try {
      setStageMessage('Salvando progresso da sessão...')
      const formState = useFormStore.getState()
      const payload = buildSaveSessionPayload(formState, false)
      const saveResult = await saveSession(formState.sessionId, formState.sessionName, payload)
      useFormStore.getState().setSessionId(saveResult.session_id, saveResult.session_public_id)
      if (requestIdRef.current !== requestId) return
      const sessionId = saveResult.session_id

      setStageMessage('Analisando amostra estatística (patentes e artigos)...')
      const [patentOutcome, articleOutcome] = await Promise.allSettled([
        hasPatent
          ? runPatentStatisticalInference(step4PatentQuery!.query!, step4PatentResults!, input.theme)
          : Promise.resolve(null),
        hasArticle
          ? runArticleStatisticalInference(step4ArticleQuery!.query!, step4ArticleResults!, input.theme)
          : Promise.resolve(null),
      ])
      if (requestIdRef.current !== requestId) return
      if (patentOutcome.status === 'rejected') {
        console.error('Falha na inferência estatística de patentes:', patentOutcome.reason)
      }
      if (articleOutcome.status === 'rejected') {
        console.error('Falha na inferência estatística de artigos:', articleOutcome.reason)
      }
      const patentInference = patentOutcome.status === 'fulfilled' ? patentOutcome.value : null
      const articleInference = articleOutcome.status === 'fulfilled' ? articleOutcome.value : null

      setStageMessage('Gerando gráficos de top depositantes e instituições...')
      await Promise.allSettled([
        patentInference?.depositants
          ? withExistingCheck(sessionId, 'ops', 'top_depositants', () =>
              generateTopEntitiesChart(
                sessionId,
                patentInference.depositants!.counts,
                'Top Depositantes',
                'patent',
                'top_depositants'
              )
            )
          : Promise.resolve(null),
        articleInference?.institutions
          ? withExistingCheck(sessionId, 'scopus', 'top_institutions', () =>
              generateTopEntitiesChart(
                sessionId,
                articleInference.institutions!.counts,
                'Top Instituições',
                'article',
                'top_institutions'
              )
            )
          : Promise.resolve(null),
      ])
      if (requestIdRef.current !== requestId) return

      setStageMessage('Gerando gráficos de distribuição (CPC e área de estudo)...')
      await Promise.allSettled([
        patentInference?.cpc
          ? withExistingCheck(sessionId, 'ops', 'top10_heatmap', () =>
              generateTop10Heatmap(sessionId, patentInference.cpc!.counts, 'Distribuição por CPC', 'patent')
            )
          : Promise.resolve(null),
        articleInference?.areaOfStudy
          ? withExistingCheck(sessionId, 'scopus', 'top10_heatmap', () =>
              generateTop10Heatmap(
                sessionId,
                articleInference.areaOfStudy!.counts,
                'Distribuição por Área de Estudo',
                'article'
              )
            )
          : Promise.resolve(null),
      ])
      if (requestIdRef.current !== requestId) return

      setStageMessage('Gerando gráficos de histórico (depósito de patentes e publicação de artigos)...')
      await Promise.allSettled([
        patentInference?.patentsByYear
          ? withExistingCheck(sessionId, 'ops', 'yearly_volume', () =>
              generateYearlyVolumeChart(sessionId, 'patent', patentInference.patentsByYear!)
            )
          : Promise.resolve(null),
        articleInference?.articlesByYear
          ? withExistingCheck(sessionId, 'scopus', 'yearly_volume', () =>
              generateYearlyVolumeChart(sessionId, 'article', articleInference.articlesByYear!)
            )
          : Promise.resolve(null),
      ])
      if (requestIdRef.current !== requestId) return

      doneForRef.current = signature
      setIsDone(true)
    } catch (err) {
      if (requestIdRef.current !== requestId) return
      console.error('Falha ao preparar a criação de gráficos:', err)
      setFatalError('Não foi possível salvar a sessão para gerar os gráficos. Tente novamente.')
    }
  }

  useEffect(() => {
    // `enabled` (step===FINAL_EXPLORATION && substep===1, ver
    // ChartCreation.tsx) impede o pipeline de disparar assim que
    // step4PatentResults/step4ArticleResults existem - eles já existem
    // desde que o usuário CHEGA em "Análise de Resultados" (substep 0), bem
    // antes de "Criação de Gráficos" ser a tela ativa. Sem esse gate, a
    // inferência estatística (chamadas reais à OPS/Scopus, até ~60s cada)
    // rodava em segundo plano por trás de "Análise de Resultados",
    // competindo com qualquer outra ação do usuário nesse meio tempo (ex.:
    // "Salvar progresso" ficando lento) e terminando antes mesmo do
    // usuário clicar "Próximo" - a tela de loading em si nunca chegava a
    // ser vista fazendo o trabalho de verdade.
    if (!enabled) return
    if (!hasPatent && !hasArticle) return
    if (doneForRef.current === signature) {
      setIsDone(true)
      return
    }
    if (startedForRef.current === signature) return
    startedForRef.current = signature
    run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, signature, hasPatent, hasArticle])

  return { stageMessage, isDone, fatalError, retry: run }
}
