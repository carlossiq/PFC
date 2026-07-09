import { useRef, useState } from 'react'
import { createPortal } from 'react-dom'

interface TooltipProps {
  label: string
  children: React.ReactNode
  position?: 'top' | 'right' | 'bottom' | 'left'
}

export function Tooltip({
  label,
  children,
  position = 'right',
}: TooltipProps) {
  const ref = useRef<HTMLDivElement>(null)

  const [visible, setVisible] = useState(false)
  const [coords, setCoords] = useState({ top: 0, left: 0 })

  function showTooltip() {
    if (!ref.current) return

    const rect = ref.current.getBoundingClientRect()

    switch (position) {
      case 'top':
        setCoords({
          top: rect.top - 8,
          left: rect.left + rect.width / 2,
        })
        break

      case 'bottom':
        setCoords({
          top: rect.bottom + 8,
          left: rect.left + rect.width / 2,
        })
        break

      case 'left':
        setCoords({
          top: rect.top + rect.height / 2,
          left: rect.left - 8,
        })
        break

      case 'right':
      default:
        setCoords({
          top: rect.top + rect.height / 2,
          left: rect.right + 8,
        })
        break
    }

    setVisible(true)
  }

  const transform = {
    top: '-translate-x-1/2 -translate-y-full',
    bottom: '-translate-x-1/2',
    left: '-translate-x-full -translate-y-1/2',
    right: 'translate-y-[-50%]',
  }[position]

  return (
    <>
      <div
        ref={ref}
        className="inline-flex"
        onMouseEnter={showTooltip}
        onMouseLeave={() => setVisible(false)}
      >
        {children}
      </div>

      {visible &&
        createPortal(
          <div
            className={`
              fixed
              ${transform}
              bg-[#0f172a]
              text-white
              text-xs
              px-3
              py-2
              rounded
              shadow-lg
              max-w-lg
              min-w-31
              whitespace-normal
              pointer-events-none
              text-center
              
            `}
            style={{
              top: coords.top,
              left: coords.left,
            }}
          >
            {label}
          </div>,
          document.body
        )}
    </>
  )
}