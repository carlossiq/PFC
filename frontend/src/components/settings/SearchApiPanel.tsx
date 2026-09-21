import { useEffect, useState } from 'react'
import { SelectField } from '../SelectField'
import { getSearchApis, setSearchApi } from '../../services/config'
import type { SearchApiState } from '../../services/config'

const FAMILY_LABELS: Record<string, string> = {
  patent: 'API de Patentes',
  scholarly: 'API de Artigos',
}

// A mesma API escolhida aqui atende tanto a probe search quanto a busca
// final dessa família (patent/scholarly) - não são seletores independentes.
// Só uma API por família fica ativa (o back garante isso). Exige reiniciar
// o backend pra valer, porque os adapters de busca são montados no boot.
export function SearchApiPanel() {
  const [state, setState] = useState<SearchApiState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [restartNotice, setRestartNotice] = useState<string | null>(null)

  useEffect(() => {
    getSearchApis()
      .then(setState)
      .catch(() => setError('Não foi possível carregar as APIs de busca.'))
  }, [])

  async function handleChange(family: string, code: string) {
    if (!state) return
    const previous = state.selections[family]
    setState({ ...state, selections: { ...state.selections, [family]: code } })
    try {
      const result = await setSearchApi(family, code)
      if (result.message) setRestartNotice(result.message)
    } catch {
      setState({ ...state, selections: { ...state.selections, [family]: previous } })
      setError('Não foi possível trocar a API de busca.')
    }
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!state) return <p className="text-sm text-gray-500">Carregando...</p>

  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500">
        A API escolhida atende tanto a busca inicial (probe) quanto a busca final dessa família - se ainda não
        houver uma seleção salva, o padrão é a mesma API pras duas etapas.
      </p>
      {Object.keys(state.options).map((family) => (
        <div key={family} className="rounded-lg border border-gray-200 bg-white p-4">
          <SelectField
            label={FAMILY_LABELS[family] ?? family}
            value={state.selections[family] ?? ''}
            options={state.options[family].map((opt) => ({ value: opt.code, label: opt.display_name }))}
            onChange={(code) => handleChange(family, code)}
          />
        </div>
      ))}
      {restartNotice && <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-2">{restartNotice}</p>}
    </div>
  )
}
