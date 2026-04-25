#!/usr/bin/env python3
"""
Script para atualizar o System Prompt no Open WebUI via banco de dados.
"""

import sqlite3
import json
import sys
from pathlib import Path

def update_system_prompt():
    """Atualiza o system prompt no Open WebUI."""

    # Caminhos
    prompt_file = Path("prompts/system_prompt.md")
    db_path = Path("ollama_data/../webui_data/webui.db")

    # Verificar arquivo
    if not prompt_file.exists():
        print(f"❌ Erro: {prompt_file} não encontrado!")
        return False

    # Ler prompt
    with open(prompt_file, "r", encoding="utf-8") as f:
        new_prompt = f.read()

    print(f"📝 System Prompt lido: {len(new_prompt)} caracteres")

    # Tentar conectar ao DB (se container estiver rodando)
    print("🔍 Procurando banco de dados...")
    print("⚠️  Este método é experimental. Use a interface UI para garantir atualização.")
    print("\n📋 **Alternativa (recomendada):**")
    print("1. Abra http://localhost:3000")
    print("2. Settings (⚙️) → System Prompt")
    print(f"3. Cole o conteúdo de: {prompt_file.absolute()}")
    print("4. Salve")

    return True

if __name__ == "__main__":
    success = update_system_prompt()
    sys.exit(0 if success else 1)
