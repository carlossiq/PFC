#!/usr/bin/env python3
"""
Script para inicializar Open WebUI com System Prompt automático.
Roda uma vez ao startup do container.
"""

import requests
import json
import time
from pathlib import Path

def wait_for_webui(max_retries=30):
    """Aguarda Open WebUI ficar pronto."""
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8080/health", timeout=5)
            if response.status_code == 200:
                print("✓ Open WebUI está pronto")
                return True
        except requests.exceptions.RequestException:
            pass

        print(f"⏳ Aguardando Open WebUI... ({i+1}/{max_retries})")
        time.sleep(1)

    return False

def load_system_prompt():
    """Carrega o system prompt do arquivo."""
    prompt_path = Path("/app/prompts/system_prompt.md")

    if not prompt_path.exists():
        print(f"❌ Arquivo não encontrado: {prompt_path}")
        return None

    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"✓ System Prompt carregado ({len(content)} caracteres)")
    return content

def save_system_prompt_to_file(prompt_content):
    """
    Salva o system prompt em um arquivo que Open WebUI pode usar.
    Open WebUI procura em /app/backend/data/ por configurações.
    """
    config_dir = Path("/app/backend/data/config")
    config_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = config_dir / "system_prompt.txt"

    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt_content)

    print(f"✓ System Prompt salvo em: {prompt_file}")
    return True

def main():
    """Executa inicialização."""
    print("")
    print("=" * 50)
    print("  Inicializando Open WebUI")
    print("=" * 50)
    print("")

    # 1. Aguardar Open WebUI
    print("[1/2] Aguardando Open WebUI iniciar...")
    if not wait_for_webui():
        print("❌ Open WebUI não iniciou no prazo")
        return False

    # 2. Carregar e salvar system prompt
    print("[2/2] Configurando System Prompt...")
    prompt = load_system_prompt()

    if not prompt:
        print("⚠️  Continuando sem system prompt automático")
        print("    Configure manualmente em: Settings → System Prompt")
        return False

    if save_system_prompt_to_file(prompt):
        print("")
        print("=" * 50)
        print("  ✓ Inicialização Concluída!")
        print("=" * 50)
        print("")
        print("📌 System Prompt foi configurado automaticamente!")
        print("")
        print("⚠️  IMPORTANTE:")
        print("   1. Acesse: http://localhost:3000")
        print("   2. Vá em: Settings → System Prompt")
        print("   3. Se estiver vazio, copie de: prompts/system_prompt.md")
        print("   4. Salve e recarregue (Ctrl+F5)")
        print("")
        return True

    return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro: {e}")
        exit(1)
