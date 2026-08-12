"""
Ajuste do modelo de crescimento logístico de Fisher-Pry sobre a série
temporal de volume de documentos (contagem acumulada de patentes/artigos
por ano de publicação).

Este módulo NÃO tem relação com análise de saturação de amostra
(estimador Chao1 / bootstrap sobre completude de países, instituições ou
autores presentes na amostra) - aquilo responde a uma pergunta estatística
diferente ("minha amostra já capturou a maioria das entidades que
existem?"). Aqui a pergunta é sobre a série temporal de VOLUME publicado
por ano: "o volume de patentes/artigos sobre este tema já está
desacelerando e, se sim, onde fica o platô?".

Modelo (Fisher-Pry / curva logística):

    N(t) = K / (1 + e^(-r * (t - t0)))

    N(t) - quantidade ACUMULADA de documentos até o ano t.
    K    - capacidade máxima / platô de saturação: a assíntota superior da
           curva, ou seja, o total estimado de documentos que este tema vai
           acumular quando a tecnologia amadurecer por completo.
    r    - taxa de crescimento: quão "íngreme" é a subida da curva. r maior
           significa adoção mais rápida, concentrada em uma janela de anos
           mais curta.
    t0   - ponto de inflexão: o ano de crescimento máximo, onde N(t) = K/2.
           É o ano em que o número de documentos PUBLICADOS POR ANO (não o
           acumulado) atinge seu pico.

Três pontos de leitura do ciclo de vida tecnológico, derivados de K, r, t0:

    GP (Growth Point / Ponto de Crescimento) - ano em que a curva acumulada
        atinge `growth_threshold` (padrão 10%) de K. Antes disso, a
        tecnologia está em fase embrionária (poucas publicações, sem sinal
        claro de tendência). A partir do GP, o crescimento passa a
        acelerar de fato.

    MP (Midpoint / Ponto Médio) - é o próprio t0: o ano de inflexão da
        curva, onde metade de K já foi atingida e a taxa de publicação
        anual é máxima. É o "auge" da fase de expansão.

    SP (Saturation Point / Ponto de Saturação) - ano em que a curva atinge
        `saturation_threshold` (padrão 90%) de K. A partir daí a tecnologia
        está entrando em fase de maturidade/estabilização: documentos
        continuam surgindo, mas a taxa de crescimento anual já desacelerou
        bastante.

Se o ano calculado para GP/MP/SP for maior que o último ano observado nos
dados, ele é uma PROJEÇÃO (o modelo está extrapolando o futuro a partir do
ajuste), não um valor observado - use `project_s_curve` para gerar os
pontos dessa parte projetada da curva (a "parte tracejada" do gráfico).
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
from scipy.optimize import curve_fit

# Limiares usados para sinalizar quando o ajuste não deve ser tratado como
# confiável - ver `fit_s_curve` para o significado de cada um.
_MIN_R_SQUARED = 0.90
_MIN_YEARS_FOR_HIGH_SATURATION_CONFIDENCE = 5
_HIGH_SATURATION_THRESHOLD = 0.85
_MAX_PLAUSIBLE_GROWTH_RATE = 5.0


class SCurveFitError(RuntimeError):
    """Levantado quando `scipy.optimize.curve_fit` não converge ao tentar
    ajustar a curva logística de Fisher-Pry aos dados fornecidos.

    Isso normalmente significa que a série ainda está numa fase de
    crescimento muito inicial (sem sinal de desaceleração), então não há
    informação suficiente nos dados para estimar com confiança onde fica o
    platô de saturação (K). Não é um erro de programação - é um sinal de
    que os dados atuais não sustentam uma projeção de saturação ainda.
    """


def logistic(t: np.ndarray | float, K: float, r: float, t0: float) -> np.ndarray:
    """Curva logística de Fisher-Pry: N(t) = K / (1 + e^(-r * (t - t0))).

    Args:
        t: ano (ou array de anos) em que avaliar a curva.
        K: capacidade máxima / platô de saturação.
        r: taxa de crescimento.
        t0: ano do ponto de inflexão (onde N(t) = K/2).
    """
    return K / (1 + np.exp(-r * (np.asarray(t, dtype=float) - t0)))


def _year_at_fraction(K: float, r: float, t0: float, fraction: float) -> float:
    """Resolve N(t) = fraction * K para t, invertendo a curva logística.

    N(t) = fraction*K  =>  t = t0 - ln(1/fraction - 1) / r
    """
    if not (0.0 < fraction < 1.0):
        raise ValueError(f"fraction deve estar entre 0 e 1 (exclusivo), recebido: {fraction}")
    return t0 - math.log(1.0 / fraction - 1.0) / r


def fit_s_curve(
    yearly_counts: dict[int, int],
    growth_threshold: float = 0.10,
    saturation_threshold: float = 0.90,
) -> dict[str, Any]:
    """Ajusta o modelo logístico de Fisher-Pry a uma série de contagens
    anuais (NÃO acumuladas) de documentos, e calcula os pontos GP/MP/SP.

    Args:
        yearly_counts: dict {ano: quantidade de documentos publicados
            NAQUELE ano} - não acumulado. A função acumula internamente
            via `np.cumsum`. Chaves podem ser `int` ou `str` numérica
            (normalizadas para `int` aqui).
        growth_threshold: fração de K que define o Ponto de Crescimento
            (GP) - ex. 0.10 = GP é o ano em que 10% da capacidade máxima
            já foi atingida. Deve ser um parâmetro configurável, nunca um
            valor fixo dentro da fórmula, pois o que conta como "início do
            crescimento real" varia por área tecnológica.
        saturation_threshold: fração de K que define o Ponto de Saturação
            (SP) - ex. 0.90. Mesma lógica do parâmetro acima, para o outro
            extremo da curva.

    Returns:
        dict com:
            K, r, t0: parâmetros ajustados do modelo (ver docstring do
                módulo para o significado de cada um).
            gp_year, mp_year, sp_year: anos correspondentes aos pontos de
                Crescimento, Médio e Saturação (mp_year == t0).
            current_saturation: razão entre o último valor acumulado
                observado e K - "quanto do platô estimado já foi
                atingido até o último ano com dado real".
            years_observed: lista ordenada dos anos de entrada.
            cumulative_observed: contagem acumulada correspondente a cada
                ano em `years_observed`.
            fit_quality: {r_squared, reliable, warning} - ver mais abaixo.

    Raises:
        ValueError: se `yearly_counts` estiver vazio, tiver menos de 2 anos
            distintos, ou se os limiares estiverem fora de (0, 1) ou
            growth_threshold >= saturation_threshold - erros de uso da
            função, não relacionados à qualidade do ajuste.
        SCurveFitError: se `curve_fit` não convergir (ver docstring da
            exceção) - erro relacionado aos DADOS, não ao uso da função.

    Nota sobre `fit_quality`: mesmo quando o ajuste converge (sem levantar
    SCurveFitError), o resultado pode ainda ser pouco confiável - por
    exemplo, poucos anos de dado podem levar a um "platô" inventado por
    sobreajuste. `fit_quality["reliable"]` é False, com uma explicação em
    linguagem simples em `fit_quality["warning"]`, quando:
      - o R² do ajuste é menor que 90% (o modelo explica pouco da
        variação real observada);
      - a saturação atual já está acima de 85% com menos de 5 anos de
        dado (sinal de sobreajuste: platô "inventado" perto do último
        valor observado, sem evidência suficiente);
      - a taxa de crescimento (r) saiu zero, negativa, ou
        implausivelmente alta (ajuste convergiu para uma solução sem
        sentido físico, ex. curva quase em degrau).
    """
    if not yearly_counts:
        raise ValueError("yearly_counts não pode ser vazio.")
    if not (0.0 < growth_threshold < 1.0):
        raise ValueError(f"growth_threshold deve estar entre 0 e 1 (exclusivo), recebido: {growth_threshold}")
    if not (0.0 < saturation_threshold < 1.0):
        raise ValueError(
            f"saturation_threshold deve estar entre 0 e 1 (exclusivo), recebido: {saturation_threshold}"
        )
    if growth_threshold >= saturation_threshold:
        raise ValueError(
            "growth_threshold deve ser menor que saturation_threshold "
            f"(recebido growth_threshold={growth_threshold}, saturation_threshold={saturation_threshold})."
        )

    normalized = {int(year): float(count) for year, count in yearly_counts.items()}
    years_observed = sorted(normalized)
    if len(years_observed) < 2:
        raise ValueError(
            f"São necessários pelo menos 2 anos distintos de dados para ajustar a curva "
            f"(recebido: {len(years_observed)})."
        )

    counts = np.array([normalized[year] for year in years_observed])
    years_arr = np.array(years_observed, dtype=float)
    cumulative = np.cumsum(counts)

    p0 = [max(float(cumulative[-1]) * 1.5, 1.0), 0.3, float(np.median(years_arr))]

    try:
        params, _covariance = curve_fit(logistic, years_arr, cumulative, p0=p0, maxfev=5000)
    except RuntimeError as exc:
        raise SCurveFitError(
            "Não foi possível ajustar a curva logística (Fisher-Pry) aos dados fornecidos "
            f"({len(years_observed)} anos observados, de {years_observed[0]} a {years_observed[-1]}). "
            "Isso costuma acontecer quando a série ainda está numa fase de crescimento muito "
            "inicial: sem nenhum sinal de desaceleração no volume anual, o modelo não tem como "
            "estimar com confiança onde fica o platô de saturação (K). Recomenda-se aguardar mais "
            "anos de dado antes de projetar a saturação, ou apresentar apenas a curva acumulada "
            "observada (sem ajuste) para este conjunto."
        ) from exc

    K, r, t0 = (float(v) for v in params)

    if r != 0.0:
        gp_year = _year_at_fraction(K, r, t0, growth_threshold)
        sp_year = _year_at_fraction(K, r, t0, saturation_threshold)
    else:
        gp_year = float("nan")
        sp_year = float("nan")
    mp_year = t0

    current_saturation = float(cumulative[-1] / K) if K != 0.0 else float("inf")

    predicted = logistic(years_arr, K, r, t0)
    residuals = cumulative - predicted
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((cumulative - np.mean(cumulative)) ** 2))
    if ss_tot > 0:
        r_squared = 1.0 - ss_res / ss_tot
    else:
        r_squared = 1.0 if ss_res == 0 else 0.0

    reasons: list[str] = []
    if r_squared < _MIN_R_SQUARED:
        reasons.append(
            f"O ajuste explica apenas {r_squared:.0%} da variação observada nos dados "
            f"(R²={r_squared:.3f}), abaixo do mínimo de {_MIN_R_SQUARED:.0%} considerado confiável "
            "- a curva logística pode não representar bem esta série ainda."
        )
    if current_saturation > _HIGH_SATURATION_THRESHOLD and len(years_observed) < _MIN_YEARS_FOR_HIGH_SATURATION_CONFIDENCE:
        reasons.append(
            f"O modelo indica {current_saturation:.0%} de saturação já atingida, mas com apenas "
            f"{len(years_observed)} anos de dado - poucos anos para um platô tão alto ser confiável. "
            "Isso é um sinal típico de sobreajuste: o modelo pode estar 'inventando' um platô "
            "próximo do último valor observado, por falta de mais pontos no tempo."
        )
    if r <= 0:
        reasons.append(
            f"A taxa de crescimento estimada (r={r:.4f}) é zero ou negativa, o que não é coerente "
            "com uma curva de adoção em expansão - o ajuste provavelmente não convergiu para uma "
            "solução com sentido físico."
        )
    elif r > _MAX_PLAUSIBLE_GROWTH_RATE:
        reasons.append(
            f"A taxa de crescimento estimada (r={r:.2f}) é implausivelmente alta - o ajuste pode "
            "ter convergido para uma curva quase em degrau, o que geralmente indica dados "
            "insuficientes ou um platô mal-definido."
        )

    fit_quality = {
        "r_squared": round(r_squared, 4),
        "reliable": len(reasons) == 0,
        "warning": " ".join(reasons) if reasons else None,
    }

    return {
        "K": K,
        "r": r,
        "t0": t0,
        "gp_year": gp_year,
        "mp_year": mp_year,
        "sp_year": sp_year,
        "current_saturation": current_saturation,
        "years_observed": years_observed,
        "cumulative_observed": cumulative.tolist(),
        "fit_quality": fit_quality,
    }


def project_s_curve(fit_result: dict[str, Any], end_year: int, step: float = 1.0) -> dict[str, list[float]]:
    """Gera a parte projetada (futura) da curva S, do último ano observado
    até `end_year` - a porção tracejada do gráfico além dos dados reais.

    Args:
        fit_result: o dict retornado por `fit_s_curve` (usa K, r, t0 e o
            último ano em `years_observed` como ponto de partida).
        end_year: até que ano projetar. Deve ser maior que o último ano
            observado em `fit_result["years_observed"]`.
        step: passo (em anos) entre pontos projetados. Use 1.0 para um
            ponto por ano; valores menores dão uma curva mais suave.

    Returns:
        dict com "years" (lista de anos projetados, incluindo o último ano
        observado como ponto de partida) e "cumulative_projected" (valor
        acumulado projetado do modelo em cada um desses anos).

    Raises:
        ValueError: se `end_year` não for maior que o último ano observado.
    """
    K, r, t0 = fit_result["K"], fit_result["r"], fit_result["t0"]
    last_year = fit_result["years_observed"][-1]
    if end_year <= last_year:
        raise ValueError(f"end_year ({end_year}) deve ser maior que o último ano observado ({last_year}).")

    years = np.arange(float(last_year), float(end_year) + step, step)
    projected_cumulative = logistic(years, K, r, t0)
    return {
        "years": years.tolist(),
        "cumulative_projected": projected_cumulative.tolist(),
    }


if __name__ == "__main__":
    # Teste rápido: gera uma curva logística conhecida (K, r, t0
    # verdadeiros), adiciona ruído gaussiano nas contagens anuais, e
    # verifica que fit_s_curve recupera os parâmetros originais dentro de
    # uma margem de erro razoável (dados são ruidosos, então não se espera
    # recuperação exata).
    rng = np.random.default_rng(42)
    true_K, true_r, true_t0 = 20000.0, 0.35, 2015.0
    years = np.arange(2000, 2026)

    true_cumulative = logistic(years, true_K, true_r, true_t0)
    true_yearly = np.diff(true_cumulative, prepend=0.0)
    noisy_yearly = np.clip(
        true_yearly + rng.normal(0, true_yearly.std() * 0.15, size=true_yearly.shape),
        0,
        None,
    )
    yearly_counts = {int(year): int(round(count)) for year, count in zip(years, noisy_yearly)}

    print("=== Teste de recuperação de parâmetros (Fisher-Pry) ===")
    print(f"Parâmetros verdadeiros: K={true_K}, r={true_r}, t0={true_t0}")

    result = fit_s_curve(yearly_counts)
    print(f"Parâmetros estimados:   K={result['K']:.1f}, r={result['r']:.4f}, t0={result['t0']:.2f}")
    print(f"GP={result['gp_year']:.1f}  MP={result['mp_year']:.1f}  SP={result['sp_year']:.1f}")
    print(f"Saturação atual: {result['current_saturation']:.1%}")
    print(f"Qualidade do ajuste: {result['fit_quality']}")

    k_error = abs(result["K"] - true_K) / true_K
    r_error = abs(result["r"] - true_r) / true_r
    t0_error = abs(result["t0"] - true_t0)

    tolerance_relative = 0.20  # 20% - dados são ruidosos, não se espera recuperação exata
    tolerance_t0_years = 2.0

    checks = [
        ("K dentro de 20% do valor verdadeiro", k_error <= tolerance_relative),
        ("r dentro de 20% do valor verdadeiro", r_error <= tolerance_relative),
        ("t0 dentro de 2 anos do valor verdadeiro", t0_error <= tolerance_t0_years),
        ("Ajuste marcado como confiável (R² alto)", result["fit_quality"]["reliable"]),
    ]

    print("\n=== Resultado do teste ===")
    all_passed = True
    for description, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {description}")
        all_passed = all_passed and passed

    projection = project_s_curve(result, end_year=int(years[-1]) + 10)
    print(
        f"\nProjeção até {int(years[-1]) + 10}: {len(projection['years'])} pontos gerados, "
        f"cumulativo projetado final = {projection['cumulative_projected'][-1]:.1f}"
    )

    if not all_passed:
        raise SystemExit(1)
    print("\nTodos os testes passaram.")
