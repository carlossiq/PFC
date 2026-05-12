# Implementação do Fluxo BPMN - Integração API Frontend

## Visão Geral

Este documento descreve como o fluxo BPMN de 7 etapas foi implementado no frontend React com integração completa à API backend.

## Arquitetura

### Stack Utilizado

- **State Management**: Zustand com persistência em `sessionStorage`
- **HTTP Client**: Axios com interceptors
- **Type Safety**: TypeScript com tipos específicos por etapa
- **UI Framework**: React + TailwindCSS

### Estrutura de Arquivos Criados

```
src/
├── types/
│   └── flow.ts                      # Tipos e interfaces do fluxo (20+ interfaces)
├── services/
│   └── flowApi.ts                   # Serviço de API com 20+ endpoints
├── store/
│   └── flowStore.ts                 # Store Zustand com estado global
└── components/
    ├── Flow/
    │   ├── FlowContainer.tsx        # Orquestrador principal
    │   ├── FlowStepper.tsx          # Indicador de progresso
    │   ├── ErrorBoundary.tsx        # Tratamento de erros
    │   ├── LoadingOverlay.tsx       # Indicador de loading
    │   ├── steps/
    │   │   ├── InitialParamsStep.tsx
    │   │   ├── SpecifyParamsStep.tsx
    │   │   ├── SearchResultsStep.tsx
    │   │   ├── QueryRefinementStep.tsx
    │   │   ├── FinalSearchStep.tsx
    │   │   ├── ChartsStep.tsx
    │   │   └── ReportStep.tsx
    │   └── dialogs/
    │       ├── ParamsConfirmDialog.tsx
    │       ├── QueryValidationDialog.tsx
    │       └── ChartsValidationDialog.tsx
```

## Fluxo Implementado

### 1️⃣ Etapa 1: Parâmetros Iniciais

**Arquivo**: `InitialParamsStep.tsx`

```
Usuário preenche: tema, keywords, fontes, período
     ↓
Gateway: "Editar parâmetros?"
  ├─ SIM: POST /flow/ai/generate-params
  │       → Exibir gerados ao usuário
  │       → Usuário aprova ou volta
  └─ NÃO: Continuar com parametros atuais
```

**Função de API**:
```typescript
generateParams(request: GenerateParamsRequest): Promise<SearchParams>
```

**State Updates**:
```typescript
- setSearchParams()
- setGeneratedParams()
- setCurrentStep('satisfaction-params')
```

### 2️⃣ Etapa 2: Especificação de Parâmetros

**Arquivo**: `SpecifyParamsStep.tsx`

```
Gateway: "Especificar parâmetros?"
  ├─ SIM: POST /flow/ai/specify-params
  │       → Retorna parâmetros especificados
  │       → Usuário revisa
  ├─ NÃO → Gateway: "Utilizar dados anteriores?"
  │        ├─ SIM: GET /flow/params/last-sample
  │        │       → Preenchimento automático
  │        └─ NÃO: POST /flow/ai/generate-params (novo)
  └─ Prosseguir
```

**Funções de API**:
```typescript
specifyParams(request: SpecifyParamsRequest): Promise<SearchParams>
getLastParamsSample(): Promise<SearchParams>
generateParams(request: GenerateParamsRequest): Promise<SearchParams>
```

### 3️⃣ Etapa 3: Armazenamento e Busca Inicial

**Arquivo**: `SearchResultsStep.tsx`

```
Parâmetros confirmados
  ↓
POST /flow/params/store
  → Salva em "Histórico de Parâmetros de busca"
  ↓
POST /flow/search/initial
  → Busca inicial com parâmetros
  ↓
GET /flow/results/return (ou no response da busca)
  → Retorna resultados iniciais
  ↓
Exibir resultados ao usuário
```

**Funções de API**:
```typescript
storeParams(params: SearchParams): Promise<StoredParamsHistoryItem>
executeInitialSearch(request: InitialSearchRequest): Promise<InitialSearchResponse>
```

**State Updates**:
```typescript
- addToParamsHistory()
- setInitialResults()
- setCurrentStep('satisfaction-results')
```

### 4️⃣ Etapa 4: Refinamento de Query

**Arquivo**: `QueryRefinementStep.tsx`

