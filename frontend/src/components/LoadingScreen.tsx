interface LoadingScreenProps {
  message?: string
  fullscreen?: boolean
}

// Spinner reutilizável para estados de carregamento (ex: aguardando resposta da IA).
// Por padrão renderiza inline, centralizado no espaço do container pai; com
// fullscreen, cobre a tela inteira como um overlay (útil para carregamentos
// que bloqueiam a tela toda, não só uma seção).
export function LoadingScreen({ message = 'Carregando...', fullscreen = false }: LoadingScreenProps) {
  const content = (
    <div className="flex flex-col items-center justify-center gap-3 py-10">
      <div className="w-10 h-10 border-4 border-gray-200 border-t-[#0f9448] rounded-full animate-spin" />
      {message && <p className="text-sm font-medium text-gray-600">{message}</p>}
    </div>
  )

  if (!fullscreen) {
    return content
  }

  return (
    <div className="fixed inset-0 bg-white/80 flex items-center justify-center z-50">
      {content}
    </div>
  )
}
