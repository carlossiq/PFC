import { create } from 'zustand'

// Dados de entrada do formulário (durante edição ou persistidos)
interface InputData {
  theme: string
  description: string | null
  keywords: string | null
  studyArea: string | null
}

// Dados gerados pelo sistema (mesma estrutura que InputData)
interface GeneratedData {
  theme: string | null
  description: string | null
  keywords: string[] | null
  studyArea: string[] | null
}

interface SelectedTheme {
  id: string
  theme: string
  description: string
  keywords?: string[]
  studyArea?: string[]
}

// Gerencia dados de entrada e parâmetros gerados
interface FormStore {
  // Dados em edição/persistidos
  input: InputData
  setInput: (data: Partial<InputData>) => void

  // Dados gerados pelo sistema
  generated: GeneratedData
  setGenerated: (data: Partial<GeneratedData>) => void

  // Estado do Step2 (tema selecionado e set de temas)
  step2SelectedTheme: SelectedTheme | null
  setStep2SelectedTheme: (theme: SelectedTheme | null) => void

  step2ThemeSet: number
  setStep2ThemeSet: (themeSet: number) => void

  // Utilitários
  getFormData: () => {
    input: InputData
    generated: GeneratedData
  }
  reset: () => void
}

const defaultInput: InputData = {
  theme: '',
  description: '',
  keywords: '',
  studyArea: '',
}

const defaultGenerated: GeneratedData = {
  theme: null,
  description: null,
  keywords: null,
  studyArea: null,
}

export const useFormStore = create<FormStore>((set, get) => ({
  input: defaultInput,
  generated: defaultGenerated,
  step2SelectedTheme: null,
  step2ThemeSet: 1,

  setInput: (data) =>
    set((state) => ({
      input: { ...state.input, ...data },
    })),

  setGenerated: (data) =>
    set((state) => ({
      generated: { ...state.generated, ...data },
    })),

  setStep2SelectedTheme: (theme) =>
    set({
      step2SelectedTheme: theme,
    }),

  setStep2ThemeSet: (themeSet) =>
    set({
      step2ThemeSet: themeSet,
    }),

  getFormData: () => {
    const state = get()
    return {
      input: state.input,
      generated: state.generated,
    }
  },

  reset: () =>
    set({
      input: defaultInput,
      generated: defaultGenerated,
      step2SelectedTheme: null,
      step2ThemeSet: 1,
    }),
}))
