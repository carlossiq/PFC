@echo off
REM Script de startup completo para PFC Patent Search Stack
REM Este arquivo faz TUDO automaticamente

setlocal enabledelayedexpansion

color 0b
cls

echo.
echo =========================================
echo.
echo   PFC Patent Search Stack - Startup
echo.
echo =========================================
echo.

REM Passo 1: Iniciar docker-compose
echo [1/3] Iniciando containers Docker...
docker-compose up -d

if errorlevel 1 (
    color 0c
    echo [ERRO] Falha ao iniciar containers
    pause
    exit /b 1
)

echo [OK] Containers iniciados
timeout /t 5 /nobreak > nul

REM Passo 2: Aguardar Open WebUI ficar pronto
echo [2/3] Aguardando Open WebUI inicializar...

set "RETRIES=0"
:wait_webui
curl -s http://localhost:3000 > nul 2>&1

if errorlevel 1 (
    if !RETRIES! lss 30 (
        set /a RETRIES=!RETRIES!+1
        timeout /t 2 /nobreak > nul
        goto wait_webui
    ) else (
        color 0c
        echo [ERRO] Open WebUI nao respondeu a tempo
        pause
        exit /b 1
    )
)

color 0a
echo [OK] Open WebUI respondendo
echo.

REM Passo 3: Copiar system prompt
echo [3/3] Configurando System Prompt...

if not exist "prompts\system_prompt.md" (
    color 0c
    echo [ERRO] Arquivo prompts\system_prompt.md nao encontrado!
    pause
    exit /b 1
)

docker cp prompts\system_prompt.md pfc-open-webui:/app/backend/data/config/ > nul 2>&1

if errorlevel 1 (
    color 0e
    echo [AVISO] Nao foi possivel copiar system prompt automaticamente
    echo.
    echo Configure manualmente:
    echo 1. Abra: http://localhost:3000
    echo 2. Settings ^> System Prompt
    echo 3. Cole conteudo de: prompts\system_prompt.md
) else (
    color 0a
    echo [OK] System Prompt configurado!
)

color 0a

echo.
echo =========================================
echo.
echo   SUCESSO! Stack Pronta!
echo.
echo =========================================
echo.

echo.
echo [URLs DE ACESSO]
echo.
echo  * Open WebUI:     http://localhost:3000
echo  * API Swagger:    http://localhost:8000/docs
echo  * API Health:     http://localhost:8000/api/v1/health
echo.

echo.
echo [STATUS DOS CONTAINERS]
docker ps --filter "name=pfc" --format "table {{.Names}}\t{{.Status}}"
echo.

echo.
echo [PROXIMOS PASSOS]
echo.
echo 1. Acesse: http://localhost:3000
echo 2. Faca login (ou crie admin na primeira vez)
echo 3. Se System Prompt vazio:
echo    - Settings ^> System Prompt
echo    - Cole conteudo de: prompts\system_prompt.md
echo    - Salve e recarregue (Ctrl+F5)
echo.
echo 4. Teste:
echo    "Procuro patentes sobre IA para medicina"
echo.

start http://localhost:3000 > nul 2>&1

pause
