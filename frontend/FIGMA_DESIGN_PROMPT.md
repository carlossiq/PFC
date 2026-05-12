# 🎨 Prompt para Figma - Design Layout BPMN Flow

## Contexto do Projeto

Estou desenvolvendo uma plataforma de **Prospecção Tecnológica Inteligente** que busca e analisa patentes, artigos e notícias usando IA. O sistema possui uma API bem estruturada com 20+ endpoints e um fluxo BPMN de 7 etapas com gateways de decisão.

---

## 🏗️ Fluxo de Dados & Arquitetura

### Dados Principais Fluindo Pelo Sistema

```
SearchParams {
  theme: string
  keywords: string[]
  yearStart: number
  yearEnd: number
  sources: { patents, articles, news: boolean }
}
         ↓
    [Armazenado]
         ↓
SearchResult[] {
  id, title, source, year, abstract, authors, url, relevanceScore
}
         ↓
    [Análise IA]
         ↓
RefinedQuery {
  original, refined, selectedTerms, removedTerms, timestamp
}
         ↓
FinalSearchResponse {
  totalResults, finalResults[], statistics {byYear, bySource, byAuthor}
}
         ↓
Chart[] {
  id, title, type (line/bar/pie/scatter), data, timestamp, description
}
         ↓
ReportData {
  id, title, searchParams, initialResults, finalResults, refinedQuery,
  charts, summary, statistics, generatedAt, generatedBy
}
         ↓
CreatedFile {
  fileUrl, fileName, fileSize, fileFormat (pdf/xlsx/docx)
}
```

### Estados em Cada Ponto

```
FlowState {
  currentStep: FlowStep (14 valores possíveis)
  previousSteps: FlowStep[] (histórico de navegação)
  searchParams: SearchParams | null
  generatedParams: GeneratedParams | null
  initialResults: SearchResult[] | null
  finalResults: SearchResult[] | null
  refinedQuery: RefinedQuery | null
  charts: Chart[] | null
  report: ReportData | null
  isLoading: boolean + loadingMessage: string
  error: string | null + errorDetails: unknown
  paramsHistory: StoredParamsHistoryItem[]
  queryHistory: QueryHistoryItem[]
  downloadUrl: string | undefined
  fileName: string | undefined
}
```

---

## 🎯 7 Etapas do BPMN (Com Gateways)

### Etapa 1️⃣: Parâmetros Iniciais
**Gateway:** "Deseja gerar parâmetros com IA?"
- **SIM** → POST `/flow/ai/generate-params` → Exibe gerados → Usuário aprova ou volta
- **NÃO** → Prossegue com atuais

**Dados Usados:**
- Input: `theme`, `keywords[]`, `yearStart`, `yearEnd`, `sources{}`
- Output: `SearchParams`
- Ação: Save em `paramsHistory`

---

### Etapa 2️⃣: Especificação de Parâmetros
**Gateway:** "Especificar parâmetros?"
- **SIM** → POST `/flow/ai/specify-params`
- **NÃO** → "Usar dados anteriores?"
  - **SIM** → GET `/flow/params/last-sample`
  - **NÃO** → POST `/flow/ai/generate-params` (novo)

**Dados Usados:**
- Input: `SearchParams` anterior
- Output: `SearchParams` refinados
- Ação: Nenhuma (passa para etapa 3)

---

### Etapa 3️⃣: Busca Inicial & Armazenamento
**Fluxo Linear (sem gateway):**
1. POST `/flow/params/store` → Salva histórico
2. POST `/flow/search/initial` → Busca com parâmetros
3. Retorna: `InitialSearchResponse { resultsCount, results[], executionTime }`

**Dados Usados:**
- Input: `SearchParams` confirmados
- Output: `SearchResult[]` iniciais
- Ação: Save em `paramsHistory`

---

### Etapa 4️⃣: Refinamento de Query
**Gateway:** "Satisfeito com resultados iniciais?"
- **SIM** → Ir para etapa 5 (Busca Final)
- **NÃO** → Refinar query:
  1. POST `/flow/ai/choose-terms` → Sugere termos
  2. Usuário seleciona termos
  3. POST `/flow/ai/create-query` → Cria nova CQL query
  4. POST `/flow/query/history` → Armazena
  5. Volta ao gateway (loop)

**Dados Usados:**
- Input: `SearchResult[]` iniciais
- Output: `QueryTerm[]` sugeridos
- Output: `RefinedQuery { original, refined, selectedTerms, removedTerms }`
- Ação: Save em `queryHistory`

