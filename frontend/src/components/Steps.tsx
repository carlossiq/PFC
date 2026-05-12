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
    ...step.substeps.map((_, substepIndex) => ({
      type: 'sub' as const,
      label: '',
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

  const progress =
    timeline.length > 1
      ? (safeCurrentIndex / (timeline.length - 1)) * 100
      : 0

  return (
    <div className="sticky top-0 bg-gray-200 border-b border-gray-300 px-6 pt-4 pb-2">
      <div className="relative">
        <div className="relative flex items-start justify-between">
          {/* Linha base */}
          <div className="absolute top-4 left-4 right-4 h-1 bg-gray-300 -translate-y-1/2 z-0" />

          {/* Linha ativa */}
          <div
            className="absolute top-4 left-4 h-1 bg-[#0f9448] -translate-y-1/2 z-0 transition-all duration-500 ease-out"
            style={{
              width:
                safeCurrentIndex === 0
                  ? '0px'
                  : `calc((100% - 2rem) * ${progress / 100} - ${timeline[safeCurrentIndex]?.type === 'sub' ? '0.5rem' : '1rem'
                  })`,
            }}
          />

          {timeline.map((item, index) => {
            const isActive = index === safeCurrentIndex
            const isDone = index < safeCurrentIndex

            return (
              <div key={index} className="flex flex-col items-center z-10">
                {item.type === 'step' ? (
                  <>
                    <div
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
                  <div className="h-8 flex items-center">
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
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}