interface ToggleProps {
  enabled: boolean
  onChange: (enabled: boolean) => void
}

export function Toggle({ enabled, onChange }: ToggleProps) {
  return (
    <button
      onClick={() => onChange(!enabled)}
      className={`
        w-12 h-6 flex items-center rounded-full p-1 transition-colors
        ${enabled ? 'bg-[#0f9448]' : 'bg-gray-300'}
      `}
    >
      <div
        className={`
          w-4 h-4 bg-white rounded-full shadow-md transform transition-transform
          ${enabled ? 'translate-x-6' : 'translate-x-0'}
        `}
      />
    </button>
  )
}
