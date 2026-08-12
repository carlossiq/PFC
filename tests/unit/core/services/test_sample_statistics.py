from app.core.services.sample_statistics import (
    bootstrap_topk_stability,
    chao1_diagnostics,
    chao1_estimate,
    is_sample_insufficient,
)


def test_chao1_estimate_no_singletons_or_doubletons_equals_s_obs():
    counts = {f"cat{i}": 20 for i in range(8)}
    assert chao1_estimate(counts) == 8.0


def test_chao1_estimate_grows_with_more_singletons():
    few_singletons = {"a": 10, "b": 10, "c": 1}
    many_singletons = {"a": 10, "b": 10, "c": 1, "d": 1, "e": 1, "f": 1}

    assert chao1_estimate(many_singletons) > chao1_estimate(few_singletons)


def test_chao1_diagnostics_empty_counts():
    diag = chao1_diagnostics({})
    assert diag["s_obs"] == 0
    assert diag["f1_ratio"] == 1.0
    assert diag["saturation"] == 1.0


def test_is_sample_insufficient_empty_is_always_insufficient():
    assert is_sample_insufficient({}) is True


def test_is_sample_insufficient_triggers_on_low_saturation():
    # cauda longa de singletons -> saturação baixa, f1_ratio alto e f2 baixo -
    # os três gatilhos disparam juntos aqui, mas o objetivo é confirmar que
    # uma amostra claramente sub-amostrada é sinalizada como insuficiente.
    undersampled = {f"cat{i}": 1 for i in range(20)}
    assert is_sample_insufficient(undersampled, saturation_threshold=0.5, f1_ratio_threshold=0.7, f2_min=5) is True


def test_is_sample_insufficient_triggers_on_high_f1_ratio_alone():
    # saturação e f2 OK, mas mais de 70% das categorias são singletons.
    counts = {"a": 50, "b": 2, "c": 2, "d": 2, "e": 2, "f": 2}
    for i in range(20):
        counts[f"tail{i}"] = 1
    diag = chao1_diagnostics(counts)
    assert diag["f1_ratio"] > 0.7
    assert is_sample_insufficient(counts, saturation_threshold=0.0, f1_ratio_threshold=0.7, f2_min=0) is True


def test_is_sample_insufficient_triggers_on_low_f2_alone():
    # sem singletons (f1=0, f1_ratio=0) e saturação alta (s_chao1==s_obs
    # quando f1=0), mas poucos doubletons.
    counts = {"a": 100, "b": 50, "c": 2, "d": 2}
    diag = chao1_diagnostics(counts)
    assert diag["f1"] == 0
    assert diag["f2"] == 2
    assert is_sample_insufficient(counts, saturation_threshold=0.0, f1_ratio_threshold=1.0, f2_min=5) is True


def test_is_sample_insufficient_false_when_all_three_thresholds_relaxed():
    counts = {"a": 50, "b": 2, "c": 2, "d": 2, "e": 2, "f": 2}
    for i in range(20):
        counts[f"tail{i}"] = 1
    # com thresholds bem permissivos, nenhum dos três gatilhos deveria disparar.
    assert is_sample_insufficient(counts, saturation_threshold=0.0, f1_ratio_threshold=1.0, f2_min=0) is False


def test_bootstrap_topk_stability_empty_counts():
    assert bootstrap_topk_stability({}) == {}


def test_bootstrap_topk_stability_dominant_distribution_is_stable():
    counts = {f"top{i}": 100 - i * 5 for i in range(10)}
    counts.update({f"tail{i}": 1 for i in range(50)})

    stability = bootstrap_topk_stability(counts, top_k=10, resamples=200, seed=42)

    assert set(stability) == {f"top{i}" for i in range(10)}
    assert all(score > 0.9 for score in stability.values())


def test_bootstrap_topk_stability_tied_distribution_is_less_stable():
    # 15 entidades com peso igual competindo por 10 vagas - nenhuma delas
    # deveria ficar perto de 1.0 (instável por definição).
    counts = {f"e{i}": 10 for i in range(15)}

    stability = bootstrap_topk_stability(counts, top_k=10, resamples=300, seed=42)

    assert len(stability) == 10
    assert all(0.3 < score < 0.95 for score in stability.values())


def test_bootstrap_topk_stability_respects_top_k_and_seed_determinism():
    counts = {f"e{i}": 10 - i for i in range(5)}

    a = bootstrap_topk_stability(counts, top_k=3, resamples=100, seed=7)
    b = bootstrap_topk_stability(counts, top_k=3, resamples=100, seed=7)

    assert len(a) == 3
    assert a == b
