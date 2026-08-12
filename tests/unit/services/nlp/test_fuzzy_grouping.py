from services.nlp.fuzzy_grouping import fuzzy_group_names


def test_fuzzy_group_names_merges_near_duplicates():
    counts = {
        "Acme Corp": 10,
        "ACME CORP.": 4,
        "Acme Corporation": 3,
        "Globex Inc": 5,
    }

    grouped = fuzzy_group_names(counts, threshold=90.0)

    assert grouped == {"Acme Corp": 17, "Globex Inc": 5}


def test_fuzzy_group_names_keeps_distinct_names_separate():
    counts = {"Acme Inc": 8, "Acme Solutions Inc": 6, "Beta Ltd": 2}

    grouped = fuzzy_group_names(counts, threshold=90.0)

    assert set(grouped) == {"Acme Inc", "Acme Solutions Inc", "Beta Ltd"}
    assert sum(grouped.values()) == 16


def test_fuzzy_group_names_empty_input():
    assert fuzzy_group_names({}, threshold=90.0) == {}


def test_fuzzy_group_names_threshold_is_configurable():
    counts = {"Acme Corp": 10, "Acme Co": 4}

    strict = fuzzy_group_names(counts, threshold=99.0)
    assert set(strict) == {"Acme Corp", "Acme Co"}

    lenient = fuzzy_group_names(counts, threshold=60.0)
    assert lenient == {"Acme Corp": 14}
