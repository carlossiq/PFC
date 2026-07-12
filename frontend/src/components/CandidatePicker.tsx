import type { ReactNode } from 'react'

// Layout de duas colunas usado pelos steps que apresentam N candidatos
// gerados pela IA para o usuário escolher (temas no Step2, opções de query
// no Step3): lista selecionável à esquerda, painel de detalhe/edição à
// direita que desliza para dentro quando há uma seleção.
interface CandidatePickerLayoutProps {
  hasSelection: boolean
  left: ReactNode
  right: ReactNode
}

export function CandidatePickerLayout({ hasSelection, left, right }: CandidatePickerLayoutProps) {
  return (
    <div className="flex-1 flex gap-6 overflow-hidden">
      <div
        className={`
          bg-gray-100 rounded-xl border border-gray-200 p-4 overflow-y-auto
          transition-all duration-500 ease-in-out
          ${hasSelection ? 'w-1/2' : 'w-full'}
        `}
      >
        {left}
      </div>

      <div
        className={`
          bg-gray-100 rounded-xl border border-gray-200 p-4 overflow-y-auto
          transition-all duration-500 ease-in-out
          ${
            hasSelection
              ? 'w-1/2 opacity-100 translate-x-0'
              : 'w-0 opacity-0 translate-x-4 p-0 border-transparent pointer-events-none'
          }
        `}
      >
        {right}
      </div>
    </div>
  )
}

// Estilo do card clicável de um candidato, realçado quando selecionado.
export function selectableCardClass(isSelected: boolean, extraClassName = ''): string {
  return `
    py-2 px-3 rounded-lg border-2 text-left bg-white shadow-sm ${extraClassName}
    transition-all duration-300 ease-in-out
    ${
      isSelected
        ? 'border-[#0f9448] ring-2 ring-[#0f9448]/10 border-2'
        : 'border-gray-200 hover:border-[#0f9448]'
    }
  `
}

// Conversão entre lista e string separada por vírgula, usada pelos campos
// editáveis dos candidatos (Step2: keywords/studyArea; Step3: os 8 campos
// estruturados da query).
export function toCsv(values?: string[]): string {
  return values?.join(', ') ?? ''
}

export function parseCsv(value: string): string[] {
  return value.split(',').map((v) => v.trim()).filter(Boolean)
}
