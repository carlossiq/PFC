import { useState } from 'react'
import { Trash2, ChevronDown } from 'lucide-react'
import { selectableCardClass } from './CandidatePicker'
import { FieldCard } from './FieldCard'
import type { ResearchSessionSummary } from '../services/researchSession'
import type { SessionInputRow } from '../services/sessionInput'

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

type InputBlockType = 'root' | 'generated'

interface SessionCardProps {
  session: ResearchSessionSummary
  isExpanded: boolean
  onToggle: () => void
  onDeleteClick: () => void
}

export function SessionCard({ session, isExpanded, onToggle, onDeleteClick }: SessionCardProps) {
  const root = session.inputs.find((i) => i.parent_id === null)
  const generated = session.inputs.find((i) => i.parent_id !== null)

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
              {root?.description && (
                <p className="text-sm text-gray-500 mt-1 line-clamp-2">{root.description}</p>
              )}
            </div>

            <div className="flex flex-col items-end gap-1 shrink-0">
              <span className="text-xs text-gray-400">{formatDate(session.created_at)}</span>
              <span className="text-xs font-semibold text-[#0f9448] bg-[#0f9448]/10 rounded-full px-2 py-0.5">
                {generated?.iterations ?? 0} {(generated?.iterations ?? 0) === 1 ? 'iteração' : 'iterações'}
              </span>
            </div>
          </div>
        </button>

        <ChevronDown
          size={18}
          className={`shrink-0 mt-1 text-gray-400 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
        />

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
        </div>
      </div>
    </div>
  )
}
