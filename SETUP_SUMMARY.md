# Setup Summary - Docker + Ollama + Open WebUI

## ✅ O que foi criado

### 1. **Docker & Containers**
```
✓ docker-compose.yml      (orquestração de 3 containers)
✓ Dockerfile              (imagem customizada da API)
```

**Containers inclusos:**
- **ollama** (porta 11434) - LLM Qwen2.5:7b/3b, CPU-only
- **pfc-api** (porta 8000) - FastAPI, seus endpoints
- **open-webui** (porta 3000) - Interface de chat com tools

### 2. **Tools para Open WebUI**
```
tools/
├─ README.md                    (guia de como criar tools)
├─ refine_topic.py              (refinar temas em 4 variações)
├─ probe_search.py              (busca exploratória 10-25 docs)
├─ final_search.py              (busca final até 500 docs)
└─ analyze_complexity.py         (analisar complexidade de queries)
```

### 3. **Prompts para o Modelo**
```
prompts/
└─ system_prompt.md            (instruções para o Qwen2.5)
```

**Contém:**
- Fluxo de busca guiado (refine → probe → final)
- Instruções de formatação (markdown, emojis, listas)
- Quando chamar cada tool
- Tratamento de erros

### 4. **Scripts de Configuração**
```
✓ setup.sh                 (Linux/macOS - all-in-one)
✓ setup.bat                (Windows - PowerShell compatible)
```

**O que faz:**
- Verifica Docker/Docker Compose
- Verifica RAM disponível (escolhe modelo 7b ou 3b)
- Sobe containers
- Aguarda Ollama/API/WebUI ficarem prontos
- Faz pull do modelo Qwen2.5
- Imprime URLs de acesso

### 5. **Documentação**
```
✓ README.md                (atualizado com seção Docker)
✓ DOCKER_GUIDE.md          (guia completo de uso/troubleshooting)
✓ tools/README.md          (como criar novas tools)
✓ SETUP_SUMMARY.md         (este arquivo)
```

---

## 🚀 Como Usar (Próximos Passos)

### Opção 1: Linux/macOS
```bash
cd /path/to/PFC
bash setup.sh
```

### Opção 2: Windows (PowerShell ou CMD)
```cmd
cd C:\path\to\PFC
setup.bat
```

### Opção 3: Manual
```bash
docker-compose up -d
# Aguarde e acesse http://localhost:3000
```

### Após inicializar:
1. **Abra** http://localhost:3000 no navegador
2. **Selecione** modelo `qwen2.5:7b` (ou `3b` se RAM baixa)
3. **Copie** o System Prompt de `prompts/system_prompt.md`
4. **Cole** nas settings do Open WebUI (System Prompt)
5. **Inicie conversa** com o assistente!

---

## 📊 Stack Architecture

```
┌─────────────────────────────────────────────────────┐
│           Open WebUI (Port 3000)                    │
│  - Chat interface com histórico                     │
│  - Function calling (tools)                         │
│  - Gerenciamento de modelos                         │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP (rede Docker)
        ┌──────────┼──────────┐
        │          │          │
┌───────▼────┐ ┌──▼────────┐ ├─────────────┐
│  Ollama    │ │API        │ │Docker Comp  │
│Port 11434  │ │Port 8000  │ │ose Network  │
│LLM Local   │ │FastAPI    │ │(pfc-net)    │
│Qwen2.5:7b  │ │Your Tools │ │             │
│CPU-only    │ │Endpoints  │ │             │
└────────────┘ └───────────┘ └─────────────┘

Volumes:
  ollama_data/   - Modelos (~3-4GB)
  webui_data/    - Configs + histórico
  ./tools/       - Tools Python (bind mount)
  ./prompts/     - System prompts (read-only)
```

---

## 📋 Checklist Pós-Setup

- [ ] Docker está rodando: `docker ps | grep pfc`
- [ ] Ollama responde: `curl http://localhost:11434/api/tags`
- [ ] API responde: `curl http://localhost:8000/api/v1/health`
- [ ] Open WebUI acessível: `curl http://localhost:3000`
- [ ] Modelo carregado: `docker exec pfc-ollama ollama list`
- [ ] Tools disponíveis em `/app/backend/data/tools`
- [ ] System prompt copiado para Open WebUI

