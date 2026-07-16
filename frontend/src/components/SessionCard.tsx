import { useState } from 'react'
import { Trash2, ChevronDown, Play } from 'lucide-react'
import { selectableCardClass } from './CandidatePicker'
import { FieldCard } from './FieldCard'
import { PROBE_FIELDS_BY_API } from '../constants/probeFields'
import {
  getSessionModels,
  getSessionTotalIterations,
  getSessionTotalTokens,
  type ResearchSessionSummary,
} from '../services/researchSession'
import type { SessionInputRow, SessionProbeQueryRow } from '../services/sessionInput'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR')
}

function InputFieldsBlock({ input, title }: { input: SessionInputRow; title: string }) {
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
        {title}
      </p>
      <div className="space-y-3">
        <FieldCard label="Theme">
          <p className="text-sm font-semibold text-gray-900">{input.theme}</p>
        </FieldCard>

        {input.description && (
          <FieldCard label="Description">
            <p className="text-sm font-semibold text-gray-900">{input.description}</p>
          </FieldCard>
        )}

        {input.area_of_study && (
          <FieldCard label="Study Area">
            <p className="text-sm font-semibold text-gray-900">{input.area_of_study}</p>
          </FieldCard>
        )}

        {input.keywords && input.keywords.length > 0 && (
          <FieldCard label="Keywords">
            <p className="text-sm font-semibold text-gray-900">{input.keywords.join(', ')}</p>
          </FieldCard>
        )}

        {(input.year_from || input.year_to) && (
          <FieldCard label="Years">
            <p className="text-sm font-semibold text-gray-900">
              {input.year_from ?? '?'} - {input.year_to ?? '?'}
            </p>
          </FieldCard>
        )}

        {input.parent_id !== null && (
          <FieldCard label="Iterations">
            <p className="text-sm font-semibold text-gray-900">{input.iterations}</p>
          </FieldCard>
        )}
      </div>
    </div>
  )
}

// Mostra a query (patente/artigo) escolhida no Step3 pra essa sessão - mesmos
// campos e rótulos usados na tela de seleção (ProbeQuerySectionView), pra
// manter a query legível igual em ambos os lugares.
function ProbeQueryFieldsBlock({ query, title }: { query: SessionProbeQueryRow; title: string }) {
  const { order, labels } = PROBE_FIELDS_BY_API[query.fonte]

  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
        {title}
      </p>
      <div className="space-y-3">
        <FieldCard label="Query">
          <p className="text-sm font-mono text-gray-900 break-all">{query.query_text}</p>
        </FieldCard>

        {order
          .filter((f) => f !== 'year' && (query.fields?.[f]?.length ?? 0) > 0)
          .map((f) => (
            <FieldCard key={f} label={labels[f]}>
              <p className="text-sm font-semibold text-gray-900">{query.fields![f].join(', ')}</p>
            </FieldCard>
          ))}

        {(query.year_from || query.year_to) && (
          <FieldCard label="Years">
            <p className="text-sm font-semibold text-gray-900">
              {query.year_from ?? '?'} - {query.year_to ?? '?'}
            </p>
          </FieldCard>
        )}

        {query.complexity_level && (
          <FieldCard label="Complexidade">
            <p className="text-sm font-semibold text-gray-900">
              {query.complexity_level}
              {query.complexity_score != null ? ` (${query.complexity_score.toFixed(1)}/100)` : ''}
            </p>
          </FieldCard>
        )}

        <FieldCard label="Resultados encontrados">
          <p className="text-sm font-semibold text-gray-900">
            {query.result_count ?? 'Ainda não buscado'}
          </p>
        </FieldCard>

        <FieldCard label="Iterations">
          <p className="text-sm font-semibold text-gray-900">{query.iterations}</p>
        </FieldCard>
      </div>
    </div>
  )
}

type InputBlockType = 'root' | 'generated' | 'patentQuery' | 'articleQuery'

interface SessionCardProps {
  session: ResearchSessionSummary
  isExpanded: boolean
  onToggle: () => void
  onDeleteClick: () => void
  onContinueClick: () => void
  isResuming?: boolean
}

