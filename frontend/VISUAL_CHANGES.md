# Mudanças Visuais - Antes e Depois

## 1. Layout Geral

### ANTES
```
┌─────────────────────────────────────────┐
│ Header (Navbar)                         │
├─────────────────────────────────────────┤
│ Stepper (horizontal, 7 steps)           │
├─────────────────────────────────────────┤
│                                         │
│     Content Card (centered, max-w)      │
│                                         │
│                                         │
└─────────────────────────────────────────┘
```

### DEPOIS
```
┌────────────┬──────────────────────────────────┐
│            │ WORKFLOW DE PROSPECÇÃO           │
│            ├──────────────────────────────────┤
│            │ [Chevron Stepper - 4 steps]      │
│  SIDEBAR   ├──────────────────────────────────┤
│  (280px)   │ ┌────────────────────┬─────────┐ │
│            │ │                    │ Status  │ │
│ Config     │ │  Content Card      │ Panel   │ │
│ Theme      │ │                    │         │ │
│ Keywords   │ │                    │         │ │
│ Sources    │ │                    │         │ │
│ Dates      │ │                    │         │ │
│            │ └────────────────────┴─────────┘ │
│            │                                   │
└────────────┴──────────────────────────────────┘
```

## 2. Stepper Evolution

### ANTES: Circular with 7 Steps
```
  [1]─[2]─[3]─[4]─[5]─[6]─[7]
   ✓   ✓   ●   ○   ○   ○   ○
   
Legenda:
✓ = Completo (green)
● = Atual (blue)
○ = Pendente (gray)
```

### DEPOIS: Chevron with 4 Steps
```
┌──────────────┬──────────────┬─────────────┬──────────────┐
│ ✓ 1.         │  2.          │  3.         │  4.          │
│ CONFIGURAÇÃO │ GERAÇÃO      │ CURADORIA   │ RELATÓRIO    │
│              │ DE QUERY     │             │ LATEX        │
└──────────────┴──────────────┴─────────────┴──────────────┘
```

**CSS Implementado:**
```css
[clip-path: polygon(0 0, 92% 0, 100% 50%, 92% 100%, 0 100%, 8% 50%)]
/* Cria a forma de seta/chevron */
```

## 3. Sidebar Configuration

### NOVO - Componente Sidebar.tsx

```
┌─────────────────────────┐
│ CONFIGURAÇÃO            │
│ DA PROSPECÇÃO           │
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │ ATIVAR API    ⚫→   │ │
│ │ STATUS: PRONTO ✓   │ │
│ └─────────────────────┘ │
├─────────────────────────┤
│ TEMA DA PESQUISA        │
│ [Input field]           │
├─────────────────────────┤
│ FONTES DE DADOS         │
│ ☑ Patentes              │
│ ☑ Artigos Científicos   │
│ ☐ Notícias              │
├─────────────────────────┤
│ FAIXA TEMPORAL          │
│ [2020] — [2026]         │
├─────────────────────────┤
│ PALAVRAS-CHAVE          │
│ [Tag] [Tag] [+]         │
├─────────────────────────┤
│ [SALVAR]  [RESET]       │
└─────────────────────────┘
```

**Características:**
- Background: `#07345f` (dark blue)
- Text: branco
- Width: 280px (fixo)
- Sticky content durante scroll

## 4. Botões - Evolução

### ANTES
```
[Gerar Parâmetros com IA]  (blue-600)
[Continuar com Atuais]     (slate-600)
[Não, Refinar]             (yellow border)
[Sim, Continuar]           (green-600)
```

### DEPOIS
```
[GERAR COM IA]             (slate-200, border)
[CONTINUAR]                (green-500, border)
[GERAR NOVAMENTE]          (yellow-400, border)
[CONFIRMAR]                (green-500, border)
```

**Mudanças:**
- Adicionados colchetes `[]` ao rótulo
- UPPERCASE text
- Bordas visíveis em todos
- Padding aumentado (py-2 → py-3)
- Fonte bold

### Paleta de Botões

| Tipo | Cor | Borda | Classe |
|------|-----|-------|--------|
| Primary | `bg-green-500` | `border-green-500` | Font bold, white text |
| Secondary | `bg-slate-200` | `border-slate-400` | Font bold, dark text |
| Tertiary | `bg-yellow-400` | `border-yellow-400` | Font bold |