---

## 🔧 Arquivos Importantes

| Arquivo | Propósito | Editable |
|---------|-----------|----------|
| `docker-compose.yml` | Orquestração containers | Sim |
| `Dockerfile` | Build da API | Sim |
| `prompts/system_prompt.md` | Instruções LLM | Sim (recarrega auto) |
| `tools/*.py` | Function calling | Sim (auto-copy) |
| `.env` | Variáveis de ambiente | Sim (precisa restart) |
| `setup.sh` / `setup.bat` | Bootstrap | Não (já foi executado) |

---

## ⚙️ Variáveis de Ambiente (.env)

```env
# API
ENVIRONMENT=production
LLM_PROVIDER=mock              # Não usar LLM externo
OPS_ENABLED=false              # APIs desabilitadas (não precisa credenciais)
SCOPUS_ENABLED=false

# Ollama (automático)
OLLAMA_BASE_URL=http://ollama:11434

# Open WebUI (automático)
OPENAI_API_KEY=sk-local-key-not-used
```

---

## 📈 Uso de Recursos

### Requisitos Mínimos
| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| **RAM** | 4GB | 8GB+ |
| **CPU** | 2 cores | 4+ cores |
| **Disco** | 5GB | 10GB |
| **Rede** | 100Mbps | 1Gbps |

### Consumo por Container
- **Ollama (7b)**: ~6GB RAM, 2 cores
- **Ollama (3b)**: ~4GB RAM, 1 core
- **API FastAPI**: ~500MB RAM, 1 core
- **Open WebUI**: ~300MB RAM, 0.5 cores

**Total estimado**: ~7-7.5GB RAM (7b) ou ~5GB RAM (3b)

---

## 🔄 Fluxo de Uso Recomendado

```
1. Abrir Open WebUI (http://localhost:3000)
2. Descrever tema de busca
3. LLM chama refine_topic
4. Escolher uma variação refinada
5. LLM chama probe_search
6. Analisar resultados
7. Se bom, LLM chama final_search
8. Extrair termos (opcional)
9. Refinar ou exportar resultados
```

---

## 🐛 Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| Docker não inicia | Verificar daemon: `docker info` |
| Ollama lento | Usar modelo 3b: `ollama pull qwen2.5:3b` |
| API não responde | Logs: `docker logs pfc-api` |
| Tools não aparecem | Restart: `docker restart pfc-open-webui` |
| Sem memória | Aumentar allocation Docker Desktop |
| Conexão recusada | Portas em uso: `netstat -an` |

**Guia completo**: Ver `DOCKER_GUIDE.md`

---

## 📚 Documentação Completa

| Documento | Conteúdo |
|-----------|----------|
| `README.md` | Overview geral + setup local |
| `DOCKER_GUIDE.md` | Guia Docker completo |
| `tools/README.md` | Como criar/usar tools |
| `prompts/system_prompt.md` | Instruções LLM |

---

## ✨ Comandos Úteis

```bash
# Status
docker ps | grep pfc
docker compose logs -f

# Parar/Iniciar
docker-compose down
docker-compose up -d

# Modelos
docker exec pfc-ollama ollama list
docker exec pfc-ollama ollama pull qwen2.5:3b

# API
curl http://localhost:8000/docs
curl http://localhost:8000/api/v1/health

# Limpar (⚠️ DELETE TUDO)
docker-compose down -v
rm -rf ollama_data webui_data
```

---

## 🎯 Próximos Passos

1. **Execute setup.sh ou setup.bat**
2. **Acesse Open WebUI em http://localhost:3000**
3. **Copie system prompt para as settings**
4. **Teste refine_topic com tema genérico**
5. **Explore probe_search e final_search**
6. **Customize tools conforme necessário**

---

## 📞 Suporte

- **Logs Docker**: `docker logs pfc-{ollama,api,open-webui}`
- **Status containers**: `docker ps`
- **Health check API**: `curl http://localhost:8000/api/v1/health`
- **Ollama status**: `curl http://localhost:11434/api/tags`

---

**Criado em:** 2026-04-24  
**Versão Stack:** 1.0  
**Modelo Padrão:** Qwen2.5 (7b ou 3b)  
**Framework:** FastAPI + Docker + Ollama + Open WebUI
