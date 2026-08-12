from services.search.scopus_service import _extract_final_fields


def test_extract_final_fields_single_affiliation_as_bare_dict():
    entry = {
        "dc:title": "Solar cells in Aarhus",
        "prism:coverDate": "2020-05-01",
        "affiliation": {"affilname": "Aarhus Universitet"},
    }

    result = _extract_final_fields(entry)

    assert result == {"title": "Solar cells in Aarhus", "institutions": ["Aarhus Universitet"], "year": 2020}


def test_extract_final_fields_multiple_affiliations_as_list():
    entry = {
        "dc:title": "Cross-institution study",
        "prism:coverDate": "2019-01-15",
        "affiliation": [{"affilname": "MIT"}, {"affilname": "Stanford"}],
    }

    result = _extract_final_fields(entry)

    assert result["institutions"] == ["MIT", "Stanford"]
    assert result["year"] == 2019


def test_extract_final_fields_missing_affiliation_and_date():
    entry = {"dc:title": "No metadata"}

    result = _extract_final_fields(entry)

    assert result == {"title": "No metadata", "institutions": [], "year": None}


def test_extract_final_fields_ignores_affiliation_without_affilname():
    entry = {
        "dc:title": "T",
        "prism:coverDate": "2021-01-01",
        "affiliation": [{"affiliation-country": "Denmark"}, {"affilname": "Aarhus Universitet"}],
    }

    result = _extract_final_fields(entry)

    assert result["institutions"] == ["Aarhus Universitet"]
