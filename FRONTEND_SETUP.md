# AGIA Frontend - Guia de Configuração

## Visão Geral

O frontend AGIA foi criado em React + Vite + TypeScript com uma interface moderna para a plataforma de prospecção tecnológica.

## Estrutura Criada

```
frontend/
├── src/
│   ├── components/
│   │   ├── Sidebar.tsx              # Painel de configuração
│   │   ├── WorkflowStepper.tsx      # Navegação entre etapas
│   │   ├── QueryGeneration.tsx      # Gerador de queries
│   │   ├── ResultsPanel.tsx         # Lista de resultados
│   │   ├── LatexWorkspace.tsx       # Editor LaTeX tipo Overleaf
│   │   └── FileTree.tsx             # Árvore de arquivos
│   ├── services/
│   │   └── api.ts                   # Cliente Axios + funções API
│   ├── types/
│   │   └── index.ts                 # Tipos TypeScript
│   ├── App.tsx                      # Componente principal
│   ├── App.css                      # Estilos da app
│   ├── index.css                    # Estilos globais + TailwindCSS
│   └── main.tsx                     # Ponto de entrada
├── .env                             # Variáveis de ambiente
├── .env.example                     # Template de variáveis
├── tailwind.config.js               # Configuração TailwindCSS
├── postcss.config.js                # Configuração PostCSS
├── vite.config.ts                   # Configuração Vite
├── tsconfig.json                    # Configuração TypeScript
├── package.json                     # Dependências
├── README.md                        # Documentação
└── index.html                       # Arquivo HTML principal
```

## Quick Start

### 1. Instalar Dependências

```bash
cd frontend
npm install
```

### 2. Configurar Backend URL

Edite ou crie o arquivo `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 3. Iniciar Dev Server

```bash
npm run dev
```

O frontend estará disponível em `http://localhost:5173`

## Componentes Principais

### 1. Sidebar (Configuração)
- **Arquivo**: `src/components/Sidebar.tsx`
- **Responsabilidade**: Painel lateral com controles de configuração
- **Funcionalidades**:
  - Definir tema de pesquisa
  - Adicionar palavras-chave
  - Selecionar fontes de dados
  - Definir período temporal
  - Toggle de API
  - Status visual

### 2. WorkflowStepper (Navegação)
- **Arquivo**: `src/components/WorkflowStepper.tsx`
- **Responsabilidade**: Indicador de progresso entre etapas
- **Etapas**:
  1. Configuração
  2. Geração de Query
  3. Curadoria
  4. Relatório LaTeX

### 3. QueryGeneration (Gerador de Queries)
- **Arquivo**: `src/components/QueryGeneration.tsx`
- **Responsabilidade**: Interface para criar/editar queries booleanas
- **Funcionalidades**:
  - Gerar query automaticamente
  - Editar manualmente
  - Preview de sintaxe CQL
  - Confirmar e prosseguir

### 4. ResultsPanel (Resultados)
- **Arquivo**: `src/components/ResultsPanel.tsx`
- **Responsabilidade**: Exibir resultados da busca
- **Funcionalidades**:
  - Listar resultados preliminares
  - Aceitar/descartar documentos
  - Mostrar metadados (fonte, ano, etc.)

### 5. LatexWorkspace (Editor LaTeX)
- **Arquivo**: `src/components/LatexWorkspace.tsx`
- **Responsabilidade**: Editor tipo Overleaf com preview PDF
- **Funcionalidades**:
  - Editar LaTeX com Monaco Editor
  - Árvore de arquivos
  - Compilar para PDF
  - Preview em tempo real
  - Salvar documento
  - Download PDF

### 6. FileTree (Navegador de Arquivos)
- **Arquivo**: `src/components/FileTree.tsx`
- **Responsabilidade**: Estrutura de arquivos do projeto
- **Funcionalidades**:
  - Exibir árvore de pastas e arquivos
  - Expandir/colapsar pastas
  - Selecionar arquivo

## Integração com Backend

### Arquivo de Configuração

`src/services/api.ts` contém todas as funções de integração com a API:

```typescript
export const saveConfig = async (config: SearchConfig)
export const generateQuery = async (config: SearchConfig)
export const refineQuery = async (query: string, feedback: string)
export const executeSearch = async (query: string)
export const acceptResult = async (resultId: string)
export const discardResult = async (resultId: string)
export const getLatexTemplate = async ()
export const saveLatex = async (document: LaTexDocument)
export const compileLatex = async (content: string)
export const downloadPdf = async (documentId: string)
```

