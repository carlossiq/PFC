# Docker Guide - PFC Patent Search Stack

Guia completo para trabalhar com Docker, Ollama e Open WebUI.

## Estrutura dos Containers

```
┌─────────────────────────────────────────────┐
│          docker-compose network             │
│                pfc-network                   │
└──────────────┬────────────┬───────────┬──────┘
               │            │           │
        ┌──────▼──┐   ┌────▼────┐   ┌──▼───────┐
        │ Ollama  │   │API      │   │Open WebUI│
        │ LLM     │   │FastAPI  │   │  Chat    │
        │11434   │   │8000    │   │3000     │
        └─────────┘   └────────┘   └──────────┘

Storage:
├─ ollama_data (models, cache)
├─ webui_data (config, tools)
└─ .env (config compartilhada)
```

## Inicialização Rápida

### Linux/macOS
```bash
bash setup.sh
```

### Windows
```bash
setup.bat
```

Ou manualmente:
```bash
docker-compose up -d
```

## Parar e Limpar

### Parar (mantém dados)
```bash
docker-compose down
```

### Parar e apagar tudo
```bash
docker-compose down -v
```

### Parar um container específico
```bash
docker stop pfc-ollama
docker stop pfc-api
docker stop pfc-open-webui
```

## Logs e Debugging

### Ver logs em tempo real
```bash
# Todos
docker-compose logs -f

# Específico
docker logs -f pfc-ollama
docker logs -f pfc-api
docker logs -f pfc-open-webui

# Últimas N linhas
docker logs --tail 100 pfc-api
```

### Verificar status
```bash
docker ps | grep pfc
docker stats pfc-ollama pfc-api pfc-open-webui
```

### Entrar em um container
```bash
docker exec -it pfc-ollama bash
docker exec -it pfc-api bash
docker exec -it pfc-open-webui bash
```

### Verificar conectividade interna
```bash
# Dentro do API container
docker exec pfc-api curl http://ollama:11434/api/tags

# Dentro do Open WebUI container
docker exec pfc-open-webui curl http://ollama:11434/api/tags
```

## Gerenciar Modelos Ollama

### Listar modelos disponíveis
```bash
docker exec pfc-ollama ollama list
```

### Baixar modelo adicional
```bash
# Modelo grande (mais preciso, ~7GB)
docker exec pfc-ollama ollama pull llama2:13b

# Modelo pequeno (rápido, ~4GB)
docker exec pfc-ollama ollama pull mistral:7b

# Versão específica
docker exec pfc-ollama ollama pull qwen2.5:7b
```

### Remover modelo
```bash
docker exec pfc-ollama ollama rm qwen2.5:7b
```

### Testar modelo
```bash
docker exec pfc-ollama ollama run qwen2.5:7b "Hello, world!"
```

## Variáveis de Ambiente

### .env (compartilhado)
```env
# API
ENVIRONMENT=production
LLM_PROVIDER=mock
OPS_ENABLED=false
SCOPUS_ENABLED=false

# Ollama (automático dentro dos containers)
OLLAMA_BASE_URL=http://ollama:11434

# Open WebUI
OPENAI_API_KEY=sk-local-key-not-used
```

### Modificar .env
```bash
# Editar
nano .env  # ou editor preferido

# Recarregar containers
docker-compose up -d
```

## Volumes e Persistência

### Dados armazenados
```
ollama_data/
├─ models/         (modelos LLM baixados)
├─ cache/          (cache de gerações)
└─ ...

webui_data/
├─ data/           (configs, histórico)
├─ tools/          (tools Python, link simbólico)
└─ ...
```

### Backup de dados
```bash
# Backup completo
docker-compose down
tar -czf pfc-backup.tar.gz ollama_data webui_data

# Restaurar
tar -xzf pfc-backup.tar.gz
docker-compose up -d
```

### Limpar cache Ollama
```bash
docker exec pfc-ollama ollama list --verbose
docker volume rm pfc_ollama_data  # ⚠️ remove tudo!
```