export function SessionCard({
  session,
  isExpanded,
  onToggle,
  onDeleteClick,
  onContinueClick,
  isResuming = false,
}: SessionCardProps) {
  const root = session.inputs.find((i) => i.parent_id === null)
  const generated = session.inputs.find((i) => i.parent_id !== null)
  // tipo === null identifica a linha de probe (Exploração Inicial) - a
  // sessão pode ter uma segunda linha por fonte pra query final (Escolha da
  // Query Final), não exibida neste card ainda.
  const patentQuery = session.probe_queries.find((q) => q.fonte === 'ops' && q.tipo === null)
  const articleQuery = session.probe_queries.find((q) => q.fonte === 'scopus' && q.tipo === null)
  const totalIterations = getSessionTotalIterations(session)
  const totalTokens = getSessionTotalTokens(session)
  const models = getSessionModels(session)

  // Independentes: os dois podem ficar abertos ao mesmo tempo, cada um
  // ocupando metade da grid.
  const [expandedBlocks, setExpandedBlocks] = useState<Set<InputBlockType>>(new Set())

  function toggleBlock(block: InputBlockType) {
    setExpandedBlocks((prev) => {
      const next = new Set(prev)
      if (next.has(block)) {
        next.delete(block)
      } else {
        next.add(block)
      }
      return next
    })
  }

  return (
    <div
      className={`
        rounded-xl border-2 bg-white shadow-sm transition-all duration-300 ease-in-out
        ${isExpanded ? 'border-[#0f9448] ring-2 ring-[#0f9448]/10' : 'border-gray-200 hover:border-[#0f9448]'}
      `}
    >
      <div className="w-full flex items-start gap-2 px-6 py-5">
        <button type="button" onClick={onToggle} className="flex-1 text-left min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-bold text-base text-gray-900">
                {session.name || `Sessão ${session.id}`}
              </h3>
              {root && (
                <p className="text-sm font-medium text-gray-700 mt-1">{root.theme}</p>
              )}
              <p className="text-xs text-gray-500 mt-1">
                Tokens utilizados na sessão: {totalTokens}
              </p>
              <p className="text-xs text-gray-500">
                {models.length > 1 ? 'Modelos Utilizados' : 'Modelo Utilizado'}: {models.length > 0 ? models.join(' + ') : '—'}
              </p>
              {root?.description && (
                <p className="text-sm text-gray-500 mt-1 line-clamp-2">{root.description}</p>
              )}
            </div>

            <div className="flex flex-col items-end gap-1 shrink-0">
              <span className="text-xs text-gray-400">{formatDate(session.created_at)}</span>
              <span
                className={`text-xs font-semibold rounded-full px-2 py-0.5 ${
                  session.completed
                    ? 'text-[#0f9448] bg-[#0f9448]/10'
                    : 'text-amber-600 bg-amber-100'
                }`}
              >
                {session.completed ? 'Concluída' : 'Pendente'}
              </span>
              <span className="text-xs font-semibold text-[#0f9448] bg-[#0f9448]/10 rounded-full px-2 py-0.5">
                {totalIterations} {totalIterations === 1 ? 'iteração total' : 'iterações totais'}
              </span>
            </div>
          </div>
        </button>

        <ChevronDown
          size={18}
          className={`shrink-0 mt-1 text-gray-400 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
        />

        {!session.completed && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onContinueClick()
            }}
            disabled={isResuming}
            className="shrink-0 p-2 rounded-lg text-gray-400 hover:text-[#0f9448] hover:bg-[#0f9448]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Continuar pesquisa"
            title="Continuar pesquisa"
          >
            <Play size={18} />
          </button>
        )}

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onDeleteClick()
          }}
          className="shrink-0 p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
          aria-label="Apagar sessão"
        >
          <Trash2 size={18} />
        </button>
      </div>

      <div
        className={`
          grid transition-all duration-300 ease-in-out
          ${isExpanded ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}
        `}
      >
        <div className="overflow-hidden">
          <div className="px-6 pb-6 pt-2 border-t border-gray-100">
            {(root || generated) && (
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                  Parâmetros de entrada
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {root && (
                    <button
                      type="button"
                      onClick={() => toggleBlock('root')}
                      className={`${selectableCardClass(expandedBlocks.has('root'))} flex items-center justify-between`}
                    >
                      <h4 className="font-semibold text-sm text-gray-900">Parâmetros do usuário</h4>
                      <ChevronDown
                        size={16}
                        className={`shrink-0 text-gray-400 transition-transform duration-300 ${expandedBlocks.has('root') ? 'rotate-180' : ''}`}
                      />
                    </button>
                  )}
                  {generated && (
                    <button
                      type="button"
                      onClick={() => toggleBlock('generated')}
                      className={`${selectableCardClass(expandedBlocks.has('generated'))} flex items-center justify-between`}
                    >
                      <h4 className="font-semibold text-sm text-gray-900">Parâmetros de busca com IA</h4>
                      <ChevronDown
                        size={16}
                        className={`shrink-0 text-gray-400 transition-transform duration-300 ${expandedBlocks.has('generated') ? 'rotate-180' : ''}`}
                      />
                    </button>
                  )}
                </div>

                {(expandedBlocks.has('root') || expandedBlocks.has('generated')) && (
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                    {expandedBlocks.has('root') && root && (
                      <InputFieldsBlock input={root} title="Input do usuário" />
                    )}
                    {expandedBlocks.has('generated') && generated && (
                      <InputFieldsBlock input={generated} title="Gerado pela IA" />
                    )}
                  </div>
                )}
              </div>
            )}

            {(patentQuery || articleQuery) && (
              <div className={(root || generated) ? 'mt-5 pt-5 border-t border-gray-100' : ''}>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                  Queries da Exploração Inicial
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {patentQuery && (
                    <button
                      type="button"
                      onClick={() => toggleBlock('patentQuery')}
                      className={`${selectableCardClass(expandedBlocks.has('patentQuery'))} flex items-center justify-between`}
                    >
                      <h4 className="font-semibold text-sm text-gray-900">Opção de query de patente</h4>
                      <ChevronDown
                        size={16}
                        className={`shrink-0 text-gray-400 transition-transform duration-300 ${expandedBlocks.has('patentQuery') ? 'rotate-180' : ''}`}
                      />
                    </button>
                  )}
                  {articleQuery && (
                    <button
                      type="button"
                      onClick={() => toggleBlock('articleQuery')}
                      className={`${selectableCardClass(expandedBlocks.has('articleQuery'))} flex items-center justify-between`}
                    >
                      <h4 className="font-semibold text-sm text-gray-900">Opção de query de artigos</h4>
                      <ChevronDown
                        size={16}
                        className={`shrink-0 text-gray-400 transition-transform duration-300 ${expandedBlocks.has('articleQuery') ? 'rotate-180' : ''}`}
                      />
                    </button>
                  )}
                </div>

                {(expandedBlocks.has('patentQuery') || expandedBlocks.has('articleQuery')) && (
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                    {expandedBlocks.has('patentQuery') && patentQuery && (
                      <ProbeQueryFieldsBlock query={patentQuery} title="Query de patente (OPS)" />
                    )}
                    {expandedBlocks.has('articleQuery') && articleQuery && (
                      <ProbeQueryFieldsBlock query={articleQuery} title="Query de artigos (Scopus)" />
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
