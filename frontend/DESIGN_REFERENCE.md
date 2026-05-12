# Design Reference Guide - Rápido

## 🎨 Quick Color Palette

```
Primary Colors:
  #07345f  Dark Blue (Sidebar) ⬛
  #0ea5e9  Sky Blue (Current step) 🔵
  #22c55e  Green (Primary action) 🟢
  #eab308  Yellow (Secondary action) 🟡
  #ffffff  White (Cards, pending) ⚪
  
Neutral:
  #f1f5f9  Slate-100 (Background)
  #e2e8f0  Slate-200 (Light borders)
  #cbd5e1  Slate-300 (Borders)
  #0f172a  Slate-900 (Dark text)
```

## 📐 Layout Grid

```
Sidebar (280px)  |  Main Content
                 |  ├─ Title (h2)
                 |  ├─ Stepper
                 |  └─ Grid: Content(600px+) | Info(280px)
```

## 🔘 Button Styles

```
Primary (Action):
  bg-green-500 border-green-500 text-white font-bold
  Ex: [CONTINUAR]

Secondary (Generate):
  bg-slate-200 border-slate-400 text-slate-900 font-bold
  Ex: [GERAR COM IA]

Tertiary (Retry):
  bg-yellow-400 border-yellow-400 text-slate-900 font-bold
  Ex: [GERAR NOVAMENTE]

All buttons:
  └─ px-6 py-3 rounded-md [UPPERCASE]
```

## 📊 Stepper

```
4 Main Steps (chevron shape):
  1. CONFIGURAÇÃO
  2. GERAÇÃO DE QUERY
  3. CURADORIA
  4. RELATÓRIO LATEX

States:
  ✓ Completo  → bg-white text-slate-900
  ● Atual     → bg-sky-500 text-white
  ○ Pendente  → bg-white text-slate-900
```

## 🔧 Sidebar Components

```
┌─ CONFIGURAÇÃO DA PROSPECÇÃO
├─ API Status (toggle + status badge)
├─ Theme Input
├─ Data Sources (checkboxes)
├─ Temporal Range (2 inputs)
├─ Keywords (tags with add/remove)
└─ Buttons (SALVAR | RESET)
```

## 📱 Responsive Notes

Current: **Desktop only** (280px + flex)

Future mobile plan:
```
<768px:
  └─ Stack layout
  └─ Sidebar in collapsible nav
  └─ Full-width content
  └─ Vertical stepper
```

## 🎯 Common Patterns

### Headings
```tsx
<h2 className="text-2xl font-bold">WORKFLOW DE PROSPECÇÃO</h2>
<h3 className="text-lg font-bold mb-4">1. CONFIGURAÇÃO</h3>
<h4 className="font-bold mb-3">PARÂMETROS GERADOS PELA IA</h4>
```

### Cards
```tsx
<div className="rounded-xl border border-slate-300 bg-white p-6 shadow-lg">
  Content
</div>
```

### Info Panels
```tsx
<div className="rounded-lg border border-slate-200 bg-white p-3">
  <div className="font-semibold text-slate-900">Label</div>
  <div className="text-xs">Value</div>
</div>
```

### Status Badge
```tsx
<span className="inline-block bg-green-100 text-green-800 px-2 py-1 
  rounded text-xs font-bold">
  PRONTO
</span>
```

## 📝 Typography

| Element | Class | Example |
|---------|-------|---------|
| Main Title | `text-2xl font-bold` | WORKFLOW DE PROSPECÇÃO |
| Section | `text-lg font-bold` | 1. CONFIGURAÇÃO |
| Label | `font-bold` | PARÂMETROS GERADOS |
| Body | `text-sm text-slate-700` | Description text |
| Small | `text-xs` | Status badges |

## 🎭 Component Import Paths

```typescript
// Sidebar
import { Sidebar } from '@/components/Flow/Sidebar';

// Steps
import { InitialParamsStep } from '@/components/Flow/steps/InitialParamsStep';
import { SpecifyParamsStep } from '@/components/Flow/steps/SpecifyParamsStep';
import { SearchResultsStep } from '@/components/Flow/steps/SearchResultsStep';
import { QueryRefinementStep } from '@/components/Flow/steps/QueryRefinementStep';
import { FinalSearchStep } from '@/components/Flow/steps/FinalSearchStep';
import { ChartsStep } from '@/components/Flow/steps/ChartsStep';
import { ReportStep } from '@/components/Flow/steps/ReportStep';

// Support
import { ErrorBoundary } from '@/components/Flow/ErrorBoundary';
import { LoadingOverlay } from '@/components/Flow/LoadingOverlay';
import { FlowStepper } from '@/components/Flow/FlowStepper';
import { FlowContainer } from '@/components/Flow/FlowContainer';
```

## 📦 Tailwind Utilities Reference

