import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'

interface RangeSliderInputProps {
  label: string
  value: number
  min: number
  max: number
  step: number
  infoIcon?: ReactNode
  onCommit: (value: number) => void
  disabled?: boolean
}

// Slider (min..max) + caixa de texto editável via teclado - digitar um valor
// fora do range corrige pro min/max mais próximo ao sair do campo (blur) ou
// apertar Enter. O slider salva ao soltar o botão (onChange do <input
// type=range> já dispara só na liberação, não a cada pixel do arraste -
// onInput é usado só pro feedback visual instantâneo enquanto arrasta).
export function RangeSliderInput({
  label,
  value,
  min,
  max,
  step,
  infoIcon,
  onCommit,
  disabled = false,
}: RangeSliderInputProps) {
  const [displayValue, setDisplayValue] = useState(String(value))
  const [sliderValue, setSliderValue] = useState(value)

  useEffect(() => {
    setDisplayValue(String(value))
    setSliderValue(value)
  }, [value])

  const clamp = (n: number) => Math.min(max, Math.max(min, n))

  const commitText = () => {
    const parsed = parseFloat(displayValue.replace(',', '.'))
    const next = Number.isFinite(parsed) ? clamp(parsed) : value
    setDisplayValue(String(next))
    setSliderValue(next)
    if (next !== value) onCommit(next)
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <label className="text-sm font-medium text-gray-800">{label}</label>
          {infoIcon}
        </div>
        <input
          type="text"
          inputMode="decimal"
          value={displayValue}
          disabled={disabled}
          onChange={(e) => setDisplayValue(e.target.value)}
          onBlur={commitText}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.currentTarget.blur()
            }
          }}
          className="w-24 text-right text-sm font-mono border border-gray-300 rounded-md px-2 py-1 text-gray-900 disabled:opacity-60 disabled:bg-gray-100"
        />
      </div>

      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={sliderValue}
        disabled={disabled}
        onInput={(e) => setSliderValue(parseFloat((e.target as HTMLInputElement).value))}
        onChange={(e) => {
          const next = clamp(parseFloat(e.target.value))
          setSliderValue(next)
          setDisplayValue(String(next))
          onCommit(next)
        }}
        className="w-full accent-[#0f9448] cursor-pointer"
      />

      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  )
}
