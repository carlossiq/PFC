# AGIA - Análise e Geração de Inteligência Acadêmica

Interface frontend em React + Vite + TypeScript para a plataforma de prospecção tecnológica AGIA.

## Características

- ✅ Layout profissional com sidebar lateral
- ✅ Workflow em 4 etapas com stepper interativo
- ✅ Geração automática de queries booleanas
- ✅ Curadoria de resultados
- ✅ Editor LaTeX estilo Overleaf (Monaco Editor)
- ✅ Preview PDF integrado
- ✅ Responsividade básica
- ✅ Tema em azul/branco moderno

## Stack

- **React 18** - UI library
- **Vite** - Build tool & dev server
- **TypeScript** - Type safety
- **TailwindCSS** - Styling
- **Monaco Editor** - LaTeX editor
- **Axios** - HTTP client

## Instalação

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Configuração

### Backend API

A interface se conecta ao backend FastAPI. Configure a URL base no arquivo `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Estrutura de Diretórios

```
src/
├── components/          # React components
│   ├── Sidebar.tsx          # Config sidebar
│   ├── WorkflowStepper.tsx  # Workflow navigation
│   ├── QueryGeneration.tsx  # Query builder
│   ├── ResultsPanel.tsx     # Results listing
│   ├── LatexWorkspace.tsx   # LaTeX editor
│   └── FileTree.tsx         # File browser
├── services/            # API services
│   └── api.ts               # Axios instance + API calls
├── types/               # TypeScript types
│   └── index.ts             # Shared interfaces
├── App.tsx              # Main app component
├── App.css              # App styles
├── index.css            # Global styles
└── main.tsx             # Entry point
```

## Componentes

### Sidebar
Painel de configuração esquerdo com:
- Seleção de tema e palavras-chave
- Fontes de dados (Patentes, Artigos, etc.)
- Faixa temporal
- Status da API

### WorkflowStepper
Navegação entre as 4 etapas:
1. Configuração
2. Geração de Query
3. Curadoria
4. Relatório LaTeX

### QueryGeneration
Editor de queries booleanas com:
- Geração automática
- Edição manual
- Preview da sintaxe
- Confirmar e prosseguir

### ResultsPanel
Painel lateral com:
- Lista de resultados preliminares
- Botões Aceitar/Descartar
- Metadados (fonte, ano, etc.)

### LatexWorkspace
Editor tipo Overleaf com:
- Monaco Editor para LaTeX
- Árvore de arquivos
- Compilação de PDF
- Download de documento
- Status de compilação

## API Integration

A integração com o backend está em `src/services/api.ts`. Atualmente, alguns endpoints estão comentados e usam dados simulados. Para ativar a integração real:

1. Descomente as chamadas `await api.*()` no arquivo `App.tsx`
2. Certifique-se de que o backend FastAPI está rodando
3. Configure a `VITE_API_BASE_URL` corretamente

### Endpoints Esperados

```
POST   /search/config                    - Salvar configuração
POST   /search/generate-query           - Gerar query
POST   /search/execute                  - Executar busca
POST   /search/results/{id}/accept      - Aceitar resultado
POST   /search/results/{id}/discard     - Descartar resultado
GET    /report/template                 - Obter template LaTeX
POST   /report/save                     - Salvar documento
POST   /report/compile                  - Compilar LaTeX
GET    /report/pdf/{id}                 - Download PDF
```

## Desenvolvimento

### Hot Module Replacement (HMR)

O Vite suporta HMR automaticamente. Alterações em arquivos são refletidas no navegador em tempo real.

### TypeScript

Todos os componentes e serviços usam TypeScript com type safety completo. Os tipos estão em `src/types/index.ts`.

### Styling com TailwindCSS

Utilize as classes utilitárias do TailwindCSS para estilização. Customizações estão em `tailwind.config.js`.

## Build

```bash
npm run build
```

Gera arquivos otimizados em `dist/`.

## Próximos Passos

- [ ] Integrar endpoints reais do backend
- [ ] Adicionar autenticação (JWT)
- [ ] Implementar histórico de pesquisas
- [ ] Adicionar mais fontes de dados
- [ ] Melhorar responsividade mobile
- [ ] Testes unitários e E2E
- [ ] CI/CD pipeline

## Licença

MIT

## Autor

Sistema AGIA - 2026