```tailwind
/* Background colors */
bg-[#07345f]      /* Dark blue (custom) */
bg-sky-500        /* Sky blue */
bg-green-500      /* Green */
bg-yellow-400     /* Yellow */
bg-slate-100      /* Light gray bg */
bg-white          /* White */

/* Text colors */
text-white        /* White text */
text-slate-900    /* Dark text */
text-green-800    /* Dark green */
text-slate-600    /* Gray text */

/* Borders */
border-slate-300  /* Default border */
border-green-500  /* Green border */
border-yellow-400 /* Yellow border */

/* Sizing */
w-[280px]         /* Fixed width */
px-6, py-8        /* Padding */
rounded-xl        /* Large radius */
rounded-md        /* Medium radius */

/* Layout */
flex              /* Flexbox */
grid              /* CSS Grid */
overflow-hidden   /* Clip overflow */

/* Effects */
shadow-lg         /* Large shadow */
border            /* 1px border */
```

## 🚀 Quick Start Template

```tsx
// New component with design pattern
import React from 'react';
import { useFlowStore } from '@/store/flowStore';

export const MyComponent: React.FC = () => {
  const { setCurrentStep } = useFlowStore();

  return (
    <div className="space-y-6">
      {/* Heading */}
      <h3 className="text-lg font-bold mb-4">SECTION TITLE</h3>

      {/* Content Card */}
      <div className="rounded-xl border border-slate-300 bg-white p-6 shadow-lg">
        <h4 className="font-bold mb-3">CARD TITLE</h4>
        {/* Content here */}
      </div>

      {/* Buttons */}
      <div className="flex gap-3 justify-end">
        <button className="px-6 py-3 rounded-md border border-slate-400 
          bg-slate-200 font-bold hover:bg-slate-300">
          [SECONDARY]
        </button>
        <button className="px-6 py-3 rounded-md border border-green-500 
          bg-green-500 font-bold text-white hover:bg-green-600">
          [PRIMARY]
        </button>
      </div>
    </div>
  );
};
```

## 🐛 Common Issues & Fixes

### Issue: Stepper looks broken
**Solution:** Check clip-path is applied to parent div, not inside JSX

### Issue: Colors don't match reference
**Solution:** Use exact color codes:
- `#07345f` (not `#073460`)
- `bg-[#07345f]` (with brackets for custom colors)

### Issue: Sidebar not sticky
**Solution:** Add `position: sticky; top: 0;` to sidebar or parent container

### Issue: Grid breaks on small screens
**Solution:** Add responsive grid:
```tsx
className="grid grid-cols-1 lg:grid-cols-[600px_280px]"
```

## 📊 File Structure

```
src/components/Flow/
├── FlowContainer.tsx        /* Main orchestrator */
├── Sidebar.tsx              /* Configuration panel (NEW) */
├── FlowStepper.tsx          /* 4-step chevron stepper */
├── ErrorBoundary.tsx        /* Error handling */
├── LoadingOverlay.tsx       /* Loading spinner */
└── steps/
    ├── InitialParamsStep.tsx
    ├── SpecifyParamsStep.tsx
    ├── SearchResultsStep.tsx
    ├── QueryRefinementStep.tsx
    ├── FinalSearchStep.tsx
    ├── ChartsStep.tsx
    └── ReportStep.tsx
```

## 🔗 Dependencies

```json
{
  "react": "^18.x",
  "zustand": "^4.x",
  "axios": "^1.x",
  "tailwindcss": "^4.x",
  "typescript": "^5.x"
}
```

## 📍 Key Measurements

```
Sidebar width:        280px (fixed)
Content min-width:    600px
Info panel width:     280px
Grid gap:             2rem (32px)
Padding (main):       px-10 py-9
Padding (sidebar):    px-6 py-8
Border radius:        rounded-xl (0.75rem)
Button padding:       px-6 py-3
```

## ✅ Design Checklist

Before committing design changes:

- [ ] Colors match palette
- [ ] Buttons have borders and uppercase labels
- [ ] Headings follow hierarchy (h2 → h3 → h4)
- [ ] Cards have proper shadows and borders
- [ ] Sidebar styling applied correctly
- [ ] Stepper displays chevron shape
- [ ] Grid layout responsive
- [ ] Typography consistent
- [ ] Spacing follows pattern (use space-y, gap utilities)
- [ ] No broken clip-paths

## 🎬 Live Demo

```bash
cd frontend
npm run dev
# Open http://localhost:5173
```

## 📚 Related Documentation

- [DESIGN_UPDATE.md](./DESIGN_UPDATE.md) — Detailed changes
- [VISUAL_CHANGES.md](./VISUAL_CHANGES.md) — Before/After
- [CHANGELOG.md](./CHANGELOG.md) — Technical changelog

---

**Last Updated:** 2026-04-28  
**Design System Version:** 1.0  
**Status:** Production Ready ✅
