  import { useState } from 'react'

  interface FloatingLabelInputProps {
    label: string
    name: string
    value: string
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void
    placeholder?: string
    error?: boolean
    type?: string
    rows?: number
    isTextarea?: boolean
  }

  export function FloatingLabelInput({
    label,
    name,
    value,
    onChange,
    placeholder,
    error = false,
    type = 'text',
    rows,
    isTextarea = false,
  }: FloatingLabelInputProps) {
    const [isFocused, setIsFocused] = useState(false)

    const hasValue = value.trim().length > 0
    const floating = isFocused || hasValue

    const baseInput = `
    w-full px-4 rounded-lg border
    bg-gray-100
    focus:outline-none transition-all duration-200
    ${isTextarea
        ? 'pt-5 pb-2'
        : 'h-12 flex items-center pt-5 pb-1'
      }
    ${error
        ? 'border-red-500 focus:border-red-500 focus:ring-1 focus:ring-red-500'
        : 'border-gray-300 focus:border-[#0f9448] focus:ring-1 focus:ring-[#0f9448]'
      }
  `

    return (
      <div className="relative">
        {/* INPUT / TEXTAREA */}
        {isTextarea ? (
          <textarea
            name={name}
            value={value}
            onChange={onChange}
            rows={rows}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={floating ? placeholder : ''}
            className={baseInput}
          />
        ) : (
          <input
            type={type}
            name={name}
            value={value}
            onChange={onChange}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={floating ? placeholder : ''}
            className={baseInput}
          />
        )}

        {/* LABEL */}
        <label
  className={`
    absolute left-3 px-1 transition-all duration-200 pointer-events-none
    z-10 bg-transparent

    before:content-['']
    before:absolute
    before:left-0
    before:right-0
    before:top-1/2
    before:h-1
    before:-translate-y-1/2
    before:bg-gray-100
    before:-z-10

    ${floating
      ? `
          -top-2 text-xs
          ${error ? 'text-red-500' : 'text-[#0c7c3d]'}
        `
      : `
          top-3 text-sm text-gray-400 before:hidden
        `
    }
  `}
>
  {label}
</label>
      </div>
    )
  }