```
Gateway: "Usuário satisfeito com resultados?"
  ├─ SIM: Ir para busca final
  └─ NÃO:
     ├─ POST /flow/ai/choose-terms
     │  → Retorna termos sugeridos
     │  → Usuário seleciona
     ├─ POST /flow/ai/create-query
     │  → Cria nova query CQL
     ├─ POST /flow/query/history
     │  → Salva em "Histórico de query por escolha de termos"
     ├─ Validação (frontend)
     └─ Volta ao gateway anterior
```

**Funções de API**:
```typescript
chooseTerms(request: ChooseTermsRequest): Promise<QueryTerm[]>
createQuery(request: CreateQueryRequest): Promise<RefinedQuery>
storeQueryHistory(query: RefinedQuery, resultsCount: number): Promise<QueryHistoryItem>
```

**State Updates**:
```typescript
- setRefinedQuery()
- addToQueryHistory()
- setCurrentStep('final-search') ou ('satisfaction-results')
```

### 5️⃣ Etapa 5: Busca Final

**Arquivo**: `FinalSearchStep.tsx`

```
POST /flow/search/final
  → Executa busca com query refinada
  ↓
Retorna resultados finais + estatísticas
  ↓
POST /flow/charts/generate
  → Gera gráficos dos resultados
  ↓
Exibir gráficos ao usuário
```

**Funções de API**:
```typescript
executeFinalSearch(request: FinalSearchRequest): Promise<FinalSearchResponse>
generateCharts(request: GenerateChartsRequest): Promise<GeneratedChartsResponse>
```

**State Updates**:
```typescript
- setFinalResults()
- setCharts()
- setCurrentStep('satisfaction-charts')
```

### 6️⃣ Etapa 6: Validação de Gráficos

**Arquivo**: `ChartsStep.tsx`

```
Gateway: "Usuário satisfeito com gráficos?"
  ├─ SIM:
  │  ├─ POST /flow/charts/add-to-report
  │  ├─ POST /flow/data/synthesize
  │  │  → Sintetiza dados em texto
  │  ├─ POST /flow/report/generate
  │  │  → Gera relatório completo
  │  ├─ POST /flow/report/create-file
  │  │  → Cria PDF/XLSX/DOCX
  │  ├─ POST /flow/data/store-final
  │  │  → Salva em "Histórico de relatórios"
  │  └─ Ir para download
  └─ NÃO:
     ├─ DELETE /flow/charts/{id}
     └─ Volta a gerar gráficos
```

**Funções de API**:
```typescript
addChartToReport(chart: Chart): Promise<{ success: boolean }>
discardChart(chartId: string): Promise<{ success: boolean }>
synthesizeData(request: SynthesizeDataRequest): Promise<{ synthesis: string }>
generateReport(request: GenerateReportRequest): Promise<GeneratedReportResponse>
createFile(request: CreateFileRequest): Promise<CreatedFileResponse>
storeFinalData(request: StoreFinalDataRequest): Promise<{ success: boolean }>
```

**State Updates**:
```typescript
- addChart() ou removeChart()
- setReport()
- setDownloadUrl()
- setCurrentStep('download-file') ou ('generate-charts')
```

### 7️⃣ Etapa Final: Download

**Arquivo**: `ReportStep.tsx`

```
Arquivo pronto
  ↓
Exibir link de download
  ↓
Usuário baixa arquivo
  ↓
Fluxo completo!
```

## Gerenciamento de Estado

### Zustand Store (`flowStore.ts`)

```typescript
interface FlowStore extends FlowState {
  // Navegação
  setCurrentStep(step: FlowStep)
  goToPreviousStep()
  resetFlow()

  // Dados
  setSearchParams()
  setGeneratedParams()
  setInitialResults()
  setFinalResults()
  setRefinedQuery()
  setCharts()
  setReport()

  // Estados
  setLoading()
  setError()
  clearError()

  // Históricos
  addToParamsHistory()
  addToQueryHistory()
}
```

### Persistência

- Salva automaticamente no `sessionStorage`
- Recupera estado ao recarregar página
- Função `resetFlow()` para limpar tudo

## Tratamento de Erros

### Estratégia

1. **Try-catch em cada chamada de API**
2. **Interceptors do Axios** para logging automático
3. **Toast/Modal** para feedback visual
4. **Fallbacks** quando possível

### Exemplo

```typescript
try {
  const response = await generateParams(request);
  store.setSearchParams(response);
} catch (error) {
  store.setError(
    'Falha ao gerar parâmetros',
    error
  );
  showErrorToast('Tente novamente');
}
```

## Loading States

Cada etapa async:

