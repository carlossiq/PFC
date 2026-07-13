import { useState } from 'react'
import { ChevronDown, FileText, BookOpen } from 'lucide-react'
import { selectableCardClass } from '../CandidatePicker'
import { StatTile } from '../StatTile'
import { useFormStore } from '../../stores/useFormStore'
import { finalizeSession, buildProbeQueryPayload } from '../../services/sessionInput'
import type { ProbeSearchResult } from '../../services/probeQuery'
import type { ProbeApi } from '../../constants/probeFields'
import { PANEL_ACCENT } from '../../constants/probePanelAccent'
import { STEPS } from '../../constants/steps'

interface ProbeResultsPanelProps {
  title: string
  api: ProbeApi
  results: ProbeSearchResult | null
  isExpanded: boolean
  onToggle: () => void
}

function formatYearRange(summary: ProbeSearchResult['summary']): string {
  if (summary.yearMin == null || summary.yearMax == null) return 'não disponível'
  return summary.yearMin === summary.yearMax ? `${summary.yearMin}` : `${summary.yearMin}–${summary.yearMax}`
}

// As outras 2 estatísticas variam por API: patentes destacam classificação
// IPC e jurisdição (dados que só o OPS retorna); artigos destacam acesso
// aberto e revista/fonte (só o Scopus retorna). O tile "Anos cobertos" é
// idêntico nos dois painéis (mesmo texto, mesmo tamanho).
function ProbeResultsStatTiles({ api, results }: { api: ProbeApi; results: ProbeSearchResult }) {
  const { summary } = results

  if (api === 'ops') {
    return (
      <div className="grid grid-cols-3 gap-2">
        <StatTile
          label="Anos cobertos"
          value={formatYearRange(summary)}
          sub={summary.distinctYears > 0 ? `${summary.distinctYears} distintos` : undefined}
        />
        <StatTile label="Classificações IPC" value={summary.distinctIpc} />
        <StatTile label="Jurisdições" value={summary.distinctCountries} />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-2">
      <StatTile
        label="Acesso aberto"
        value={`${results.resultsCount > 0 ? Math.round((summary.openAccessCount / results.resultsCount) * 100) : 0}%`}
        tooltip="Publicação Open Access: o artigo em si está disponível gratuitamente ao público, sem paywall nem assinatura institucional. Não indica se temos o abstract - todo artigo listado aqui já tem abstract garantido."
        sub={`${summary.openAccessCount} de ${results.resultsCount}`}
      />
      <StatTile
        label="Anos cobertos"
        value={formatYearRange(summary)}
        sub={summary.distinctYears > 0 ? `${summary.distinctYears} distintos` : undefined}
      />
      <StatTile label="Revistas/fontes" value={summary.distinctSources} />
    </div>
  )
}

// Um lado do painel (patente ou artigo): card com cabeçalho (ícone + título +
// contagem), estatísticas agregadas, e uma lista expansível de título/autor
// de cada item encontrado.
function ProbeResultsPanel({ title, api, results, isExpanded, onToggle }: ProbeResultsPanelProps) {
  const accent = PANEL_ACCENT[api]
  const Icon = api === 'ops' ? FileText : BookOpen
  const hasResults = results !== null && results.resultsCount > 0

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${accent.icon}`}>
            <Icon size={16} />
          </span>
          <h4 className="font-semibold text-sm text-gray-900 truncate">{title}</h4>
        </div>
        {hasResults && (
          <div className="text-right shrink-0">
            <div className="text-lg font-bold text-gray-900 leading-none">{results.resultsCount}</div>
            {results.totalAvailable != null && results.totalAvailable !== results.resultsCount && (
              <div className="text-[10px] text-gray-400 mt-0.5">de {results.totalAvailable.toLocaleString('pt-BR')}</div>
            )}
          </div>
        )}
      </div>

      {results === null && <p className="text-sm text-gray-500">Ainda não buscado.</p>}

      {results !== null && results.resultsCount === 0 && (
        <p className="text-sm text-gray-500">Nenhum resultado encontrado pra essa query.</p>
      )}

      {hasResults && (
        <>
          <div className="mb-3">
            <ProbeResultsStatTiles api={api} results={results} />
          </div>

          <button
            type="button"
            onClick={onToggle}
            className={`${selectableCardClass(isExpanded)} w-full flex items-center justify-between`}
          >
            <span className="text-sm font-semibold text-gray-900">Ver resultados</span>
            <ChevronDown
              size={16}
              className={`shrink-0 text-gray-400 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
            />
          </button>

          {isExpanded && (
            <ol className="mt-3 space-y-1.5 max-h-64 overflow-y-auto">
              {results.items.map((item, index) => (
                <li key={index} className="flex gap-2 py-1.5 border-b border-gray-100 last:border-0">
                  <span className="text-xs font-bold text-gray-300 shrink-0 w-4 pt-0.5">{index + 1}</span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 leading-snug">{item.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {item.year && <span className="font-semibold text-gray-400">{item.year}</span>}
                      {item.year && item.author && ' · '}
                      {item.author}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </div>
  )
}

interface InitialResultsProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

export function InitialResults({ step, substep, onBack, onNext }: InitialResultsProps) {
  const {
    sessionName,
    input,
    step2SelectedTheme,
    step2Iterations,
    step3Queries,
    step3SelectedIndex,
    step3Iterations,
    step3ArticleQueries,
    step3ArticleSelectedIndex,
    step3ArticleIterations,
    step3PatentResults,
    step3ArticleResults,
  } = useFormStore()

  const [expandedPanel, setExpandedPanel] = useState<'patent' | 'article' | null>(null)

  const [isFinalizing, setIsFinalizing] = useState(false)
  const [finalizeResult, setFinalizeResult] = useState<string | null>(null)
  const [finalizeError, setFinalizeError] = useState<string | null>(null)

  if (step !== STEPS.INITIAL_EXPLORATION || substep !== 0) return null

  // Botão de teste: os passos seguintes ainda são placeholder, então isso só
  // serve pra exercitar a rota POST /session-input enquanto o fluxo real de
  // finalização (ao fim da Geração do Relatório) não existe de verdade.
  async function handleFinalize() {
    setIsFinalizing(true)
    setFinalizeError(null)
    setFinalizeResult(null)
    try {
      const wasRefinedByAI = !!step2SelectedTheme && step2SelectedTheme.id !== 'input'
      const generated = wasRefinedByAI
        ? { theme: step2SelectedTheme!.theme, description: step2SelectedTheme!.description || null }
        : null

      const patentQuery = buildProbeQueryPayload(
        step3SelectedIndex !== null ? step3Queries?.[step3SelectedIndex] : undefined,
        'ops',
        step3Iterations,
        step3PatentResults?.resultsCount ?? null,
      )
      const articleQuery = buildProbeQueryPayload(
        step3ArticleSelectedIndex !== null ? step3ArticleQueries?.[step3ArticleSelectedIndex] : undefined,
        'scopus',
        step3ArticleIterations,
        step3ArticleResults?.resultsCount ?? null,
      )
      const probeQueries = [patentQuery, articleQuery].filter(
        (q): q is NonNullable<typeof q> => q !== null
      )

      const result = await finalizeSession(sessionName, input, generated, step2Iterations, probeQueries)
      setFinalizeResult(
        `Sessão ${result.session_public_id} criada (session_id=${result.session_id}, root_input_id=${result.root.id}${
          result.generated ? `, generated_input_id=${result.generated.id}, iterations=${result.generated.iterations}` : ''
        })`
      )
    } catch (err) {
      console.error('Falha ao finalizar sessão:', err)
      setFinalizeError('Não foi possível finalizar a sessão. Tente novamente.')
    } finally {
      setIsFinalizing(false)
    }
  }

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <h3 className="text-lg font-semibold text-gray-900 mb-1">Resultados Iniciais</h3>
      <p className="text-xs text-gray-500 mb-4">
        Resultado da busca real com as queries escolhidas no passo anterior - patentes (OPS) à
        esquerda, artigos (Scopus) à direita.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
        <ProbeResultsPanel
          title="Patentes (OPS)"
          api="ops"
          results={step3PatentResults}
          isExpanded={expandedPanel === 'patent'}
          onToggle={() => setExpandedPanel((prev) => (prev === 'patent' ? null : 'patent'))}
        />
        <ProbeResultsPanel
          title="Artigos (Scopus)"
          api="scopus"
          results={step3ArticleResults}
          isExpanded={expandedPanel === 'article'}
          onToggle={() => setExpandedPanel((prev) => (prev === 'article' ? null : 'article'))}
        />
      </div>

      {finalizeResult && (
        <p className="mb-4 text-sm text-[#0f9448] font-medium">{finalizeResult}</p>
      )}
      {finalizeError && (
        <p className="mb-4 text-sm text-red-600 font-medium">{finalizeError}</p>
      )}

      <div className="mt-2 pt-4 border-t border-gray-200 flex gap-4">
        <button
          type="button"
          onClick={onBack}
          className="flex-1 bg-gray-400 hover:bg-gray-500 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          Voltar
        </button>
        <button
          type="button"
          onClick={onNext}
          className="flex-1 bg-[#0f9448] hover:bg-[#0d843f] text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          Próximo
        </button>
        <button
          type="button"
          onClick={handleFinalize}
          disabled={isFinalizing}
          className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          {isFinalizing ? 'Finalizando...' : 'Finalizar Sessão (teste)'}
        </button>
      </div>
    </div>
  )
}
