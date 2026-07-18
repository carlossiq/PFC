import { useEffect, useState } from 'react'
import { IterationsBarChart } from '../components/charts/IterationsBarChart'
import { SessionStatusBarChart } from '../components/charts/SessionStatusBarChart'
import { SessionsTimelineAreaChart } from '../components/charts/SessionsTimelineAreaChart'
import { TokenAveragesCard } from '../components/charts/TokenAveragesCard'
import { SectionHeader } from '../components/SectionHeader'
import { searchSessions, type ResearchSessionSummary } from '../services/researchSession'

// Teto de sessões buscadas pra estatísticas - bem acima do limite padrão (50)
// usado pela busca normal (SearchPage), mas ainda um teto: com mais de 500
// sessões salvas, as mais antigas ficam de fora das médias/gráficos.
const STATISTICS_SESSIONS_LIMIT = 500

export function StatisticsPage() {
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setIsLoading(true)
    setError(null)
    searchSessions(undefined, STATISTICS_SESSIONS_LIMIT)
      .then(setSessions)
      .catch((err) => {
        console.error('Falha ao buscar sessões para estatísticas:', err)
        setError('Não foi possível carregar as estatísticas. Tente novamente.')
      })
      .finally(() => setIsLoading(false))
  }, [])

  return (
    <div className="w-full">
      <SectionHeader
        title="Estatísticas das nossas prospecções:"
        description="Métricas agregadas das suas sessões de prospecção."
      />

      {isLoading && <p className="text-sm text-gray-500">Carregando...</p>}
      {!isLoading && error && <p className="text-sm text-red-600 font-medium">{error}</p>}
      {!isLoading && !error && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col md:flex-row gap-4">
            <SessionStatusBarChart sessions={sessions} />
            <IterationsBarChart sessions={sessions} />
          </div>

          <TokenAveragesCard sessions={sessions} />

          <SessionsTimelineAreaChart sessions={sessions} />
        </div>
      )}
    </div>
  )
}
