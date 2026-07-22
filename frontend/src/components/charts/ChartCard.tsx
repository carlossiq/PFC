import type { ReactNode } from 'react'

const DEFAULT_EMPTY_MESSAGE = 'Nenhuma sessão encontrada ainda - inicie uma prospecção pra ver estatísticas aqui.'

interface ChartCardProps {
  title: string
  description?: string
  /** 'half' pra gráficos lado a lado (grid 2 colunas), 'full' pra largura da página. */
  width?: 'half' | 'full'
  /** Conteúdo à direita do título (ex: toggle Gráfico/Tabela). */
  headerExtra?: ReactNode
  /** Linha extra abaixo do cabeçalho (ex: legenda de cores). */
  legend?: ReactNode
  isEmpty?: boolean
  emptyMessage?: string
  children?: ReactNode
}

// Card padrão de todo gráfico da página de Estatísticas - mesmo container,
// mesmo cabeçalho (título + descrição) e mesmo estado vazio em todos, pra não
// reescrever esse invólucro a cada gráfico novo.
export function ChartCard({
  title,
  description,
  width = 'full',
  headerExtra,
  legend,
  isEmpty,
  emptyMessage = DEFAULT_EMPTY_MESSAGE,
  children,
}: ChartCardProps) {
  const widthClass = width === 'half' ? 'w-1/2' : 'w-full'

  if (isEmpty) {
    return (
      <div className={`rounded-xl border-2 border-gray-200 bg-white shadow-sm p-6 ${widthClass}`}>
        <h3 className="font-bold text-base text-gray-900 mb-1">{title}</h3>
        <p className="text-sm text-gray-500">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className={`rounded-xl border-2 border-gray-200 bg-white shadow-sm p-6 ${widthClass}`}>
      <div className={`flex items-start justify-between gap-3 ${legend ? 'mb-2' : 'mb-4'}`}>
        <div>
          <h3 className="font-bold text-base text-gray-900">{title}</h3>
          {description && <p className="text-xs text-gray-500 mt-1">{description}</p>}
        </div>
        {headerExtra && <div className="shrink-0">{headerExtra}</div>}
      </div>

      {legend && <div className="flex items-center gap-4 text-xs text-gray-600 mb-2">{legend}</div>}

      {children}
    </div>
  )
}
