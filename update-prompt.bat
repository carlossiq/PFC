@echo off
setlocal enabledelayedexpansion

color 0b
cls

echo.
echo ========================================
echo.
echo   Atualizador de System Prompt
echo.
echo ========================================
echo.

REM 1. Verificar API
echo [1/3] Verificando API...
curl -s http://localhost:8000/api/v1/health > nul 2>&1

if errorlevel 1 (
    color 0c
    echo.
    echo [ERRO] API nao esta respondendo!
    echo.
    echo Execute: docker restart pfc-api
    echo.
    pause
    exit /b 1
)

color 0b
echo [OK] API respondendo em http://localhost:8000
echo.

REM 2. Obter prompt da API
echo [2/3] Obtendo System Prompt...

curl -s http://localhost:8000/api/v1/chat/system-prompt ^
  -H "Content-Type: application/json" > temp_response.json

if errorlevel 1 (
    color 0c
    echo [ERRO] Falha ao obter prompt
    pause
    exit /b 1
)

REM 3. Extrair conteudo (precisa de jq ou python)
echo [3/3] Processando...

REM Tentar usar Python se disponivel
where python > nul 2>&1

if not errorlevel 1 (
    python -c "import json; data=json.load(open('temp_response.json')); print(data['data']['content'])" > system_prompt_extracted.txt 2>nul

    if not errorlevel 1 (
        echo [OK] Prompt salvo em: system_prompt_extracted.txt
        goto :success
    )
)

REM Se falhar, apenas mostrar instrucoes
echo.
echo [ATENCAO] Para copiar o prompt automaticamente:
echo - Instale Python ou jq
echo - Ou copie manualmente de: prompts\system_prompt.md
echo.
goto :success

:success
color 0a

echo.
echo ========================================
echo.
echo   PROXIMOS PASSOS
echo.
echo ========================================
echo.

echo 1. Abra: http://localhost:3000
echo.

echo 2. Clique em Settings (engrenagem)
echo.

echo 3. Procure por "System Prompt"
echo.

echo 4. Cole o conteudo de:
echo    - system_prompt_extracted.txt (se gerado)
echo    - OU prompts\system_prompt.md (copie manualmente)
echo.

echo 5. Clique em SAVE
echo.

echo 6. Recarregue com Ctrl+F5
echo.

echo 7. Teste com:
echo    "Procuro patentes sobre IA para medicina"
echo.

echo ========================================
echo.

REM Tentar abrir navegador
start http://localhost:3000 > nul 2>&1

echo [OK] Open WebUI abrindo...
echo.

REM Limpar arquivo temporario
del temp_response.json > nul 2>&1

pause
