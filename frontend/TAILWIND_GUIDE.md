# TailwindCSS - Guia de Estilos AGIA

## Visão Geral

O frontend AGIA usa TailwindCSS 4 para estilização. Toda a interface é estilizada com classes utilitárias do Tailwind.

## Configuração

**Arquivo**: `tailwind.config.js`

### Cores Customizadas

```javascript
// Cores AGIA
agia: {
  'dark-blue': '#0f172a',     // Sidebar background
  'dark-slate': '#1e293b',    // Sidebar darker
  'light-slate': '#f1f5f9',   // Background
  'border': '#e2e8f0',        // Borders
  'text': '#1e293b',          // Text color
}

// Cores dos Botões
'btn-yellow': '#facc15',      // Gerar Novamente
'btn-green': '#22c55e',       // Confirmar
'btn-red': '#ef4444',         // Descartar
```

### Fontes

```javascript
fontFamily: {
  sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', ...],
  mono: ['Monaco', 'Menlo', 'Ubuntu Mono', monospace],
}
```

### Tamanhos de Fonte Padrão

- `xs`: 0.75rem (12px)
- `sm`: 0.875rem (14px)
- `base`: 1rem (16px)
- `lg`: 1.125rem (18px)
- `xl`: 1.25rem (20px)

## Componentes Customizados

### Botões

Classe utilitária `@layer components` com componentes prontos:

**Primário** (Azul)
```jsx
<button className="btn-primary">Clique aqui</button>
```

**Sucesso** (Verde)
```jsx
<button className="btn-success">Confirmar e Prosseguir</button>
```

**Warning** (Amarelo)
```jsx
<button className="btn-warning">Gerar Novamente</button>
```

**Danger** (Vermelho)
```jsx
<button className="btn-danger">Descartar</button>
```

**Secundário** (Outline)
```jsx
<button className="btn-secondary">Refinar Manualmente</button>
```

### Cards

```jsx
<div className="card">
  <h3>Título</h3>
  {/* conteúdo */}
</div>
```

### Inputs

```jsx
// Input normal (branco)
<input className="input-field" />

// Input escuro (sidebar)
<input className="input-field-dark" />
```

### Labels

```jsx
// Label pequeno (light)
<label className="label-sm">Tema</label>

// Label pequeno (dark/sidebar)
<label className="label-dark">Fontes de Dados</label>
```

### Tags/Badges

```jsx
// Tag cinza (padrão)
<span className="tag">JavaScript</span>

// Tag azul
<span className="tag-blue">Featured</span>
```

## Paleta de Cores

### Azuis (Primária)
```
slate-900  #0f172a  (muito escuro - sidebar)
slate-800  #1e293b  (escuro)
slate-700  #334155  (médio escuro)
slate-600  #475569  (médio)
slate-500  #64748b  (médio claro)
blue-600   #2563eb  (azul principal - ativa)
blue-500   #3b82f6  (azul claro)
```

### Botões
```
yellow-400 #facc15  (Gerar Novamente)
green-500  #22c55e  (Aceitar/Confirmar)
red-500    #ef4444  (Descartar)
```

### Fundos e Borders
```
white      #ffffff  (Cards)
slate-50   #f8fafc  (Background geral)
slate-100  #f1f5f9  (Hover, backgrounds leves)
slate-200  #e2e8f0  (Borders)
slate-300  #cbd5e1  (Borders escuros)
```

## Espaciamento

### Padrão Tailwind

- `p-2` = 0.5rem (8px) - Pequeno
- `p-4` = 1rem (16px) - Médio
- `p-6` = 1.5rem (24px) - Grande
- `p-8` = 2rem (32px) - Muito grande

### Uso Comum

```jsx
// Padding simétrico
<div className="p-6">Conteúdo</div>

// Padding por lado
<div className="px-6 py-4">Conteúdo</div>

// Margin
<div className="mb-6">Com margem inferior</div>
<div className="gap-3">Gap entre filhos flexbox</div>
```

## Responsive Design

### Breakpoints

```
sm: 640px
md: 768px
lg: 1024px
xl: 1280px
2xl: 1536px
```

