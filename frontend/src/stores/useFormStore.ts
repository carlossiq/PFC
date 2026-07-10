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
  // Nome da sessão, definido pelo usuário ao clicar em "Start" na sidebar,
  // antes mesmo de preencher o Step1. Enviado ao backend junto com o resto
  // do session_input quando a sessão é finalizada.
  sessionName: string
  setSessionName: (name: string) => void

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

  // Contador de iterações de refinamento por IA da sessão atual: +1 ao clicar
  // "Refinar parâmetros" (Step1), +1 a cada "Generate Others Parameters" e +1 a
  // cada "Especializar" (Step2). Resetado a 0 quando o usuário edita o input
  // original do Step1. Não é enviado ao backend a cada ação - só quando a sessão
  // é finalizada, junto com o restante do session_input.
  step2Iterations: number
  incrementStep2Iterations: () => void
  resetStep2Iterations: () => void

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
  sessionName: '',
  input: defaultInput,
  generated: defaultGenerated,
  step2SelectedTheme: null,
  step2Candidates: [],
  shouldRegenerateStep2: true,
  step2Iterations: 0,

  setSessionName: (name) =>
    set({
      sessionName: name,
    }),

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

  incrementStep2Iterations: () =>
    set((state) => ({
      step2Iterations: state.step2Iterations + 1,
    })),

  resetStep2Iterations: () =>
    set({
      step2Iterations: 0,
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
      sessionName: '',
      input: defaultInput,
      generated: defaultGenerated,
      step2SelectedTheme: null,
      step2Candidates: [],
      shouldRegenerateStep2: true,
      step2Iterations: 0,
    }),
}))
