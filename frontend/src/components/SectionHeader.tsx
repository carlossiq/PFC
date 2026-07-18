import type { ReactNode } from 'react'

interface SectionHeaderProps {
  title: ReactNode
  description?: ReactNode
}

// Cabeçalho (título + descrição) 
export function SectionHeader({ title, description }: SectionHeaderProps) {
  return (
    <>
      <h2 className="text-2xl font-bold mb-1">{title}</h2>
      {description && <p className="text-sm text-gray-500 mb-6">{description}</p>}
    </>
  )
}
