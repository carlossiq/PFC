from app.core.services.dedup_service import DedupService

import pytest


@pytest.fixture
def svc():
    return DedupService()


# ---- deduplicate_patents ----

def test_deduplicate_patents_removes_by_publication_number(svc):
    docs = [
        {"publication_number": "EP123", "title": "Foo"},
        {"publication_number": "EP123", "title": "Foo copy"},
    ]
    unique, duplicates = svc.deduplicate_patents(docs)
    assert len(unique) == 1
    assert len(duplicates) == 1


def test_deduplicate_patents_all_unique(svc):
    docs = [
        {"publication_number": "EP1"},
        {"publication_number": "EP2"},
        {"publication_number": "EP3"},
    ]
    unique, duplicates = svc.deduplicate_patents(docs)
    assert len(unique) == 3
    assert len(duplicates) == 0


# ---- deduplicate_scholarly ----

def test_deduplicate_scholarly_removes_by_doi(svc):
    docs = [
        {"doi": "10.1234/abc", "title": "Article A"},
        {"doi": "10.1234/abc", "title": "Article A duplicate"},
    ]
    unique, duplicates = svc.deduplicate_scholarly(docs)
    assert len(unique) == 1
    assert len(duplicates) == 1


def test_deduplicate_scholarly_removes_by_title_year(svc):
    docs = [
        {"title": "Deep Learning Review", "year": 2022},
        {"title": "Deep Learning Review", "year": 2022},
    ]
    unique, duplicates = svc.deduplicate_scholarly(docs)
    assert len(unique) == 1
    assert len(duplicates) == 1


# ---- create_dedup_key ----

def test_create_dedup_key_patent_deterministic(svc):
    key1 = svc.create_dedup_key("patent", publication_number="EP999")
    key2 = svc.create_dedup_key("patent", publication_number="EP999")
    assert key1 == key2


def test_create_dedup_key_scholarly_uses_doi(svc):
    key = svc.create_dedup_key("scholarly", doi="10.1234/x")
    assert "scholarly" in key
    assert "10.1234/x" in key


# ---- merge_duplicates ----

def test_merge_duplicates_patent(svc):
    docs = [
        {"publication_number": "EP1"},
        {"publication_number": "EP1"},
        {"publication_number": "EP2"},
    ]
    result = svc.merge_duplicates(docs, "patent")
    assert len(result) == 2


def test_merge_duplicates_unknown_type_raises(svc):
    with pytest.raises(ValueError):
        svc.merge_duplicates([], "video")
