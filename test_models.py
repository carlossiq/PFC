import google.generativeai as genai
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém a chave da API do ambiente (ajuste o nome da variável se for diferente no seu .env)
api_key = os.getenv("LLM_GEMINI_API_KEY")

if not api_key:
    print(
        "Erro: A variável de ambiente LLM_GEMINI_API_KEY não foi encontrada no arquivo .env."
    )
    exit(1)

genai.configure(api_key=api_key)

print("Consultando modelos disponíveis na sua conta...")
print("-" * 50)

try:
    models = genai.list_models()

    print(
        "Modelos suportados para geração de texto (copie o nome em negrito para o seu .env):\n"
    )
    for m in models:
        if "generateContent" in m.supported_generation_methods:
            # Extrai apenas o nome final do modelo, removendo "models/"
            short_name = m.name.replace("models/", "")
            print(f"✅ {short_name}")

except Exception as e:
    print(f"❌ Ocorreu um erro ao consultar a API: {e}")

print("-" * 50)
