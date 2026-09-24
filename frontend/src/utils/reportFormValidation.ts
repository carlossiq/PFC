// Validação dos campos digitados no formulário do relatório - mesmas regras
// de app/core/services/report_form_validation.py (a API também rejeita, com
// 422). Evita que placeholders como "sasassas"/"sdasdsad"/"diex 2322-1"
// cheguem ao documento final.

const VOWELS = new Set('aeiouáéíóúâêôãõàü'.split(''))
// Tipo do documento + número + data: "DIEx Nº 115-A3/DCT de 6 de janeiro de 2023".
const ADMIN_REF_RE = /^\S+.*\bn[º°o.]?\s*\S*\d.*\bde\s+\d{1,2}\s+de\s+[a-zà-ú]+\s+de\s+\d{4}\b/i
// ABNT: "SOBRENOME, X. ... ano".
const BIBLIO_REF_RE = /^[A-ZÀ-Ý][A-ZÀ-Ý'\- ]+,\s*\S.*\b(1[5-9]|20)\d{2}\b/

function isGibberishWord(word: string): boolean {
  const letters = [...word.toLowerCase()].filter((c) => /\p{L}/u.test(c))
  if (letters.length < 5) return false
  const distinct = new Set(letters)
  return distinct.size <= 2 || ![...distinct].some((c) => VOWELS.has(c))
}

export function looksLikePlaceholder(text: string): boolean {
  const words = text.trim().split(/\s+/).filter(Boolean)
  return words.length === 0 || words.some(isGibberishWord)
}

export function adminReferenceError(ref: string): string | null {
  return ADMIN_REF_RE.test(ref.trim()) && !looksLikePlaceholder(ref)
    ? null
    : 'Informe tipo, número e data do documento (ex.: "DIEx Nº 115-A3/DCT de 6 de janeiro de 2023").'
}

export function bibliographyError(ref: string): string | null {
  return BIBLIO_REF_RE.test(ref.trim()) && !looksLikePlaceholder(ref)
    ? null
    : 'Use o padrão ABNT: comece por "SOBRENOME, Iniciais." e inclua o ano.'
}

export function signerNameError(nome: string): string | null {
  const trimmed = nome.trim()
  if (!trimmed) return null
  return trimmed.split(/\s+/).length >= 2 && !looksLikePlaceholder(trimmed) ? null : 'Informe o nome completo.'
}

export function signerPostoError(posto: string): string | null {
  const trimmed = posto.trim()
  if (!trimmed) return null
  return trimmed.length >= 2 && !looksLikePlaceholder(trimmed) ? null : 'Posto/função inválido.'
}

export function textFieldError(value: string, minWords = 2): string | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  return trimmed.split(/\s+/).length >= minWords && !looksLikePlaceholder(trimmed) ? null : 'Texto inválido.'
}
