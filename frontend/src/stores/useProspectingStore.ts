import { create } from 'zustand'
import { stepsData, TOTAL_STEPS } from '../constants/steps'

// Gerencia apenas o estado do workflow (steps e substeps)
interface ProspectingStore {
  step: number
  substep: number | null
  setStep: (step: number, substep?: number | null) => void
  nextStep: () => void
  prevStep: () => void
  reset: () => void
}

export const useProspectingStore = create<ProspectingStore>((set) => ({
  step: 0,
  substep: null,

  setStep: (step, substep = null) =>
    set({
      step: Math.max(0, Math.min(step, TOTAL_STEPS - 1)),
      substep,
    }),

  nextStep: () =>
    set((state) => {
      const currentStepData = stepsData[state.step]
      const hasSubsteps = currentStepData.substeps.length > 0

      // Se está em um step com substeps e ainda não entrou no substep, ir para o substep
      if (hasSubsteps && state.substep === null) {
        return { substep: 0 }
      }

      // Se está em um substep, ir para o próximo step
      if (state.substep !== null) {
        return {
          step: Math.min(state.step + 1, TOTAL_STEPS - 1),
          substep: null,
        }
      }

      // Se é um step sem substeps, ir para o próximo step
      return {
        step: Math.min(state.step + 1, TOTAL_STEPS - 1),
        substep: null,
      }
    }),

  prevStep: () =>
    set((state) => {
      // Se está em um substep, voltar para o step anterior (sem substep)
      if (state.substep !== null) {
        return { substep: null }
      }

      // Se está em um step, voltar para o step anterior
      return {
        step: Math.max(state.step - 1, 0),
        substep: null,
      }
    }),

  reset: () =>
    set({
      step: 0,
      substep: null,
    }),
}))
