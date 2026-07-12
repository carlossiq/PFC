import { create } from 'zustand'
import type { QueryOptionResult } from '../services/probeQuery'

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

  // Estado do Step3 (queries geradas por IA): N tentativas independentes (não
  // são variantes nomeadas - só chamadas repetidas com a mesma instrução, ver
  // ChatService.build_probe_queries_multi), qual delas está selecionada (por
  // índice), e o intake (tema/descrição/keywords resolvido) que gerou essas
  // queries - usado pra comparar com o intake atual e decidir se regenera ao
  // reentrar no Step3, em vez de um flag manual que os callers precisariam
  // lembrar de setar. Assim as queries (e edições feitas nelas) sobrevivem à
  // navegação Voltar/Próximo e só são recriadas se o parâmetro realmente
  // mudou, ou se o usuário clicar em "Gerar outras".
  step3Queries: QueryOptionResult[] | null
  setStep3Queries: (queries: QueryOptionResult[], generatedForIntake: string) => void
  updateStep3QueryAt: (index: number, patch: Partial<QueryOptionResult>) => void

  step3SelectedIndex: number | null
  setStep3SelectedIndex: (index: number | null) => void

  step3GeneratedForIntake: string | null

  step3Iterations: number
  incrementStep3Iterations: () => void
  resetStep3Iterations: () => void

  // Espelha o bloco step3* acima, mas pra queries de artigos (Scopus) - a
  // segunda seção do Step3. Mesmo padrão de comparação de assinatura do
  // intake pra decidir regeneração, independente da seção de patentes.
  step3ArticleQueries: QueryOptionResult[] | null
  setStep3ArticleQueries: (queries: QueryOptionResult[], generatedForIntake: string) => void
  updateStep3ArticleQueryAt: (index: number, patch: Partial<QueryOptionResult>) => void

  step3ArticleSelectedIndex: number | null
  setStep3ArticleSelectedIndex: (index: number | null) => void

  step3ArticleGeneratedForIntake: string | null

  step3ArticleIterations: number
  incrementStep3ArticleIterations: () => void
  resetStep3ArticleIterations: () => void

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
  step3Queries: null,
  step3SelectedIndex: null,
  step3GeneratedForIntake: null,
  step3Iterations: 0,
  step3ArticleQueries: null,
  step3ArticleSelectedIndex: null,
  step3ArticleGeneratedForIntake: null,
  step3ArticleIterations: 0,

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

  setStep3Queries: (queries, generatedForIntake) =>
    set({
      step3Queries: queries,
      step3GeneratedForIntake: generatedForIntake,
    }),

  updateStep3QueryAt: (index, patch) =>
    set((state) => {
      if (!state.step3Queries) return {}
      return {
        step3Queries: state.step3Queries.map((q, i) => (i === index ? { ...q, ...patch } : q)),
      }
    }),

  setStep3SelectedIndex: (index) =>
    set({
      step3SelectedIndex: index,
    }),

  incrementStep3Iterations: () =>
    set((state) => ({
      step3Iterations: state.step3Iterations + 1,
    })),

  resetStep3Iterations: () =>
    set({
      step3Iterations: 0,
    }),

  setStep3ArticleQueries: (queries, generatedForIntake) =>
    set({
      step3ArticleQueries: queries,
      step3ArticleGeneratedForIntake: generatedForIntake,
    }),

  updateStep3ArticleQueryAt: (index, patch) =>
    set((state) => {
      if (!state.step3ArticleQueries) return {}
      return {
        step3ArticleQueries: state.step3ArticleQueries.map((q, i) => (i === index ? { ...q, ...patch } : q)),
      }
    }),

  setStep3ArticleSelectedIndex: (index) =>
    set({
      step3ArticleSelectedIndex: index,
    }),

  incrementStep3ArticleIterations: () =>
    set((state) => ({
      step3ArticleIterations: state.step3ArticleIterations + 1,
    })),

  resetStep3ArticleIterations: () =>
    set({
      step3ArticleIterations: 0,
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
      step3Queries: null,
      step3SelectedIndex: null,
      step3GeneratedForIntake: null,
      step3Iterations: 0,
      step3ArticleQueries: null,
      step3ArticleSelectedIndex: null,
      step3ArticleGeneratedForIntake: null,
      step3ArticleIterations: 0,
    }),
}))
