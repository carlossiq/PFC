"""
Estimador Chao1 (riqueza de espécies) e bootstrap de estabilidade de ranking
- responde à pergunta "minha amostra já capturou a maioria das entidades que
existem, ou ainda há descobertas relevantes escondidas por falta de
volume?", aplicada sobre contagens de categorias (CPC, área de estudo) ou
entidades (depositantes, instituições) observadas numa busca final.

Este módulo NÃO tem relação com a curva S de crescimento temporal
(`app/core/services/s_curve.py`) - aquele responde a uma pergunta diferente
sobre a série de VOLUME publicado por ano. Aqui a pergunta é sobre
COMPLETUDE da amostra num dado momento (ver
`app/core/services/statistical_inference_service.py`, que usa este módulo
num loop de iterações de busca final até a amostra saturar).

Chao1 (Chao, 1984/1987): dado um conjunto de categorias observadas com suas
contagens, estima quantas categorias DISTINTAS existiriam numa amostra
infinita da mesma população, a partir de quantas aparecem raramente (só 1x
ou 2x) na amostra atual - muitos "singletons" (f1) e poucos "doubletons"
(f2) é sinal de que a amostra ainda não capturou a cauda longa da
distribuição.

Bootstrap: reamostra a distribuição observada, com reposição, muitas vezes,
e mede em quantas dessas reamostragens cada uma das entidades do top-10
ORIGINAL permanece no top-10 reamostrado - um ranking que muda muito entre
reamostragens é sinal de que a amostra ainda é pequena demais pra confiar
nele.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def chao1_estimate(counts: dict[str, int]) -> float:
    """
    Riqueza estimada (S_chao1) - fórmula bias-corrected de Chao1 (Chao,
    1987; a mesma usada por EstimateS/vegan), preferida sobre a fórmula
    clássica (S_obs + f1²/(2·f2)) por não precisar de caso especial pra
    f2=0 (indefinida na fórmula clássica) e ser mais estável em amostras
    pequenas/moderadas:

        S_chao1 = S_obs + f1*(f1-1) / (2*(f2+1))

    onde S_obs é o nº de categorias distintas observadas, f1 o nº de
    singletons (contagem == 1) e f2 o nº de doubletons (contagem == 2).
    """
    values = list(counts.values())
    s_obs = len(values)
    f1 = sum(1 for v in values if v == 1)
    f2 = sum(1 for v in values if v == 2)

    return s_obs + f1 * (f1 - 1) / (2 * (f2 + 1))


def chao1_diagnostics(counts: dict[str, int]) -> dict[str, Any]:
    """
    Números crus por trás da decisão de `is_sample_insufficient` - úteis
    pra log/depuração além do booleano (ex: expor no response da rota de
    inferência estatística pra quem quiser auditar por que parou onde
    parou).

    Returns:
        Dict com s_obs, f1, f2, s_chao1, saturation (S_obs/S_chao1, capado
        em 1.0) e f1_ratio (f1/S_obs).
    """
    values = list(counts.values())
    s_obs = len(values)
    f1 = sum(1 for v in values if v == 1)
    f2 = sum(1 for v in values if v == 2)
    s_chao1 = chao1_estimate(counts)

    saturation = min(1.0, s_obs / s_chao1) if s_chao1 > 0 else 1.0
    f1_ratio = f1 / s_obs if s_obs > 0 else 1.0

    return {
        "s_obs": s_obs,
        "f1": f1,
        "f2": f2,
        "s_chao1": s_chao1,
        "saturation": saturation,
        "f1_ratio": f1_ratio,
    }


def is_sample_insufficient(
    counts: dict[str, int],
    saturation_threshold: float = 0.5,
    f1_ratio_threshold: float = 0.7,
    f2_min: int = 5,
) -> bool:
    """
    Critério composto: a amostra é considerada insuficiente se QUALQUER UM
    dos três sinais abaixo for verdadeiro (cada um capta um jeito diferente
    de "ainda não vimos o suficiente"):

    - saturation < saturation_threshold (cobertura estimada baixa - a
      riqueza observada está longe da riqueza total estimada).
    - f1_ratio > f1_ratio_threshold (mais de X% das categorias observadas
      só apareceram 1 vez - cauda longa não capturada).
    - f2 < f2_min (poucas categorias vistas exatamente 2x - a própria
      estimativa Chao1 fica instável/pouco confiável com f2 baixo).

    counts vazio é sempre insuficiente (nada foi observado ainda).
    """
    if not counts:
        return True

    diag = chao1_diagnostics(counts)
    return (
        diag["saturation"] < saturation_threshold
        or diag["f1_ratio"] > f1_ratio_threshold
        or diag["f2"] < f2_min
    )


def bootstrap_topk_stability(
    counts: dict[str, int],
    top_k: int = 10,
    resamples: int = 1000,
    seed: int | None = None,
) -> dict[str, float]:
    """
    Estabilidade do ranking top-`top_k`: reamostra a distribuição observada
    (com reposição, mesmo tamanho total da amostra original) `resamples`
    vezes e mede, pra cada entidade do top-`top_k` ORIGINAL, em que fração
    dessas reamostragens ela permaneceu entre as `top_k` primeiras.

    Implementado via `rng.multinomial` (reamostragem vetorizada por
    contagem) em vez de sortear observação-a-observação - matematicamente
    equivalente a reamostrar o multiset de observações com reposição (é
    exatamente a definição de distribuição multinomial), mas muito mais
    rápido em numpy.

    Returns:
        Dict {nome: fração 0-1} só com as entidades do top-`top_k`
        original (as que já não estavam no top-`top_k` de partida não são
        avaliadas - a pergunta é "essas 10 continuam lá", não "quem mais
        poderia entrar").
    """
    if not counts:
        return {}

    names = list(counts.keys())
    weights = np.array([counts[n] for n in names], dtype=float)
    n_total = int(weights.sum())
    if n_total <= 0:
        return {}
    probs = weights / weights.sum()

    original_top_k = [name for name, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_k]]
    if not original_top_k:
        return {}

    name_to_idx = {name: i for i, name in enumerate(names)}
    original_idx = [name_to_idx[name] for name in original_top_k]

    rng = np.random.default_rng(seed)
    hit_counts = np.zeros(len(original_idx), dtype=int)

    for _ in range(resamples):
        resample_counts = rng.multinomial(n_total, probs)
        # np.argpartition é O(n) (não precisa ordenar tudo) - suficiente
        # pra achar os top_k maiores; a ordem entre eles não importa aqui,
        # só se um índice está ou não no conjunto top_k reamostrado.
        top_k_n = min(top_k, len(resample_counts))
        top_k_idx = set(np.argpartition(resample_counts, -top_k_n)[-top_k_n:].tolist())
        for j, idx in enumerate(original_idx):
            if idx in top_k_idx:
                hit_counts[j] += 1

    return {name: float(hit_counts[j]) / resamples for j, name in enumerate(original_top_k)}
