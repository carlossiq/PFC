"""
Tool para analisar complexidade de queries booleanas.
"""

import aiohttp
import asyncio


class Tools:
    """Tool para analisar complexidade de queries."""

    async def analyze_query_complexity(self, query: str) -> str:
        """
        Analisa a complexidade de uma query booleana.

        Mede:
        - Número de operadores (AND, OR, NOT)
        - Profundidade de aninhamento de parênteses
        - Número de termos
        - Score de complexidade (0-100)

        O score >70 geralmente causa falhas no OPS.

        Args:
            query: Query CQL, SQL ou expressão booleana

        Returns:
            String com análise detalhada de complexidade
        """
        try:
            payload = {"query": query}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://api:8000/api/v1/chat/analyze-query",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        return f"❌ Erro ao analisar query: {response.status}"

                    result = await response.json()

            if not result.get("success"):
                return f"❌ Erro: {result.get('error')}"

            data = result.get("data", {})
            score = data.get("complexity_score", 0)
            level = data.get("complexity_level", "Desconhecido")
            operators = data.get("operator_counts", {})
            nesting = data.get("nesting_depth", {})
            terms = data.get("term_count", {})
            warnings = data.get("warnings", [])
            recommendations = data.get("recommendations", [])

            # Determinar ícone baseado no score
            if score < 25:
                icon = "✅"
            elif score < 50:
                icon = "⚠️"
            elif score < 75:
                icon = "⚠️⚠️"
            else:
                icon = "❌"

            output = f"{icon} **Análise de Complexidade da Query**\n\n"

            output += f"**Score:** {score:.1f}/100 ({level})\n\n"

            output += f"**Operadores:**\n"
            output += f"  - AND: {operators.get('AND', 0)}\n"
            output += f"  - OR: {operators.get('OR', 0)}\n"
            output += f"  - NOT: {operators.get('NOT', 0)}\n"
            output += f"  - Total: {operators.get('total', 0)}\n\n"

            output += f"**Estrutura:**\n"
            output += f"  - Profundidade de aninhamento: {nesting.get('max_depth', 0)} níveis\n"
            output += f"  - Parênteses balanceados: {'Sim' if nesting.get('parentheses_balanced') else 'NÃO'}\n\n"

            output += f"**Termos:**\n"
            output += f"  - Total: {terms.get('total_terms', 0)}\n"
            output += f"  - Únicos: {terms.get('unique_terms', 0)}\n"
            output += f"  - Repetidos: {terms.get('repeated_terms', 0)}\n\n"

            # Mostrar avisos
            if warnings and warnings[0] != "[OK] Nenhum warning":
                output += f"**⚠️ Avisos:**\n"
                for warning in warnings[:3]:
                    output += f"  - {warning}\n"
                output += "\n"

            # Mostrar recomendações
            if recommendations and recommendations[0] != "[OK] Query bem otimizada!":
                output += f"**💡 Recomendações:**\n"
                for rec in recommendations[:3]:
                    output += f"  - {rec}\n"
                output += "\n"

            # Aviso especial
            if score > 70:
                output += f"**⚠️ ATENÇÃO:** Score > 70 pode causar timeout ou erro HTTP 404 no OPS.\n"
                output += f"Considere simplificar a query reduzindo termos e operadores.\n"
            elif score > 60:
                output += f"**ℹ️ Nota:** Query está próxima do limite recomendado (60).\n"
                output += f"Funciona na maioria dos casos, mas pode ser instável em APIs rigorosas.\n"
            else:
                output += f"**✅ Query está dentro dos limites recomendados.**\n"

            return output

        except asyncio.TimeoutError:
            return "❌ Timeout ao conectar com a API (>30s)"
        except Exception as e:
            return f"❌ Erro ao analisar complexidade: {str(e)}"
