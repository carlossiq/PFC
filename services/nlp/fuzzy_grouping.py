"""
Agrupamento fuzzy de nomes de entidade (depositantes de patente, instituições
de artigo) - extraído de ChatService pra poder ser reusado por outros
serviços (ex: StatisticalInferenceService, que precisa re-fundir contagens
somadas de múltiplas iterações de busca final) sem acessar um método privado
de outra classe.
"""

from typing import Optional


def fuzzy_group_names(counts: dict[str, int], threshold: float) -> dict[str, int]:
    """
    Funde nomes de entidade que provavelmente são a mesma (variação de
    grafia/pontuação/sufixo societário - ex: "Acme Corp" vs "ACME CORP." vs
    "Acme Corporation") antes de expor a contagem final. Usado tanto pra
    depositantes de patente (OPS) quanto instituições de artigo (Scopus) -
    mesma natureza de problema, só muda de onde `counts` e `threshold` vêm.

    Clustering guloso, não pairwise completo: ordena por contagem desc (o
    nome mais frequente de cada cluster vira o "representante" - normalmente
    a grafia mais usada/canônica) e compara cada nome seguinte contra os
    representantes já aceitos via rapidfuzz.fuzz.WRatio (0-100; robusto a
    diferenças de tamanho/ordem de tokens, melhor pra nomes de
    empresa/instituição que ratio simples). O(n²) em nomes ÚNICOS, não em
    itens - na prática algumas centenas de nomes distintos por busca final,
    custo desprezível.
    """
    if not counts:
        return {}

    from rapidfuzz import fuzz, utils

    ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)

    grouped: dict[str, int] = {}
    representatives: list[str] = []
    for name, count in ordered:
        best_match: Optional[str] = None
        best_score = 0.0
        for rep in representatives:
            # default_process (lowercase + remove pontuação) - sem isso
            # "Acme Corp" vs "ACME CORP." pontua baixo só por causa de
            # caixa/pontuação, exatamente o tipo de variação que esse
            # agrupamento deveria pegar.
            score = fuzz.WRatio(name, rep, processor=utils.default_process)
            if score >= threshold and score > best_score:
                best_match = rep
                best_score = score
        if best_match is not None:
            grouped[best_match] += count
        else:
            grouped[name] = count
            representatives.append(name)
    return grouped
