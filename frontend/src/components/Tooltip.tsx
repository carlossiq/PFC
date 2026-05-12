export function Tooltip({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="relative group flex justify-center">
      {children}

      <span
        className="
          absolute left-full ml-3 top-1/2 -translate-y-1/2
          opacity-0 group-hover:opacity-100 pointer-events-none
          transition-opacity duration-200
          bg-[#0f172a] text-white text-xs px-2 py-1 rounded shadow-lg
          whitespace-nowrap z-50
        "
      >
        {label}
      </span>
    </div>
  )
}