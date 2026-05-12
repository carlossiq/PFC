import { create } from 'zustand'

// Snapshot do estado de navegação capturado ao sair de um step
export interface HistorySnapshot {
  step: number
  substep: number | null
  selectedTheme: {
    id: string
    theme: string
    description: string
    keywords?: string[]
    studyArea?: string[]
  } | null
  themeSet: number
}

// Stack de histórico de navegação (push ao confirmar, pop ao voltar)
interface HistoryStore {
  history: HistorySnapshot[]
  push: (snapshot: HistorySnapshot) => void
  pop: () => HistorySnapshot | null
  reset: () => void
}

export const useHistoryStore = create<HistoryStore>((set, get) => ({
  history: [],

  push: (snapshot) => {
    set((state) => ({
      history: [...state.history, snapshot],
    }))
  },

  pop: () => {
    const state = get()
    if (state.history.length === 0) return null
    const last = state.history[state.history.length - 1]
    set({ history: state.history.slice(0, -1) })
    return last
  },

  reset: () => set({ history: [] }),
}))
