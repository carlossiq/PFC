import type { ReactNode } from 'react'

interface FieldCardProps {
  label: string
  children: ReactNode
}

// Caixinha padrão de "campo com rótulo" usada em vários lugares que mostram
// detalhes de um item (parâmetros de sessão no SessionCard, campos do tema no
// Step2, campos da query no Step3): rótulo pequeno em cima, valor em baixo.
// O valor fica livre (children) porque varia entre texto simples, lista
// numerada (keywords) ou texto monoespaçado (CQL).
export function FieldCard({ label, children }: FieldCardProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-600 font-medium mb-1">{label}</p>
      {children}
    </div>
  )
}