### Implementação Atual

Atualmente, o frontend usa **dados simulados** para funcionamento demonstrativo. Para conectar com o backend real:

1. **Descomente** as chamadas `await api.*()` em `App.tsx`
2. **Certifique-se** de que o backend FastAPI está rodando em `localhost:8000`
3. **Implemente** os endpoints correspondentes no backend

### Endpoints Esperados do Backend

```
# Configuração
POST /api/v1/search/config
  Input: { theme, keywords, sources, yearStart, yearEnd, apiEnabled }
  Output: { success, message }

# Geração de Query
POST /api/v1/search/generate-query
  Input: SearchConfig
  Output: { query, refined }

# Refinar Query
POST /api/v1/search/refine-query
  Input: { query, feedback }
  Output: { query, refined }

# Executar Busca
POST /api/v1/search/execute
  Input: { query }
  Output: { results: SearchResult[] }

# Resultado Individual
POST /api/v1/search/results/{id}/accept
POST /api/v1/search/results/{id}/discard
  Output: { success }

# LaTeX
GET /api/v1/report/template
  Output: { id, name, content }

POST /api/v1/report/save
  Input: { id, name, content, lastSaved }
  Output: { success, message }

POST /api/v1/report/compile
  Input: { content }
  Output: { success, message, pdfUrl, errors }

GET /api/v1/report/pdf/{id}
  Output: PDF binary
```

## Estilos e Temas

### TailwindCSS

O projeto usa TailwindCSS com configuração em `tailwind.config.js`:

- **Cores principais**: Azul (primary) em diferentes tons
- **Classes utilitárias**: Responsive design
- **Customizações**: Tema azul escuro para sidebar

### Dark Mode (Futuro)

Para adicionar suporte a dark mode, utilize:

```tsx
className="dark:bg-slate-800 dark:text-white"
```

## Desenvolvimento

### Hot Module Replacement (HMR)

Vite suporta HMR automaticamente. Alterações em arquivos são refletidas em tempo real no navegador.

### Debug

O Firefox DevTools ou Chrome DevTools pode ser usado para debug. O React DevTools extension é recomendado:
- [React DevTools (Chrome)](https://chrome.google.com/webstore/detail/react-developer-tools/)
- [React DevTools (Firefox)](https://addons.mozilla.org/firefox/addon/react-devtools/)

### Tipos TypeScript

Todos os tipos estão em `src/types/index.ts`. Adicione novos tipos conforme necessário:

```typescript
export interface MyNewType {
  id: string;
  name: string;
  // ...
}
```

## Build para Produção

```bash
npm run build
```

Gera arquivos otimizados em `dist/`. Para testar localmente:

```bash
npm run preview
```

## Variáveis de Ambiente

Crie um arquivo `.env.local` para usar variáveis diferentes do `.env`:

```env
VITE_API_BASE_URL=http://seu-backend.com/api/v1
```

## Troubleshooting

### Erro "Cannot find module @monaco-editor/react"

```bash
npm install @monaco-editor/react
```

### Vite port já está em uso

```bash
npm run dev -- --port 3000
```

### TailwindCSS não está sendo aplicado

Verifique se `src/index.css` contém:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

## Próximas Funcionalidades

- [ ] Autenticação com JWT
- [ ] Histórico de pesquisas
- [ ] Compartilhamento de relatórios
- [ ] Mais temas de cores
- [ ] Modo dark
- [ ] Exportar em vários formatos (PDF, DOCX, etc.)
- [ ] Testes unitários
- [ ] E2E tests com Cypress/Playwright

## Deployment

### Vercel (Recomendado)

1. Push para GitHub
2. Conectar repositório no Vercel
3. Configurar variável `VITE_API_BASE_URL`
4. Deploy automático

### Docker

Crie um `Dockerfile`:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

## Support

Para dúvidas ou issues, consulte:
- [React Docs](https://react.dev)
- [Vite Docs](https://vitejs.dev)
- [TailwindCSS Docs](https://tailwindcss.com)
- [Monaco Editor Docs](https://microsoft.github.io/monaco-editor/)

---

**Criado em**: 2026-04-28  
**Versão**: 1.0.0  
**Stack**: React 18 + Vite + TypeScript + TailwindCSS
