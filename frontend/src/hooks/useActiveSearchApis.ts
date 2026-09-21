import { useEffect, useState } from 'react'
import { getSearchApis } from '../services/config'
import type { ProbeApi } from '../constants/probeFields'

// A mesma API escolhida em Configurações > Busca (search_api_selection)
// atende tanto o probe (Step3.tsx) quanto a busca final (FinalExploration.tsx)
// dessa família - por isso um hook único compartilhado, não uma leitura
// separada em cada componente (garante que os dois vejam exatamente o
// mesmo valor resolvido dentro da mesma sessão do wizard). Cacheado a
// nível de módulo: a seleção não muda no meio de uma prospecção em
// andamento, então só busca uma vez por carregamento de página.
let cache: Promise<{ patent: string; scholarly: string }> | null = null

function fetchActiveApis() {
  if (!cache) {
    cache = getSearchApis()
      .then((state) => ({
        patent: state.selections.patent ?? 'ops',
        scholarly: state.selections.scholarly ?? 'scopus',
      }))
      .catch(() => ({ patent: 'ops', scholarly: 'scopus' }))
  }
  return cache
}

// Só ops/scopus são de fato suportados no parsing de resultados hoje (ver
// constants/probeFields.ts) - Lens ativo cai no default em vez de quebrar.
function coerceToSupportedApi(code: string, fallback: ProbeApi): ProbeApi {
  return code === 'ops' || code === 'scopus' ? code : fallback
}

export function useActiveSearchApis(): { patentApi: ProbeApi; articleApi: ProbeApi } {
  const [patentApi, setPatentApi] = useState<ProbeApi>('ops')
  const [articleApi, setArticleApi] = useState<ProbeApi>('scopus')

  useEffect(() => {
    let cancelled = false
    fetchActiveApis().then((apis) => {
      if (cancelled) return
      setPatentApi(coerceToSupportedApi(apis.patent, 'ops'))
      setArticleApi(coerceToSupportedApi(apis.scholarly, 'scopus'))
    })
    return () => {
      cancelled = true
    }
  }, [])

  return { patentApi, articleApi }
}
