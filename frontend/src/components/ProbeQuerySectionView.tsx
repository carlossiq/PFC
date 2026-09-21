import { LoadingScreen } from './LoadingScreen'
import { FloatingLabelInput } from './FloatingLabelInput'
import { Tooltip } from './Tooltip'
import { CandidatePickerLayout, selectableCardClass } from './CandidatePicker'
import { FieldCard } from './FieldCard'
import { QuerySyntaxMeter } from './QuerySyntaxMeter'
import { Button } from './Button'
import { friendlyErrorMessage, friendlyWarningMessage } from '../hooks/useProbeQuerySection'
import type { QueryOptionResult } from '../services/probeQuery'

interface ProbeQuerySectionViewProps {
  title: string
  tooltip: string
  cardsSectionLabel: string
  fieldOrder: readonly string[]
  fieldLabels: Record<string, string>
  queries: QueryOptionResult[] | null
  selectedIndex: number | null
  setSelectedIndex: (index: number | null) => void
  selected: QueryOptionResult | undefined
  isLoading: boolean
  error: string | null
  isRebuilding: boolean
  rebuildError: string | null
  isBusy: boolean
  isEditing: boolean
  editQueryText: string
  setEditQueryText: (value: string) => void
  onRetry: () => void
  onStartEdit: () => void
  onCancelEdit: () => void
  onSaveEdit: () => void
}

// Uma seção completa de "gerar/escolher/editar N queries" no Step3 - usada
// duas vezes (patentes/OPS e artigos/Scopus), cada uma com seu próprio estado
// (via useProbeQuerySection) mas a mesma estrutura visual.
export function ProbeQuerySectionView({
  title,
  tooltip,
  cardsSectionLabel,
  fieldOrder,
  fieldLabels,
  queries,
  selectedIndex,
  setSelectedIndex,
  selected,
  isLoading,
  error,
  isRebuilding,
  rebuildError,
  isBusy,
  isEditing,
  editQueryText,
  setEditQueryText,
  onRetry,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
}: ProbeQuerySectionViewProps) {
  const leftPane = (
    <>
      <div className="flex items-center gap-1.5 mb-2">
        <p className="text-xs font-semibold text-black uppercase tracking-wide">{title}</p>
        <Tooltip position="right" label={tooltip}>
          <span className="w-4 h-4 flex items-center justify-center rounded-full border border-gray-400 text-gray-500 text-[10px] font-bold leading-none cursor-help">
            ?
          </span>
        </Tooltip>
      </div>

      {isLoading && <LoadingScreen message="Gerando queries com IA..." />}

      {!isLoading && error && (
        <div className="p-4 rounded-lg border-2 border-red-200 bg-red-50">
          <p className="text-sm text-red-700 mb-2">{error}</p>
          <Button variant="link" onClick={onRetry}>
            Tentar novamente
          </Button>
        </div>
      )}

      {!isLoading && !error && queries && (
        <>
          <p className="text-sm  text-gray-600 font-medium tracking-wide mb-2">
            {cardsSectionLabel}
          </p>
          <div className="grid gap-3">
            {queries.map((result, index) => (
              <button
                key={index}
                onClick={() => setSelectedIndex(index)}
                disabled={!result.success}
                className={`${selectableCardClass(selectedIndex === index, 'w-full')} ${!result.success ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <h4 className="font-semibold text-sm text-gray-900 mb-1">Opção {index + 1}</h4>
                {!result.success && (
                  <p className="text-xs text-red-600">{friendlyErrorMessage(result.error)}</p>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </>
  )

  const rightPane = (
    <>
      {selected && selected.success && (
        <p className="text-xs font-semibold text-black uppercase tracking-wide mb-2">
          Detalhes da query selecionada
        </p>
      )}

      {/* Fora do bloco de !isEditing de propósito: o erro acontece
          justamente ao tentar salvar (durante a edição), então precisa
          aparecer também com isEditing=true - senão "Salvar" falha em
          silêncio e a tela fica presa na edição sem explicação. */}
      {rebuildError && (
        <div className="mx-2 mb-3 p-3 rounded-lg border-2 border-red-200 bg-red-50">
          <p className="text-sm text-red-700">{rebuildError}</p>
        </div>
      )}

      {selected && selected.success && !isEditing && (
        <>
          <div className="flex justify-end gap-4 mb-2 p-2">
            <Button size="xs" onClick={onStartEdit} disabled={isBusy}>
              Editar
            </Button>
          </div>

          <div className="space-y-5 mt-1 mx-1">
            <FieldCard label="Query">
              <p className="text-sm font-mono text-gray-900 break-all">{selected.query?.query}</p>
            </FieldCard>

            {fieldOrder
              .filter((f) => f !== 'year' && (selected.fields?.[f]?.length ?? 0) > 0)
              .map((f) => (
                <FieldCard key={f} label={fieldLabels[f]}>
                  <p className="text-sm font-semibold text-gray-900">
                    {selected.fields![f].join(', ')}
                  </p>
                </FieldCard>
              ))}

            {/* Year sempre aparece, mesmo sem edição. selected.year_range vem
                do backend: se a query tiver uma cláusula de data
                reconhecível (ex: "pd within ..."), reflete ela; senão cai no
                padrão de settings - não dá pra saber qual dos dois é só
                olhando aqui, por isso não rotula como "(padrão)". */}
            <FieldCard label={fieldLabels.year}>
              <p className="text-sm font-semibold text-gray-900">
                {selected.fields?.year && selected.fields.year.length > 0
                  ? selected.fields.year.join(', ')
                  : selected.year_range
                    ? `${selected.year_range.from} - ${selected.year_range.to}`
                    : '—'}
              </p>
            </FieldCard>

            {selected.complexity && (
              <FieldCard label="Complexidade">
                <p className="text-sm font-semibold text-gray-900">
                  {selected.complexity.level} ({selected.complexity.score.toFixed(1)}/100)
                </p>
              </FieldCard>
            )}

            {selected.warning && (
              <p className="text-xs text-amber-600">{friendlyWarningMessage(selected.warning)}</p>
            )}
          </div>
        </>
      )}

      {selected && selected.success && isEditing && (
        <div className="space-y-4 mt-1 mx-1">
          <FloatingLabelInput
            label="Query completa"
            name="edit-query"
            value={editQueryText}
            onChange={(e) => setEditQueryText(e.target.value)}
            placeholder='ex: TITLE("machine learning") AND (ABS("neural network") OR ABS("deep learning"))'
            isTextarea
            rows={10}
          />
          <QuerySyntaxMeter query={editQueryText} />
          <p className="text-xs text-gray-500 -mt-2">
            Edite o texto inteiro da query, incluindo AND/OR/NOT, parênteses e campos (ex: TITLE(...), ABS(...)).
            A complexidade é recalculada ao salvar.
          </p>

          <div className="flex gap-3 pt-1">
            <Button fullWidth size="sm" variant="secondary" onClick={onCancelEdit} disabled={isRebuilding}>
              Cancelar
            </Button>
            <Button fullWidth size="sm" onClick={onSaveEdit} disabled={isRebuilding}>
              {isRebuilding ? 'Salvando...' : 'Salvar'}
            </Button>
          </div>
        </div>
      )}
    </>
  )

  return (
    <div className="mb-8 flex flex-col h-95">
      <CandidatePickerLayout hasSelection={selectedIndex !== null} left={leftPane} right={rightPane} />
      <div className="mt-3 shrink-0">
        <Button size="sm" onClick={onRetry} disabled={isBusy}>
          {isLoading ? 'Gerando...' : 'Gerar outras'}
        </Button>
      </div>
    </div>
  )
}
