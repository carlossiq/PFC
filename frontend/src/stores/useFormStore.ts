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

  // Estado do Step2 (tema selecionado)
  step2SelectedTheme: SelectedTheme | null
  setStep2SelectedTheme: (theme: SelectedTheme | null) => void

  // Id da tupla PARAM_INIT já persistida no backend (null se ainda não salva)
  paramInitId: number | null
  setParamInitId: (id: number | null) => void

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
  paramInitId: null,

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

  setParamInitId: (id) =>
    set({
      paramInitId: id,
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
      paramInitId: null,
    }),
}))
