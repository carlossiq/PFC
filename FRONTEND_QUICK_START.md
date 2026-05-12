# AGIA Frontend - Quick Start

## 5-Minuto Setup

### 1. Verificar Node.js

```bash
node --version  # v18+
npm --version   # v9+
```

### 2. Instalar Dependências

```bash
cd frontend
npm install
```

**Tempo**: ~2 minutos

### 3. Iniciar o Servidor de Desenvolvimento

```bash
npm run dev
```

**Output esperado**:
```
  VITE v5.0.0  ready in 123 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

### 4. Abrir no Navegador

Acesse: **http://localhost:5173**

Você verá a interface AGIA com:
- Sidebar azul escuro à esquerda
- Workflow stepper no topo
- Área central de conteúdo
- Panel lateral (quando aplicável)

## Testando Cada Etapa

### Etapa 1: Configuração
1. Defina um tema (ex: "Machine Learning")
2. Adicione palavras-chave (ex: "AI", "Healthcare")
3. Selecione as fontes de dados
4. Clique em "Salvar Configurações"
5. Clique em "Próximo: Gerar Query"

### Etapa 2: Geração de Query
1. A query é gerada automaticamente
2. Clique em "Gerar Novamente" para refazer
3. Edite manualmente se necessário
4. Veja os resultados preliminares no painel direito
5. Aceite/Descarte resultados conforme necessário
6. Clique em "Confirmar e Prosseguir"

### Etapa 3: Curadoria
1. Revise os resultados
2. Finalize a seleção
3. Clique em "Próximo: Gerar Relatório LaTeX"

### Etapa 4: Relatório LaTeX
1. O editor LaTeX (Monaco) está pronto
2. Edite o documento conforme necessário
3. Clique em "Compilar" para gerar PDF
4. Veja o preview do PDF na direita
5. Clique em "Baixar PDF" para salvar

## Estrutura de Componentes

```
App (Estado Global)
├── Sidebar (Config)
├── WorkflowStepper (Nav)
└── Content (por etapa)
    ├── Config Step
    ├── Query Step
    │   ├── QueryGeneration
    │   └── ResultsPanel
    ├── Curation Step
    │   └── ResultsPanel
    └── Report Step
        ├── FileTree
        ├── LatexWorkspace
        │   └── Monaco Editor
        └── PDF Preview
```

## API Integration (Após)

Para conectar com o backend real:

1. **Edite** `frontend/src/services/api.ts`
2. **Descomente** as chamadas reais `await api.*(...)`
3. **Configure** a URL do backend em `frontend/.env`
4. **Teste** cada função isoladamente

Exemplo em `App.tsx`:
```typescript
// Antes (simulado):
// const newQuery = await api.generateQuery(config);

// Depois (real):
const newQuery = await api.generateQuery(config);
```

## Arquivos Importantes

| Arquivo | Propósito |
|---------|-----------|
| `src/App.tsx` | Lógica principal + estado |
| `src/services/api.ts` | Integração com backend |
| `src/components/*.tsx` | Componentes reutilizáveis |
| `src/types/index.ts` | Tipos TypeScript |
| `.env` | Variáveis de ambiente |
| `tailwind.config.js` | Configuração de estilos |

## Comandos Úteis

```bash
# Dev server com hot reload
npm run dev

# Build para produção
npm run build

# Preview do build
npm run preview

# Verificar tipos TypeScript
npm run type-check

# Lint com ESLint
npm run lint

# Fix de código automático
npm run lint:fix
```

## Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| "Port 5173 is in use" | `npm run dev -- --port 3000` |
| Estilos não aparecem | Limpe cache: `npm run dev -- --force` |
| TypeScript errors | Salve arquivo novamente (HMR) |
| API não conecta | Verifique `.env` e backend rodando |

## Dados Simulados

Atualmente o frontend usa **mock data** para demonstração. Resultados:

- 3 documentos de exemplo
- Query gerada como string CQL
- PDF preview estático

Para dados reais, implemente os endpoints do backend e descomente as chamadas em `App.tsx`.

## Próximos Passos

1. ✅ Frontend rodando
2. 📋 Configure backend endpoints
3. 🔌 Conecte API real
4. 🧪 Teste cada funcionalidade
5. 🚀 Deploy (Vercel, Docker, etc.)

## Atalhos de Teclado

| Atalho | Ação |
|--------|------|
| `Ctrl+S` | Salvar (se implementado) |
| `Ctrl+B` | Bold no editor LaTeX |
| `Ctrl+I` | Italic no editor LaTeX |
| `F1` | Monaco Editor Command Palette |

## Performance

- **Vite HMR**: <100ms
- **Build**: ~10s
- **Bundle size**: ~200KB (gzipped)

## Browser Support

- Chrome/Edge: ✅ (Latest)
- Firefox: ✅ (Latest)
- Safari: ✅ (14+)
- IE 11: ❌ (não suportado)

## Documentação Completa

Para informações mais detalhadas:
- Leia [FRONTEND_SETUP.md](./FRONTEND_SETUP.md)
- Consulte [frontend/README.md](./frontend/README.md)

---

**Tempo total**: ~5 minutos para estar rodando ⚡  
**Próximo passo**: Implementar endpoints do backend  
**Stack**: React 18 + Vite + TypeScript + TailwindCSS
