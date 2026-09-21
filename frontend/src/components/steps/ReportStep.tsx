import { useEffect, useState } from 'react'
import { STEPS } from '../../constants/steps'
import { useFormStore } from '../../stores/useFormStore'
import { getReportDocument } from '../../services/report'
import { LoadingScreen } from '../LoadingScreen'
import { ReportGeneration } from './ReportGeneration'
import { ReportDocumentEditor } from './ReportDocumentEditor'

interface ReportStepProps {
  step: number
  substep: number | null
  onBack: () => void
}

// Passo "Geração do Relatório" (STEPS.REPORT) - decide entre o checklist de
// seções (ReportGeneration) e o editor do documento já montado
// (ReportDocumentEditor), consultando GET /report/{id}/document uma vez ao
// entrar no passo: uma sessão que já tem `.tex` montado (ex: usuário saiu no
// meio da edição do documento e voltou) pula direto pro editor, sem refazer
// o checklist. Substitui o antigo placeholder genérico em OutrosSteps.tsx.
export function ReportStep({ step, onBack }: ReportStepProps) {
  const isActive = step === STEPS.REPORT
  const sessionId = useFormStore((s) => s.sessionId)

  const [phase, setPhase] = useState<'loading' | 'sections' | 'document'>('loading')
  const [initialTexContent, setInitialTexContent] = useState<string | null>(null)

  useEffect(() => {
    if (!isActive || !sessionId) return
    let cancelled = false
    getReportDocument(sessionId)
      .then((doc) => {
        if (cancelled) return
        if (doc.hasReport && doc.texContent) {
          setInitialTexContent(doc.texContent)
          setPhase('document')
        } else {
          setPhase('sections')
        }
      })
      .catch((err) => {
        console.error('Falha ao verificar o estado do relatório, iniciando o checklist:', err)
        if (!cancelled) setPhase('sections')
      })
    return () => {
      cancelled = true
    }
  }, [isActive, sessionId])

  if (!isActive) return null

  // sessionId só é null se o usuário chegou aqui sem nunca ter salvo a
  // sessão (não deveria acontecer - ver useChartCreation.ts, que já garante
  // o primeiro save antes de qualquer coisa no passo anterior).
  if (!sessionId || phase === 'loading') {
    return <LoadingScreen message="Carregando relatório..." fullscreen={false} />
  }

  if (phase === 'document') {
    return <ReportDocumentEditor sessionId={sessionId} initialTexContent={initialTexContent} />
  }

  return (
    <ReportGeneration
      sessionId={sessionId}
      onBack={onBack}
      onAssembled={(texContent) => {
        setInitialTexContent(texContent)
        setPhase('document')
      }}
    />
  )
}
