export const TABS = {
  // Bem-vindo/Home
  WELCOME: 0,

  // Botão "Iniciar Prospecção"
  START_PROSPECTION: 1,

  // Abas da barra lateral
  SETTINGS: 2,
  STATISTICS: 3,
  SEARCH: 4,

  // Abas da navbar
  ABOUT: 5,
  DOCUMENTATION: 6,
  DOC_USER_GUIDE: 7,
  DOC_API: 8,
  DOC_FAQ: 9,

  // Botões da barra lateral
  HELP: 10,
  USER: 11,

  // Páginas adicionais do menu Documentação (navbar)
  DOC_PIPELINE: 12,
  DOC_TERMS: 13,
  DOC_LATEX: 14,
  DOC_ERRORS: 15,
} as const

export type TabType = typeof TABS[keyof typeof TABS]
