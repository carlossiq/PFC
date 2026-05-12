import { useState, useRef, useEffect } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { Modal } from './Modal'
import { useWorkflowStore } from '../stores/useWorkflowStore'
import { TABS } from '../constants/tabs'

const docTopics = [
  { id: 'intro', title: 'Introduction', tab: TABS.DOCUMENTATION },
  { id: 'guia', title: 'User Guide', tab: TABS.DOC_USER_GUIDE },
  { id: 'api', title: 'API Reference', tab: TABS.DOC_API },
  { id: 'faq', title: 'FAQ', tab: TABS.DOC_FAQ },
]

export function Navbar() {
  const { tab, setTab } = useWorkflowStore()
  const prospecting = tab === TABS.START_PROSPECTION
  const [isDocsOpen, setIsDocsOpen] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [pendingTab, setPendingTab] = useState<number | null>(null)
  const docsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (docsRef.current && !docsRef.current.contains(event.target as Node)) {
        setIsDocsOpen(false)
      }
    }

    if (isDocsOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isDocsOpen])

  const handleDocClick = () => {
    setIsDocsOpen(!isDocsOpen)
  }

  const handleNavClick = (targetTab: number) => {
    if (prospecting) {
      setPendingTab(targetTab)
      setShowConfirm(true)
    } else {
      setTab(targetTab)
    }
  }

  const handleConfirmNavigation = () => {
    if (pendingTab !== null) {
      setTab(pendingTab)
      setPendingTab(null)
    }
    setShowConfirm(false)
  }

  const handleDocTopicClick = (topicTab: number) => {
    if (prospecting) {
      setPendingTab(topicTab)
      setShowConfirm(true)
    } else {
      setTab(topicTab)
      setIsDocsOpen(false)
    }
  }

  return (
    <nav className="w-full bg-[#17212b] text-white relative">
      <div className="h-20 px-12 flex items-center justify-between">
        <a href="/" className="flex items-center">
          <span className="text-[#029645] text-4xl font-bold tracking-tight" style={{ fontFamily: 'Anurati' }}>
            AGIA
          </span>
        </a>

        <div className="flex items-center gap-10 text-sm font-medium">
          <div className="relative" ref={docsRef}>
            <button
              onClick={handleDocClick}
              className={`flex items-center gap-2 transition-all ${isDocsOpen ? 'font-bold' : ''} hover:text-[#27e27a]`}
            >
              Documentation
              {isDocsOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </button>

            {isDocsOpen && (
              <div className="absolute top-full left-0 mt-2 bg-[#1a2635] border border-[#344250] rounded-lg shadow-lg py-2 z-50 min-w-48">
                {docTopics.map((topic) => (
                  <button
                    key={topic.id}
                    onClick={() => handleDocTopicClick(topic.tab)}
                    className={`w-full text-left px-4 py-2 hover:bg-white/10 transition-colors`}
                  >
                    {topic.title}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={() => handleNavClick(TABS.ABOUT)}
            className={`transition-all ${tab === TABS.ABOUT ? 'font-bold' : ''} hover:text-[#27e27a]`}
          >
            About
          </button>
          <span className="text-gray-400">v 1.0</span>
        </div>
      </div>

      <Modal
        isOpen={showConfirm}
        title="Exit Prospection?"
        message="You are in an ongoing prospection. Are you sure you want to exit?"
        confirmText="Exit"
        cancelText="Cancel"
        onConfirm={handleConfirmNavigation}
        onCancel={() => setShowConfirm(false)}
        isDangerous
      />
    </nav>
  )
}