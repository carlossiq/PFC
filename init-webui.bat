@echo off
setlocal enabledelayedexpansion

color 0b
cls

echo.
echo ========================================
echo.
echo   Inicializador Open WebUI
echo   (Configuracao automatica de Prompt)
echo.
echo ========================================
echo.

REM Verificar se Open WebUI esta rodando
echo [1/2] Verificando Open WebUI...

:check_webui
curl -s http://localhost:3000 > nul 2>&1

if errorlevel 1 (
    echo [INFO] Open WebUI nao respondendo ainda...
    echo        Aguardando 5 segundos...
    timeout /t 5 /nobreak > nul
    goto check_webui
)

color 0a
echo [OK] Open WebUI respondendo!
echo.

REM Copiar system prompt para container
echo [2/2] Copiando System Prompt para container...

if not exist "prompts\system_prompt.md" (
    echo [ERRO] Arquivo prompts\system_prompt.md nao encontrado!
    pause
    exit /b 1
)

docker cp prompts\system_prompt.md pfc-open-webui:/app/backend/data/config/ > nul 2>&1

if errorlevel 1 (
    echo [AVISO] Nao foi possivel copiar (permissoes)
    echo [INFO] Configure manualmente em: Settings ^> System Prompt
    echo.
    echo        Cole o conteudo de: prompts\system_prompt.md
    pause
    exit /b 0
)

color 0a

echo [OK] System Prompt copiado!
echo.

echo ========================================
echo.
echo   Inicializacao Concluida!
echo.
echo ========================================
echo.

echo PROXIMOS PASSOS:
echo.
echo 1. Abra: http://localhost:3000
echo.
echo 2. Settings ^(engrenagem^) ^> System Prompt
echo.
echo 3. Se estiver vazio, cole de: prompts\system_prompt.md
echo    (Copie todo o arquivo e cole)
echo.
echo 4. Clique em SAVE
echo.
echo 5. Recarregue com Ctrl+F5
echo.
echo 6. Teste:
echo    "Procuro patentes sobre IA para medicina"
echo.

start http://localhost:3000 > nul 2>&1

echo ========================================
echo.

pause
