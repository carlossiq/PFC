"""
Tests for query builders.
"""

import pytest

from schemas.intake import InputIntake
from schemas.llm import TextualFieldQuery, TermGroup, SimpleFieldQuery
from services.llm import LLMServiceFactory, LLMOutputNormalizer
from services.query_builders import QueryBuilderFactory


def test_query_builder_factory_creates_builders():
    """
    Verifica criação de builders para diferentes APIs.
    """
    apis = ["lens_patent", "lens_scholarly", "ops", "scopus"]

    for api in apis:
        builder = QueryBuilderFactory.create(api)
        assert builder is not None
        assert builder.api_name == api


def test_query_builder_factory_supported_apis():
    """
    Verifica lista de APIs suportadas.
    """
    apis = QueryBuilderFactory.get_supported_apis()
    assert len(apis) > 0
    assert "lens_patent" in apis
    assert "ops" in apis


def test_lens_patent_builder_builds_query():
    """
    Verifica construção de query Lens Patent.
    """
    from schemas.llm import LLMOutput

    builder = QueryBuilderFactory.create("lens_patent")

    llm_output = LLMOutput(
        title=TextualFieldQuery(
            groups=[TermGroup(terms=["test"])]
        ),
    )

    query = builder.build_query(llm_output, year_from=2020, year_to=2024)

    assert query is not None
    assert isinstance(query, dict)


def test_ops_builder_builds_cql_query():
    """
    Verifica construção de query CQL OPS.
    """
    from schemas.llm import LLMOutput

    builder = QueryBuilderFactory.create("ops")

    llm_output = LLMOutput(
        title=TextualFieldQuery(
            groups=[TermGroup(terms=["machine learning"])]
        ),
    )

    query = builder.build_query(llm_output, year_from=2020, year_to=2024)

    assert query is not None
    assert "query" in query


def test_query_builder_respects_max_length():
    """
    Verifica que builders respeitam comprimento máximo.
    """
    builders = [
        QueryBuilderFactory.create("lens_patent"),
        QueryBuilderFactory.create("ops"),
        QueryBuilderFactory.create("scopus"),
    ]

    for builder in builders:
        assert builder.max_query_length > 0


def test_query_builder_probe_vs_general():
    """
    Verifica diferenças entre probe e general search modes.
    """
    probe_builder = QueryBuilderFactory.create("lens_patent", search_mode="probe")
    general_builder = QueryBuilderFactory.create("lens_patent", search_mode="general")

    assert probe_builder.search_mode == "probe"
    assert general_builder.search_mode == "general"
