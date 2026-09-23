import xml.etree.ElementTree as ET

from services.search.ops_service import OPSService, _extract_party_names_xml


def _json_party(data_format, sequence, name):
    return {"@data-format": data_format, "@sequence": sequence, "applicant-name": {"name": {"$": name}}}


def test_non_latin_original_name_falls_back_to_epodoc_without_country_suffix():
    entries = [
        _json_party("epodoc", "1", "HUANENG CLEAN ENERGY RES INST [CN]"),
        _json_party("original", "1", "华能清洁能源研究院"),
    ]

    assert OPSService._extract_party_names(entries, "applicant-name") == ["HUANENG CLEAN ENERGY RES INST"]


def test_latin_original_name_is_kept_even_with_accents():
    entries = [
        _json_party("original", "1", "Müller GmbH"),
        _json_party("epodoc", "1", "MUELLER GMBH [DE]"),
    ]

    assert OPSService._extract_party_names(entries, "applicant-name") == ["Müller GmbH"]


def test_non_latin_name_without_epodoc_pair_is_kept():
    entries = [_json_party("original", "1", "华能")]

    assert OPSService._extract_party_names(entries, "applicant-name") == ["华能"]


def test_xml_variant_uses_same_fallback():
    xml = """
    <applicants>
      <applicant data-format="epodoc" sequence="1"><applicant-name><name>BYD CO LTD [CN]</name></applicant-name></applicant>
      <applicant data-format="original" sequence="1"><applicant-name><name>比亚迪股份有限公司</name></applicant-name></applicant>
    </applicants>
    """
    parties = list(ET.fromstring(xml))

    assert _extract_party_names_xml(parties, "applicant-name") == ["BYD CO LTD"]
