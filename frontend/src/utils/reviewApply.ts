// Aplicação das correções da revisão do .tex (ver ReportDocumentEditor.tsx)
// - funções puras. As posições (offset/length) vêm do backend calculadas
// sobre o texto no momento da revisão; se o usuário editou desde então, o
// trecho pode ter mudado de lugar - nesse caso a correção NÃO é aplicada e
// fica marcada como desatualizada (nunca substitui o texto errado).

export interface TextEdit {
  id: string
  offset: number
  length: number
  original: string
  replacement: string
}

export interface ApplyResult {
  text: string
  applied: string[]
  stale: string[]
  // Deslocamentos aplicados (posição original, variação de tamanho) - usados
  // pra reposicionar as correções que sobraram (ver shiftOffset).
  shifts: Array<{ offset: number; delta: number }>
}

export function isStillValid(text: string, edit: Pick<TextEdit, 'offset' | 'length' | 'original'>): boolean {
  return text.slice(edit.offset, edit.offset + edit.length) === edit.original
}

// Aplica da ÚLTIMA posição pra primeira - assim cada troca não desloca as
// posições das que ainda vão ser aplicadas. Sobreposições (raras - o backend
// já descarta sugestões da IA que se sobrepõem às do LanguageTool): vale a de
// posição mais adiante; as outras ficam como desatualizadas.
export function applyEdits(text: string, edits: TextEdit[]): ApplyResult {
  const ordered = [...edits].sort((a, b) => b.offset - a.offset)
  const applied: string[] = []
  const stale: string[] = []
  const shifts: Array<{ offset: number; delta: number }> = []
  let result = text
  let lowestAppliedStart = Number.POSITIVE_INFINITY

  for (const edit of ordered) {
    const overlapsApplied = edit.offset + edit.length > lowestAppliedStart
    if (overlapsApplied || !isStillValid(result, edit)) {
      stale.push(edit.id)
      continue
    }
    result = result.slice(0, edit.offset) + edit.replacement + result.slice(edit.offset + edit.length)
    applied.push(edit.id)
    shifts.push({ offset: edit.offset, delta: edit.replacement.length - edit.length })
    lowestAppliedStart = edit.offset
  }
  return { text: result, applied, stale, shifts }
}

// Nova posição de um trecho depois das trocas aplicadas antes dele.
export function shiftOffset(offset: number, shifts: ApplyResult['shifts']): number {
  return offset + shifts.filter((s) => s.offset < offset).reduce((sum, s) => sum + s.delta, 0)
}
