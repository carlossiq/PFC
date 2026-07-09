// Etapas do workflow de prospecção
export const STEPS = {
  // Entrada de dados do usuário
  INPUT: 0,

  // Exploração inicial de tópicos
  INITIAL_EXPLORATION: 1,

  // Exploração final / prospecção de documentos
  FINAL_EXPLORATION: 2,

  // Geração de relatório
  REPORT: 3,
} as const

export type StepType = typeof STEPS[keyof typeof STEPS]

// Substeps disponíveis para cada etapa
export const SUBSTEPS = {
  // Etapa de Input Inicial
  PARAM_REFINE: 'param_refine',

  // Etapa de Exploração Inicial
  INITIAL_RESULTS: 'initial_results',

  // Etapa de Exploração Final
  RESULTS_ANALYSIS: 'results_analysis',

  // Etapa de Geração do Relatório
  REPORTING: 'reporting',
} as const

export type SubstepType = typeof SUBSTEPS[keyof typeof SUBSTEPS]

// Estrutura de dados dos steps com seus substeps. Cada substep tem um nome
// próprio, exibido na StepsBar junto do nome do step "pai".
export const stepsData = [
  {
    name: 'Input Inicial',
    substeps: [{ id: SUBSTEPS.PARAM_REFINE, name: 'Refinamento de Parâmetros' }],
  },
  {
    name: 'Exploração Inicial',
    substeps: [{ id: SUBSTEPS.INITIAL_RESULTS, name: 'Resultados Iniciais' }],
  },
  {
    name: 'Exploração Final',
    substeps: [{ id: SUBSTEPS.RESULTS_ANALYSIS, name: 'Análise de Resultados' }],
  },
  {
    name: 'Geração do Relatório',
    substeps: [{ id: SUBSTEPS.REPORTING, name: 'Reportar' }],
  },
] as const

export const TOTAL_STEPS = 4
