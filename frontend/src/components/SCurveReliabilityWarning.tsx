import { AlertTriangle } from 'lucide-react'
import type { SCurveFitQuality } from '../services/report'

// Antes desenhado dentro do próprio PNG da curva S (ver
// ReportService._render_s_curve_chart) - agora é só texto vindo do backend
// (GeneratedChart.fitQuality), exibido como aviso separado da imagem.
// Renderiza null quando não há ajuste, quando o ajuste é confiável, ou
// quando fitQuality ainda não foi buscado (curva salva antiga, gerada antes
// desse campo existir). Reaproveitado tanto em FinalResults.tsx (curva
// recém-gerada) quanto em SessionCard.tsx (curva já salva).
export function SCurveReliabilityWarning({ fitQuality }: { fitQuality: SCurveFitQuality | null | undefined }) {
  if (!fitQuality || fitQuality.reliable || !fitQuality.warning) return null

  return (
    <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
      <AlertTriangle size={14} className="mt-0.5 shrink-0" />
      <p>
        <span className="font-semibold">Ajuste pouco confiável: </span>
        {fitQuality.warning}
      </p>
    </div>
  )
}
