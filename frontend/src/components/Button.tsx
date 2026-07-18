import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'accent' | 'link'
export type ButtonSize = 'xs' | 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  // xs: botões pequenos dentro de card (Editar/Especificar)
  // sm: botões de ação secundária, não full-width (Gerar de novo/outras/novos)
  // md (padrão): botões de navegação principal (Voltar/Próximo/Confirmar)
  size?: ButtonSize
  fullWidth?: boolean
}

const VARIANT_CLASSES: Record<Exclude<ButtonVariant, 'link'>, string> = {
  primary: 'bg-[#0f9448] hover:bg-[#0d843f] text-white',
  secondary: 'bg-gray-400 hover:bg-gray-500 text-white',
  accent: 'bg-indigo-600 hover:bg-indigo-700 text-white',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  xs: 'px-3 py-1.5 text-xs',
  sm: 'px-4 py-2 text-sm',
  md: 'px-4 py-2',
}

// Botão de ação compartilhado por todo o wizard de prospecção 
export function Button({
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  type = 'button',
  className = '',
  ...rest
}: ButtonProps) {
  if (variant === 'link') {
    return (
      <button
        type={type}
        className={`text-sm font-semibold text-[#0f9448] hover:text-[#0d843f] ${className}`}
        {...rest}
      />
    )
  }

  return (
    <button
      type={type}
      className={`${fullWidth ? 'flex-1 ' : ''}rounded-lg font-semibold transition-colors duration-300 disabled:opacity-60 disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
      {...rest}
    />
  )
}
