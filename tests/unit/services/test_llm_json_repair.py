import json

import pytest

from app.core.services.chat_service import ChatService
from core.config import Settings
from services.llm.base import LLMJSONParseError, parse_llm_json
from services.llm.ollama_service import OllamaLLMService


# ---------------------------------------------------------------- parse_llm_json


def test_valid_json_is_untouched():
    assert parse_llm_json('{"a": [1, 2]}') == {"a": [1, 2]}


def test_missing_commas_are_inserted_where_json_points():
    raw = '{"TITLE": {"group_operator": "AND" "groups": [{"operator": "OR", "terms": ["drone" "uav"]}]}}'
    assert parse_llm_json(raw) == {
        "TITLE": {"group_operator": "AND", "groups": [{"operator": "OR", "terms": ["drone", "uav"]}]}
    }


def test_trailing_commas_are_removed():
    assert parse_llm_json('{"a": ["x", "y",], "b": 1,}') == {"a": ["x", "y"], "b": 1}


def test_unrepairable_json_raises_original_error():
    with pytest.raises(json.JSONDecodeError):
        parse_llm_json('{"a": "sem fechamento}')


def test_ollama_extracts_and_repairs_fenced_json_after_reasoning_text():
    response = 'Checklist:\n1. ok\n\n```json\n{"TITLE": {"groups": [{"terms": ["a" "b"]}]}}\n```'
    assert OllamaLLMService._extract_json(response) == {"TITLE": {"groups": [{"terms": ["a", "b"]}]}}


# ---------------------------------------------------------------- variante final: nova tentativa


class _AlwaysBrokenLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def process_intake(self, request, system_prompt):
        self.calls += 1
        raise LLMJSONParseError("Invalid JSON in ```json block: Expecting ',' delimiter", raw_response="{")


class _Resolver:
    def __init__(self, llm) -> None:
        self.llm = llm

    async def resolve(self, call_site):
        return self.llm


@pytest.mark.asyncio
async def test_final_variant_retries_on_broken_json_instead_of_aborting():
    llm = _AlwaysBrokenLLM()
    svc = ChatService(llm_resolver=_Resolver(llm), patent_pairs=[], scholarly_pairs=[], settings=Settings())
    intake = type("Intake", (), {"theme": "drones in war", "description": None, "area_of_study": None, "keywords": []})()

    result = await svc.build_final_query_variant(intake, [], "generic", "scopus")

    assert llm.calls > 1  # antes: parava na primeira resposta quebrada
    assert result["success"] is False
    assert "tentativas" in result["error"]
