from app.core.services.chart_labels import MAX_LABEL_LENGTH, abbreviate_label, abbreviate_labels


def test_short_names_are_untouched():
    assert abbreviate_label("MOTOROLA SOLUTIONS INC") == "MOTOROLA SOLUTIONS INC"
    assert abbreviate_label("Beijing Institute of Technology") == "Beijing Institute of Technology"


def test_long_names_use_standard_abbreviations_first():
    name = "Universidade Federal do Rio de Janeiro Instituto de Pesquisa"
    assert abbreviate_label(name) == "Univ. Fed. do Rio de Janeiro Inst. de Pesq."


def test_uppercase_names_keep_uppercase_abbreviations():
    # 57 caracteres -> abreviações em MAIÚSCULAS -> ainda 48 -> sem "OF".
    label = abbreviate_label("SHANGHAI RESEARCH INSTITUTE OF MATERIALS TECHNOLOGY CO LTD")
    assert label == "SHANGHAI RES. INST. MATERIALS TECHNOL. CO LTD"


def test_very_long_names_are_cut_at_word_boundary_without_dot_before_ellipsis():
    label = abbreviate_label("STATE GRID CORPORATION OF CHINA ELECTRIC POWER RESEARCH INSTITUTE CO LTD")
    assert len(label) <= MAX_LABEL_LENGTH
    assert label.endswith("…") and not label.endswith(".…")
    assert label.startswith("STATE GRID CORP. CHINA ELEC.")


def test_every_label_fits_the_limit():
    names = [
        "HUANENG CLEAN ENERGY RESEARCH INSTITUTE OF CHINA HUANENG GROUP CO LTD",
        "Nanjing University of Aeronautics and Astronautics College of Automation Engineering",
        "State Key Laboratory of Advanced Electromagnetic Engineering and Technology, Huazhong University",
    ]
    assert all(len(label) <= MAX_LABEL_LENGTH for label in abbreviate_labels(names))


def test_labels_stay_distinct_so_bars_are_not_merged():
    base = "Very Long Name Of A Research Institute Of Something Else Entirely"
    labels = abbreviate_labels([base + " North", base + " South"])
    assert len(set(labels)) == 2
    assert all(len(label) <= MAX_LABEL_LENGTH for label in labels)
