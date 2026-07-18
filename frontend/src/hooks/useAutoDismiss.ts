import { useEffect } from 'react'

// Erros transitórios de chamadas de IA (limite de tokens/rate limit, falhas
// de rede) não precisam ficar na tela indefinidamente - o botão de "tentar
// novamente" já continua disponível, então o aviso some sozinho depois de
// um tempo em vez de exigir que o usuário o feche manualmente.
export function useAutoDismiss(value: string | null, onDismiss: () => void, delayMs = 5000) {
  useEffect(() => {
    if (!value) return
    const id = setTimeout(onDismiss, delayMs)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])
}
