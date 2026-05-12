# 🎨 Figma Design - Quick Reference Card

## 📊 Fluxo em 1 Página

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  STEP 1              STEP 2             STEP 3            STEP 4       │
│  Parâmetros   →    Especificar   →   Busca Inicial  →   Refinamento  │
│  Iniciais           de Params         de Query         (com loop)     │
│  [Form]           [Choice]           [Results]        [Select Terms]  │
│                                           ↓                 ↓         │
│                                       [Satisfeito?]    [Satisfeito?]  │
│                                       SIM ↓ NÃO       SIM ↓ NÃO      │
│                                           ↓ └──────────┘              │
│  ┌──────────────────────────────────────┘                           │
│  ↓                                                                    │
│  STEP 5              STEP 6            STEP 7                        │
│  Busca Final   →   Validação    →    Relatório                      │
│  + Charts          de Gráficos       & Download                      │
│  [Spinner]         [Charts Grid]     [Report Card]                   │
│                        ↓                 ↓                            │
│                    [Satisfeito?]    [Download PDF]                   │
│                    SIM ↓ NÃO                                          │
│                        ↓ └──────────┐                                │
│                                     ↓ [Regenerar]                    │
│                      [Prosseguir]                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🎯 Dados por Step

| Step | Input | Output | Action |
|------|-------|--------|--------|
| 1 | Theme, Keywords, Dates, Sources | SearchParams | Save |
| 2 | SearchParams anterior | SearchParams refinados | - |
| 3 | SearchParams | SearchResult[] (50-200) | Save |
| 4 | SearchResult[] | RefinedQuery | Save (loop) |
| 5 | RefinedQuery | Chart[] (3-5) | - |
| 6 | Chart[] | Chart[] (filtered) | Delete |
| 7 | All data | ReportData + File | Download |

## 🎨 Colors

```
Primary:     #07345F (Dark Blue - Sidebar)
Active:      #0EA5E9 (Sky Blue - Current step)
Success:     #22C55E (Green - Actions)
Warning:     #EAB308 (Yellow - Secondary)
Error:       #EF4444 (Red - Errors)
Text:        #0F172A (Dark) / #FFFFFF (Light)
Border:      #CBD5E1 (Slate-300)
Background:  #F1F5F9 (Slate-100)
Card:        #FFFFFF (White)
```

## 📐 Layout

```
Sidebar: 280px | Main: Flex (600px min) | Panel: 280px
Padding: 32px | Gap: 16-32px | Radius: 12px
Font: 14px (body) | 24px (h2) | 32px (h1)
```

## 🔘 Components

**Button Types:**
- Primary: Green bg + white text [CONTINUAR]
- Secondary: Gray bg + dark text [GERAR]
- Tertiary: Yellow bg [REGENERAR]
- Link: Blue text

**Input States:**
- Default: Border slate-300
- Focus: Blue ring
- Error: Red border + error text
- Disabled: Gray bg, 50% opacity

**Cards:**
- Result: Title + Badge + Abstract + Relevance + Buttons
- Chart: Chart canvas + Title + Description + Actions
- Stats: Big number + Label + Icon

## 📋 Step Screens

### Step 1: Form
```
[Theme Input]
[Keywords Input - with tags]
[Date Range - 2 inputs]
[Sources - 3 checkboxes]
[Button Group]
  [GERAR COM IA] [CONTINUAR]
```

### Step 2: Choice
```
[Option Card] Especificar
[Option Card] Usar Anterior  
[Option Card] Gerar Novo
[Spinner during action]
```

### Step 3: Results
```
"125 Resultados" [badge]
[Result Card × 10 - scrollable]
  ├─ Title
  ├─ Source badge + Year
  ├─ Abstract
  ├─ Relevance %
  └─ [INFO] [ACEITAR] [DESCARTAR]
[Gateway: Satisfeito?]
  [NÃO - REFINAR] [SIM - CONTINUAR]
```

### Step 4: Query Refinement
```
"Analyze Terms" [button]
OR
[Suggested Terms - list with checkboxes]
[Selected summary]
[CRIAR QUERY] [VOLTAR]
```

### Step 5: Final Search
```
[⟳ Executando busca final...]
[⟳ Gerando gráficos...]
OR
Stats:
  Total: 245 | Patentes: 120
  Artigos: 100 | Notícias: 25
  Timeline: 2020-2026
[REVISAR GRÁFICOS]
```

### Step 6: Charts
```
"4 Gráficos Gerados"
[Chart Grid 2x2 - scrollable]
  ├─ Line Chart
  ├─ Bar Chart
  ├─ Pie Chart
  └─ Scatter Plot
[Gateway: Satisfeito?]
  [NÃO - REGENERAR] [SIM - RELATÓRIO]
```

### Step 7: Report
```
Report Card:
  "Análise de Prospecção Tecnológica"
  Summary text...
  
Stats Grid (2×2):
  Total Resultados: 245
  Patentes: 120
  Artigos: 100
  Timeline: 2020-2026
  
File Options:
  Format: [PDF ▼] | Size: 2.4MB
  Generated: 2024-04-28
  
[NOVA BUSCA] [BAIXAR PDF]
```

## 🔄 States

**Loading:**
- Spinner + Message
- Skeleton loaders
- Buttons disabled

**Error:**
- Toast (red, bottom-right)
- Red border on input
- Error message below field

**Success:**
- Toast (green, 3s)
- Checkmark on item
- Stepper shows ✓

**Empty:**
- Icon + Message
- Suggestion text
- Action button

## 📊 Charts Needed

1. **Line Chart** - Year vs Count (3 lines: Patents, Articles, News)
2. **Bar Chart** - Source vs Count (blue, purple, orange bars)
3. **Pie Chart** - Distribution by source with legend
4. **Scatter** - Year vs Relevance (colored by source, sized by importance)

## 🎬 Interactive Flows

1. **Happy Path:** Step 1 → 2 → 3 → [Satisfeito] → 5 → 6 → [Satisfeito] → 7
2. **Refine Loop:** Step 4 → [Select Terms] → [Create Query] → [Not Satisfied] → Loop Step 4
3. **Error Flow:** [Action] → [API Error] → [Toast Error] → [Retry]
4. **Generator Loop:** [Generate] → [Show Generated] → [Reject] → [Generate again]

## ✅ Checklist Design System

- [ ] Colors defined and accessible (AA)
- [ ] Typography hierarchy (H1-H4, body, small)
- [ ] Button components (primary, secondary, tertiary, states)
- [ ] Input components (text, number, checkbox, states)
- [ ] Card components (result, chart, stats, info)
- [ ] Badge/Pill components (source, status, relevance)
- [ ] Icons (action icons, status icons)
- [ ] Spacing system (padding, gaps, margins)
- [ ] Border radius defined
- [ ] Shadow/elevation system
- [ ] Animation/transition specs

## 📦 Deliverables

1. **Design Screens** - All 7 steps + component states
2. **Design System** - Colors, typography, components
3. **Interactive Prototype** - Main flow + loops
4. **Assets** - Icons as SVG, any illustrations
5. **Specs Document** - Spacing, colors, typography, interactions

## 🎯 Design Goals

✓ User knows exactly which step they're in  
✓ Data flows clearly through the interface  
✓ Gateways (decisions) are obvious  
✓ Loading states give feedback  
✓ Errors are clear and actionable  
✓ Loop/refinement is intuitive  
✓ Mobile-ready for future (desktop-first now)  
✓ Professional and clean aesthetic  

---

**Use:** Share with Figma designer + main FIGMA_DESIGN_PROMPT.md for full context
