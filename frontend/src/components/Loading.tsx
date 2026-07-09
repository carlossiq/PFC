import loadingIcon from '../assets/loading.svg'

interface LoadingProps {
  message?: string
  transparent?: boolean
}

export function Loading({ message, transparent = false }: LoadingProps) {
  return (
    <div
      className={`
        w-full h-full flex flex-col items-center justify-center gap-3
        ${transparent ? 'bg-transparent' : 'bg-gray-200'}
      `}
    >
      <img src={loadingIcon} alt="Carregando" className="w-16 h-16" />
      {message && <p className="text-sm text-gray-500">{message}</p>}
    </div>
  )
}
