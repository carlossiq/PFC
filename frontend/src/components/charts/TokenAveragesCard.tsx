import { StatTile } from '../StatTile'
import {
  getSessionTotalIterations,
  getSessionTotalTokens,
  type ResearchSessionSummary,
} from '../../services/researchSession'

interface TokenAveragesCardProps {
  sessions: ResearchSessionSummary[]
}

// duration_ms vem por chamada, não por sessão - abaixo de 1s mostra em ms
// (arredondado, sem casas decimais fazem sentido pra IA), acima mostra em
// segundos com 1 casa decimal.
function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`
}

// Médias de consumo de tokens das sessões buscadas. 
export function TokenAveragesCard({ sessions }: TokenAveragesCardProps) {
  if (sessions.length === 0) {
    return (
      <div className="rounded-xl border-2 border-gray-200 bg-white shadow-sm p-6 w-full">
        <h3 className="font-bold text-base text-gray-900 mb-1">Consumo médio de tokens</h3>
        <p className="text-sm text-gray-500">
          Nenhuma sessão encontrada ainda - inicie uma prospecção pra ver estatísticas aqui.
        </p>
      </div>
    )
  }

  const totalTokens = sessions.reduce((sum, s) => sum + getSessionTotalTokens(s), 0)
  const totalIterations = sessions.reduce((sum, s) => sum + getSessionTotalIterations(s), 0)
  const avgTokensPerSession = totalTokens / sessions.length

  // "IA externa" = chamadas com provider !== 'internal' (o NLP local de
  // extração de termos usa provider 'internal' e não tem tempo de rede
  // comparável - ver INTERNAL_AI_LABEL em researchSession.ts).
  const externalCalls = sessions.flatMap((s) => s.ai_calls).filter((c) => c.provider !== 'internal')
  const avgExternalDurationMs =
    externalCalls.length === 0 ? null : externalCalls.reduce((sum, c) => sum + c.duration_ms, 0) / externalCalls.length

  // Contraparte da IA interna (extração de termos, provider 'internal') -
  const internalCalls = sessions.flatMap((s) => s.ai_calls).filter((c) => c.provider === 'internal')
  const avgInternalDurationMs =
    internalCalls.length === 0 ? null : internalCalls.reduce((sum, c) => sum + c.duration_ms, 0) / internalCalls.length

  return (
    <div className="rounded-xl border-2 border-gray-200 bg-white shadow-sm p-6 w-full">
      <div className="mb-4">
        <h3 className="font-bold text-base text-gray-900">Consumo médio de tokens</h3>
        <p className="text-xs text-gray-500 mt-1">
          {sessions.length} {sessions.length === 1 ? 'sessão considerada' : 'sessões consideradas'}.
        </p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatTile
          label="Média de tokens por sessão"
          value={Math.round(avgTokensPerSession).toLocaleString('pt-BR')}
          sub={`${sessions.length} ${sessions.length === 1 ? 'sessão' : 'sessões'}`}
          tooltip="Total de tokens (entrada + saída) de todas as chamadas de IA de cada sessão, em média entre as sessões buscadas."
        />
        <StatTile
          label="Média de tokens por iteração"
          value={totalIterations === 0 ? '—' : Math.round(totalTokens / totalIterations).toLocaleString('pt-BR')}
          sub={totalIterations > 0 ? `${totalIterations.toLocaleString('pt-BR')} iterações no total` : 'Nenhuma iteração registrada ainda'}
          tooltip="Soma de todos os tokens dividida pela soma de todas as iterações de IA."
        />
        <StatTile
          label="Tempo médio de resposta (IA externa)"
          value={avgExternalDurationMs === null ? '—' : formatDuration(avgExternalDurationMs)}
          sub={externalCalls.length > 0 ? `${externalCalls.length.toLocaleString('pt-BR')} chamadas` : 'Nenhuma chamada externa ainda'}
          tooltip="Tempo médio de ida e volta das chamadas pra IA externa (Gemini/Anthropic)."
        />
        <StatTile
          label="Tempo médio de resposta (IA interna)"
          value={avgInternalDurationMs === null ? '—' : formatDuration(avgInternalDurationMs)}
          sub={internalCalls.length > 0 ? `${internalCalls.length.toLocaleString('pt-BR')} chamadas` : 'Nenhuma chamada interna ainda'}
          tooltip="Tempo médio da extração de termos, que roda localmente não depende de rede."
        />
      </div>
    </div>
  )
}
