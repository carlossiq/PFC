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


def test_scopus_simple_query_multiple_values():
    """
    Garante que múltiplos valores em campo simples geram predicados OR separados.
    """
    from schemas.llm import LLMOutput

    builder = QueryBuilderFactory.create("scopus")
    llm_output = LLMOutput(authors=SimpleFieldQuery(values=["Smith", "Jones"]))
    query = builder.build_query(llm_output, year_from=2020, year_to=2024)
    q = query["query"]

    assert 'AUTH("Smith")' in q
    assert 'AUTH("Jones")' in q
    assert " OR " in q
    assert 'AUTH("Smith" OR "AUTH(' not in q


def test_lens_scholarly_loads_field_map():
    """
    Garante que o Lens Scholarly usa os campos do JSON (não apenas filtro de data).
    """
    from schemas.llm import LLMOutput

    builder = QueryBuilderFactory.create("lens_scholarly")
    llm_output = LLMOutput(
        title=TextualFieldQuery(groups=[TermGroup(terms=["machine learning"])])
    )
    query = builder.build_query(llm_output, year_from=2020, year_to=2024)
    should_clauses = query["query"]["bool"].get("should", [])
    assert len(should_clauses) > 0, "title deveria gerar cláusula should"


def test_lens_patent_adapter_respects_search_mode():
    """
    Garante que search_mode=probe é repassado ao builder interno do Lens Patent.
    """
    from app.adapters.driven.query_builders.lens_patent_query_builder_adapter import LensPatentQueryBuilderAdapter
    from app.core.domain.types import LLMResponse

    adapter = LensPatentQueryBuilderAdapter()
    adapter.build_query(LLMResponse(), year_from=2020, year_to=2024, search_mode="probe")
    assert adapter._builder.search_mode == "probe"


def test_lens_scholarly_adapter_respects_search_mode():
    """
    Garante que search_mode=probe é repassado ao builder interno do Lens Scholarly.
    """
    from app.adapters.driven.query_builders.lens_scholarly_query_builder_adapter import LensScholarlyQueryBuilderAdapter
    from app.core.domain.types import LLMResponse

    adapter = LensScholarlyQueryBuilderAdapter()
    adapter.build_query(LLMResponse(), year_from=2020, year_to=2024, search_mode="probe")
    assert adapter._builder.search_mode == "probe"


def test_scopus_adapter_respects_search_mode():
    """
    Garante que search_mode é repassado ao builder interno do adapter.
    """
    from app.adapters.driven.query_builders.scopus_query_builder_adapter import ScopusQueryBuilderAdapter
    from app.core.domain.types import LLMResponse

    adapter = ScopusQueryBuilderAdapter()
    result = adapter.build_query(LLMResponse(), year_from=2020, year_to=2024, search_mode="probe")

    assert isinstance(result, dict)
    assert "query" in result
    assert adapter._builder.search_mode == "probe"