## Performance e Tunning

### Monitores de recurso
```bash
docker stats pfc-ollama pfc-api pfc-open-webui

# Com intervalo customizado
docker stats --no-stream
```

### Limitar recursos (docker-compose.yml)
```yaml
services:
  ollama:
    # ... outras configs ...
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 12G
        reservations:
          cpus: '2'
          memory: 8G
```

### Otimizações
```bash
# Usar CPU apenas (padrão)
# Nada a fazer, é o padrão

# GPU (se tiver NVIDIA)
# Ver: https://github.com/ollama/ollama/blob/main/docs/docker.md
```

## Troubleshooting

### "Connection refused"
```bash
# Ollama não respondendo?
docker logs pfc-ollama

# Verificar porta
docker port pfc-ollama

# Reiniciar
docker restart pfc-ollama
```

### "Out of Memory"
```bash
# Ver consumo
docker stats pfc-ollama

# Solução 1: Usar modelo menor
docker exec pfc-ollama ollama pull qwen2.5:3b

# Solução 2: Aumentar swap/alocação
# Editar docker-compose.yml > deploy > resources > limits > memory
```

### "Cannot connect to API"
```bash
# Verificar se está up
docker ps | grep pfc-api

# Ver logs
docker logs pfc-api

# Verificar porta
docker port pfc-api

# Testar acesso
curl http://localhost:8000/api/v1/health
```

### "Tools não aparecem no Open WebUI"
```bash
# Verificar volume de tools
docker exec pfc-open-webui ls /app/backend/data/tools

# Se vazio, copiar manualmente
docker cp tools/. pfc-open-webui:/app/backend/data/tools

# Reiniciar
docker restart pfc-open-webui
```

### "Modelo não carrega no Open WebUI"
```bash
# Verificar qual modelo está disponível
docker exec pfc-ollama ollama list

# Aquele que aparece ali é o disponível
# No Open WebUI, selecione o nome exato

# Se não aparecer em dropdown, reinicie WebUI
docker restart pfc-open-webui
```

## Desenvolvimento

### Recarregar código Python (API)
```bash
# Editar código em api/routes, services, etc
# Containerização já mapeia volume, precisa restart

docker restart pfc-api

# Ou editar docker-compose.yml para hot-reload:
volumes:
  - ./:/app

# Depois reiniciar
docker-compose restart api
```

### Testar tools localmente
```bash
# Sem rodar container
python -m pytest tests/

# Com container rodando
curl -X POST http://localhost:8000/api/v1/chat/probe/query \
  -H "Content-Type: application/json" \
  -d '{"theme":"IA para medicina"}'
```

### Adicionar nova tool
```bash
# 1. Criar arquivo em tools/
touch tools/minha_tool.py

# 2. Implementar classe Tools
# (ver tools/README.md)

# 3. Copiar para container (se já está rodando)
docker cp tools/minha_tool.py pfc-open-webui:/app/backend/data/tools/

# 4. Ou reiniciar para pegar do volume
docker-compose restart open-webui
```

## Exportar e Importar

### Salvar imagem Docker
```bash
# Commit do container rodando
docker commit pfc-api pfc-api:backup

# Ou salvar para arquivo
docker save pfc-api:backup -o pfc-api-backup.tar
```

### Compartilhar stack
```bash
# Incluir no repo
git add docker-compose.yml Dockerfile setup.sh setup.bat
git add prompts/ tools/
git commit -m "Add Docker + Ollama + Open WebUI stack"

# Clone e execute
git clone ...
bash setup.sh
```

## Recursos Úteis

- [Docker Compose Docs](https://docs.docker.com/compose/)
- [Ollama GitHub](https://github.com/ollama/ollama)
- [Open WebUI Docs](https://docs.openwebui.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

---

**Dúvidas?** Consulte os logs ou crie uma issue no GitHub.
