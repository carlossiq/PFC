import { FileText, Download } from 'lucide-react'
import { useFormStore } from '../../stores/useFormStore'
import { useFinalSCurve } from '../../hooks/useFinalSCurve'
import type { SCurveKind } from '../../hooks/useFinalSCurve'
import { Button } from '../Button'
import { LoadingScreen } from '../LoadingScreen'
import { SectionHeader } from '../SectionHeader'
import { SCurveFitLegend } from '../SCurveFitLegend'
import { SCurveReliabilityWarning } from '../SCurveReliabilityWarning'
import { STEPS } from '../../constants/steps'
import { PANEL_ACCENT } from '../../constants/probePanelAccent'
import type { OpsFinalAggregateResult, ScopusFinalAggregateResult } from '../../services/finalQuery'

// Curva S (Fisher-Pry) de patentes ou artigos, gerada a partir do
// patentsByYear/articlesByYear que a busca final já devolve - gera
// automaticamente assim que há resultado (ver useFinalSCurve), sem exigir
// clique do usuário; "Baixar Gráfico" baixa o PNG já renderizado pelo
// backend (ver ReportService._render_s_curve_chart). "Anos para projetar"
// deixa o usuário mudar quantos anos a parte tracejada cobre (default 5) -
// clicar "Atualizar" regera e sobrescreve o gráfico salvo com o novo valor.
function SCurveSection({ kind, yearlyByYear }: { kind: SCurveKind; yearlyByYear: Record<string, number> | null }) {
  const {
    hasData,
    isLoading,
    error,
    chart,
    chartUrl,
    downloadError,
    handleDownload,
    projectionYearsInput,
    setProjectionYearsInput,
    applyProjectionYears,
    isApplyingProjection,
  } = useFinalSCurve(kind, yearlyByYear)

  // Sem contagem por ano (ex.: a API da fonte falhou em todas as consultas
  // por ano) - antes a seção simplesmente sumia, sem explicar por que não
  // havia curva S.
  if (!hasData) {
    return (
      <div className="mt-3 pt-3 border-t border-gray-100">
        <h5 className="text-xs font-semibold text-gray-600 mb-2">Curva S (evolução temporal)</h5>
        <p className="text-sm text-gray-500">
          A busca não retornou a contagem de {kind === 'patent' ? 'patentes' : 'artigos'} por ano, então a curva S não
          pôde ser gerada. Refaça a busca final para tentar novamente.
        </p>
      </div>
    )
  }

  return (
    <div className="mt-3 pt-3 border-t border-gray-100">
      <h5 className="text-xs font-semibold text-gray-600 mb-2">Curva S (evolução temporal)</h5>

      {isLoading && <LoadingScreen message="Gerando curva S..." />}

      {!isLoading && error && <p className="text-sm text-red-600">{error}</p>}

      {!isLoading && !error && !chart && (
        <p className="text-sm text-gray-500">
          Não foi possível ajustar a curva S com os dados disponíveis (série de anos ainda muito curta ou sem
          sinal de desaceleração).
        </p>
      )}

      {!isLoading && chart && chartUrl && (
        <div className="space-y-3">
          <img
            src={chartUrl}
            alt={`Curva S de ${kind === 'patent' ? 'patentes' : 'artigos'}`}
            className="w-full rounded-md border border-gray-200"
          />
          <SCurveReliabilityWarning fitQuality={chart.fitQuality} />
          {downloadError && <p className="text-sm text-red-600">{downloadError}</p>}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <label className="inline-flex items-center gap-1.5 text-xs text-gray-600">
                Anos para projetar
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={projectionYearsInput}
                  onChange={(e) => setProjectionYearsInput(Number(e.target.value))}
                  className="w-16 rounded-md border border-gray-300 px-2 py-1 text-sm text-gray-900"
                />
              </label>
              <Button size="sm" onClick={applyProjectionYears} disabled={isApplyingProjection}>
                {isApplyingProjection ? 'Atualizando...' : 'Atualizar'}
              </Button>
            </div>
            <Button size="sm" onClick={handleDownload}>
              <span className="inline-flex items-center gap-1.5">
                <Download size={14} />
                Baixar Gráfico
              </span>
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// Painel de patentes (OPS) da busca final - a rota devolve um compilado
// agregado (depositants/cpc/title/patentsByYear), não mais uma lista de
// documentos (ver OpsFinalAggregateResult), então não dá mais pra reusar
// ProbeResultsPanel (que espera ProbeSearchResult) pro lado OPS aqui. Uma
// visualização completa (gráficos) fica pra depois - por ora só um resumo
// simples dos agregados, sem quebrar a tela.
function OpsFinalAggregatePanel({
  title,
  results,
}: {
  title: string
  results: OpsFinalAggregateResult | null
}) {
  const accent = PANEL_ACCENT.ops
  const depositantsCount = results ? Object.keys(results.depositants).length : 0
  const cpcCount = results ? Object.keys(results.cpc).length : 0

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${accent.icon}`}>
            <FileText size={16} />
          </span>
          <h4 className="font-semibold text-sm text-gray-900 truncate">{title}</h4>
        </div>
        {results && (
          <div className="text-right shrink-0">
            {/* Total real encontrado na base (o número do Quadro de busca do
                relatório); a amostra baixada pra análise vem logo abaixo. */}
            <div className="text-lg font-bold text-gray-900 leading-none">
              {(results.totalCount ?? results.resultsCount).toLocaleString('pt-BR')}
            </div>
            {(results.totalCount ?? results.resultsCount) !== results.resultsCount && (
              <div className="text-[10px] text-gray-500 mt-0.5">
                amostra analisada: {results.resultsCount.toLocaleString('pt-BR')}
              </div>
            )}
          </div>
        )}
      </div>

      {results === null && <p className="text-sm text-gray-500">Ainda não buscado.</p>}

      {results !== null && results.resultsCount === 0 && (
        <p className="text-sm text-gray-500">Nenhum resultado encontrado pra essa query.</p>
      )}

      {results !== null && results.resultsCount > 0 && (
        <>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-gray-50 p-2">
              <div className="text-xs text-gray-500">Depositantes distintos</div>
              <div className="font-semibold text-gray-900">{depositantsCount}</div>
            </div>
            <div className="rounded-md bg-gray-50 p-2">
              <div className="text-xs text-gray-500">Classificações CPC distintas</div>
              <div className="font-semibold text-gray-900">{cpcCount}</div>
            </div>
          </div>

          <SCurveSection kind="patent" yearlyByYear={results.patentsByYear} />
        </>
      )}
    </div>
  )
}

// Equivalente a OpsFinalAggregatePanel, pro Scopus (artigos) - mesmo motivo
// de existir (ver ScopusFinalAggregateResult em finalQuery.ts): a rota
// devolve institutions/areaOfStudy agregados, não mais uma lista de
// artigos, então ProbeResultsPanel (que espera ProbeSearchResult) também
// não serve mais aqui.
function ScopusFinalAggregatePanel({
  title,
  results,
}: {
  title: string
  results: ScopusFinalAggregateResult | null
}) {
  const accent = PANEL_ACCENT.scopus
  const institutionsCount = results ? Object.keys(results.institutions).length : 0
  const areaOfStudyCount = results ? Object.keys(results.areaOfStudy).length : 0

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${accent.icon}`}>
            <FileText size={16} />
          </span>
          <h4 className="font-semibold text-sm text-gray-900 truncate">{title}</h4>
        </div>
        {results && (
          <div className="text-right shrink-0">
            {/* Total real encontrado na base (o número do Quadro de busca do
                relatório); a amostra baixada pra análise vem logo abaixo. */}
            <div className="text-lg font-bold text-gray-900 leading-none">
              {(results.totalCount ?? results.resultsCount).toLocaleString('pt-BR')}
            </div>
            {(results.totalCount ?? results.resultsCount) !== results.resultsCount && (
              <div className="text-[10px] text-gray-500 mt-0.5">
                amostra analisada: {results.resultsCount.toLocaleString('pt-BR')}
              </div>
            )}
          </div>
        )}
      </div>

      {results === null && <p className="text-sm text-gray-500">Ainda não buscado.</p>}

      {results !== null && results.resultsCount === 0 && (
        <p className="text-sm text-gray-500">Nenhum resultado encontrado pra essa query.</p>
      )}

      {results !== null && results.resultsCount > 0 && (
        <>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-gray-50 p-2">
              <div className="text-xs text-gray-500">Instituições distintas</div>
              <div className="font-semibold text-gray-900">{institutionsCount}</div>
            </div>
            <div className="rounded-md bg-gray-50 p-2">
              <div className="text-xs text-gray-500">Áreas de estudo distintas</div>
              <div className="font-semibold text-gray-900">{areaOfStudyCount}</div>
            </div>
          </div>

          <SCurveSection kind="article" yearlyByYear={results.articlesByYear} />
        </>
      )}
    </div>
  )
}

interface FinalResultsProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

// Resultados da busca final real, exibidos depois que o usuário escolhe e
// confirma uma das 3 variantes de query em FinalExploration.tsx - mesmo
// papel que InitialResults.tsx tem pra probe search. substep 0 é
// "Análise de Resultados" (SUBSTEPS.RESULTS_ANALYSIS); "Próximo" aqui leva
// pro substep 1, "Criação de Gráficos" (ver ChartCreation.tsx).
export function FinalResults({ step, substep, onBack, onNext }: FinalResultsProps) {
  const { step4PatentResults, step4ArticleResults } = useFormStore()

  if (step !== STEPS.FINAL_EXPLORATION || substep !== 0) return null

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <SectionHeader
        title="Resultados da Busca Final"
        description="Resultado da busca real com a query final escolhida no passo anterior - patentes (OPS) à esquerda, artigos (Scopus) à direita."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
        <OpsFinalAggregatePanel title="Patentes (OPS)" results={step4PatentResults} />
        <ScopusFinalAggregatePanel title="Artigos (Scopus)" results={step4ArticleResults} />
      </div>

      {((step4PatentResults?.resultsCount ?? 0) > 0 || (step4ArticleResults?.resultsCount ?? 0) > 0) && (
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4 mb-4">
          <h5 className="text-xs font-semibold text-gray-600 mb-2">Curva S — Legenda</h5>
          <SCurveFitLegend />
        </div>
      )}

      <div className="mt-2 pt-4 border-t border-gray-200 flex gap-4">
        <Button fullWidth variant="secondary" onClick={onBack}>
          Voltar
        </Button>
        <Button fullWidth onClick={onNext}>
          Próximo
        </Button>
      </div>
    </div>
  )
}
