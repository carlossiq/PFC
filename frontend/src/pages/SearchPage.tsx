import { useEffect, useState } from 'react'
import { Modal } from '../components/Modal'
import { SessionSearchFilter } from '../components/SessionSearchFilter'
import { SessionCard } from '../components/SessionCard'
import { searchSessions, deleteSession, type ResearchSessionSummary } from '../services/researchSession'

export function SearchPage() {
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
      <h2 className="text-2xl font-bold mb-1">Sessões de Prospecção</h2>
      <p className="text-sm text-gray-500 mb-6">
        Busque, pelo tema pesquisado, sessões de prospecção já iniciadas.Clique num card pra ver os detalhes, ou use o ícone de lixeira
        pra apagar a sessão (e tudo o que ela guarda) permanentemente.
      </p>

      <SessionSearchFilter value={query} onChange={setQuery} />

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
