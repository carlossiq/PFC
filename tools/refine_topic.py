"""
Tool para refinar um tema genérico em 4 variações mais específicas.
"""

import asyncio
import aiohttp
import json
from typing import Optional

class Tools:
    """Tool para refinar tópicos usando a API de prospecção."""

    async def refine_topic(
        self,
        theme: str,
        description: Optional[str] = None,
        area_of_study: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> str:
        """
        Refina um tema genérico em 4 variações mais específicas.

        A LLM analisa o tema e sugere 4 tópicos mais focados e diferentes,
        preenchendo todos os campos para cada variação.

        Args:
            theme: Tema principal a refinar (obrigatório)
            description: Descrição adicional do tema (opcional)
            area_of_study: Área de estudo (opcional)
            keywords: Palavras-chave separadas por vírgula (opcional)

        Returns:
            String com os 4 tópicos refinados em formato legível
        """
        try:
            # Preparar payload
            keywords_list = None
            if keywords:
                keywords_list = [k.strip() for k in keywords.split(",")]

            payload = {
                "theme": theme,
                "description": description,
                "area_of_study": area_of_study,
                "keywords": keywords_list,
            }

            # Chamar API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://api:8000/api/v1/chat/refine-topic",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"Erro ao refinar tópico: {response.status} - {error_text}"

                    result = await response.json()

            if not result.get("success"):
                return f"Erro: {result.get('error', 'Desconhecido')}"

            # Formatar resposta
            candidates = result.get("data", {}).get("candidates", [])
            if not candidates:
                return "Nenhum tópico refinado foi gerado."

            output = "**4 Variações de Tópico Refinadas:**\n\n"
            for i, candidate in enumerate(candidates, 1):
                output += f"**Variação {i}:**\n"
                output += f"- **Tema:** {candidate.get('theme', 'N/A')}\n"
                if candidate.get("description"):
                    output += f"- **Descrição:** {candidate.get('description')}\n"
                if candidate.get("area_of_study"):
                    output += f"- **Área:** {candidate.get('area_of_study')}\n"
                if candidate.get("keywords"):
                    keywords_str = ", ".join(candidate.get("keywords", []))
                    output += f"- **Keywords:** {keywords_str}\n"
                output += "\n"

            return output

        except asyncio.TimeoutError:
            return "Erro: Timeout ao conectar com a API (>60s)"
        except Exception as e:
            return f"Erro ao refinar tópico: {str(e)}"
