import { useCallback, useLayoutEffect, useRef, useState } from 'react'
import { stepsData } from '../constants/steps'
import { useProspectingStore } from '../stores/useProspectingStore'

const steps = stepsData.map((step) => ({
  name: step.name,
  substeps: step.substeps,
}))

export function StepsBar() {
  const { step: currentStep, substep: currentSubstep } = useProspectingStore()

  const timeline = steps.flatMap((step, stepIndex) => [
    {
      type: 'step' as const,
      label: step.name,
      stepIndex,
      substepIndex: null,
    },
    ...step.substeps.map((substep, substepIndex) => ({
      type: 'sub' as const,
      label: substep.name,
      stepIndex,
      substepIndex,
    })),
  ])

  const currentIndex = timeline.findIndex((item) => {
    if (currentSubstep === null) {
      return item.type === 'step' && item.stepIndex === currentStep
    }

    return (
      item.type === 'sub' &&
      item.stepIndex === currentStep &&
      item.substepIndex === currentSubstep
    )
  })

  const safeCurrentIndex = currentIndex === -1 ? 0 : currentIndex

  // Os rótulos abaixo de cada bolinha têm larguras bem diferentes ("Input
  // Inicial" vs "Refinamento de Parâmetros"), então com justify-between os
  // itens do timeline NÃO ficam espaçados em frações iguais de índice - uma
  // largura de linha calculada só por porcentagem (index/(N-1)) nunca bate
  // com o centro real de cada bolinha. Em vez disso, medimos a posição real
  // no DOM de cada bolinha (via ref) e desenhamos a linha entre os centros
  // medidos, não por estimativa percentual.
  const containerRef = useRef<HTMLDivElement>(null)
  const dotRefs = useRef<(HTMLDivElement | null)[]>([])
  const [line, setLine] = useState({ startX: 0, endX: 0, activeEndX: 0 })

  const measure = useCallback(() => {
    const container = containerRef.current
    const firstDot = dotRefs.current[0]
    const lastDot = dotRefs.current[timeline.length - 1]
    const activeDot = dotRefs.current[safeCurrentIndex]
    if (!container || !firstDot || !lastDot || !activeDot) return

    const containerRect = container.getBoundingClientRect()
    const centerOf = (el: HTMLDivElement) => {
      const rect = el.getBoundingClientRect()
      return rect.left + rect.width / 2 - containerRect.left
    }

    setLine({
      startX: centerOf(firstDot),
      endX: centerOf(lastDot),
      activeEndX: centerOf(activeDot),
    })
  }, [safeCurrentIndex, timeline.length])

  useLayoutEffect(() => {
    measure()
  }, [measure])

  // Recalcula a medição quando o CONTAINER muda de tamanho (não só a janela)
  // - cobre redimensionar a janela, mas também abrir/fechar a sidebar ou
  // qualquer outra mudança de layout que afete a largura da barra sem
  // disparar um resize da janela em si.
  useLayoutEffect(() => {
    const container = containerRef.current
    if (!container) return
    const observer = new ResizeObserver(() => measure())
    observer.observe(container)
    return () => observer.disconnect()
  }, [measure])

  return (
    <div className="sticky top-0 bg-gray-200 border-b border-gray-300 px-6 pt-4 pb-2">
      <div className="relative">
        <div ref={containerRef} className="relative flex items-start justify-between">
          {/* Linha base */}
          <div
            className="absolute top-4 h-1 bg-gray-300 -translate-y-1/2 z-0"
            style={{ left: `${line.startX}px`, width: `${line.endX - line.startX}px` }}
          />

          {/* Linha ativa */}
          <div
            className="absolute top-4 h-1 bg-[#0f9448] -translate-y-1/2 z-0 transition-all duration-500 ease-out"
            style={{ left: `${line.startX}px`, width: `${line.activeEndX - line.startX}px` }}
          />

          {timeline.map((item, index) => {
            const isActive = index === safeCurrentIndex
            const isDone = index < safeCurrentIndex

            return (
              <div key={index} className="flex flex-col items-center z-10">
                {item.type === 'step' ? (
                  <>
                    <div
                      ref={(el) => { dotRefs.current[index] = el }}
                      className={`
                        w-8 h-8 rounded-full flex items-center justify-center
                        text-xs font-bold transition-all duration-300
                        ${isActive
                          ? 'bg-[#0f9448] text-white'
                          : isDone
                            ? 'bg-[#185f37] text-white'
                            : 'bg-white text-gray-500 border border-gray-300'
                        }
                      `}
                    >
                      {item.stepIndex + 1}
                    </div>

                    <span
                      className={`
                        text-xs font-semibold mt-2 whitespace-nowrap transition-colors
                        ${isActive || isDone ? 'text-gray-900' : 'text-gray-500'}
                      `}
                    >
                      {item.label}
                    </span>
                  </>
                ) : (
                  <>
                    <div
                      ref={(el) => { dotRefs.current[index] = el }}
                      className="w-8 h-8 flex items-center justify-center"
                    >
                      <div
                        className={`
                          w-4 h-4 rounded-full transition-all duration-300 border-2
                          ${isActive
                            ? 'bg-[#0f9448] border-[#0f9448]'
                            : isDone
                              ? 'bg-[#185f37] border-[#185f37]'
                              : 'bg-white border-gray-300'
                          }
                        `}
                      />
                    </div>

                    <span
                      className={`
                        text-[10px] font-semibold mt-2 whitespace-nowrap transition-colors
                        ${isActive || isDone ? 'text-gray-900' : 'text-gray-500'}
                      `}
                    >
                      {item.label}
                    </span>
                  </>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
