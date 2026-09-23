import { Image as ImageIcon } from 'lucide-react'
import { Tooltip } from './Tooltip'
import { useSidebarStore } from '../stores/useSidebarStore'
import { useReportImagesPanelStore } from '../stores/useReportImagesPanelStore'

// Ícone de imagem na sidebar (mesmo padrão visual do SaveProgressButton) -
// abre/fecha o painel "Imagens" do editor do .tex. Só renderizado pelo
// Sidebar enquanto o editor está na tela (editorMounted). Verde quando o
// painel está aberto, sem fundo quando fechado.
export function ReportImagesToggleButton() {
  const { collapsed } = useSidebarStore()
  const { isOpen, toggle } = useReportImagesPanelStore()
  const label = isOpen ? 'Fechar imagens' : 'Abrir imagens'

  const button = (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      aria-pressed={isOpen}
      className={`pointer-events-auto shrink-0 w-9 h-9 rounded-sm flex items-center justify-center text-white transition-colors ${
        isOpen ? 'bg-[#0f9448] hover:bg-[#0d843f]' : 'hover:bg-white/10'
      }`}
    >
      <ImageIcon size={30} />
    </button>
  )

  return (
    <div className={`flex flex-col items-center gap-1 mb-4 ${collapsed ? '' : 'self-start'}`}>
      {collapsed ? <Tooltip label={label}>{button}</Tooltip> : button}
    </div>
  )
}