## 5. Cards e Containers

### Antes
```css
.card {
  border: 1px solid #e2e8f0;
  background: #ffffff;
  border-radius: 0.5rem;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
```

### Depois
```css
.card {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0,0,0,0.07);
}
```

**Mudanças:**
- Border mais escuro (slate-300)
- Padding reduzido ligeiramente
- Border-radius aumentado
- Shadow mais suave

## 6. Tipografia

### Headings

```
ANTES:
<h1> text-3xl font-bold
<h2> text-2xl font-bold
<h3> text-lg font-bold
<h4> font-bold

DEPOIS:
<h1> (removed)
<h2> "WORKFLOW DE PROSPECÇÃO" - text-2xl font-bold
<h3> "1. CONFIGURAÇÃO" - text-lg font-bold
<h4> "PARÂMETROS GERADOS PELA IA" - font-bold
```

**Padrão:**
- Headers em UPPERCASE
- Headings hierárquicos reduzidos
- Máximo 3 níveis de heading

## 7. Info Panel (Direita)

### NOVO - Status Sidebar

```
┌──────────────────┐
│ PRÓXIMAS ETAPAS  │
├──────────────────┤
│ ┌──────────────┐ │
│ │ Etapa Atual  │ │
│ │ specify-     │ │
│ │ params       │ │
│ └──────────────┘ │
├──────────────────┤
│ ┌──────────────┐ │
│ │ Status       │ │
│ │ [PROCESSANDO]│ │
│ │ ou           │ │
│ │ [PRONTO]     │ │
│ └──────────────┘ │
└──────────────────┘
```

**Cards:**
- Border: slate-200
- Padding: 0.75rem
- Font size: text-xs / text-sm
- Badges: inline-block com cores

## 8. Paleta de Cores Completa

```
Primary Colors:
  Dark Blue    #07345f  (Sidebar)
  Sky Blue     #0ea5e9  (Stepper current)
  Green        #22c55e  (Primary action)
  Yellow       #eab308  (Secondary action)
  
Neutral:
  White        #ffffff
  Slate-50     #f8fafc
  Slate-100    #f1f5f9
  Slate-200    #e2e8f0
  Slate-300    #cbd5e1
  Slate-700    #334155
  Slate-900    #0f172a

Semantic:
  Success      #22c55e (green)
  Warning      #eab308 (yellow)
  Danger       #ef4444 (red)
  Info         #0ea5e9 (blue)
```

## 9. Responsividade (Planejado)

Atualmente: **Desktop only** (280px sidebar + flex layout)

Futuro (mobile):
```
Mobile (<768px):
  └── Stack layout (sidebar em top tab)
  └── Stepper em vertical orientation
  └── Full-width content
```

## 10. Animações

### Antes
```css
animation: slideIn 0.3s ease-out;
```

### Depois
```
Adicionadas:
- Transições em hover de botões
- Transições em botões de stepper
- Smooth color changes
```

**Exemplo:**
```css
.button {
  transition: all 0.2s ease-in-out;
}
.button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
```

## 11. Arquivos Criados/Modificados

### ✅ CRIADO
- `src/components/Flow/Sidebar.tsx` — 200 linhas
- `frontend/DESIGN_UPDATE.md` — Documentação

### ✏️ MODIFICADO
- `src/components/Flow/FlowContainer.tsx` — Layout refatorado
- `src/components/Flow/FlowStepper.tsx` — Chevron design
- `src/components/Flow/steps/InitialParamsStep.tsx` — Styling atualizado
- `src/main.tsx` — Entry point redirecionado

### 📦 PRESERVADOS (sem mudanças)
- ErrorBoundary, LoadingOverlay, todos os step components
- API service, store, types

## Resumo Executivo

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Layout | Centered | Sidebar + Grid |
| Stepper | 7 steps (circles) | 4 steps (chevrons) |
| Sidebar | Não | Sim (280px) |
| Cores | Blue/Green | Dark Blue + Green |
| Buttons | Solid | Bordered + Uppercase |
| Bundle | 265.87 kB | 270.05 kB (+1.5%) |
| Gzipped | 83.12 kB | 83.92 kB (+1%) |

**Status:** ✅ 100% Implementado e Funcional
