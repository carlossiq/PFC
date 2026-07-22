import { StatTile } from '../StatTile'
import {
  getSessionTotalIterations,
  getSessionTotalTokens,
  type ResearchSessionSummary,
} from '../../services/researchSession'
import { ChartCard } from './ChartCard'

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
    return <ChartCard title="Consumo médio de tokens" isEmpty />
  }

  const totalTokens = sessions.reduce((sum, s) => sum + getSessionTotalTokens(s), 0)
  const totalIterations = sessions.reduce((sum, s) => sum + getSessionTotalIterations(s), 0)
  const avgTokensPerSession = totalTokens / sessions.length

  // Chamadas de IA de verdade (Gemini/Anthropic, via rede) - provider
  // 'internal' fica de fora, porque não é uma chamada de IA: é a extração de
  // termos (NLP local, sem tempo de rede comparável - ver TERM_EXTRACTION_LABEL
  // em researchSession.ts).
  const aiCalls = sessions.flatMap((s) => s.ai_calls).filter((c) => c.provider !== 'internal')
  const avgAiDurationMs = aiCalls.length === 0 ? null : aiCalls.reduce((sum, c) => sum + c.duration_ms, 0) / aiCalls.length

  // Extração de termos (spaCy + KeyBERT + TF-IDF) - registrada na mesma
  // tabela ai_calls (provider 'internal') só pra reaproveitar o tracking de
  // duração, mas não é uma chamada de IA.
  const termExtractionCalls = sessions.flatMap((s) => s.ai_calls).filter((c) => c.provider === 'internal')
  const avgTermExtractionDurationMs =
    termExtractionCalls.length === 0
      ? null
      : termExtractionCalls.reduce((sum, c) => sum + c.duration_ms, 0) / termExtractionCalls.length

  return (
    <ChartCard
      title="Consumo médio de tokens"
      description={`${sessions.length} ${sessions.length === 1 ? 'sessão considerada' : 'sessões consideradas'}.`}
    >
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
          label="Tempo médio de resposta (IA)"
          value={avgAiDurationMs === null ? '—' : formatDuration(avgAiDurationMs)}
          sub={aiCalls.length > 0 ? `${aiCalls.length.toLocaleString('pt-BR')} chamadas` : 'Nenhuma chamada de IA ainda'}
          tooltip="Tempo médio de ida e volta das chamadas de IA (Gemini/Anthropic)."
        />
        <StatTile
          label="Duração média da extração de termos"
          value={avgTermExtractionDurationMs === null ? '—' : formatDuration(avgTermExtractionDurationMs)}
          sub={termExtractionCalls.length > 0 ? `${termExtractionCalls.length.toLocaleString('pt-BR')} extrações` : 'Nenhuma extração de termos ainda'}
          tooltip="Tempo médio da extração de termos (spaCy + KeyBERT + TF-IDF) - processamento local, não é uma chamada de IA."
        />
      </div>
    </ChartCard>
  )
}
