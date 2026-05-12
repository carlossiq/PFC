import { create } from 'zustand'

interface WorkflowStore {
  tab: number
  setTab: (tab: number) => void
  nextTab: () => void
  prevTab: () => void
  prospecting: boolean
  setProspecting: (prospecting: boolean) => void
}

const TOTAL_TABS = 12

export const useWorkflowStore = create<WorkflowStore>((set) => ({
  tab: 0,
  setTab: (tab) => set({ tab: Math.max(0, Math.min(tab, TOTAL_TABS - 1)) }),
  nextTab: () => set((state) => ({ tab: Math.min(state.tab + 1, TOTAL_TABS - 1) })),
  prevTab: () => set((state) => ({ tab: Math.max(state.tab - 1, 0) })),
  prospecting: false,
  setProspecting: (prospecting) => set({ prospecting }),
}))
