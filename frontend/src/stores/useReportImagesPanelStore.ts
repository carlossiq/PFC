import { create } from 'zustand'

// Painel lateral "Imagens" do editor do .tex (ReportDocumentEditor.tsx) -
// compartilhado com o botão de imagem da Sidebar (ReportImagesToggleButton),
// que abre/fecha o mesmo painel. `editorMounted` diz se o editor está na
// tela: fora dele o botão da Sidebar nem aparece.
interface ReportImagesPanelStore {
  isOpen: boolean
  setOpen: (isOpen: boolean) => void
  toggle: () => void
  editorMounted: boolean
  setEditorMounted: (editorMounted: boolean) => void
}

export const useReportImagesPanelStore = create<ReportImagesPanelStore>((set) => ({
  isOpen: true,
  setOpen: (isOpen) => set({ isOpen }),
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  editorMounted: false,
  setEditorMounted: (editorMounted) => set({ editorMounted }),
}))
