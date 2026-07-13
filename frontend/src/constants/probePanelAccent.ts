import type { ProbeApi } from './probeFields'

// Identidade visual por API, usada no ícone do cabeçalho do card de
// Resultados Iniciais - diferencia os dois painéis sem competir com o verde
// (#0f9448) que já é a cor de ação principal do resto da tela.
export const PANEL_ACCENT: Record<ProbeApi, { icon: string }> = {
  ops: { icon: 'bg-indigo-50 text-indigo-600' },
  scopus: { icon: 'bg-teal-50 text-teal-600' },
}
