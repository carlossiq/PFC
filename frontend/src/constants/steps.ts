// Etapas do workflow de prospecção
export const STEPS = {
  // Entrada de dados do usuário
  INPUT: 0,

  // Exploração de tópicos
  EXPLORATION: 1,

  // Prospecção de documentos
  PROSPECTION: 2,

  // Análise de resultados
  ANALYSIS: 3,

  // Geração de relatório
  REPORT: 4,
} as const

export type StepType = typeof STEPS[keyof typeof STEPS]

// Substeps disponíveis para cada etapa
export const SUBSTEPS = {
  // Etapa de Entrada
  REFINE: 'refine',

  // Etapa de Análise
  METADATA: 'metadata',
} as const

export type SubstepType = typeof SUBSTEPS[keyof typeof SUBSTEPS]

// Estrutura de dados dos steps com seus substeps
export const stepsData = [
  { name: 'Input', substeps: [SUBSTEPS.REFINE] },
  { name: 'Exploration', substeps: [] },
  { name: 'Prospection', substeps: [SUBSTEPS.REFINE] },
  { name: 'Analysis', substeps: [SUBSTEPS.METADATA] },
  { name: 'Report', substeps: [] },
] as const

export const TOTAL_STEPS = 5
