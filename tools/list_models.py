"""
Tool para listar os modelos LLM disponíveis.
"""

import asyncio
import aiohttp


class Tools:
    """Tool para listar modelos disponíveis."""

    async def list_available_models(self) -> str:
        """
        Lista todos os modelos LLM disponíveis no sistema.

        Mostra quais modelos estão carregados e prontos para usar.

        Returns:
            String com informações formatadas sobre os modelos disponíveis.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://api:8000/api/v1/chat/models",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"❌ Erro ao listar modelos: {response.status} - {error_text}"

                    result = await response.json()

            if not result.get("success"):
                return f"❌ Erro: {result.get('message', 'Desconhecido')}"

            models = result.get("data", {})
            if not models:
                return "⚠️ Nenhum modelo encontrado."

            # Formatar resposta
            output = "🤖 **Modelos LLM Disponíveis**\n\n"

            model_info = {
                "qwen2.5:7b": {
                    "description": "Qwen 2.5 - Versão Grande",
                    "parameters": "7 Bilhões",
                    "memory": "~6-7 GB",
                    "speed": "Média",
                    "quality": "Alta",
                    "recommended": "Para buscas complexas e análises detalhadas",
                },
                "qwen2.5:3b": {
                    "description": "Qwen 2.5 - Versão Compacta",
                    "parameters": "3 Bilhões",
                    "memory": "~2-3 GB",
                    "speed": "Rápida",
                    "quality": "Boa",
                    "recommended": "Para buscas simples e máquinas com RAM limitada",
                },
            }

            for model_name, available in models.items():
                info = model_info.get(model_name, {})
                status = "✅ Carregado" if available else "❌ Não disponível"

                output += f"**{info.get('description', model_name)}** - {status}\n"
                output += f"- 🧠 Parâmetros: {info.get('parameters', 'N/A')}\n"
                output += f"- 💾 Memória: {info.get('memory', 'N/A')}\n"
                output += f"- ⚡ Velocidade: {info.get('speed', 'N/A')}\n"
                output += f"- 🎯 Qualidade: {info.get('quality', 'N/A')}\n"
                output += f"- 💡 Recomendado: {info.get('recommended', 'N/A')}\n\n"

            loaded_models = [k for k, v in models.items() if v]
            if loaded_models:
                output += f"**Modelos Prontos para Usar:** {', '.join(loaded_models)}\n"
                output += "\n💡 Qual modelo você gostaria de usar?\n"
            else:
                output += "⚠️ Nenhum modelo está carregado no momento.\n"

            return output

        except asyncio.TimeoutError:
            return "❌ Timeout ao conectar com a API (>10s)"
        except Exception as e:
            return f"❌ Erro ao listar modelos: {str(e)}"
