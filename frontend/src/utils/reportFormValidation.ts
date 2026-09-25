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

// Expressões de "campo não preenchido" digitadas por extenso (mesma lista do backend).
const PLACEHOLDER_PHRASES = new Set([
  'nao especificado', 'nao especificada', 'nao informado', 'nao informada', 'sem posto', 'sem funcao',
  'sem nome', 'a definir', 'n/a', 'na', 'teste', 'xxx', 'fulano de tal', 'nome sobrenome', '-',
])

function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Mn}/gu, '')
    .replace(/\s+/g, ' ')
    .replace(/^[\s.]+|[\s.]+$/g, '')
}

export function looksLikePlaceholder(text: string): boolean {
  const words = text.trim().split(/\s+/).filter(Boolean)
  return words.length === 0 || PLACEHOLDER_PHRASES.has(normalize(text)) || words.some(isGibberishWord)
}

// O Destinatário entra no FIM da frase fixa da Finalidade - digitar a frase
// inteira no campo a duplicava no PDF (mesma regra do backend).
const FINALIDADE_FRAGMENTS = ['apresentar', 'relatorio de prospeccao', 'a fim de fornecer', 'ciclo de vida da tecnologia']
const DESTINATARIO_MAX_WORDS = 12

export function destinatarioError(value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const normalized = normalize(trimmed)
  if (
    FINALIDADE_FRAGMENTS.some((fragment) => normalized.includes(fragment)) ||
    trimmed.split(/\s+/).length > DESTINATARIO_MAX_WORDS
  ) {
    return 'Informe só o destinatário (ex.: AGITEC, DCT) - o restante da frase já é fixo.'
  }
  return looksLikePlaceholder(trimmed) ? 'Texto inválido.' : null
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
  return trimmed.length >= 2 && !looksLikePlaceholder(trimmed) ? null : 'Posto/graduação inválido.'
}

// Função do assinante - obrigatória num bloco preenchido (só cobrada depois
// que nome e posto já foram digitados, pra não acusar erro no meio do
// preenchimento).
export function signerFuncaoError(signer: { nome: string; posto: string; funcao: string }): string | null {
  const funcao = signer.funcao.trim()
  if (!funcao) return signer.nome.trim() && signer.posto.trim() ? 'Informe a função.' : null
  return looksLikePlaceholder(funcao) ? 'Função inválida.' : null
}

export function textFieldError(value: string, minWords = 2): string | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  return trimmed.split(/\s+/).length >= minWords && !looksLikePlaceholder(trimmed) ? null : 'Texto inválido.'
}
