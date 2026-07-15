import { useEffect, useState } from 'react'
import { IterationsBarChart } from '../components/charts/IterationsBarChart'
import { SessionStatusBarChart } from '../components/charts/SessionStatusBarChart'
import { searchSessions, type ResearchSessionSummary } from '../services/researchSession'

export function StatisticsPage() {
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setIsLoading(true)
    setError(null)
    searchSessions()
      .then(setSessions)
      .catch((err) => {
        console.error('Falha ao buscar sessões para estatísticas:', err)
        setError('Não foi possível carregar as estatísticas. Tente novamente.')
      })
      .finally(() => setIsLoading(false))
  }, [])

  return (
    <div className="w-full">
      <h2 className="text-2xl font-bold mb-1">Estatísticas das nossas prospecções:</h2>
      <p className="text-sm text-gray-500 mb-6">
        Métricas agregadas das suas sessões de prospecção. 
      </p>

      {isLoading && <p className="text-sm text-gray-500">Carregando...</p>}
      {!isLoading && error && <p className="text-sm text-red-600 font-medium">{error}</p>}
      {!isLoading && !error && (
        <div className="flex flex-col md:flex-row gap-4">
          <SessionStatusBarChart sessions={sessions} />
          <IterationsBarChart sessions={sessions} />
          
        </div>
      )}
    </div>
  )
}
