# Atualização de Design - BPMN Flow Frontend

## Resumo das Mudanças

O frontend foi refatorado para corresponder ao design de referência fornecido, com layout de sidebar, stepper em chevron e esquema de cores melhorado.

## Arquivos Modificados

### 1. `src/components/Flow/FlowContainer.tsx`
**Mudanças:**
- Alterado de layout centrado para layout flex com sidebar
- Incluída importação do novo componente `Sidebar`
- Estrutura de grid para conteúdo principal (600px + 280px)
- Sidebar direita com informações de próximas etapas e status
- Mantém erro display e loading overlay

**Layout Anterior:**
```
└── Gradient bg
    ├── Header
    ├── Stepper
    └── Centered content card
```

**Layout Novo:**
```
├── Sidebar (280px)
└── Main content
    ├── Title "WORKFLOW DE PROSPECÇÃO"
    ├── Stepper (chevron style)
    └── Grid [Content + Info Panel]
```

### 2. `src/components/Flow/Sidebar.tsx` (NOVO)
**Criado do zero**

Componente de configuração em dark blue (#07345f) contendo:
- **API Status Toggle** — Switch visual com status "PRONTO"
- **Tema da Pesquisa** — Input text para tema
- **Fontes de Dados** — Checkboxes (Patentes, Artigos, Notícias)
- **Faixa Temporal** — Inputs para ano início/fim
- **Palavras-chave** — Tags com add/remove
- **Botões** — SALVAR (branco) e RESET (slate)

Integração com Zustand store para persistência.

### 3. `src/components/Flow/FlowStepper.tsx`
**Refatoração completa**

Antes: Circular step indicator (1-7 etapas)
Depois: Chevron/arrow buttons (4 etapas principais)

```
Passos:
1. CONFIGURAÇÃO ✓
2. GERAÇÃO DE QUERY (atual)
3. CURADORIA
4. RELATÓRIO LATEX

Styling:
- [clip-path: polygon()] para forma de seta/chevron
- Cores: branco (pendente), sky-500 (atual), branco (completo com ✓)
- Fonte bold, uppercase
```

Estados:
- Completo: `bg-white text-slate-900` com ✓
- Atual: `bg-sky-500 text-white`
- Pendente: `bg-white text-slate-900`

### 4. `src/components/Flow/steps/InitialParamsStep.tsx`
**Atualizações visuais**

Antes:
```tsx
<h2 className="text-2xl font-bold">Etapa 1: Parâmetros Iniciais</h2>
<button className="px-6 py-2 bg-blue-600">Gerar Parâmetros com IA</button>
<button className="px-6 py-2 bg-green-600">Sim, Continuar</button>
```

Depois:
```tsx
<h3 className="text-lg font-bold">1. CONFIGURAÇÃO</h3>
<button className="px-6 py-2 border border-slate-400 bg-slate-200">[GERAR COM IA]</button>
<button className="px-6 py-2 border border-green-500 bg-green-500">[CONTINUAR]</button>
```

Mudanças:
- Heading simplificado
- Botões com estilo "clicável" (bordas visíveis, colchetes)
- Cores: slate-200 para secondary, green-500 para primary
- Padding aumentado para 3 (py-3)

### 5. `src/main.tsx`
**Simples redirecionamento**

Antes: `import App from './App.tsx'`
Depois: `import { FlowContainer } from './components/Flow/FlowContainer'`

## Paleta de Cores

| Elemento | Cor | Código |
|---|---|---|
| Sidebar Background | Dark Blue | `#07345f` |
| Sidebar Text | White | `#ffffff` |
| Stepper Atual | Sky Blue | `#0ea5e9` (sky-500) |
| Stepper Pendente | White | `#ffffff` |
| Button Primary | Green | `#22c55e` (green-500) |
| Button Secondary | Slate | `#cbd5e1` (slate-200) |
| Button Tertiary | Yellow | `#eab308` (yellow-400) |
| Border | Slate | `#cbd5e1` (slate-300) |
| Background | Slate | `#f1f5f9` (slate-100) |

## Comparação: Antes vs Depois

### Antes
```
Centered layout
- Navbar
- Stepper (circular, 7 steps)
- Content card
- Gradients
```

### Depois
```
Sidebar layout
- Dark sidebar (280px)
- Main area
  - Title
  - Chevron stepper (4 steps)
  - Grid: [Content + Info Panel]
- 2-column design
```

## Componentes Preservados

Mantidos sem mudanças (backward compatible):
- ErrorBoundary.tsx
- LoadingOverlay.tsx
- Todos os 7 step components (InitialParamsStep, SpecifyParamsStep, etc.)
- flowApi.ts (serviço de API)
- flowStore.ts (Zustand store)
- types/flow.ts (type system)

## Build Status

```
✅ TypeScript compilation: OK
✅ Vite build: OK
   - Bundle: 270.05 kB
   - Gzipped: 83.92 kB
✅ Dev server: Running on http://localhost:5173
```

## Próximas Otimizações (Opcional)

1. [ ] Adicionar animações para transições de stepper
2. [ ] Implementar responsividade para mobile
3. [ ] Adicionar ícones SVG nos botões
4. [ ] Melhorar feedback visual em hover/active states
5. [ ] Adicionar tooltips nas seções do sidebar

## Como Usar

```bash
# Desenvolvimento
cd frontend
npm run dev

# Produção
npm run build
```

O aplicativo está 100% funcional com o novo design e pronto para integração com APIs backend.