### Uso

```jsx
// Diferentes tamanho em diferentes telas
<div className="w-full md:w-1/2 lg:w-1/3">
  Responsive width
</div>

// Mostrar/esconder
<div className="hidden md:block">
  Mostra apenas em tablet+
</div>
```

## Flexbox e Grid

### Flexbox

```jsx
// Row (padrão)
<div className="flex gap-4">
  <div>Item 1</div>
  <div>Item 2</div>
</div>

// Column
<div className="flex flex-col gap-4">
  <div>Item 1</div>
  <div>Item 2</div>
</div>

// Justificação
<div className="flex justify-between">Espaçado</div>
<div className="flex justify-center">Centralizado</div>
<div className="flex justify-start">À esquerda</div>
```

### Items

```jsx
<div className="flex items-center">Verticalmente centralizado</div>
<div className="flex items-stretch">Altura total</div>
```

## Estados Interativos

### Hover

```jsx
<button className="bg-blue-600 hover:bg-blue-700">
  Muda cor ao passar o mouse
</button>
```

### Focus

```jsx
<input className="focus:outline-none focus:ring-2 focus:ring-blue-500" />
```

### Disabled

```jsx
<button disabled className="disabled:bg-slate-400">
  Desabilitado
</button>
```

### Active

```jsx
<button className="active:scale-95">
  Escala ao clicar
</button>
```

## Exemplo Completo de Componente

```jsx
export const MyComponent = () => {
  return (
    <div className="p-6 bg-white rounded-lg shadow-md border border-slate-200">
      {/* Header */}
      <h2 className="text-lg font-bold text-slate-900 mb-4">
        Título
      </h2>

      {/* Conteúdo */}
      <p className="text-sm text-slate-600 mb-6">
        Descrição do componente
      </p>

      {/* Botões */}
      <div className="flex gap-3">
        <button className="btn-secondary">
          Cancelar
        </button>
        <button className="btn-primary">
          Confirmar
        </button>
      </div>
    </div>
  );
};
```

## Utilitários Mais Usados

| Classe | O que faz |
|--------|-----------|
| `flex` | Display flex |
| `flex-col` | Flex direction column |
| `gap-4` | Gap entre items |
| `p-6` | Padding 1.5rem |
| `mb-4` | Margin-bottom 1rem |
| `bg-white` | Background branco |
| `text-sm` | Font-size small |
| `font-bold` | Font-weight bold |
| `uppercase` | Text-transform uppercase |
| `rounded` | Border-radius |
| `shadow-md` | Box-shadow médio |
| `border` | Border 1px |
| `hover:` | Hover state |
| `focus:` | Focus state |
| `disabled:` | Disabled state |
| `transition-` | Animação suave |

## Diferenças Sidebar vs Centro

### Sidebar (dark)
```jsx
<div className="bg-slate-900 text-white">
  <label className="label-dark">Escuro</label>
  <input className="input-field-dark" />
</div>
```

### Centro (light)
```jsx
<div className="bg-slate-50">
  <label className="label-sm">Claro</label>
  <input className="input-field" />
</div>
```

## Performance

- TailwindCSS é **purificado em build** - apenas classes usadas são incluídas
- Bundle CSS: **~7.4KB gzipped**
- Sem CSS não-utilizado
- Carrega rápido no navegador

## Recursos Oficiais

- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Color Palette](https://tailwindcss.com/docs/customizing-colors)
- [Layout](https://tailwindcss.com/docs/display)
- [Flexbox](https://tailwindcss.com/docs/flexbox)

## Dicas

1. **Use variáveis de espaçamento**: `p-4`, `gap-3`, etc.
2. **Combine com @ aplicar**: Crie componentes em `@layer components`
3. **Use dark mode**: Adicione `dark:` prefix para versões escuras
4. **Responsive first**: Mobile-first com `md:`, `lg:`, etc.
5. **Não customize tudo**: Use padrões do Tailwind quando possível

---

**Tailwind Version**: 4.0.0  
**Config File**: `tailwind.config.js`  
**Globals**: `src/index.css`
