// Checagem estrutural leve de queries booleanas (CQL/estilo Scopus-OPS),
// 100% client-side (sem round-trip pro backend) - complementa (não substitui)
// a validação de complexidade do backend, calculada só ao salvar (ver
// core/services/chat_service.py::_validate_query). Serve pra dar feedback
// imediato enquanto o usuário digita na caixa única de edição.

export interface QuerySyntaxCheck {
  isValid: boolean
  issues: string[]
}

export function checkQuerySyntax(query: string): QuerySyntaxCheck {
  const issues: string[] = []

  // Parênteses: conta aberturas sem fechamento e fechamentos sem abertura
  // correspondente separadamente, em vez de só comparar a contagem total -
  // "())(" tem contagem igual (2 e 2) mas não é válido.
  let openParens = 0
  let unmatchedCloseParens = 0
  for (const char of query) {
    if (char === '(') openParens++
    else if (char === ')') {
      if (openParens > 0) openParens--
      else unmatchedCloseParens++
    }
  }
  if (openParens > 0) {
    issues.push(`${openParens} parêntese${openParens > 1 ? 's' : ''} de abertura "(" sem fechamento`)
  }
  if (unmatchedCloseParens > 0) {
    issues.push(
      `${unmatchedCloseParens} parêntese${unmatchedCloseParens > 1 ? 's' : ''} de fechamento ")" sem abertura correspondente`
    )
  }

  // Aspas duplas: usadas pra frases exatas (ex: TITLE("machine learning")) -
  // contagem ímpar significa uma frase que nunca fechou.
  const doubleQuotes = (query.match(/"/g) ?? []).length
  if (doubleQuotes % 2 !== 0) {
    issues.push('Aspas duplas (") não fechadas')
  }

  if (/\(\s*\)/.test(query)) {
    issues.push('Parênteses vazios "()" encontrados')
  }

  const trimmed = query.trim()
  if (trimmed && /\b(AND|OR|NOT)\s*$/i.test(trimmed)) {
    issues.push('A query termina com um operador (AND/OR/NOT) sem termo depois')
  }
  if (trimmed && /^(AND|OR)\b/i.test(trimmed)) {
    issues.push('A query começa com um operador (AND/OR) sem termo antes')
  }

  return { isValid: issues.length === 0, issues }
}
