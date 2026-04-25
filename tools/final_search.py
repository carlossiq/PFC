"""
Tool para executar busca final: construir query final + buscar.
"""

import aiohttp
import json
from typing import Optional
import asyncio


class Tools:
    """Tool para executar busca final."""

    async def final_search(
        self,
        theme: str,
        description: Optional[str] = None,
        area_of_study: Optional[str] = None,
        keywords: Optional[str] = None,
        api: str = "ops",
        max_results: int = 500,
    ) -> str:
        """
        Executa busca final (produção) com termos expandidos.

        Construir query final com termos já refinados e executar busca
        retornando até max_results documentos.

        Args:
            theme: Tema principal (obrigatório)
            description: Descrição adicional (opcional)
            area_of_study: Área de estudo (opcional)
            keywords: Palavras-chave separadas por vírgula (opcional)
            api: API a usar (ops, scopus, lens_patent, lens_scholarly)
            max_results: Máximo de resultados a retornar (padrão: 500)

        Returns:
            String com resumo da busca final e quantidade de resultados
        """
        try:
            # Preparar payload
            keywords_list = None
            if keywords:
                keywords_list = [k.strip() for k in keywords.split(",")]

            intake_payload = {
                "theme": theme,
                "description": description,
                "area_of_study": area_of_study,
                "keywords": keywords_list,
            }

            output = f"🎯 **Busca Final (Produção)** - API: {api.upper()}\n\n"

            async with aiohttp.ClientSession() as session:
                # Passo 1: Construir query final
                output += "⏳ Construindo query final com termos expandidos...\n"
                async with session.post(
                    "http://api:8000/api/v1/chat/final/query",
                    json=intake_payload,
                    params={"api": api},
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as response:
                    if response.status != 200:
                        return f"❌ Erro ao construir query final: {response.status}"

                    query_result = await response.json()

                if not query_result.get("success"):
                    return f"❌ Erro: {query_result.get('error')}"

                query_data = query_result.get("data", {})
                complexity = query_result.get("complexity", {})

                # Mostrar complexidade
                if complexity:
                    complexity_score = complexity.get("score", 0)
                    complexity_level = complexity.get("level", "Desconhecido")
                    output += f"✓ Query final construída\n"
                    output += f"  - **Complexidade:** {complexity_score:.1f}/100 ({complexity_level})\n"
                    output += "\n"

                # Passo 2: Executar busca final
                output += f"⏳ Executando busca em {api.upper()}...\n"
                output += f"  (pode demorar alguns minutos com {max_results} documentos)\n"

                search_payload = {
                    "query": query_data.get("query"),
                    "api": api,
                    "max_results": max_results,
                }

                async with session.post(
                    "http://api:8000/api/v1/chat/final/search",
                    json=search_payload,
                    timeout=aiohttp.ClientTimeout(total=300),  # 5 minutos
                ) as response:
                    if response.status != 200:
                        return f"❌ Erro ao executar busca: {response.status}"

                    search_result = await response.json()

                if not search_result.get("success"):
                    error = search_result.get("error", "Desconhecido")
                    if "not yet implemented" in error.lower():
                        return f"⚠️ Busca final para {api} ainda não está implementada.\nUse 'scopus' para testes."
                    return f"❌ Erro na busca: {error}"

                # Formatar resultados
                results_data = search_result.get("data", {})
                total = results_data.get("total_available", 0)
                returned = results_data.get("results_count", 0)
                results = results_data.get("results", [])

                output += f"✓ Busca concluída!\n\n"
                output += f"📊 **Resultados:**\n"
                output += f"  - **Total disponível:** {total}\n"
                output += f"  - **Documentos retornados:** {returned}\n"
                output += f"  - **Máximo solicitado:** {max_results}\n\n"

                if not results:
                    output += "⚠️ Nenhum resultado encontrado.\n"
                else:
                    output += f"**Primeiros 10 Resultados:**\n\n"
                    for i, doc in enumerate(results[:10], 1):
                        title = doc.get("title", "Sem título")
                        abstract = doc.get("abstract", "")
                        abstract = abstract[:150] + "..." if len(abstract) > 150 else abstract

                        output += f"{i}. **{title}**\n"
                        if abstract:
                            output += f"   {abstract}\n"
                        output += "\n"

                    if returned > 10:
                        output += f"... e mais {returned - 10} resultados disponíveis para download.\n\n"

                output += f"💾 **Próximos passos:**\n"
                output += f"1. Deseja extrair termos-chave destes resultados?\n"
                output += f"2. Deseja refinara query e fazer nova busca?\n"
                output += f"3. Deseja exportar os resultados?\n"

                return output

        except asyncio.TimeoutError:
            return "❌ Timeout ao conectar com a API (>300s)"
        except Exception as e:
            return f"❌ Erro ao executar busca final: {str(e)}"
