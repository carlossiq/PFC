import { checkQuerySyntax } from '../utils/querySyntax'

interface QuerySyntaxMeterProps {
  query: string
}

// Feedback ao vivo (sem chamada ao backend) sobre erros estruturais óbvios
// na query editada como texto livre - parênteses/aspas não fechados,
// parênteses vazios, operador solto nas pontas. Não bloqueia o "Salvar":
// é só um sinal rápido enquanto o usuário digita, não substitui a
// validação/complexidade real do backend (calculada ao salvar).
export function QuerySyntaxMeter({ query }: QuerySyntaxMeterProps) {
  if (!query.trim()) return null

  const { isValid, issues } = checkQuerySyntax(query)

  return (
    <div
      className={`flex items-start gap-2 text-xs rounded-lg px-3 py-2 ${
        isValid ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
      }`}
    >
      <span className="mt-0.5 shrink-0">{isValid ? '✓' : '✗'}</span>
      {isValid ? (
        <span>Sintaxe da query parece válida (parênteses e aspas balanceados).</span>
      ) : (
        <ul className="space-y-0.5 list-disc list-inside">
          {issues.map((issue) => (
            <li key={issue}>{issue}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
