import { useState } from 'react'
import { HelpCircle, User, Power, ChevronLeft, ChevronRight, Settings, Search, ChartNoAxesCombined } from 'lucide-react'
import { Tooltip } from './Tooltip';
import { Modal } from './Modal'
import { useSidebarStore } from '../stores/useSidebarStore'
import { useWorkflowStore } from '../stores/useWorkflowStore'
import { useFormStore } from '../stores/useFormStore'
import { TABS } from '../constants/tabs'

export function Sidebar() {
  const { collapsed, toggleCollapsed, setCollapsed, locked } = useSidebarStore()
  const { tab, setTab } = useWorkflowStore()
  const { sessionName, setSessionName } = useFormStore()
  const [showConfirm, setShowConfirm] = useState(false)
  const [nameError, setNameError] = useState(false)

  const handleStartProspection = () => {
    setNameError(false)
    setShowConfirm(true)
  }

  const handleConfirmProspection = () => {
    if (!sessionName.trim()) {
      setNameError(true)
      return
    }
    setShowConfirm(false)
    if (!collapsed) {
      setCollapsed(true)
    }
    setTab(TABS.START_PROSPECTION)
  }
  const usedAi = 'GEMINI 2.5';
  const usedPatent = 'OPS';
  const usedArticles = 'SCOPUS';

  return (
    <aside
      className={`
    h-[calc(100vh-5rem)]
    bg-[#17212b]
    transition-[width] duration-300 ease-in-out
    ${collapsed ? 'w-16' : 'w-65'}
    ${locked ? 'pointer-events-none text-gray-500' : 'text-white'}
  `}
    >
      <div className="h-full flex flex-col px-3 py-6">

        {/* Toggle */}
        <div className="flex justify-end mb-4">
          <button
            onClick={toggleCollapsed}
            className="p-1 hover:bg-white/10 rounded-full"
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        {/* New project */}
        <button
          onClick={handleStartProspection}
          className={`
            h-10 rounded-full
            text-sm font-semibold
            flex items-center justify-center
            transition-colors
            ${locked ? 'bg-gray-700 cursor-not-allowed text-gray-300' : 'bg-[#0f9448] hover:bg-[#0d843f] text-white'}
          `}
        >
          {collapsed ? <Tooltip label="Start prospection"><Power size={18} /></Tooltip> : 'Start'}
        </button>

        {/* Links */}
        <nav className="mt-6 space-y-1 text-sm">
          <SidebarItem label="Settings" active={tab === TABS.SETTINGS} collapsed={collapsed} icon={<Settings />} description='Settings' onClick={() => setTab(TABS.SETTINGS)} />
          <SidebarItem label="Statistics" active={tab === TABS.STATISTICS} collapsed={collapsed} icon={<ChartNoAxesCombined />} description='Statistics' onClick={() => setTab(TABS.STATISTICS)} />
          <SidebarItem label="Search" active={tab === TABS.SEARCH} collapsed={collapsed} icon={<Search />} description='Search' onClick={() => setTab(TABS.SEARCH)} />
        </nav>

        <div className="my-6 border-t border-[#344250]" />

        {/* Tags */}
        {/* {!collapsed && (
          <>
            <p className="text-xs font-bold tracking-wide text-gray-300 mb-2">
              ORGANIZE TAGS
            </p>

            <button className="flex items-center gap-2 text-sm hover:text-[#27e27a]">
              <Plus size={16} />
              New tag
            </button>
          </>
        )} */}

        {/* Bottom */}
        <div className="mt-auto px-2 pb-4">
          <div
            className={`
      flex items-center transition-all duration-300
      ${collapsed ? 'flex-col gap-5' : 'flex-row gap-4'}
    `}
          >
            <button
              onClick={() => setTab(TABS.HELP)}
              className={`p-2 rounded-md transition-colors ${locked ? 'text-gray-500 cursor-not-allowed' : 'hover:bg-white/10 hover:text-[#27e27a]'}`}
            >
              <HelpCircle className="w-6 h-6" />
            </button>

            <button
              onClick={() => setTab(TABS.USER)}
              className={`p-2 rounded-md transition-colors ${locked ? 'text-gray-500 cursor-not-allowed' : 'hover:bg-white/10 hover:text-[#27e27a]'}`}
            >
              <User className="w-6 h-6" />
            </button>
          </div>

          <div
            className={`
      mt-5 text-xs font-bold tracking-wide text-gray-300
      transition-all duration-500 ease-in-out overflow-hidden
      ${collapsed ? 'opacity-0 max-h-0 pointer-events-none' : 'opacity-100 max-h-24 flex flex-col gap-1'}
    `}
          >
            <p className="transition-opacity duration-500">LLM: {usedAi}</p>
            <p className="transition-opacity duration-500">API Patentes: {usedPatent}</p>
            <p className="transition-opacity duration-500">API Artigos: {usedArticles}</p>
          </div>
        </div>
      </div>

      <Modal
        isOpen={showConfirm}
        title="Start Prospection"
        message="Dê um nome para essa sessão de prospecção antes de começar."
        confirmText="Start"
        cancelText="Cancel"
        onConfirm={handleConfirmProspection}
        onCancel={() => setShowConfirm(false)}
        input={{
          label: "Nome da sessão",
          value: sessionName,
          onChange: (value) => {
            setSessionName(value)
            if (value.trim()) setNameError(false)
          },
          placeholder: "Ex: Drones militares 2026",
          error: nameError,
          errorMessage: "Nome da sessão é obrigatório",
        }}
      />
    </aside>
  )
}

function SidebarItem({
  label,
  collapsed,
  active = false,
  icon,
  description,
  onClick,
}: {
  label: string
  collapsed: boolean
  active?: boolean
  icon?: React.ReactNode
  description: string
  onClick?: () => void
}) {
  return (
    <>
      {collapsed ? <Tooltip label={description}><button onClick={onClick} className={`place-self-center rounded p-2 hover:bg-white/10
      ${active ? 'bg-[#185f37] font-semibold' : ''}`}>
        {icon && collapsed && <span className=" [&>svg]:w-7 [&>svg]:h-7" >{icon}</span>}
      </button></Tooltip> : <button onClick={onClick}
        className={`
      px-3 py-2 rounded text-sm w-full text-left
      ${active ? 'bg-[#185f37] font-semibold' : 'hover:bg-white/10'}
      `}
      >
        {label}
      </button>
      }
    </>

  )
}