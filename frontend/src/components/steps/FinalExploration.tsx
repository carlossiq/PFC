import { useState } from 'react'
import { useFormStore } from '../../stores/useFormStore'
import { useFinalQuerySection } from '../../hooks/useFinalQuerySection'
import { friendlyErrorMessage } from '../../hooks/useProbeQuerySection'
import { runFinalSearch } from '../../services/finalQuery'
import { FieldCard } from '../FieldCard'
import { FloatingLabelInput } from '../FloatingLabelInput'
import { LoadingScreen } from '../LoadingScreen'
import { Button } from '../Button'
import { SectionHeader } from '../SectionHeader'
import { PROBE_FIELDS_BY_API } from '../../constants/probeFields'
import { FINAL_QUERY_VARIANT_LABELS } from '../../constants/finalQueryVariants'
import { STEPS } from '../../constants/steps'
import { useAutoDismiss } from '../../hooks/useAutoDismiss'

interface FinalQueryCardProps {
  title: string
  fieldOrder: readonly string[]
  fieldLabels: Record<string, string>
  section: ReturnType<typeof useFinalQuerySection>
}

// Card de revisão/edição da única query final de uma fonte (o tipo já foi
// escolhido antes, em TermSampling.tsx) - mostra o que foi gerado (texto,
// campos estruturados, complexidade), com "Editar" (campos estruturados,
// sem IA, via rebuildFinalQuery) e "Gerar de novo" (regenera com o mesmo
// tipo, conta como iteração) - mesmo padrão visual de card+botão abaixo já
// usado em TermSampling.tsx.
function FinalQueryCard({ title, fieldOrder, fieldLabels, section }: FinalQueryCardProps) {
  const {
    query,
    isRegenerating,
    regenerateError,
    isRebuilding,
    rebuildError,
    isBusy,
    isEditing,
    editFields,
    setEditFields,
    handleRegenerate,
    handleStartEdit,
    handleCancelEdit,
    handleSaveEdit,
  } = section

  return (
    <div className="flex flex-col">
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="font-semibold text-sm text-gray-900">{title}</h4>
          {query?.success && !isEditing && !isRegenerating && (
            <Button size="xs" onClick={handleStartEdit} disabled={isBusy}>
              Editar
            </Button>
          )}
        </div>

        {isRegenerating && <LoadingScreen message="Gerando query final com IA..." />}

        {!isRegenerating && regenerateError && (
          <div className="p-4 rounded-lg border-2 border-red-200 bg-red-50">
            <p className="text-sm text-red-700">{regenerateError}</p>
          </div>
        )}

        {!isRegenerating && !regenerateError && query && !query.success && (
          <div className="p-4 rounded-lg border-2 border-red-200 bg-red-50">
            <p className="text-sm text-red-700">{query.error ?? 'Falha ao gerar esta query.'}</p>
          </div>
        )}

        {!isRegenerating && query?.success && !isEditing && (
          <>
            {rebuildError && (
              <div className="mb-3 p-3 rounded-lg border-2 border-red-200 bg-red-50">
                <p className="text-sm text-red-700">{rebuildError}</p>
              </div>
            )}
            <div className="space-y-3">
              <FieldCard label="Query">
                <p className="text-sm font-mono text-gray-900 break-all">{query.query?.query}</p>
              </FieldCard>

              {fieldOrder
                .filter((f) => f !== 'year' && (query.fields?.[f]?.length ?? 0) > 0)
                .map((f) => (
                  <FieldCard key={f} label={fieldLabels[f]}>
                    <p className="text-sm font-semibold text-gray-900">{query.fields![f].join(', ')}</p>
                  </FieldCard>
                ))}

              {/* Year sempre aparece, mesmo sem edição - mostra o padrão do
                  backend quando o campo está vazio, mesmo padrão de
                  ProbeQuerySectionView.tsx. */}
              <FieldCard label={fieldLabels.year}>
                <p className="text-sm font-semibold text-gray-900">
                  {query.fields?.year && query.fields.year.length > 0
                    ? query.fields.year.join(', ')
                    : query.year_range
                      ? `${query.year_range.from} - ${query.year_range.to} (padrão)`
                      : '—'}
                </p>
              </FieldCard>

              {query.complexity && (
                <FieldCard label="Complexidade">
                  <p className="text-sm font-semibold text-gray-900">
                    {query.complexity.level} ({query.complexity.score.toFixed(1)}/100)
                  </p>
                </FieldCard>
              )}
            </div>
          </>
        )}

        {!isRegenerating && query?.success && isEditing && (
          <div className="space-y-4">
            {fieldOrder.map((f) => (
              <FloatingLabelInput
                key={f}
                label={fieldLabels[f]}
                name={`edit-${f}`}
                value={editFields[f] ?? ''}
                onChange={(e) => setEditFields((prev) => ({ ...prev, [f]: e.target.value }))}
                placeholder={f === 'year' ? 'ex: 2020 ou 2015, 2020 (intervalo)' : 'separados por vírgula'}
              />
            ))}

            <div className="flex gap-3 pt-1">
              <Button fullWidth size="sm" variant="secondary" onClick={handleCancelEdit} disabled={isRebuilding}>
                Cancelar
              </Button>
              <Button fullWidth size="sm" onClick={handleSaveEdit} disabled={isRebuilding}>
                {isRebuilding ? 'Salvando...' : 'Salvar'}
              </Button>
            </div>
          </div>
        )}
      </div>

      {!isEditing && (
        <div className="mt-3 shrink-0">
          <Button size="sm" onClick={handleRegenerate} disabled={isBusy}>
            {isRegenerating ? 'Gerando...' : 'Gerar de novo'}
          </Button>
        </div>
      )}
    </div>
  )
}