---

### Etapa 5️⃣: Busca Final & Gráficos
**Fluxo Linear (sem gateway):**
1. POST `/flow/search/final` → Busca com query refinada
2. Retorna: `FinalSearchResponse { totalResults, finalResults[], statistics }`
3. POST `/flow/charts/generate` → Analisa dados
4. Retorna: `GeneratedChartsResponse { charts[], summary }`

**Dados Usados:**
- Input: `RefinedQuery`
- Output: `FinalSearchResponse`
- Output: `Chart[]` (line, bar, pie, scatter)
- Ação: Nenhuma (passa para etapa 6)

---

### Etapa 6️⃣: Validação de Gráficos
**Gateway:** "Satisfeito com gráficos?"
- **SIM** → Gerar relatório (etapa 7)
- **NÃO** → DELETE `/flow/charts/{id}` → Volta para regenerar

**Dados Usados:**
- Input: `Chart[]`
- Output: Nenhum novo (reutiliza dados anteriores)
- Ação: Pode descartar gráficos

---

### Etapa 7️⃣: Geração de Relatório & Download
**Fluxo Linear (sem gateway):**
1. POST `/flow/charts/add-to-report` → Adiciona gráficos
2. POST `/flow/data/synthesize` → Sintetiza dados em texto
3. POST `/flow/report/generate` → Gera relatório
4. POST `/flow/report/create-file` → Cria PDF/XLSX/DOCX
5. POST `/flow/data/store-final` → Salva no histórico
6. Exibe link de download

**Dados Usados:**
- Input: `Chart[]`, `FinalSearchResponse`, `SearchParams`
- Output: `GeneratedReportResponse { report, fileUrl, fileName }`
- Output: `CreatedFileResponse { fileUrl, fileName, fileSize, fileFormat }`
- Ação: Save em histórico de relatórios

---

## 🎨 Layout Estrutural Desejado

### Visão Geral (Desktop - Primeira Prioridade)

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER (Navigation + Help)                                      │
├──────────────────┬─────────────────────────────────────────────┤
│                  │                                              │
│  SIDEBAR         │  MAIN CONTENT AREA                          │
│  (280-320px)     │  ┌──────────────────────────────────────┐  │
│                  │  │ Step Title + Step Number             │  │
│  • Config        │  ├──────────────────────────────────────┤  │
│    - Theme       │  │ Progress/Stepper                     │  │
│    - Keywords    │  ├──────────────────────────────────────┤  │
│    - Sources     │  │                                      │  │
│    - Date Range  │  │  Main Content (varia por step)       │  │
│                  │  │                                      │  │
│  • Status        │  │  - Forms (step 1-2)                 │  │
│    - API         │  │  - Results list (step 3, 4)         │  │
│    - Current     │  │  - Charts (step 5-6)                │  │
│    - Processing  │  │  - Report (step 7)                  │  │
│                  │  │                                      │  │
│  • History       │  ├──────────────────────────────────────┤  │
│    - Searches    │  │ [Back] [Next/Action]                │  │
│    - Queries     │  └──────────────────────────────────────┘  │
│    - Reports     │                                              │
│                  │  SIDE PANEL (Context-specific)              │
│  [SAVE]          │  ┌──────────────────────────────────────┐  │
│  [RESET]         │  │ • Próximas Ações                     │  │
│                  │  │ • Status do Processamento            │  │
│                  │  │ • Dados Atuais                       │  │
│                  │  │ • Dicas & Avisos                     │  │
│                  │  └──────────────────────────────────────┘  │
└──────────────────┴─────────────────────────────────────────────┘
```

---

## 📐 Dimensões Recomendadas

```
Viewport: 1920x1080 (mínimo 1366x768)

Sidebar:
  Width: 280px (min 240px, max 320px)
  Padding: 24px
  
Main Content:
  Max width: 900px (responsive até 100%)
  Padding: 32px
  
Side Panel:
  Width: 300px (min 280px, max 320px)
  
Cards/Sections:
  Border radius: 12px
  Padding: 24px
  Gap entre cards: 16px
  
Typography:
  H1 (Page title): 32px, bold
  H2 (Section): 24px, bold
  H3 (Card): 18px, bold
  Body: 14px, regular
  Small: 12px, regular
  