```typescript
store.setLoading(true, 'Gerando parâmetros...');
try {
  // API call
  store.setLoading(false);
} catch (error) {
  store.setLoading(false);
  // Handle error
}
```

## Data Stores (Backend)

| Data Store | Via API | Quando |
|---|---|---|
| Histórico de Parâmetros | POST /params/store | Após confirmar parâmetros |
| Histórico de Query | POST /query/history | Após criar nova query |
| Histórico de Relatórios | POST /data/store-final | Ao completar fluxo |

## Endpoints Implementados

### AI/Geração
- `POST /flow/ai/generate-params` - Gera parâmetros
- `POST /flow/ai/specify-params` - Especifica parâmetros
- `POST /flow/ai/choose-terms` - Escolhe termos
- `POST /flow/ai/create-query` - Cria query

### Busca
- `POST /flow/search/initial` - Busca inicial
- `POST /flow/search/final` - Busca final

### Parâmetros/Query
- `POST /flow/params/store` - Armazena parâmetros
- `GET /flow/params/last-sample` - Recupera última amostra
- `GET /flow/params/history` - Histórico de parâmetros
- `POST /flow/query/history` - Armazena query
- `GET /flow/query/history` - Histórico de queries

### Gráficos
- `POST /flow/charts/generate` - Gera gráficos
- `POST /flow/charts/add-to-report` - Adiciona ao relatório
- `DELETE /flow/charts/{id}` - Descarta gráfico

### Relatório/Dados
- `POST /flow/data/synthesize` - Sintetiza dados
- `POST /flow/report/generate` - Gera relatório
- `POST /flow/report/create-file` - Cria arquivo
- `POST /flow/data/store-final` - Armazena final
- `GET /flow/reports/history` - Histórico de relatórios

## Uso no React

### Em um Componente

```typescript
import { useFlowStore } from '@/store/flowStore';

export const MyComponent = () => {
  const { currentStep, setCurrentStep, isLoading } = useFlowStore();

  return (
    <div>
      {isLoading && <LoadingOverlay />}
      {currentStep === 'initial-params' && <InitialParamsStep />}
      {currentStep === 'specify-params' && <SpecifyParamsStep />}
      {/* ... */}
    </div>
  );
};
```

### Chamada de API

```typescript
import { generateParams } from '@/services/flowApi';

const handleGenerateParams = async () => {
  const { setLoading, setError, setGeneratedParams } = useFlowStore.getState();
  
  setLoading(true, 'Gerando parâmetros...');
  
  try {
    const params = await generateParams({
      theme: 'Machine Learning',
      keywords: ['AI', 'Healthcare'],
      yearRange: { start: 2020, end: 2024 }
    });
    
    setGeneratedParams(params);
    setLoading(false);
  } catch (error) {
    setError('Falha ao gerar parâmetros', error);
    setLoading(false);
  }
};
```

## Componentes a Criar

### Flow/FlowContainer.tsx
Orquestrador principal que:
- Lê estado de `useFlowStore`
- Renderiza componente de etapa atual
- Gerencia gateways (lógica condicional)
- Trata erros globais

### Flow/steps/*.tsx (7 arquivos)
Cada etapa com:
- Inputs/seleções de usuário
- Chamadas de API
- Feedback visual
- Botões de ação

### Flow/dialogs/*.tsx
Diálogos de confirmação para gateways

## Testing

Exemplo com Mock:

```typescript
// mock/flowApi.mock.ts
export const mockGenerateParams = async () => ({
  theme: 'Machine Learning',
  keywords: ['AI', 'Healthcare'],
  yearStart: 2020,
  yearEnd: 2024,
  sources: { patents: true, articles: true, news: false }
});
```

## Próximos Passos

1. ✅ Definir tipos (`flow.ts`)
2. ✅ Criar serviço de API (`flowApi.ts`)
3. ✅ Criar store global (`flowStore.ts`)
4. ⏳ Criar componentes das 7 etapas
5. ⏳ Criar FlowContainer orquestrador
6. ⏳ Implementar tratamento de erros globais
7. ⏳ Adicionar LoadingOverlay
8. ⏳ Testar fluxo ponta-a-ponta
9. ⏳ Integrar com backend real

## Documentação Referenciada

- BPMN Flow: Conforme prompt original
- Tipo Safety: `/src/types/flow.ts`
- API Service: `/src/services/flowApi.ts`
- State Management: `/src/store/flowStore.ts`