interface FinalExplorationProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

// Tela principal da "Exploração Final" (Passo 3): revisão/edição da única
// query final gerada por fonte (o tipo specific/balanced/generic já foi
// escolhido antes, no select de TermSampling.tsx) - não há mais "escolher
// entre 3 variantes" aqui, só confirmar a que foi gerada (ou editar/gerar
// de novo) antes de rodar a busca final.
export function FinalExploration({ step, substep, onBack, onNext }: FinalExplorationProps) {
  const {
    input,
    step2SelectedTheme,
    step4PatentTerms,
    step4PatentSelectedTerms,
    step4PatentSelectedVariant,
    step4PatentQuery,
    setStep4PatentQuery,
    updateStep4PatentQuery,
    incrementStep4PatentQueryIterations,
    step4ArticleTerms,
    step4ArticleSelectedTerms,
    step4ArticleSelectedVariant,
    step4ArticleQuery,
    setStep4ArticleQuery,
    updateStep4ArticleQuery,
    incrementStep4ArticleQueryIterations,
    setStep4PatentResults,
    setStep4ArticleResults,
  } = useFormStore()

  const [isConfirming, setIsConfirming] = useState(false)
  const [confirmError, setConfirmError] = useState<string | null>(null)

  useAutoDismiss(confirmError, () => setConfirmError(null))

  const hasPatentQuery = step4PatentQuery !== null
  const hasArticleQuery = step4ArticleQuery !== null

  const patentSection = useFinalQuerySection({
    api: 'ops',
    fieldOrder: PROBE_FIELDS_BY_API.ops.order,
    variant: step4PatentSelectedVariant,
    input,
    step2SelectedTheme,
    extractedTerms: (step4PatentTerms ?? []).filter((t) => step4PatentSelectedTerms.includes(t.term)),
    slice: {
      query: step4PatentQuery,
      setQuery: setStep4PatentQuery,
      updateQuery: updateStep4PatentQuery,
      incrementIterations: incrementStep4PatentQueryIterations,
    },
  })

  const articleSection = useFinalQuerySection({
    api: 'scopus',
    fieldOrder: PROBE_FIELDS_BY_API.scopus.order,
    variant: step4ArticleSelectedVariant,
    input,
    step2SelectedTheme,
    extractedTerms: (step4ArticleTerms ?? []).filter((t) => step4ArticleSelectedTerms.includes(t.term)),
    slice: {
      query: step4ArticleQuery,
      setQuery: setStep4ArticleQuery,
      updateQuery: updateStep4ArticleQuery,
      incrementIterations: incrementStep4ArticleQueryIterations,
    },
  })

  if (step !== STEPS.FINAL_EXPLORATION || substep !== null) return null

  const isBusy = patentSection.isBusy || articleSection.isBusy
  const canConfirm =
    (hasPatentQuery || hasArticleQuery) &&
    (!hasPatentQuery || !!patentSection.query?.success) &&
    (!hasArticleQuery || !!articleSection.query?.success)

  async function handleConfirm() {
    if (!canConfirm) return
    setIsConfirming(true)
    setConfirmError(null)
    try {
      const [patentOutcome, articleOutcome] = await Promise.allSettled([
        hasPatentQuery && patentSection.query?.success
          ? runFinalSearch(patentSection.query.query!, 'ops')
          : Promise.resolve(null),
        hasArticleQuery && articleSection.query?.success
          ? runFinalSearch(articleSection.query.query!, 'scopus')
          : Promise.resolve(null),
      ])

      if (patentOutcome.status === 'rejected' || articleOutcome.status === 'rejected') {
        console.error('Falha ao buscar resultados finais:', patentOutcome, articleOutcome)
        const reason = patentOutcome.status === 'rejected' ? patentOutcome.reason : articleOutcome.status === 'rejected' ? articleOutcome.reason : undefined
        const message = reason instanceof Error ? reason.message : undefined
        setConfirmError(friendlyErrorMessage(message, 'Falha ao buscar os resultados finais. Tente novamente.'))
        return
      }

      if (patentOutcome.value) setStep4PatentResults(patentOutcome.value)
      if (articleOutcome.value) setStep4ArticleResults(articleOutcome.value)
      onNext()
    } finally {
      setIsConfirming(false)
    }
  }

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <SectionHeader
        title="Revisão da Query Final"
        description="Query gerada a partir do tipo e dos termos escolhidos na Amostragem de Termos - revise, edite se quiser, ou gere de novo antes de confirmar a busca."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
        {hasPatentQuery && (
          <FinalQueryCard
            title={`Query final de patentes (OPS) - ${FINAL_QUERY_VARIANT_LABELS[step4PatentSelectedVariant]}`}
            fieldOrder={PROBE_FIELDS_BY_API.ops.order}
            fieldLabels={PROBE_FIELDS_BY_API.ops.labels}
            section={patentSection}
          />
        )}
        {hasArticleQuery && (
          <FinalQueryCard
            title={`Query final de artigos (Scopus) - ${FINAL_QUERY_VARIANT_LABELS[step4ArticleSelectedVariant]}`}
            fieldOrder={PROBE_FIELDS_BY_API.scopus.order}
            fieldLabels={PROBE_FIELDS_BY_API.scopus.labels}
            section={articleSection}
          />
        )}
      </div>

      {confirmError && <p className="mt-2 text-sm text-red-600 font-medium">{confirmError}</p>}

      <div className="mt-2 pt-4 border-t border-gray-200 flex gap-4">
        <Button fullWidth variant="secondary" onClick={onBack} disabled={isBusy || isConfirming}>
          Voltar
        </Button>
        <Button fullWidth onClick={handleConfirm} disabled={!canConfirm || isBusy || isConfirming}>
          {isConfirming ? 'Buscando resultados...' : 'Confirmar e buscar'}
        </Button>
      </div>
    </div>
  )
}
