import { useEffect, useRef, useState } from 'react'

// Largura do gráfico segue o container (ex: metade da página, via CSS) - todo
// gráfico SVG da página de estatísticas usa o mesmo ResizeObserver em vez de
// reimplementar a medição a cada componente. `enabled=false` pausa a
// observação (ex: enquanto o card mostra uma tabela em vez do SVG).
export function useChartWidth(initialWidth: number, enabled = true) {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(initialWidth)

  useEffect(() => {
    if (!enabled) return
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width
      if (w) setWidth(Math.round(w))
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [enabled])

  return { ref, width }
}
