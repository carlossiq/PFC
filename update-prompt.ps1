# Script PowerShell para atualizar System Prompt no Open WebUI
# Uso: ./update-prompt.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Atualizador de System Prompt" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar se API está rodando
Write-Host "[1/4] Verificando API..." -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -ErrorAction Stop
    Write-Host "✓ API respondendo em http://localhost:8000" -ForegroundColor Green
} catch {
    Write-Host "✗ API não respondendo!" -ForegroundColor Red
    Write-Host "   Execute: docker restart pfc-api" -ForegroundColor Yellow
    pause
    exit 1
}

# 2. Obter System Prompt da API
Write-Host "[2/4] Obtendo System Prompt..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/chat/system-prompt" `
        -ContentType "application/json" `
        -ErrorAction Stop

    $json = $response.Content | ConvertFrom-Json

    if (-not $json.success) {
        throw "API retornou erro: $($json.message)"
    }

    $prompt = $json.data.content
    Write-Host "✓ Prompt obtido ($($prompt.Length) caracteres)" -ForegroundColor Green
} catch {
    Write-Host "✗ Erro ao obter prompt: $_" -ForegroundColor Red
    pause
    exit 1
}

# 3. Copiar para área de transferência
Write-Host "[3/4] Copiando para área de transferência..." -ForegroundColor Yellow
try {
    $prompt | Set-Clipboard
    Write-Host "✓ Prompt copiado!" -ForegroundColor Green
} catch {
    Write-Host "✗ Erro ao copiar: $_" -ForegroundColor Red
    Write-Host "   Salve manualmente: prompts\system_prompt.md" -ForegroundColor Yellow
}

# 4. Instruções finais
Write-Host "[4/4] Abrindo Open WebUI..." -ForegroundColor Yellow
Write-Host ""

# Tentar abrir no navegador
try {
    Start-Process "http://localhost:3000"
    Write-Host "✓ Open WebUI abrindo..." -ForegroundColor Green
} catch {
    Write-Host "⚠ Abra manualmente: http://localhost:3000" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PRÓXIMOS PASSOS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. No Open WebUI (http://localhost:3000):" -ForegroundColor Cyan
Write-Host "   → Clique em Settings (⚙️ canto superior)" -ForegroundColor White
Write-Host ""
Write-Host "2. Procure por 'System Prompt' ou 'System Message':" -ForegroundColor Cyan
Write-Host "   → Pode estar em Settings > General" -ForegroundColor White
Write-Host "   → Ou em uma aba de 'Advanced Settings'" -ForegroundColor White
Write-Host ""
Write-Host "3. Cole o prompt (já está na área de transferência!):" -ForegroundColor Cyan
Write-Host "   → Ctrl+V para colar" -ForegroundColor White
Write-Host ""
Write-Host "4. Salve as configurações:" -ForegroundColor Cyan
Write-Host "   → Clique em 'Save' ou pressione Ctrl+S" -ForegroundColor White
Write-Host ""
Write-Host "5. Recarregue a página:" -ForegroundColor Cyan
Write-Host "   → Pressione Ctrl+F5 (força limpar cache)" -ForegroundColor White
Write-Host ""
Write-Host "6. Teste:" -ForegroundColor Cyan
Write-Host '   → Digite: "Procuro patentes sobre IA para medicina"' -ForegroundColor White
Write-Host "   → Qwen deve chamar refine_topic() automaticamente ✓" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "✓ Tudo pronto! System Prompt está na área de transferência." -ForegroundColor Green
Write-Host ""
pause
