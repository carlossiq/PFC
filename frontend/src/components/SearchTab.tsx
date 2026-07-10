import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { FloatingLabelInput } from './FloatingLabelInput'
import { Modal } from './Modal'
import { searchSessions, deleteSession, type ResearchSessionSummary } from '../services/researchSession'
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
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-600 font-medium mb-1">Theme</p>
          <p className="text-sm font-semibold text-gray-900">{input.theme}</p>
        </div>

        {input.description && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600 font-medium mb-1">Description</p>
            <p className="text-sm font-semibold text-gray-900">{input.description}</p>
          </div>
        )}

        {input.area_of_study && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600 font-medium mb-1">Study Area</p>
            <p className="text-sm font-semibold text-gray-900">{input.area_of_study}</p>
          </div>
        )}

        {input.keywords && input.keywords.length > 0 && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600 font-medium mb-1">Keywords</p>
            <p className="text-sm font-semibold text-gray-900">{input.keywords.join(', ')}</p>
          </div>
        )}

        {(input.year_from || input.year_to) && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600 font-medium mb-1">Years</p>
            <p className="text-sm font-semibold text-gray-900">
              {input.year_from ?? '?'} - {input.year_to ?? '?'}
            </p>
          </div>
        )}

        {input.parent_id !== null && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600 font-medium mb-1">Iterations</p>
            <p className="text-sm font-semibold text-gray-900">{input.iterations}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function SessionCard({
  session,
  isExpanded,
  onToggle,
  onDeleteClick,
}: {
  session: ResearchSessionSummary
  isExpanded: boolean
  onToggle: () => void
  onDeleteClick: () => void
}) {
  const root = session.inputs.find((i) => i.parent_id === null)
  const generated = session.inputs.find((i) => i.parent_id !== null)

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
          <div className="px-6 pb-6 pt-2 border-t border-gray-100 grid grid-cols-1 md:grid-cols-2 gap-6">
            {root && <InputFieldsBlock input={root} title="Input do usuário" />}
            {generated && <InputFieldsBlock input={generated} title="Gerado pela IA" />}
          </div>
        </div>
      </div>
    </div>
  )
}

export function SearchTab() {
  const [query, setQuery] = useState('')
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [sessionPendingDelete, setSessionPendingDelete] = useState<ResearchSessionSummary | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  async function handleConfirmDelete() {
    if (!sessionPendingDelete) return
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await deleteSession(sessionPendingDelete.id)
      setSessions((prev) => prev.filter((s) => s.id !== sessionPendingDelete.id))
      if (expandedId === sessionPendingDelete.id) setExpandedId(null)
      setSessionPendingDelete(null)
    } catch (err) {
      console.error('Falha ao apagar sessão:', err)
      setDeleteError('Não foi possível apagar a sessão. Tente novamente.')
    } finally {
      setIsDeleting(false)
    }
  }

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setIsLoading(true)
      setError(null)
      searchSessions(query)
        .then(setSessions)
        .catch((err) => {
          console.error('Falha ao buscar sessões:', err)
          setError('Não foi possível buscar as sessões. Tente novamente.')
        })
        .finally(() => setIsLoading(false))
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [query])

  return (
    <div className="w-full">
      <h2 className="text-2xl font-bold mb-6">Search</h2>

      <div className="max-w-md mb-6">
        <FloatingLabelInput
          label="Buscar por tema"
          name="sessionThemeQuery"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ex: Drones, IA em Saúde..."
        />
      </div>

      {isLoading && <p className="text-sm text-gray-500">Buscando...</p>}

      {!isLoading && error && (
        <p className="text-sm text-red-600 font-medium">{error}</p>
      )}

      {!isLoading && !error && sessions.length === 0 && (
        <p className="text-sm text-gray-500">Nenhuma sessão encontrada.</p>
      )}

      {!isLoading && !error && sessions.length > 0 && (
        <div className="flex flex-col gap-4">
          {sessions.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              isExpanded={expandedId === session.id}
              onToggle={() => setExpandedId(expandedId === session.id ? null : session.id)}
              onDeleteClick={() => {
                setDeleteError(null)
                setSessionPendingDelete(session)
              }}
            />
          ))}
        </div>
      )}

      <Modal
        isOpen={sessionPendingDelete !== null}
        title="Apagar sessão?"
        message={`Isso vai apagar "${sessionPendingDelete?.name || `Sessão ${sessionPendingDelete?.id}`}" e todos os seus dados (input do usuário e gerado pela IA) permanentemente.${
          deleteError ? ` ${deleteError}` : ''
        }`}
        confirmText={isDeleting ? 'Apagando...' : 'Apagar'}
        cancelText="Cancelar"
        onConfirm={handleConfirmDelete}
        onCancel={() => setSessionPendingDelete(null)}
        isDangerous
      />
    </div>
  )
}
