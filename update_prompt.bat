@echo off
setlocal enabledelayedexpansion

echo.
echo =========================================
echo Atualizando System Prompt no Open WebUI
echo =========================================
echo.

echo [INFO] Obtendo system prompt da API...

curl -s http://localhost:8000/api/v1/chat/system-prompt ^
  -H "Content-Type: application/json" > temp_prompt.json

if errorlevel 1 (
    echo [ERRO] Nao foi possivel conectar com a API
    echo Certifique-se que a API esta rodando em http://localhost:8000
    pause
    exit /b 1
)

echo [OK] Prompt obtido!
echo.
echo =========================================
echo PROXIMOS PASSOS:
echo =========================================
echo.
echo 1. Abra no navegador: http://localhost:3000
echo 2. Clique em Settings (engrenagem no canto superior direito)
echo 3. Procure por "System Prompt" ou "System Message"
echo 4. Limpe o conteudo anterior
echo 5. Cole o novo prompt (arquivo: prompts\system_prompt.md)
echo 6. Clique em Salvar/Save
echo 7. Recarregue a pagina com Ctrl+F5
echo.
echo O arquivo foi salvo em: temp_prompt.json
echo.
pause
