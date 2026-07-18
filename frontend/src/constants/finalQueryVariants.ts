// Variantes da query final (Escolha da Query Final) 
export const FINAL_QUERY_VARIANTS = ['specific', 'balanced', 'generic'] as const

export type FinalQueryVariant = (typeof FINAL_QUERY_VARIANTS)[number]

export const FINAL_QUERY_VARIANT_LABELS: Record<FinalQueryVariant, string> = {
  specific: 'Específica',
  balanced: 'Balanceada',
  generic: 'Ampla',
}