Spacing (vertical):
  Section → Section: 32px
  Card → Card: 24px
  Element → Element: 16px
  Input → Label: 8px
```

---

## 🎨 Paleta de Cores

### Primary
```
Dark Blue:     #07345f (Sidebar, primary accent)
Sky Blue:      #0ea5e9 (Current step, links, hover)
Green:         #22c55e (Success, primary action)
Yellow:        #eab308 (Warning, secondary action)
Red:           #ef4444 (Error, danger)
```

### Neutral
```
White:         #ffffff (Cards, backgrounds)
Slate-50:      #f8fafc (Very light bg)
Slate-100:     #f1f5f9 (Light bg)
Slate-200:     #e2e8f0 (Light borders)
Slate-300:     #cbd5e1 (Borders)
Slate-600:     #475569 (Secondary text)
Slate-900:     #0f172a (Primary text)
```

### Status
```
Success:       #22c55e (✓ Complete, ready)
Processing:    #0ea5e9 (⟳ Loading, in progress)
Warning:       #eab308 (⚠ Needs attention)
Error:         #ef4444 (✗ Failed)
```

---

## 🔄 Estados dos Componentes

### Buttons
```
States:
  - Default (idle)
  - Hover (darken 10%, lift shadow)
  - Active/Pressed (darken 20%, drop shadow)
  - Disabled (opacity 50%, cursor not-allowed)
  - Loading (spinner inside, disabled)

Types:
  - Primary (Green, white text)
  - Secondary (Slate-200, dark text)
  - Tertiary (Yellow, dark text)
  - Danger (Red, white text)
  - Link (Blue, no bg)
```

### Forms
```
Input States:
  - Default (border: slate-300)
  - Focus (border: blue-500, ring: blue)
  - Error (border: red-500, help text red)
  - Disabled (bg: slate-100, opacity 50%)
  - Filled (bg: white, border: slate-300)

Validation:
  - Success checkmark (green)
  - Error message below (red, small text)
  - Helper text below (gray, small text)
```

### Results List
```
Each Result Card:
  - Title (bold, 14px)
  - Source badge (colored: Patent=blue, Article=purple, News=orange)
  - Year (small, gray)
  - Abstract (max 3 lines, truncate with ellipsis)
  - Relevance score (star rating or %)
  - Action buttons (Accept/Discard or Info)
  
Hover:
  - Lift card (small shadow)
  - Highlight border
  - Show more details/expand option
```

### Charts
```
Chart Container:
  - Title (bold)
  - Chart type label (line, bar, pie, scatter)
  - Chart area (canvas or SVG, min-height 300px)
  - Description (small, under chart)
  - Actions (Export, Delete, Info)

Interactive:
  - Hover shows data point details
  - Click toggles selection (highlight)
  - Can be removed individually
```

---

## 📋 Screens Específicas Necessárias

### Screen 1: Initial Parameters (Step 1)
```
Content:
  ├─ Title: "1. Parâmetros Iniciais"
  ├─ Description text
  ├─ Form:
  │  ├─ Theme input (text)
  │  ├─ Keywords input (with add/remove tags)
  │  ├─ Date range (2 inputs: start, end)
  │  ├─ Sources checkboxes (3x)
  │  └─ [Generate with AI] [Continue]
  │
  └─ OR Generated Params Show:
     ├─ Card showing generated params
     ├─ [Reject] [Accept]
     └─ Loading spinner (if generating)
```

### Screen 2: Specify Parameters (Step 2)
```
Content:
  ├─ Title: "2. Especificação de Parâmetros"
  ├─ Description text
  ├─ Choice buttons (3 options):
  │  ├─ [Specify] → Form to refine
  │  ├─ [Use Previous] → GET last sample
  │  └─ [Generate New] → AI generates
  └─ Loading state
```

### Screen 3: Search Results (Step 3)
```
Content:
  ├─ Title: "3. Resultados da Busca Inicial"
  ├─ Results count badge
  ├─ Results list:
  │  └─ [Result Card] × N (scrollable, max 10 shown)
  ├─ Satisfaction gateway:
  │  ├─ "Satisfeito com resultados?"
  │  └─ [No, Refine] [Yes, Continue]
  └─ Loading state
```

### Screen 4: Query Refinement (Step 4)
```
Content:
  ├─ Title: "4. Refinamento de Query"
  ├─ Step indicator (3 substeps):
  │  ├─ Choose terms (show suggested)
  │  ├─ Select terms (checkboxes)
  │  └─ Create query
  ├─ Terms list:
  │  └─ [Checkbox] Term (frequency, relevance %)
  ├─ Selected summary
  └─ [Back] [Create Query]
