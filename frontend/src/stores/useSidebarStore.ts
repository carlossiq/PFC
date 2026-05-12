import { create } from 'zustand'

interface SidebarStore {
  collapsed: boolean
  setCollapsed: (collapsed: boolean) => void
  toggleCollapsed: () => void
  locked: boolean
  setLocked: (locked: boolean) => void
}

export const useSidebarStore = create<SidebarStore>((set) => ({
  collapsed: true,
  setCollapsed: (collapsed) => set({ collapsed }),
  toggleCollapsed: () => set((state) => ({ collapsed: !state.collapsed })),
  locked: false,
  setLocked: (locked) => set({ locked }),
}))
