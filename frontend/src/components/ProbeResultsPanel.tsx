import { ChevronDown, FileText, BookOpen } from 'lucide-react'
import { selectableCardClass } from './CandidatePicker'
import { StatTile } from './StatTile'
import type { ProbeSearchResult } from '../services/probeQuery'
import type { ProbeApi } from '../constants/probeFields'
import { PANEL_ACCENT } from '../constants/probePanelAccent'

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
// IPC e jurisdição (dados que só o OPS retorna); artigos destacam países
// (afiliação dos autores) e revista/fonte (só o Scopus retorna). O tile
// "Anos cobertos" é idêntico nos dois painéis (mesmo texto, mesmo tamanho).
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
        label="Anos cobertos"
        value={formatYearRange(summary)}
        sub={summary.distinctYears > 0 ? `${summary.distinctYears} distintos` : undefined}
        />
      <StatTile
        label="Países"
        value={summary.distinctCountries}
              />

      <StatTile label="Revistas/fontes" value={summary.distinctSources} />
    </div>
  )
}

// Um lado do painel (patente ou artigo): card com cabeçalho (ícone + título +
// contagem), estatísticas agregadas, e uma lista expansível de título/autor
// de cada item encontrado. Compartilhado entre InitialResults.tsx (probe) e
// FinalResults.tsx (busca final) - mesmo shape de resultado (ProbeSearchResult)
// nos dois casos.
export function ProbeResultsPanel({ title, api, results, isExpanded, onToggle }: ProbeResultsPanelProps) {
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
                      {item.year && (api === 'ops' ? item.inventor : item.author) && ' · '}
                      {api === 'ops' ? item.inventor : item.author}
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

