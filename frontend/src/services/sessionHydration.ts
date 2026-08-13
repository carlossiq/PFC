import { resolveIntakePayload } from './refineTopic'
import type { ResearchSessionSummary } from './researchSession'
import type { SessionProbeQueryRow } from './sessionInput'
import { buildProbeSearchResult } from './probeQuery'
import type { QueryOptionResult } from './probeQuery'
import { buildFinalQuerySelectionSignature } from './finalQuery'
import type { ExtractedTerm, FinalQueryVariant } from './finalQuery'
import type { FormStorePatch } from '../stores/useFormStore'

// Mapeia uma sessão salva pra um patch de useFormStore, usado ao retomar uma
// sessão pendente ("Continuar pesquisa"). Sempre reabre no Step1 - não tenta
// restaurar o step/substep exato de onde o usuário parou.
export function mapSessionToFormStorePatch(session: ResearchSessionSummary): FormStorePatch {
  const root = session.inputs.find((i) => i.parent_id === null)
  const generated = session.inputs.find((i) => i.parent_id !== null)
  // tipo === null identifica a linha de probe (Exploração Inicial) - session
  // pode ter uma segunda linha por fonte (tipo=variante escolhida) pra query
  // final (ver patentFinalQuery/articleFinalQuery abaixo).
  const patentQuery = session.probe_queries.find((q) => q.fonte === 'ops' && q.tipo === null)
  const articleQuery = session.probe_queries.find((q) => q.fonte === 'scopus' && q.tipo === null)
  // Linha de query final (tipo=variante escolhida), auto-relacionada à
  // linha de probe acima pela mesma fonte - ver buildProbeQueryPayload em
  // sessionInput.ts. undefined = usuário ainda não gerou uma query final
  // nesta sessão (Amostragem de Termos preenchida, mas "Gerar Query Final"
  // nunca confirmado).
  const patentFinalQuery = session.probe_queries.find((q) => q.fonte === 'ops' && q.tipo !== null)
  const articleFinalQuery = session.probe_queries.find((q) => q.fonte === 'scopus' && q.tipo !== null)

  const input = {
    theme: root?.theme ?? '',
    description: root?.description ?? null,
    keywords: root?.keywords?.length ? root.keywords.join(', ') : null,
    studyArea: root?.area_of_study ?? null,
  }

  const step2SelectedTheme = generated
    ? {
        id: 'generated',
        theme: generated.theme,
        description: generated.description ?? '',
        keywords: generated.keywords ?? undefined,
        studyArea: generated.area_of_study ? [generated.area_of_study] : undefined,
      }
    : null

  // Mesma assinatura que Step2/useProbeQuerySection calculam no mount, pra
  // não forçar uma regeneração por IA desnecessária logo ao reabrir a sessão
  // (assumindo que nada foi editado desde o último save).
  const step2Signature = JSON.stringify(input)
  const intakeSignature = JSON.stringify(resolveIntakePayload(input, step2SelectedTheme))

  function toQueryOption(row: SessionProbeQueryRow | undefined): QueryOptionResult[] | null {
    if (!row) return null
    return [
      {
        success: true,
        query: { query: row.query_text },
        fields: row.fields ?? undefined,
        complexity:
          row.complexity_level != null
            ? { score: row.complexity_score ?? 0, level: row.complexity_level, warnings: [], recommendations: [] }
            : undefined,
        year_range:
          row.year_from != null && row.year_to != null ? { from: row.year_from, to: row.year_to } : undefined,
      },
    ]
  }

  // Mesma reconstrução de toQueryOption, mas devolve um único objeto (não
  // uma lista de tentativas) - formato que step4PatentQuery/step4ArticleQuery
  // esperam (Escolha da Query Final não tem mais "3 variantes pra escolher",
  // só a única já gerada pro tipo escolhido em TermSampling.tsx).
  function toFinalQueryOption(row: SessionProbeQueryRow | undefined): QueryOptionResult | null {
    const wrapped = toQueryOption(row)
    return wrapped ? wrapped[0] : null
  }

  // Reconstrói os termos da Amostragem de Termos (todos os extraídos, com
  // `selected` marcando os escolhidos) - null se a linha não tem termos
  // salvos (sessão sem docs na fonte, ou salva antes dessa feature existir).
  function toTerms(row: SessionProbeQueryRow | undefined): ExtractedTerm[] | null {
    if (!row || row.terms.length === 0) return null
    return row.terms.map((t) => ({ term: t.term, score: t.score, frequency: t.frequency }))
  }

  function toSelectedTerms(row: SessionProbeQueryRow | undefined): string[] {
    if (!row) return []
    return row.terms.filter((t) => t.selected).map((t) => t.term)
  }

  // Reconstrói o resultado da busca a partir dos documentos persistidos
  // (patent/article), pra "Próximo" no Step3 não refazer a busca à toa ao
  // retomar uma sessão. A assinatura precisa bater exatamente com o que
  // Step3.handleConfirm vai calcular a partir do query reconstruído acima
  // (`{ query: row.query_text }`), senão o cache não é reconhecido.
  function toResults(row: SessionProbeQueryRow | undefined, api: 'ops' | 'scopus') {
    if (!row || row.documents.length === 0) return { result: null, querySignature: null }
    return {
      result: buildProbeSearchResult(row.documents, api),
      querySignature: JSON.stringify({ query: row.query_text }),
    }
  }

  const patentResults = toResults(patentQuery, 'ops')
  const articleResults = toResults(articleQuery, 'scopus')

  const patentFinalVariant = (patentFinalQuery?.tipo ?? 'balanced') as FinalQueryVariant
  const articleFinalVariant = (articleFinalQuery?.tipo ?? 'balanced') as FinalQueryVariant
  const patentFinalSelectedTerms = toSelectedTerms(patentQuery)
  const articleFinalSelectedTerms = toSelectedTerms(articleQuery)

  return {
    sessionId: session.id,
    sessionPublicId: session.public_id,
    sessionName: session.name ?? '',
    input,
    step2SelectedTheme,
    step2Candidates: step2SelectedTheme ? [step2SelectedTheme] : [],
    step2GeneratedForInput: step2Signature,
    step2Iterations: generated?.iterations ?? 0,
    step3Queries: toQueryOption(patentQuery),
    step3SelectedIndex: patentQuery ? 0 : null,
    step3GeneratedForIntake: patentQuery ? intakeSignature : null,
    step3Iterations: patentQuery ? Math.max(0, patentQuery.iterations) : 0,
    step3ArticleQueries: toQueryOption(articleQuery),
    step3ArticleSelectedIndex: articleQuery ? 0 : null,
    step3ArticleGeneratedForIntake: articleQuery ? intakeSignature : null,
    step3ArticleIterations: articleQuery ? Math.max(0, articleQuery.iterations -1) : 0,
    step3PatentResults: patentResults.result,
    step3PatentResultsQuery: patentResults.querySignature,
    step3ArticleResults: articleResults.result,
    step3ArticleResultsQuery: articleResults.querySignature,
    // termsForQuery usa a MESMA assinatura de step3PatentResultsQuery - é
    // essa igualdade que faz useTermSampling.ts:needsExtraction reconhecer
    // que os termos já estão atualizados e não reextrair à toa ao reabrir.
    step4PatentTerms: toTerms(patentQuery),
    step4PatentTermsForQuery: toTerms(patentQuery) ? patentResults.querySignature : null,
    step4PatentSelectedTerms: toSelectedTerms(patentQuery),
    step4ArticleTerms: toTerms(articleQuery),
    step4ArticleTermsForQuery: toTerms(articleQuery) ? articleResults.querySignature : null,
    step4ArticleSelectedTerms: toSelectedTerms(articleQuery),
    // Query final já gerada nesta sessão (Escolha da Query Final), com a
    // assinatura da seleção que a gerou - permite que TermSampling.tsx
    // reconheça, logo ao reabrir a sessão, que a query já existe pra
    // seleção atual e pule a chamada de IA em "Gerar Query Final" (mesmo
    // cache que evita regeneração ao só navegar dentro da sessão, ver
    // handleBuildQueries em TermSampling.tsx).
    step4PatentSelectedVariant: patentFinalVariant,
    step4PatentQuery: toFinalQueryOption(patentFinalQuery),
    step4PatentGeneratedForSelection: patentFinalQuery
      ? buildFinalQuerySelectionSignature(patentFinalSelectedTerms, patentFinalVariant)
      : null,
    step4ArticleSelectedVariant: articleFinalVariant,
    step4ArticleQuery: toFinalQueryOption(articleFinalQuery),
    step4ArticleGeneratedForSelection: articleFinalQuery
      ? buildFinalQuerySelectionSignature(articleFinalSelectedTerms, articleFinalVariant)
      : null,
  }
}
