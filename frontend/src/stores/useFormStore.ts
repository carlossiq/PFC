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

  // Parâmetros gerados pela IA no Step2, persistidos entre montagens do
  // componente (ex: ao navegar para outro step e voltar) para que não sejam
  // recriados à toa. Só devem ser regenerados quando: (1) o usuário clica em
  // "Generate Others Parameters", (2) o usuário volta ao Step1 e clica em
  // "Refinar parâmetros" de novo, ou (4) uma nova sessão é iniciada (o store
  // não é persistido, então reseta sozinho). O caso (3) - especializar um
  // tema - atualiza só o card selecionado, sem tocar nos demais.
  step2Candidates: SelectedTheme[]
  setStep2Candidates: (candidates: SelectedTheme[]) => void

  // Sinaliza que a próxima montagem do Step2 deve regenerar os parâmetros do
  // zero. Setado ao clicar em "Refinar parâmetros" no Step1; consumido (volta
  // a false) assim que o Step2 monta e dispara a geração.
  shouldRegenerateStep2: boolean
  setShouldRegenerateStep2: (value: boolean) => void

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
  step2Candidates: [],
  shouldRegenerateStep2: true,
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

  setStep2Candidates: (candidates) =>
    set({
      step2Candidates: candidates,
    }),

  setShouldRegenerateStep2: (value) =>
    set({
      shouldRegenerateStep2: value,
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
      step2Candidates: [],
      shouldRegenerateStep2: true,
      paramInitId: null,
    }),
}))
