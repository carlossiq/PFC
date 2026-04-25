"""
Tool para executar probe search: construir query + buscar + analisar complexidade.
"""

import aiohttp
import json
from typing import Optional
import asyncio


class Tools:
    """Tool para executar probe search completo."""

    async def probe_search(
        self,
        theme: str,
        description: Optional[str] = None,
        area_of_study: Optional[str] = None,
        keywords: Optional[str] = None,
        api: str = "ops",
    ) -> str:
        """
        Executa busca exploratória (probe search) com análise de complexidade.

        Etapas:
        1. Constrói query de probe baseada no tema
        2. Analisa complexidade da query
        3. Executa busca na API especificada
        4. Retorna resultados formatados

        Args:
            theme: Tema principal (obrigatório)
            description: Descrição adicional (opcional)
            area_of_study: Área de estudo (opcional)
            keywords: Palavras-chave separadas por vírgula (opcional)
            api: API a usar (ops, scopus, lens_patent, lens_scholarly) - padrão: ops

        Returns:
            String com resumo da busca, complexidade e primeiros resultados
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

            output = f"🔍 **Probe Search** - API: {api.upper()}\n\n"

            async with aiohttp.ClientSession() as session:
                # Passo 1: Construir query
                output += "⏳ Construindo query...\n"
                async with session.post(
                    "http://api:8000/api/v1/chat/probe/query",
                    json=intake_payload,
                    params={"api": api},
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        return f"❌ Erro ao construir query: {response.status}"

                    query_result = await response.json()

                if not query_result.get("success"):
                    return f"❌ Erro: {query_result.get('error')}"

                query_data = query_result.get("data", {})
                query_str = query_data.get("query", {}).get("query", "")
                complexity = query_result.get("complexity", {})

                # Mostrar complexidade
                if complexity:
                    complexity_score = complexity.get("score", 0)
                    complexity_level = complexity.get("level", "Desconhecido")
                    output += f"✓ Query construída\n"
                    output += f"  - **Complexidade:** {complexity_score:.1f}/100 ({complexity_level})\n"
                    if complexity.get("warnings") and complexity["warnings"][0] != "[OK] Nenhum warning":
                        output += f"  - **Avisos:** {', '.join(complexity.get('warnings', [])[:2])}\n"
                    output += "\n"

                # Passo 2: Executar busca
                output += "⏳ Executando busca...\n"
                search_payload = {
                    "query": query_data.get("query"),
                    "api": api,
                }

                async with session.post(
                    "http://api:8000/api/v1/chat/probe/search",
                    json=search_payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as response:
                    if response.status != 200:
                        return f"❌ Erro ao executar busca: {response.status}"

                    search_result = await response.json()

                if not search_result.get("success"):
                    return f"❌ Erro na busca: {search_result.get('error')}"

                # Formatar resultados
                results = search_result.get("data", {}).get("results", [])
                total = search_result.get("data", {}).get("total_available", 0)
                returned = search_result.get("data", {}).get("results_count", 0)

                output += f"✓ Busca concluída\n"
                output += f"  - **Documentos encontrados:** {total}\n"
                output += f"  - **Documentos retornados:** {returned}\n\n"

                if not results:
                    output += "⚠️ Nenhum resultado encontrado. Considere refinar o tema.\n"
                else:
                    output += f"**Primeiros {min(5, len(results))} Resultados:**\n\n"
                    for i, doc in enumerate(results[:5], 1):
                        # Extrair campos relevantes
                        title = doc.get("title", "Sem título")
                        abstract = doc.get("abstract", "")
                        abstract = abstract[:200] + "..." if len(abstract) > 200 else abstract

                        output += f"{i}. **{title}**\n"
                        if abstract:
                            output += f"   {abstract}\n"
                        output += "\n"

                output += f"💡 **Próximos passos:**\n"
                output += f"1. Deseja extrair termos relevantes destes resultados?\n"
                output += f"2. Deseja refinar a query e fazer nova busca?\n"
                output += f"3. Deseja prosseguir para a busca final?\n"

                return output

        except asyncio.TimeoutError:
            return "❌ Timeout ao conectar com a API (>120s)"
        except Exception as e:
            return f"❌ Erro ao executar probe search: {str(e)}"
