import pytest

from app.core.services.chat_service import ChatService
from core.config import Settings


def _svc(threshold: float = 90.0) -> ChatService:
    settings = Settings(depositant_fuzzy_match_threshold=threshold)
    return ChatService(llm=None, patent_pairs=[], scholarly_pairs=[], settings=settings)


def test_fuzzy_group_depositants_merges_near_duplicates():
    svc = _svc()
    counts = {
        "Acme Corp": 10,
        "ACME CORP.": 4,
        "Acme Corporation": 3,
        "Globex Inc": 5,
    }

    grouped = svc._fuzzy_group_depositants(counts)

    assert grouped == {"Acme Corp": 17, "Globex Inc": 5}


def test_fuzzy_group_depositants_keeps_distinct_names_separate():
    svc = _svc()
    counts = {"Acme Inc": 8, "Acme Solutions Inc": 6, "Beta Ltd": 2}

    grouped = svc._fuzzy_group_depositants(counts)

    assert set(grouped) == {"Acme Inc", "Acme Solutions Inc", "Beta Ltd"}
    assert sum(grouped.values()) == 16


def test_fuzzy_group_depositants_empty_input():
    svc = _svc()
    assert svc._fuzzy_group_depositants({}) == {}


def test_fuzzy_group_depositants_threshold_is_configurable():
    counts = {"Acme Corp": 10, "Acme Co": 4}

    strict = _svc(threshold=99.0)._fuzzy_group_depositants(counts)
    assert set(strict) == {"Acme Corp", "Acme Co"}

    lenient = _svc(threshold=60.0)._fuzzy_group_depositants(counts)
    assert lenient == {"Acme Corp": 14}


def test_aggregate_ops_final_items_groups_depositants_and_cpc():
    svc = _svc()
    items = [
        {"applicants": ["Acme Corp"], "cpc": ["B64G 1/2222"], "title": "t1"},
        {"applicants": ["ACME CORP."], "cpc": ["B64G 1/443"], "title": "t2"},
        {"applicants": ["Globex Inc"], "cpc": ["H02S 10/40"], "title": None},
    ]

    depositants, cpc, titles = svc._aggregate_ops_final_items(items)

    assert depositants == {"Acme Corp": 2, "Globex Inc": 1}
    assert cpc == {"B64G": 2, "H02S": 1}
    assert titles == ["t1", "t2"]