```

### Screen 5: Final Search (Step 5)
```
Content:
  ├─ Title: "5. Busca Final & Gráficos"
  ├─ Progress indicator (Searching → Generating charts)
  ├─ Stats:
  │  ├─ Total results
  │  ├─ By year
  │  ├─ By source
  │  └─ By author (if applicable)
  └─ [Proceed to Charts]
```

### Screen 6: Charts Validation (Step 6)
```
Content:
  ├─ Title: "6. Validação de Gráficos"
  ├─ Charts grid (1-2 columns):
  │  └─ [Chart Card] × N
  │     ├─ Chart (line, bar, pie, scatter)
  │     ├─ Title & description
  │     └─ [Info] [Export] [Remove]
  ├─ Satisfaction gateway:
  │  ├─ "Satisfeito com gráficos?"
  │  └─ [No, Regenerate] [Yes, Generate Report]
  └─ Loading state
```

### Screen 7: Report & Download (Step 7)
```
Content:
  ├─ Title: "7. Relatório"
  ├─ Report summary:
  │  ├─ Title
  │  ├─ Summary text
  │  └─ Statistics grid (4 cards):
  │     ├─ Total results
  │     ├─ Patentes count
  │     ├─ Artigos count
  │     └─ Timeline (start-end)
  ├─ File info:
  │  ├─ Format: PDF (selector for XLSX, DOCX)
  │  ├─ File size
  │  └─ Generated at
  └─ [Download] [New Search]
```

---

## 🎭 Componentes Reutilizáveis

```
ATOMS:
  • Button (variants: primary, secondary, tertiary, danger)
  • Input (text, number, date, with validation states)
  • Checkbox
  • Radio
  • Badge/Pill (for tags, status, counts)
  • Icon (SVG icons for actions)
  • Spinner (loading indicator)
  • Alert (success, warning, error, info)

MOLECULES:
  • Input with label
  • Input with label + validation message
  • Search bar
  • Filter panel
  • Date range picker
  • Tag list with add/remove
  • Result card
  • Chart card
  • Status indicator
  • Progress bar
  • Breadcrumbs

ORGANISMS:
  • Form (parameters input)
  • Results list
  • Charts grid
  • Report summary
  • Navigation stepper
  • Sidebar
  • Side panel
  • Modal/Dialog (for confirmations)
  • Toast (for notifications)
```

---

## 🔄 Animations & Transitions

```
Timing:
  - Quick: 150ms (hover, button press)
  - Medium: 300ms (page transitions, card expand)
  - Slow: 500ms (large movements, modals)

Types:
  - Fade in/out (opacity)
  - Slide up/down (transform translateY)
  - Grow/shrink (scale)
  - Color change (background, border)

States:
  - Loading: Spinner (infinite rotation)
  - Transition between steps: Fade + Slide
  - Item removed: Fade out + collapse
  - Data update: Highlight then fade
```

---

## 📱 Responsive Breakpoints (Futuro)

```
Mobile (< 768px):
  - Single column
  - Sidebar as drawer/collapsible nav
  - Stepper vertical
  - Cards full width
  
Tablet (768px - 1024px):
  - Sidebar narrower
  - Content 2 columns where needed
  
Desktop (> 1024px):
  - Full layout as designed
```

---

## ✨ Special UX Considerations

### Loading States
```
1. When fetching from API:
   - Show spinner overlay or skeleton loader
   - Disable buttons
   - Show message: "Gerando parâmetros..."

2. Skeleton loaders for:
   - Results list (5 placeholder cards)
   - Charts (placeholder rectangles)
   - Report (gray blocks)
```

### Error Handling
```
1. API errors:
   - Toast message (bottom-right, red)
   - Retry button in toast
   - Card shows error state
   
2. Form validation:
   - Red border on invalid field
   - Red text below with error message
   - Disable submit until valid
```

### Empty States
```
1. No results found:
   - Icon (magnifying glass)
   - Message: "Nenhum resultado encontrado"
   - Suggestion: "Tente refinar seus parâmetros"
   - Button: [Adjust Parameters]

2. No history:
   - Icon (history/clock)
   - Message: "Nenhum histórico"
   - Suggestion: "Inicie uma nova busca"
