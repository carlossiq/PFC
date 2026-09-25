// Estrutura de dados das páginas de Documentação/About - o conteúdo fica em
// constants/docs/*.ts (um arquivo por página), separado do JSX, e é
// desenhado por components/docs/DocPage.tsx.

// Um bloco de conteúdo dentro de uma subseção. Texto simples, sem markdown:
// trechos entre `crases` viram <code> inline (ver DocPage.tsx::renderInline).
export type DocBlock =
  | { type: 'paragraph'; text: string }
  | { type: 'note'; text: string }
  | { type: 'warning'; text: string }
  | { type: 'list'; items: string[]; ordered?: boolean }
  | { type: 'code'; code: string; caption?: string }
  | { type: 'table'; headers: string[]; rows: string[][] }

export interface DocSubsection {
  title: string
  blocks: DocBlock[]
  inProgress?: boolean
}

export interface DocSection {
  id: string
  title: string
  intro?: string
  subsections: DocSubsection[]
}

export interface DocPageData {
  title: string
  description: string
  sections: DocSection[]
}
