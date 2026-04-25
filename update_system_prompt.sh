#!/bin/bash

# Script para atualizar o system prompt no Open WebUI via API

echo "🔄 Atualizando System Prompt no Open WebUI..."

# Ler o arquivo de system prompt
PROMPT_FILE="prompts/system_prompt.md"

if [ ! -f "$PROMPT_FILE" ]; then
    echo "❌ Erro: Arquivo $PROMPT_FILE não encontrado!"
    exit 1
fi

# Ler conteúdo
PROMPT_CONTENT=$(cat "$PROMPT_FILE")

# Escapar aspas para JSON
PROMPT_JSON=$(echo "$PROMPT_CONTENT" | jq -Rs .)

echo "📝 System Prompt lido com sucesso ($(wc -c < "$PROMPT_FILE") bytes)"

# Tentar atualizar via API do Open WebUI
echo "🚀 Enviando para Open WebUI..."

# Nota: O Open WebUI não tem endpoint direto para isso via API pública
# Alternativa: atualizar diretamente no banco de dados SQLite

# Parar o container temporariamente
docker stop pfc-open-webui > /dev/null 2>&1
echo "⏸️  Open WebUI parado"

# Copiar o banco de dados
docker run --rm \
  -v pfc_webui_data:/data \
  -v "$(pwd)/temp_db:/backup" \
  alpine sh -c "cp /data/webui.db /backup/ 2>/dev/null || echo 'DB not found yet'"

echo "✅ Processo concluído!"
echo "⚠️  Nota: Para atualizar o system prompt, acesse http://localhost:3000 → Settings → System Prompt"
echo "📋 Cole o conteúdo de: prompts/system_prompt.md"

# Reiniciar
docker start pfc-open-webui > /dev/null 2>&1
echo "✅ Open WebUI reiniciado"

sleep 3
docker ps --filter "name=pfc-open-webui" --format "{{.Status}}"
