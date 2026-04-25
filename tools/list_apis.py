"""
Tool para listar as APIs de busca disponíveis e seu status.
"""

import asyncio
import aiohttp


class Tools:
    """Tool para listar APIs disponíveis."""

    async def list_available_apis(self) -> str:
        """
        Lista todas as APIs de busca disponíveis e seu status de habilitação.

        Mostra quais APIs estão habilitadas e prontas para usar.

        Returns:
            String com informações formatadas sobre as APIs disponíveis.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://api:8000/api/v1/chat/apis",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"❌ Erro ao listar APIs: {response.status} - {error_text}"

                    result = await response.json()

            if not result.get("success"):
                return f"❌ Erro: {result.get('message', 'Desconhecido')}"

            apis = result.get("data", {})
            if not apis:
                return "⚠️ Nenhuma API encontrada."

            # Formatar resposta
            output = "📋 **APIs de Busca Disponíveis**\n\n"

            api_info = {
                "ops": {
                    "name": "OPS (European Patent Office)",
                    "description": "Patentes europeias e mundiais",
                    "coverage": "~90M patentes",
                    "best_for": "Patentes globais",
                },
                "scopus": {
                    "name": "Scopus",
                    "description": "Artigos científicos e citações",
                    "coverage": "~100M artigos",
                    "best_for": "Artigos científicos",
                },
                "lens_patent": {
                    "name": "Lens (Patent)",
                    "description": "Patentes globais com full-text",
                    "coverage": "~150M patentes",
                    "best_for": "Patentes com full-text",
                },
                "lens_scholarly": {
                    "name": "Lens (Scholarly)",
                    "description": "Artigos científicos com full-text",
                    "coverage": "~50M artigos",
                    "best_for": "Artigos com full-text",
                },
            }

            for api_key, enabled in apis.items():
                info = api_info.get(api_key, {})
                status = "✅ Habilitada" if enabled else "❌ Desabilitada"

                output += f"**{info.get('name', api_key.upper())}** - {status}\n"
                output += f"- 📌 {info.get('description', '')}\n"
                output += f"- 🌍 Cobertura: {info.get('coverage', 'N/A')}\n"
                output += f"- 💡 Melhor para: {info.get('best_for', 'N/A')}\n\n"

            enabled_apis = [k for k, v in apis.items() if v]
            if enabled_apis:
                output += f"**APIs Prontas para Usar:** {', '.join(enabled_apis)}\n"
            else:
                output += "⚠️ Nenhuma API está habilitada no momento.\n"

            return output

        except asyncio.TimeoutError:
            return "❌ Timeout ao conectar com a API (>10s)"
        except Exception as e:
            return f"❌ Erro ao listar APIs: {str(e)}"
