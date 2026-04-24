"""
Query Complexity Analyzer - Mede complexidade de expresses booleanas (CQL, SQL, etc).

Anlisa:
- Nmero de operadores (AND, OR, NOT)
- Profundidade de aninhamento
- Nmero de termos/palavras-chave
- Tamanho total
- Score de complexidade
"""

import re
from typing import Any


class QueryComplexityAnalyzer:
    """Analisa complexidade de queries booleanas."""

    def __init__(self, query: str) -> None:
        """
        Inicializa o analisador.

        Args:
            query: String de query booleana (CQL, SQL, etc).
        """
        self.query = query.strip()

    def analyze(self) -> dict[str, Any]:
        """
        Executa anlise completa da query.

        Returns:
            Dict com todas as mtricas de complexidade.
        """
        return {
            "query_length": self._count_characters(),
            "operator_counts": self._count_operators(),
            "nesting_depth": self._calculate_nesting_depth(),
            "term_count": self._count_terms(),
            "complexity_score": self._calculate_complexity_score(),
            "complexity_level": self._get_complexity_level(),
            "warnings": self._generate_warnings(),
            "recommendations": self._generate_recommendations(),
        }

    def _count_characters(self) -> int:
        """Contagem de caracteres."""
        return len(self.query)

    def _count_operators(self) -> dict[str, int]:
        """Conta operadores booleanos."""
        # Case-insensitive para AND, OR, NOT
        and_count = len(re.findall(r"\bAND\b", self.query, re.IGNORECASE))
        or_count = len(re.findall(r"\bOR\b", self.query, re.IGNORECASE))
        not_count = len(re.findall(r"\bNOT\b", self.query, re.IGNORECASE))

        return {
            "AND": and_count,
            "OR": or_count,
            "NOT": not_count,
            "total": and_count + or_count + not_count,
        }

    def _calculate_nesting_depth(self) -> dict[str, Any]:
        """Calcula profundidade de aninhamento de parnteses."""
        max_depth = 0
        current_depth = 0

        for char in self.query:
            if char == "(":
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ")":
                current_depth -= 1

        return {
            "max_depth": max_depth,
            "parentheses_balanced": current_depth == 0,
        }

    def _count_terms(self) -> dict[str, int]:
        """Conta termos/palavras-chave entre aspas."""
        # Encontrar termos entre aspas duplas
        quoted_terms = re.findall(r'"([^"]+)"', self.query)
        # Encontrar termos entre aspas simples
        single_quoted_terms = re.findall(r"'([^']+)'", self.query)

        all_terms = quoted_terms + single_quoted_terms
        unique_terms = set(all_terms)

        return {
            "total_terms": len(all_terms),
            "unique_terms": len(unique_terms),
            "repeated_terms": len(all_terms) - len(unique_terms),
        }

    def _calculate_complexity_score(self) -> float:
        """
        Calcula score de complexidade (0-100).

        Baseado em:
        - Nmero de operadores (peso: 20)
        - Profundidade de aninhamento (peso: 30)
        - Nmero de termos (peso: 30)
        - Tamanho da query (peso: 20)
        """
        operators = self._count_operators()
        nesting = self._calculate_nesting_depth()
        terms = self._count_terms()
        length = self._count_characters()

        # Score individual (0-100)
        operator_score = min(100, (operators["total"] / 10) * 100)  # 10+ operadores = 100
        nesting_score = min(100, (nesting["max_depth"] / 5) * 100)  # 5+ nveis = 100
        term_score = min(100, (terms["total_terms"] / 20) * 100)  # 20+ termos = 100
        length_score = min(100, (length / 1000) * 100)  # 1000+ chars = 100

        # Mdia ponderada
        complexity = (
            operator_score * 0.2
            + nesting_score * 0.3
            + term_score * 0.3
            + length_score * 0.2
        )

        return round(complexity, 2)

    def _get_complexity_level(self) -> str:
        """Retorna nvel de complexidade (Simples, Moderado, Complexo, Muito Complexo)."""
        score = self._calculate_complexity_score()

        if score < 25:
            return "Simples"
        elif score < 50:
            return "Moderado"
        elif score < 75:
            return "Complexo"
        else:
            return "Muito Complexo"

    def _generate_warnings(self) -> list[str]:
        """Gera warnings sobre problemas na query."""
        warnings = []
        operators = self._count_operators()
        nesting = self._calculate_nesting_depth()
        terms = self._count_terms()

        # Warnings
        if operators["total"] > 15:
            warnings.append(f"[WARNING] Muitos operadores: {operators['total']} (limite recomendado: 10)")

        if nesting["max_depth"] > 4:
            warnings.append(
                f"[WARNING] Aninhamento muito profundo: {nesting['max_depth']} niveis (limite: 4)"
            )

        if not nesting["parentheses_balanced"]:
            warnings.append("[WARNING] Parenteses desbalanceados!")

        if terms["repeated_terms"] > 5:
            warnings.append(
                f"[WARNING] Termos repetidos: {terms['repeated_terms']} (considere remover duplicatas)"
            )

        if self._count_characters() > 2000:
            warnings.append(
                f"[WARNING] Query muito longa: {self._count_characters()} chars (limite: 2000)"
            )

        if operators["OR"] > operators["AND"] * 2:
            warnings.append(
                f"[WARNING] Muitos ORs relativos a ANDs (OR: {operators['OR']}, AND: {operators['AND']})"
            )

        return warnings if warnings else ["[OK] Nenhum warning"]

    def _generate_recommendations(self) -> list[str]:
        """Gera recomendacoes para simplificar a query."""
        recommendations = []
        score = self._calculate_complexity_score()
        operators = self._count_operators()
        nesting = self._calculate_nesting_depth()
        terms = self._count_terms()

        if score > 70:
            recommendations.append("- Reduzir numero de termos (de " + str(terms["total_terms"]) + " para ~5-8)")
            recommendations.append("- Limitar profundidade de aninhamento")
            recommendations.append("- Combinar termos similares com OR em um unico campo")
            recommendations.append("- Usar campos mais genericos quando possivel")

        if operators["OR"] > 10:
            recommendations.append("- Reduzir alternativas (ORs) - use apenas termos mais relevantes")

        if nesting["max_depth"] > 3:
            recommendations.append("- Simplificar estrutura de parenteses")

        if terms["repeated_terms"] > 0:
            recommendations.append("- Remover termos duplicados")

        if len(recommendations) == 0:
            recommendations.append("[OK] Query bem otimizada!")

        return recommendations

    def print_report(self) -> None:
        """Imprime relatorio formatado."""
        analysis = self.analyze()

        print("\n" + "=" * 70)
        print("QUERY COMPLEXITY ANALYSIS")
        print("=" * 70)

        print(f"\n[QUERY]:")
        print(f"  {self.query[:100]}{'...' if len(self.query) > 100 else ''}")

        print(f"\n[METRICAS]:")
        print(f"  Tamanho: {analysis['query_length']} caracteres")
        print(f"  Operadores: AND={analysis['operator_counts']['AND']}, OR={analysis['operator_counts']['OR']}, NOT={analysis['operator_counts']['NOT']} (Total: {analysis['operator_counts']['total']})")
        print(
            f"  Aninhamento: {analysis['nesting_depth']['max_depth']} niveis {'[OK]' if analysis['nesting_depth']['parentheses_balanced'] else '[ERROR]'}"
        )
        print(
            f"  Termos: {analysis['term_count']['total_terms']} total, {analysis['term_count']['unique_terms']} unicos"
        )

        print(f"\n[COMPLEXIDADE]:")
        print(f"  Score: {analysis['complexity_score']}/100")
        print(f"  Nivel: {analysis['complexity_level']}")

        print(f"\n[WARNINGS]:")
        for warning in analysis["warnings"]:
            print(f"  {warning}")

        print(f"\n[RECOMENDACOES]:")
        for rec in analysis["recommendations"]:
            print(f"  {rec}")

        print("\n" + "=" * 70 + "\n")


def compare_queries(query1: str, query2: str) -> None:
    """Compara complexidade de duas queries."""
    print("\n" + "=" * 70)
    print("COMPARAO DE QUERIES")
    print("=" * 70)

    analyzer1 = QueryComplexityAnalyzer(query1)
    analyzer2 = QueryComplexityAnalyzer(query2)

    analysis1 = analyzer1.analyze()
    analysis2 = analyzer2.analyze()

    print(f"\n QUERY 1:")
    print(f"   {query1[:80]}...")
    print(f"   Score: {analysis1['complexity_score']} ({analysis1['complexity_level']})")

    print(f"\n QUERY 2:")
    print(f"   {query2[:80]}...")
    print(f"   Score: {analysis2['complexity_score']} ({analysis2['complexity_level']})")

    diff = analysis2["complexity_score"] - analysis1["complexity_score"]
    print(f"\n DIFERENA: {diff:+.2f} ({'Mais simples' if diff < 0 else 'Mais complexa'})")

    print("\n" + "=" * 70 + "\n")
