import { useEffect } from 'react'
import { useChartCreation } from '../../hooks/useChartCreation'
import { LoadingScreen } from '../LoadingScreen'
import { Button } from '../Button'
import { SectionHeader } from '../SectionHeader'
import { STEPS } from '../../constants/steps'

interface ChartCreationProps {
  step: number
  substep: number | null
  onBack: () => void
  onNext: () => void
}

// "Criação de Gráficos" (substep 1 de Exploração Final, depois de "Análise
// de Resultados") - roda a inferência estatística e os gráficos que dependem
// dela (ver useChartCreation.ts) automaticamente, numa única tela de loading
// (sem dividir em duas colunas como FinalResults/FinalExploration), e avança
// pro step de Relatório sozinho ao terminar - não há botão "Próximo" manual
// aqui, só "Voltar"/"Tentar novamente" se algo impedir o processo de rodar
// (ex.: falha ao salvar a sessão).
export function ChartCreation({ step, substep, onBack, onNext }: ChartCreationProps) {
  const isActive = step === STEPS.FINAL_EXPLORATION && substep === 1
  const { stageMessage, isDone, fatalError, retry } = useChartCreation(isActive)

  useEffect(() => {
    if (isActive && isDone) {
      onNext()
    }
  }, [isActive, isDone, onNext])

  if (!isActive) return null

  return (
    <div className="w-full flex flex-col h-full overflow-y-auto">
      <SectionHeader
        title="Criação de Gráficos"
        description="Gerando a amostra estatística e os gráficos da sessão a partir da busca final - isso pode levar alguns instantes."
      />

      <div className="flex-1 flex items-center justify-center">
        {fatalError ? (
          <div className="max-w-md w-full flex flex-col items-center gap-4 text-center">
            <p className="text-sm text-red-600 font-medium">{fatalError}</p>
            <div className="flex gap-4 w-full">
              <Button fullWidth variant="secondary" onClick={onBack}>
                Voltar
              </Button>
              <Button fullWidth onClick={retry}>
                Tentar novamente
              </Button>
            </div>
          </div>
        ) : (
          <LoadingScreen message={stageMessage} />
        )}
      </div>
    </div>
  )
}
