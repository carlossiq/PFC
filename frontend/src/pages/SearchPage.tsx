import { useEffect, useState } from 'react'
import { Modal } from '../components/Modal'
import { SessionSearchFilter } from '../components/SessionSearchFilter'
import { SessionCard } from '../components/SessionCard'
import { searchSessions, deleteSession, getSessionById, type ResearchSessionSummary } from '../services/researchSession'
import { mapSessionToFormStorePatch } from '../services/sessionHydration'
import { useFormStore } from '../stores/useFormStore'
import { useProspectingStore } from '../stores/useProspectingStore'
import { useHistoryStore } from '../stores/useHistoryStore'
import { useWorkflowStore } from '../stores/useWorkflowStore'
import { TABS } from '../constants/tabs'

type StatusFilter = 'all' | 'pending' | 'completed'

const STATUS_FILTER_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'Todas' },
  { value: 'pending', label: 'Pendentes' },
  { value: 'completed', label: 'Concluídas' },
]

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [sessionPendingDelete, setSessionPendingDelete] = useState<ResearchSessionSummary | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [resumingId, setResumingId] = useState<number | null>(null)
  const [resumeError, setResumeError] = useState<string | null>(null)

  const filteredSessions = sessions.filter((session) => {
    if (statusFilter === 'pending') return !session.completed
    if (statusFilter === 'completed') return session.completed
    return true
  })

  // Busca a sessão completa (dados frescos) e repopula o form store, sempre
  // reabrindo no Step1 preenchido - não restaura o step/substep exato de onde
  // o usuário parou.
  async function handleContinue(session: ResearchSessionSummary) {
    setResumingId(session.id)
    setResumeError(null)
    try {
      const full = await getSessionById(session.id)
      useFormStore.getState().hydrateFromSession(mapSessionToFormStorePatch(full))
      useHistoryStore.getState().reset()
      useProspectingStore.getState().reset()
      useWorkflowStore.getState().setTab(TABS.START_PROSPECTION)
    } catch (err) {
      console.error('Falha ao retomar sessão:', err)
      setResumeError('Não foi possível retomar a sessão. Tente novamente.')
    } finally {
      setResumingId(null)
    }
  }

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

      <SessionSearchFilter
        value={query}
        onChange={setQuery}
        statusFilter={{ options: STATUS_FILTER_OPTIONS, value: statusFilter, onChange: setStatusFilter }}
      />

      {isLoading && <p className="text-sm text-gray-500">Buscando...</p>}

      {!isLoading && error && (
        <p className="text-sm text-red-600 font-medium">{error}</p>
      )}

      {resumeError && (
        <p className="mb-4 text-sm text-red-600 font-medium">{resumeError}</p>
      )}

      {!isLoading && !error && filteredSessions.length === 0 && (
        <p className="text-sm text-gray-500">Nenhuma sessão encontrada.</p>
      )}

      {!isLoading && !error && filteredSessions.length > 0 && (
        <div className="flex flex-col gap-4">
          {filteredSessions.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              isExpanded={expandedId === session.id}
              onToggle={() => setExpandedId(expandedId === session.id ? null : session.id)}
              onDeleteClick={() => {
                setDeleteError(null)
                setSessionPendingDelete(session)
              }}
              onContinueClick={() => handleContinue(session)}
              isResuming={resumingId === session.id}
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
