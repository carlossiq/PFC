import pytest

from app.core.services.chat_service import ChatService
from app.core.services.query_field_extractor import extract_fields_from_query
from core.config import Settings


def _as_sets(fields: dict[str, list[str]]) -> dict[str, set[str]]:
    # Os builders deduplicam termos via set, então a ordem dentro de cada
    # campo na query gerada não é determinística.
    return {k: set(v) for k, v in fields.items()}


def _svc() -> ChatService:
    return ChatService(llm_resolver=None, patent_pairs=[], scholarly_pairs=[], settings=Settings())


# ---------------------------------------------------------------- round-trip


@pytest.mark.parametrize("search_mode", ["probe", "final"])
def test_ops_round_trip_with_builder(search_mode):
    fields = {"title": ["solar cell", "photovoltaic"], "abstract": ["perovskite"], "ipc": ["H01L31/00"]}
    llm_output = ChatService._query_fields_to_llm_output(fields)
    builder = ChatService._get_raw_query_builder("ops", search_mode)
    query = builder.build_query(llm_output=llm_output, year_from=2015, year_to=2026)["query"]

    assert _as_sets(extract_fields_from_query(query, "ops")) == _as_sets(fields)


@pytest.mark.parametrize("search_mode", ["probe", "final"])
def test_scopus_round_trip_with_builder(search_mode):
    fields = {"title": ["machine learning", "deep learning"], "abstract": ["healthcare"], "field_of_study": ["COMP"]}
    llm_output = ChatService._query_fields_to_llm_output(fields)
    builder = ChatService._get_raw_query_builder("scopus", search_mode)
    query = builder.build_query(llm_output=llm_output, year_from=2015, year_to=2026)["query"]

    assert _as_sets(extract_fields_from_query(query, "scopus")) == _as_sets(fields)


# ---------------------------------------------------------------- OPS manual


def test_ops_manual_edit_with_spacing_case_and_date():
    query = '(TI="solar cell" or ti = photovoltaic) and ab all "thin film" and pd within "20150101 20261231"'

    assert extract_fields_from_query(query, "ops") == {
        "title": ["solar cell", "photovoltaic"],
        "abstract": ["thin film"],
        "ipc": [],
    }


def test_ops_combined_field_goes_to_title_and_abstract():
    assert extract_fields_from_query('ta = "graphene" and ic = C01B32/182', "ops") == {
        "title": ["graphene"],
        "abstract": ["graphene"],
        "ipc": ["C01B32/182"],
    }


def test_ops_negated_terms_are_ignored():
    query = 'ti = "battery" not (ab = "lead acid" or ab = "nickel") and ab = "lithium" not ti = "car"'

    assert extract_fields_from_query(query, "ops") == {
        "title": ["battery"],
        "abstract": ["lithium"],
        "ipc": [],
    }


def test_ops_field_syntax_inside_quoted_term_is_not_a_predicate():
    assert extract_fields_from_query('ti = "ab = fake"', "ops")["abstract"] == []


# ---------------------------------------------------------------- Scopus manual


def test_scopus_manual_edit_with_unquoted_and_braced_terms():
    query = 'TITLE(machine learning OR {neural network}) AND ABS("deep learning") AND PUBYEAR > 2014 AND PUBYEAR < 2027'

    assert extract_fields_from_query(query, "scopus") == {
        "title": ["machine learning", "neural network"],
        "abstract": ["deep learning"],
        "field_of_study": [],
    }


def test_scopus_title_abs_key_goes_to_title_and_abstract():
    fields = extract_fields_from_query('TITLE-ABS-KEY("robotics") AND (SUBJAREA(ENGI) OR SUBJAREA(COMP))', "scopus")

    assert fields == {"title": ["robotics"], "abstract": ["robotics"], "field_of_study": ["ENGI", "COMP"]}


def test_scopus_negated_terms_are_ignored():
    query = 'TITLE("drone" AND NOT "military") AND NOT ABS("toy") AND ABS("delivery")'

    assert extract_fields_from_query(query, "scopus") == {
        "title": ["drone"],
        "abstract": ["delivery"],
        "field_of_study": [],
    }


def test_scopus_unknown_function_is_skipped_but_nested_fields_found():
    fields = extract_fields_from_query('KEY("iot") AND (TITLE("sensor"))', "scopus")

    assert fields["title"] == ["sensor"]
    assert fields["abstract"] == []


# ---------------------------------------------------------------- edge cases


@pytest.mark.parametrize("api", ["ops", "scopus"])
def test_query_without_recognizable_fields_returns_empty_lists(api):
    fields = extract_fields_from_query("just some words ((", api)

    assert all(values == [] for values in fields.values())


def test_unsupported_api_returns_empty_dict():
    assert extract_fields_from_query('ti = "x"', "lens_patent") == {}


@pytest.mark.asyncio
async def test_validate_query_returns_extracted_fields():
    result = await _svc().validate_final_query('ti = "solar cell" and ab = "perovskite"', "ops")

    assert result["success"] is True
    assert result["fields"] == {"title": ["solar cell"], "abstract": ["perovskite"], "ipc": []}
