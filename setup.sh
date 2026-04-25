#!/bin/bash

set -e

echo "=========================================="
echo "🚀 Setup - PFC Patent Search Stack"
echo "=========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir com cores
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Verificar se Docker está instalado
print_info "Verificando Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker não está instalado!"
    echo "Por favor, instale Docker em: https://docs.docker.com/install"
    exit 1
fi
print_success "Docker encontrado: $(docker --version)"

# Verificar docker-compose
if ! command -v docker-compose &> /dev/null; then
    print_warn "docker-compose não encontrado, tentando 'docker compose'..."
    if ! command -v docker compose &> /dev/null; then
        print_error "Docker Compose não está disponível!"
        exit 1
    fi
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi
print_success "Docker Compose disponível"

# Verificar RAM disponível
print_info "Verificando recursos..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    AVAILABLE_RAM=$(free -m | awk 'NR==2{print $7}')
    MODEL_SIZE="7b"
    if [ $AVAILABLE_RAM -lt 8000 ]; then
        print_warn "RAM baixa (<8GB). Usando modelo 3b ao invés de 7b"
        MODEL_SIZE="3b"
    else
        print_success "RAM disponível: ~${AVAILABLE_RAM}MB - usando modelo 7b"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    AVAILABLE_RAM=$(vm_stat | grep -E 'Pages free' | awk '{print $3}' | tr -d '.' | awk '{print int($1/256)}')
    MODEL_SIZE="7b"
    if [ $AVAILABLE_RAM -lt 8000 ]; then
        print_warn "RAM baixa (<8GB). Usando modelo 3b ao invés de 7b"
        MODEL_SIZE="3b"
    fi
else
    print_warn "Não foi possível verificar RAM. Assumindo 7b..."
    MODEL_SIZE="7b"
fi

echo ""
print_info "Iniciando containers Docker..."
echo ""

# Subir docker-compose
$DOCKER_COMPOSE up -d

# Aguardar Ollama estar pronto
print_info "Aguardando Ollama iniciar (isso pode demorar até 30s)..."
RETRY=0
MAX_RETRIES=30
until docker exec pfc-ollama curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    if [ $RETRY -eq $MAX_RETRIES ]; then
        print_error "Ollama não iniciou no prazo esperado"
        echo "Tente: docker logs pfc-ollama"
        exit 1
    fi
    RETRY=$((RETRY+1))
    sleep 1
done
print_success "Ollama está pronto!"

# Fazer pull do modelo
echo ""
print_info "Baixando modelo Qwen2.5:${MODEL_SIZE}..."
print_warn "Isso pode levar alguns minutos (~2-3GB)..."
echo ""

docker exec pfc-ollama ollama pull qwen2.5:${MODEL_SIZE}

if [ $? -eq 0 ]; then
    print_success "Modelo Qwen2.5:${MODEL_SIZE} baixado com sucesso!"
else
    print_error "Erro ao baixar modelo"
    exit 1
fi

# Aguardar API FastAPI
print_info "Aguardando API FastAPI iniciar..."
RETRY=0
MAX_RETRIES=30
until docker exec pfc-api curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; do
    if [ $RETRY -eq $MAX_RETRIES ]; then
        print_warn "API não respondeu no prazo. Verifique os logs: docker logs pfc-api"
        break
    fi
    RETRY=$((RETRY+1))
    sleep 1
done
print_success "API FastAPI está pronta!"

# Aguardar Open WebUI
print_info "Aguardando Open WebUI iniciar..."
RETRY=0
MAX_RETRIES=30
until docker exec pfc-open-webui curl -s http://localhost:8080 > /dev/null 2>&1; do
    if [ $RETRY -eq $MAX_RETRIES ]; then
        print_warn "Open WebUI pode ainda estar inicializando..."
        break
    fi
    RETRY=$((RETRY+1))
    sleep 1
done
print_success "Open WebUI está pronta!"

echo ""
echo "=========================================="
echo "✅ Setup Concluído com Sucesso!"
echo "=========================================="
echo ""
echo -e "${GREEN}🎉 Seu stack PFC está pronto!${NC}"
echo ""
echo "📱 Acessar:"
echo "  • Open WebUI (Chat com Ollama):  ${BLUE}http://localhost:3000${NC}"
echo "  • API FastAPI (REST):              ${BLUE}http://localhost:8000${NC}"
echo "  • API Docs (Swagger):              ${BLUE}http://localhost:8000/docs${NC}"
echo "  • Ollama API:                      ${BLUE}http://localhost:11434${NC}"
echo ""
echo "📋 Status dos containers:"
docker ps --filter "label!=name" -a --format "table {{.Names}}\t{{.Status}}" | grep -E "pfc-"
echo ""
echo "🤖 Modelo carregado:"
echo "  • Qwen2.5:${MODEL_SIZE}"
echo ""
echo "⚙️  Próximos passos:"
echo "  1. Abra http://localhost:3000 no seu navegador"
echo "  2. Você pode escolher o modelo 'qwen2.5:${MODEL_SIZE}' na seleção de modelos"
echo "  3. Use os prompts e tools para fazer buscas de patentes!"
echo ""
echo "📚 Documentação:"
echo "  • System Prompt: ./prompts/system_prompt.md"
echo "  • Tools: ./tools/"
echo "  • API OpenAPI: http://localhost:8000/openapi.json"
echo ""
echo "🛑 Para parar os containers:"
echo "  • ${BLUE}docker-compose down${NC}"
echo ""
echo "🗑️  Para limpar tudo (incluindo volumes):"
echo "  • ${BLUE}docker-compose down -v${NC}"
echo ""
echo "=========================================="