```

### Success States
```
1. After successful action:
   - Toast message (bottom-right, green)
   - Checkmark icon
   - Auto-dismiss after 3s
   
2. Step completed:
   - Stepper shows checkmark
   - Card has green border/background
```

---

## 📊 Data Visualization

### Chart Types Needed
```
1. Line Chart:
   - X: Year
   - Y: Count (results, patentes, articles)
   - Multiple lines (by source or category)

2. Bar Chart:
   - X: Source (Patents, Articles, News)
   - Y: Count
   - Colored by source

3. Pie Chart:
   - Distribution (sources, types)
   - Show percentages
   - Legend

4. Scatter:
   - X: Year
   - Y: Relevance Score
   - Color: Source
   - Size: Importance
```

### Statistics Display
```
Metric Cards (4 grid):
  ├─ Large number (48px font, bold)
  ├─ Label (14px, gray)
  ├─ Trend indicator (↑↓ with color)
  └─ Icon (top-right corner)
```

---

## 🔑 Key Design Principles

```
1. **Data Visualization First**
   - Show data immediately
   - Use colors to group/categorize
   - Numbers prominent and easy to scan

2. **Clear Navigation**
   - User always knows which step they're in
   - Progress visible (stepper)
   - Back button always available
   - Clear next action button

3. **Minimal Cognitive Load**
   - One task per screen
   - Progressive disclosure (show details on demand)
   - Consistent patterns across screens

4. **Accessible Colors**
   - Sufficient contrast (AA standard)
   - Don't rely on color alone for meaning
   - Icons + text for actions

5. **Responsive & Scalable**
   - Works desktop-first, mobile-ready for future
   - Scales content appropriately
   - Touch-friendly on mobile (future)

6. **Feedback & Confirmation**
   - Every action has feedback
   - Destructive actions need confirmation
   - Loading states shown
   - Errors clearly displayed

7. **Performance Hints**
   - Show progress during long operations
   - Skeleton loaders instead of blank
   - Smooth transitions between states
```

---

## 📝 Specifications for Figma

### File Structure
```
Figma Project: AGIA - Prospecting Platform
├── 📋 Design System
│   ├── Colors
│   ├── Typography
│   ├── Components (atoms, molecules)
│   └── Icons
│
├── 📱 Screens
│   ├── Step 1: Initial Parameters
│   ├── Step 2: Specify Parameters
│   ├── Step 3: Search Results
│   ├── Step 4: Query Refinement
│   ├── Step 5: Final Search
│   ├── Step 6: Charts Validation
│   ├── Step 7: Report & Download
│   └── 📋 Component States
│       ├── Loading
│       ├── Error
│       ├── Empty
│       └── Success
│
├── 🎨 Layouts
│   ├── Desktop (1920x1080)
│   ├── Sidebar variations
│   └─ Modal templates
│
└── 📖 Prototypes
    ├── Main flow (step 1 → 7)
    ├── Loop flow (refinement loop)
    └── Error handling flows
```

### Component Naming
```
Button/Primary/Default
Button/Primary/Hover
Button/Primary/Active
Button/Primary/Disabled

Input/Default
Input/Focus
Input/Error
Input/Disabled

Card/Default
Card/Hover
Card/Selected

Badge/Success
Badge/Warning
Badge/Error
```

---

## 🎬 Interactive Prototypes Needed

```
1. Main Flow:
   Step 1 → [Generate or Continue] → Step 2 → Step 3 → Step 4 
   → [Refine or Continue] → Step 5 → Step 6 
   → [Regenerate or Accept] → Step 7 → [Download]

2. Refinement Loop (Step 4):
   [Choose Terms] → [Select] → [Generate Query] 
   → [Accept or Reject] → Loop back or continue

3. Error Flow:
   [Action] → [API Error] → [Show Error Toast] 
   → [Retry] → Success or another error

4. Loading States:
   [Click Action] → [Show Spinner] → [Process] → [Show Results]
```

---

## 🚀 Export & Handoff

When design is complete:
1. **Components** - Export as Figma libraries for devs
2. **Specs** - Generate design specs (spacing, typography, colors)
3. **Assets** - Icons as SVG, logos, illustrations
4. **Prototypes** - Interactive prototypes for user testing
5. **Documentation** - Design system documentation

---

**Objetivo Final:** Um design clean, profissional e intuitivo que reflita a complexidade da análise de dados mantendo a simplicidade na interface.
