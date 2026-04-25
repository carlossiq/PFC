@echo off
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo.
echo   PFC Patent Search Stack Setup
echo.
echo ==========================================
echo.

REM Verificar se Docker está instalado
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Docker nao encontrado!
    echo Por favor, instale Docker: https://docs.docker.com/desktop/install/windows-install/
    echo.
    pause
    exit /b 1
)

REM Verificar docker-compose
where docker-compose >nul 2>nul
if errorlevel 1 (
    REM Tentar docker compose (versão integrada)
    docker compose version >nul 2>nul
    if errorlevel 1 (
        echo [ERRO] Docker Compose nao encontrado!
        exit /b 1
    )
    set DOCKER_COMPOSE=docker compose
) else (
    set DOCKER_COMPOSE=docker-compose
)

echo [INFO] Verificando Docker...
docker version >nul 2>nul
echo [OK] Docker encontrado!
echo.

echo [INFO] Iniciando containers Docker...
echo.
call %DOCKER_COMPOSE% up -d

REM Aguardar Ollama
echo [INFO] Aguardando Ollama iniciar (ate 30s)...
set RETRY=0
:wait_ollama
docker exec pfc-ollama curl -s http://localhost:11434/api/tags >nul 2>nul
if errorlevel 1 (
    if !RETRY! lss 30 (
        set /a RETRY=!RETRY!+1
        timeout /t 1 /nobreak >nul
        goto wait_ollama
    ) else (
        echo [ERRO] Ollama nao iniciou no prazo!
        echo Tente: docker logs pfc-ollama
        pause
        exit /b 1
    )
)
echo [OK] Ollama esta pronto!
echo.

REM Fazer pull do modelo
echo [INFO] Baixando modelo Qwen2.5:7b...
echo [AVISO] Isso pode levar alguns minutos (~2-3GB)...
echo.
docker exec pfc-ollama ollama pull qwen2.5:7b
if errorlevel 1 (
    echo [AVISO] Tentando modelo 3b (menor) alternativo...
    docker exec pfc-ollama ollama pull qwen2.5:3b
)
echo [OK] Modelo baixado!
echo.

REM Aguardar API
echo [INFO] Aguardando API FastAPI iniciar...
set RETRY=0
:wait_api
docker exec pfc-api curl -s http://localhost:8000/api/v1/health >nul 2>nul
if errorlevel 1 (
    if !RETRY! lss 30 (
        set /a RETRY=!RETRY!+1
        timeout /t 1 /nobreak >nul
        goto wait_api
    )
)
echo [OK] API esta pronta!
echo.

REM Aguardar Open WebUI
echo [INFO] Aguardando Open WebUI iniciar...
set RETRY=0
:wait_webui
docker exec pfc-open-webui curl -s http://localhost:8080 >nul 2>nul
if errorlevel 1 (
    if !RETRY! lss 30 (
        set /a RETRY=!RETRY!+1
        timeout /t 1 /nobreak >nul
        goto wait_webui
    )
)
echo [OK] Open WebUI esta pronta!
echo.

echo ==========================================
echo.
echo   SUCESSO! Setup completado!
echo.
echo ==========================================
echo.

echo Acesse:
echo   * Open WebUI: http://localhost:3000
echo   * API FastAPI: http://localhost:8000
echo   * API Docs: http://localhost:8000/docs
echo   * Ollama: http://localhost:11434
echo.

echo Status dos containers:
docker ps --filter "name=pfc" --format "table {{.Names}}\t{{.Status}}"
echo.

echo Proximos passos:
echo   1. Abra http://localhost:3000 no navegador
echo   2. Escolha o modelo qwen2.5:7b (ou 3b)
echo   3. Comece a usar as tools para buscar patentes!
echo.

echo Para parar:
echo   * docker-compose down
echo.

echo Para limpar tudo (CUIDADO!):
echo   * docker-compose down -v
echo.

pause
