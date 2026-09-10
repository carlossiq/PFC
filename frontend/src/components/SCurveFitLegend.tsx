// Legenda estática explicando GP/MP/SP - os anos de cada ponto já aparecem
// desenhados na própria imagem da curva S (ver
// ReportService._render_s_curve_chart), então esse componente não recebe
// nem depende de nenhum dado calculado, só texto fixo. Reaproveitado tanto
// em FinalResults.tsx (curva recém-gerada) quanto em SessionCard.tsx (curva
// já salva, consultada sem regenerar).
export function SCurveFitLegend() {
  return (
    <dl className="text-xs text-gray-600 space-y-1.5">
      <div className="flex flex-wrap items-baseline gap-x-1.5">
        <dt className="shrink-0 font-bold text-sm text-gray-900">GP — Ponto de Crescimento</dt>
        <dd>início da fase de crescimento real da tecnologia.</dd>
      </div>
      <div className="flex flex-wrap items-baseline gap-x-1.5">
        <dt className="shrink-0 font-bold text-sm text-gray-900">MP — Ponto Médio</dt>
        <dd>ano de maior taxa de publicação (pico de crescimento).</dd>
      </div>
      <div className="flex flex-wrap items-baseline gap-x-1.5">
        <dt className="shrink-0 font-bold text-sm text-gray-900">SP — Ponto de Saturação</dt>
        <dd>início da fase de maturidade/estabilização.</dd>
      </div>
    </dl>
  )
}
