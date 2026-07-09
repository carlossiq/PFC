from __future__ import annotations

import re
from typing import Any


class QueryComplexityAnalyzer:
    """Analisa complexidade de queries booleanas (CQL, SQL, etc)."""

    def __init__(self, query: str) -> None:
        self.query = query.strip()

    def analyze(self) -> dict[str, Any]:
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
        return len(self.query)

    def _count_operators(self) -> dict[str, int]:
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
        quoted_terms = re.findall(r'"([^"]+)"', self.query)
        single_quoted_terms = re.findall(r"'([^']+)'", self.query)
        all_terms = quoted_terms + single_quoted_terms
        unique_terms = set(all_terms)
        return {
            "total_terms": len(all_terms),
            "unique_terms": len(unique_terms),
            "repeated_terms": len(all_terms) - len(unique_terms),
        }

    def _calculate_complexity_score(self) -> float:
        operators = self._count_operators()
        nesting = self._calculate_nesting_depth()
        terms = self._count_terms()
        length = self._count_characters()

        operator_score = min(100, (operators["total"] / 10) * 100)
        nesting_score = min(100, (nesting["max_depth"] / 5) * 100)
        term_score = min(100, (terms["total_terms"] / 20) * 100)
        length_score = min(100, (length / 1000) * 100)

        return round(
            operator_score * 0.2 + nesting_score * 0.3 + term_score * 0.3 + length_score * 0.2,
            2,
        )

    def _get_complexity_level(self) -> str:
        score = self._calculate_complexity_score()
        if score < 25:
            return "Simples"
        elif score < 50:
            return "Moderado"
        elif score < 75:
            return "Complexo"
        return "Muito Complexo"

    def _generate_warnings(self) -> list[str]:
        warnings = []
        operators = self._count_operators()
        nesting = self._calculate_nesting_depth()
        terms = self._count_terms()

        if operators["total"] > 15:
            warnings.append(f"[WARNING] Muitos operadores: {operators['total']} (limite recomendado: 10)")
        if nesting["max_depth"] > 4:
            warnings.append(f"[WARNING] Aninhamento muito profundo: {nesting['max_depth']} niveis (limite: 4)")
        if not nesting["parentheses_balanced"]:
            warnings.append("[WARNING] Parenteses desbalanceados!")
        if terms["repeated_terms"] > 5:
            warnings.append(f"[WARNING] Termos repetidos: {terms['repeated_terms']}")
        if self._count_characters() > 2000:
            warnings.append(f"[WARNING] Query muito longa: {self._count_characters()} chars (limite: 2000)")
        if operators["OR"] > operators["AND"] * 2:
            warnings.append(
                f"[WARNING] Muitos ORs relativos a ANDs (OR: {operators['OR']}, AND: {operators['AND']})"
            )
        return warnings if warnings else ["[OK] Nenhum warning"]

    def _generate_recommendations(self) -> list[str]:
        recommendations = []
        score = self._calculate_complexity_score()
        operators = self._count_operators()
        nesting = self._calculate_nesting_depth()
        terms = self._count_terms()

        if score > 70:
            recommendations.append(f"- Reduzir numero de termos (de {terms['total_terms']} para ~5-8)")
            recommendations.append("- Limitar profundidade de aninhamento")
            recommendations.append("- Combinar termos similares com OR em um unico campo")
        if operators["OR"] > 10:
            recommendations.append("- Reduzir alternativas (ORs) - use apenas termos mais relevantes")
        if nesting["max_depth"] > 3:
            recommendations.append("- Simplificar estrutura de parenteses")
        if terms["repeated_terms"] > 0:
            recommendations.append("- Remover termos duplicados")
        return recommendations if recommendations else ["[OK] Query bem otimizada!"]
