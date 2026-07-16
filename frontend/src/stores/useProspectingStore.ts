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

      // Se está em um step com substeps e ainda não entrou no substep, ir para o primeiro substep
      if (hasSubsteps && state.substep === null) {
        return { substep: 0 }
      }

      // Se está num substep e ainda há um próximo substep no mesmo step, avança pra ele
      if (hasSubsteps && state.substep !== null && state.substep + 1 < currentStepData.substeps.length) {
        return { substep: state.substep + 1 }
      }

      // Último substep (ou step sem substeps): vai pro próximo step, do zero
      return {
        step: Math.min(state.step + 1, TOTAL_STEPS - 1),
        substep: null,
      }
    }),

  prevStep: () =>
    set((state) => {
      // Se está num substep além do primeiro, volta pro substep anterior no mesmo step
      if (state.substep !== null && state.substep > 0) {
        return { substep: state.substep - 1 }
      }

      // Primeiro substep: volta pra tela "principal" do step (substep null)
      if (state.substep !== null) {
        return { substep: null }
      }

      // Se está num step sem substep ativo, volta pro step anterior
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
