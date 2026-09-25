import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Sparkles, X } from 'lucide-react'
import { Button } from '../Button'
import type { ReviewLatexIssue, ReviewSuggestion } from '../../services/report'

export type ReviewSuggestionItem = ReviewSuggestion & { id: string }
// `original`: o trecho em [offset, offset+length) no momento da revisão -
// usado pra conferir que ainda está no lugar antes de corrigir.
export type ReviewIssueItem = ReviewLatexIssue & { id: string; original: string }

interface ReviewPanelProps {
  issues: ReviewIssueItem[]
  suggestions: ReviewSuggestionItem[]
  scopeSections: string[]
  warnings: string[]
  staleIds: Set<string>
  hasAiResults: boolean
  isReviewing: boolean
  isReviewingAi: boolean
  onClose: () => void
  onRerun: () => void
  onRunAi: () => void
  onGoTo: (offset: number, length: number) => void
  // Correções aprovadas: sugestão -> substituição escolhida.
  onApply: (items: Array<{ id: string; offset: number; length: number; original: string; replacement: string }>) => void
}

const SOURCE_LABELS: Record<ReviewSuggestion['source'], string> = {
  languagetool: 'LanguageTool',
  ia: 'IA',
}

// Painel lateral (à direita do .tex) da revisão: problemas de LaTeX e
// sugestões de ortografia/acentuação/concordância - LanguageTool no
// documento todo, IA (opcional) só nas seções geradas por IA e trechos
// editados (ver report_review.py). Nada é aplicado sem o usuário marcar e
// clicar em "Aplicar".
export function ReviewPanel({
  issues,
  suggestions,
  scopeSections,
  warnings,
  staleIds,
  hasAiResults,
  isReviewing,
  isReviewingAi,
  onClose,
  onRerun,
  onRunAi,
  onGoTo,
  onApply,
}: ReviewPanelProps) {
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  // Qual substituição foi escolhida, quando o LanguageTool oferece várias.
  const [choice, setChoice] = useState<Record<string, number>>({})

  const selectable = suggestions.filter((s) => s.replacements.length > 0 && !staleIds.has(s.id))
  const allSelected = selectable.length > 0 && selectable.every((s) => selected.has(s.id))

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function applySelected() {
    const items = selectable
      .filter((s) => selected.has(s.id))
      .map((s) => ({
        id: s.id,
        offset: s.offset,
        length: s.length,
        original: s.original,
        replacement: s.replacements[choice[s.id] ?? 0],
      }))
    if (items.length === 0) return
    onApply(items)
    setSelected(new Set())
  }

  function fixIssue(issue: ReviewIssueItem) {
    if (issue.offset === null || issue.replacement === null) return
    onApply([
      { id: issue.id, offset: issue.offset, length: issue.length, original: issue.original, replacement: issue.replacement },
    ])
  }

  const busy = isReviewing || isReviewingAi

  return (
    <div className="shrink-0 w-80 border border-gray-200 rounded-lg bg-white flex flex-col min-h-0">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-600">Revisão</p>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-700" aria-label="Fechar revisão">
          <X size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4 text-xs">
        {busy && (
          <p className="text-gray-500">{isReviewingAi ? 'Revisando com IA (pode levar alguns segundos)...' : 'Revisando...'}</p>
        )}

        {warnings.map((warning) => (
          <p key={warning} className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1.5 text-amber-800">
            {warning}
          </p>
        ))}

        <p className="text-gray-500">
          LanguageTool: <span className="text-gray-700">documento inteiro (exceto o quadro de busca)</span>
        </p>
        {hasAiResults && scopeSections.length > 0 && (
          <p className="text-gray-500">
            IA: <span className="text-gray-700">{scopeSections.join('; ')}</span>
          </p>
        )}

        <section>
          <p className="font-semibold text-gray-700 mb-1.5">Problemas de LaTeX ({issues.length})</p>
          {issues.length === 0 && (
            <p className="flex items-center gap-1 text-[#0f9448]">
              <CheckCircle2 size={12} /> Nenhum problema encontrado.
            </p>
          )}
          <ul className="space-y-1.5">
            {issues.map((issue) => (
              <li key={issue.id} className="rounded-md border border-gray-200 px-2 py-1.5">
                <div className="flex items-start gap-1.5">
                  <AlertTriangle
                    size={12}
                    className={`mt-0.5 shrink-0 ${issue.severity === 'error' ? 'text-red-600' : 'text-amber-600'}`}
                  />
                  <button
                    type="button"
                    className="text-left text-gray-700 hover:text-gray-900"
                    onClick={() => issue.offset !== null && onGoTo(issue.offset, issue.length)}
                    disabled={issue.offset === null}
                  >
                    {issue.line > 0 && <span className="font-semibold">Linha {issue.line}: </span>}
                    {issue.message}
                  </button>
                </div>
                {issue.replacement !== null && issue.offset !== null && !staleIds.has(issue.id) && (
                  <button
                    type="button"
                    onClick={() => fixIssue(issue)}
                    className="mt-1 text-[11px] font-semibold text-[#0f9448] hover:text-[#0d843f]"
                  >
                    Corrigir
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section>
          <div className="flex items-center justify-between mb-1.5">
            <p className="font-semibold text-gray-700">Sugestões de texto ({suggestions.length})</p>
            {selectable.length > 0 && (
              <label className="flex items-center gap-1 text-gray-500">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={() => setSelected(allSelected ? new Set() : new Set(selectable.map((s) => s.id)))}
                />
                Todas
              </label>
            )}
          </div>
          {suggestions.length === 0 && !busy && (
            <p className="flex items-center gap-1 text-[#0f9448]">
              <CheckCircle2 size={12} /> Nenhuma sugestão.
            </p>
          )}
          <ul className="space-y-1.5">
            {suggestions.map((s) => {
              const isStale = staleIds.has(s.id)
              return (
                <li
                  key={s.id}
                  className={`rounded-md border px-2 py-1.5 ${isStale ? 'border-gray-200 opacity-50' : 'border-gray-200'}`}
                >
                  <div className="flex items-start gap-1.5">
                    <input
                      type="checkbox"
                      className="mt-0.5"
                      checked={selected.has(s.id)}
                      disabled={isStale || s.replacements.length === 0}
                      onChange={() => toggle(s.id)}
                    />
                    <div className="min-w-0 flex-1">
                      <button
                        type="button"
                        className="text-left"
                        onClick={() => onGoTo(s.offset, s.length)}
                        title="Mostrar no texto"
                      >
                        <span className="line-through text-red-600">{s.original}</span>
                        {s.replacements.length > 0 && (
                          <span className="text-[#0f9448] font-semibold"> → {s.replacements[choice[s.id] ?? 0]}</span>
                        )}
                      </button>
                      {s.replacements.length > 1 && !isStale && (
                        <select
                          className="mt-1 block w-full rounded border border-gray-200 text-[11px]"
                          value={choice[s.id] ?? 0}
                          onChange={(e) => setChoice((c) => ({ ...c, [s.id]: Number(e.target.value) }))}
                        >
                          {s.replacements.map((r, i) => (
                            <option key={r} value={i}>
                              {r}
                            </option>
                          ))}
                        </select>
                      )}
                      <p className="mt-0.5 text-gray-500">{s.message}</p>
                      <p className="mt-0.5 text-[10px] text-gray-400">
                        {s.category} · {SOURCE_LABELS[s.source]}
                        {s.section ? ` · ${s.section}` : ''}
                        {isStale ? ' · desatualizada (o trecho mudou)' : ''}
                      </p>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      </div>

      <div className="border-t border-gray-200 p-3 space-y-2">
        <Button fullWidth size="sm" onClick={applySelected} disabled={busy || selected.size === 0} type="button">
          Aplicar selecionadas ({selected.size})
        </Button>
        <div className="flex gap-2">
          <Button fullWidth size="sm" variant="secondary" onClick={onRerun} disabled={busy} type="button">
            Revisar de novo
          </Button>
          <Button fullWidth size="sm" variant="secondary" onClick={onRunAi} disabled={busy} type="button">
            <span className="inline-flex items-center gap-1">
              <Sparkles size={12} /> {hasAiResults ? 'Refazer com IA' : 'Revisão com IA'}
            </span>
          </Button>
        </div>
      </div>
    </div>
  )
}
