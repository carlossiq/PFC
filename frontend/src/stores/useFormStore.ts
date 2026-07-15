import { create } from 'zustand'
import type { ProbeSearchResult, QueryOptionResult } from '../services/probeQuery'
import type { AiUsage } from '../services/aiUsage'

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

// Patch aplicado por `hydrateFromSession` ao retomar uma sessão salva -
// mesmas chaves do FormStore, todas opcionais (só as que a sessão traz).
export type FormStorePatch = Partial<
  Pick<
    FormStore,
    | 'sessionId'
    | 'sessionPublicId'
    | 'sessionName'
    | 'input'
    | 'step2SelectedTheme'
    | 'step2Candidates'
    | 'step2GeneratedForInput'
    | 'step2Iterations'
    | 'step3Queries'
    | 'step3SelectedIndex'
    | 'step3GeneratedForIntake'
    | 'step3Iterations'
    | 'step3ArticleQueries'
    | 'step3ArticleSelectedIndex'
    | 'step3ArticleGeneratedForIntake'
    | 'step3ArticleIterations'
    | 'step3PatentResults'
    | 'step3PatentResultsQuery'
    | 'step3ArticleResults'
    | 'step3ArticleResultsQuery'
  >
>

// Gerencia dados de entrada e parâmetros gerados
interface FormStore {
  // Identifica a sessão já persistida no backend, uma vez que o primeiro save
  // (progresso ou finalização) acontece. null = sessão ainda não salva nenhuma
  // vez - o próximo save deve criar (POST); não-null - deve atualizar (PUT).
  sessionId: number | null
  sessionPublicId: string | null
  setSessionId: (id: number | null, publicId: string | null) => void

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
  // `generatedForInput`, quando informado, é a assinatura (JSON) do input do
  // Step1 que gerou esses candidatos - usada por "Refinar parâmetros" pra
  // decidir se o input mudou desde a última geração (ver handleRefineParameters
  // em Workflow.tsx). Omitido em updates que não são uma nova geração por IA
  // (ex: editar ou especializar um card já existente), pra não mascarar uma
  // mudança real de input.
  setStep2Candidates: (candidates: SelectedTheme[], generatedForInput?: string) => void

  // Assinatura do input usado na última geração de candidatos do Step2.
  step2GeneratedForInput: string | null

  // Sinaliza que a próxima montagem do Step2 deve regenerar os parâmetros do
  // zero. Setado ao clicar em "Refinar parâmetros" no Step1 quando o input
  // mudou desde a última geração; consumido (volta a false) assim que o
  // Step2 monta e dispara a geração.
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

  // Resultado da busca real (OPS/Scopus) disparada ao confirmar o Step3 -
  // preenchido só depois que as duas buscas (patente + artigo) terminam com
  // sucesso, consumido pela tela "Resultados Iniciais". null = ainda não
  // buscou (nunca deveria acontecer no fluxo normal, já que só se chega em
  // "Resultados Iniciais" vindo do Step3).
  // `*ResultsQuery` guarda a assinatura (JSON da query) que gerou esse
  // resultado - comparada com a query selecionada no momento do "Próximo"
  // pra decidir se a busca precisa rodar de novo (ver Step3.tsx) ou se dá
  // pra só reaproveitar o resultado já buscado (ex: usuário voltou de
  // "Resultados Iniciais" sem mudar a query selecionada).
  step3PatentResults: ProbeSearchResult | null
  step3PatentResultsQuery: string | null
  setStep3PatentResults: (result: ProbeSearchResult | null, querySignature: string | null) => void

  step3ArticleResults: ProbeSearchResult | null
  step3ArticleResultsQuery: string | null
  setStep3ArticleResults: (result: ProbeSearchResult | null, querySignature: string | null) => void

  // Log local de chamadas de IA medidas durante a sessão atual (duração +
  // tokens de cada resposta de /chat/*), acumulado a cada geração/refinamento
  // e reenviado como `ai_calls` no próximo save de progresso/finalização (ver
  // sessionInput.ts) - limpo após um save bem-sucedido pra não reenviar as
  // mesmas entradas duas vezes.
  aiCallLog: AiUsage[]
  addAiUsage: (usage: AiUsage | null | undefined) => void
  clearAiCallLog: () => void

  // Contador de chamadas de IA em andamento (Step2 refinar/especializar, Step3
  // gerar queries) - usado só pra travar os botões de salvar/finalizar
  // enquanto há uma resposta pendente, evitando salvar antes de addAiUsage
  // rodar (o que deixaria a chamada em andamento de fora do `ai_calls`
  // enviado). Contador em vez de boolean porque patente e artigo no Step3
  // podem gerar em paralelo.
  aiCallsInFlight: number
  beginAiCall: () => void
  endAiCall: () => void

  // Utilitários
  getFormData: () => {
    input: InputData
    generated: GeneratedData
  }
  reset: () => void

  // Repopula o form store a partir de uma sessão salva (ver
  // services/sessionHydration.ts), ao clicar "Continuar pesquisa" num card
  // pendente. Os resultados reais de busca (Step3) não são persistidos, então
  // são sempre zerados aqui - o usuário rebusca ao reconfirmar o Step3.
  hydrateFromSession: (patch: FormStorePatch) => void
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
  sessionId: null,
  sessionPublicId: null,
  sessionName: '',
  input: defaultInput,
  generated: defaultGenerated,
  step2SelectedTheme: null,
  step2Candidates: [],
  step2GeneratedForInput: null,
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
  step3PatentResults: null,
  step3PatentResultsQuery: null,
  step3ArticleResults: null,
  step3ArticleResultsQuery: null,
  aiCallLog: [],
  aiCallsInFlight: 0,

  setSessionId: (id, publicId) =>
    set({
      sessionId: id,
      sessionPublicId: publicId,
    }),

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

  setStep2Candidates: (candidates, generatedForInput) =>
    set((state) => ({
      step2Candidates: candidates,
      step2GeneratedForInput:
        generatedForInput !== undefined ? generatedForInput : state.step2GeneratedForInput,
    })),

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

  setStep3PatentResults: (result, querySignature) =>
    set({
      step3PatentResults: result,
      step3PatentResultsQuery: querySignature,
    }),

  setStep3ArticleResults: (result, querySignature) =>
    set({
      step3ArticleResults: result,
      step3ArticleResultsQuery: querySignature,
    }),

  addAiUsage: (usage) => {
    if (!usage) return
    set((state) => ({
      aiCallLog: [...state.aiCallLog, usage],
    }))
  },

  clearAiCallLog: () =>
    set({
      aiCallLog: [],
    }),

  beginAiCall: () =>
    set((state) => ({
      aiCallsInFlight: state.aiCallsInFlight + 1,
    })),

  endAiCall: () =>
    set((state) => ({
      aiCallsInFlight: Math.max(0, state.aiCallsInFlight - 1),
    })),

  getFormData: () => {
    const state = get()
    return {
      input: state.input,
      generated: state.generated,
    }
  },

  hydrateFromSession: (patch) =>
    set({
      ...patch,
      shouldRegenerateStep2: false,
      aiCallLog: [],
    }),

  reset: () =>
    set({
      sessionId: null,
      sessionPublicId: null,
      sessionName: '',
      input: defaultInput,
      generated: defaultGenerated,
      step2SelectedTheme: null,
      step2Candidates: [],
      step2GeneratedForInput: null,
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
      step3PatentResults: null,
      step3PatentResultsQuery: null,
      step3ArticleResults: null,
      step3ArticleResultsQuery: null,
      aiCallLog: [],
      aiCallsInFlight: 0,
    }),
}))
