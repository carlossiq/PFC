from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.adapters.driven.llm.openai_compatible_adapter import OpenAICompatibleAdapter


def _fake_response(content: str) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value={"choices": [{"message": {"content": content}}]})
    return response


@pytest.fixture
def adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(base_url="http://localhost:11434", model="qwen2.5:3b-instruct")


@pytest.mark.asyncio
async def test_generate_posts_to_chat_completions_and_strips_response(adapter):
    adapter._client.post = AsyncMock(return_value=_fake_response("  Olá mundo  "))

    result = await adapter.generate("prompt aqui", system="system aqui")

    assert result == "Olá mundo"
    adapter._client.post.assert_called_once()
    url, kwargs = adapter._client.post.call_args
    assert url[0] == "http://localhost:11434/v1/chat/completions"
    assert kwargs["json"]["model"] == "qwen2.5:3b-instruct"
    assert kwargs["json"]["messages"] == [
        {"role": "system", "content": "system aqui"},
        {"role": "user", "content": "prompt aqui"},
    ]
    assert "Authorization" not in kwargs["headers"]


@pytest.mark.asyncio
async def test_generate_without_system_prompt_omits_system_message(adapter):
    adapter._client.post = AsyncMock(return_value=_fake_response("resposta"))

    await adapter.generate("só prompt")

    _, kwargs = adapter._client.post.call_args
    assert kwargs["json"]["messages"] == [{"role": "user", "content": "só prompt"}]


@pytest.mark.asyncio
async def test_generate_sends_bearer_token_when_api_key_set():
    adapter = OpenAICompatibleAdapter(
        base_url="http://192.168.90.50:4000", model="m", api_key="sk-test123"
    )
    adapter._client.post = AsyncMock(return_value=_fake_response("ok"))

    await adapter.generate("prompt")

    _, kwargs = adapter._client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test123"


@pytest.mark.asyncio
async def test_generate_connect_error_raises_runtime_error(adapter):
    adapter._client.post = AsyncMock(side_effect=httpx.ConnectError("boom"))

    with pytest.raises(RuntimeError):
        await adapter.generate("prompt")
