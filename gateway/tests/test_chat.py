import pytest

HEADERS = {"X-API-Key": "test-key-123"}


@pytest.mark.asyncio
async def test_chat_completions_success(client, monkeypatch):
    from app.core.llm import LLMService

    async def fake_completions(self, messages, **kwargs):
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Hello!"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

    monkeypatch.setattr(LLMService, "chat_completions", fake_completions)

    resp = await client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Hello!"
    assert data["usage"]["total_tokens"] == 15


@pytest.mark.asyncio
async def test_chat_completions_injects_system_prompt(client, monkeypatch):
    from app.core.llm import LLMService

    received = {}

    async def capturing_completions(self, messages, **kwargs):
        received["messages"] = messages
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            "usage": {},
        }

    monkeypatch.setattr(LLMService, "chat_completions", capturing_completions)

    await client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={"messages": [{"role": "user", "content": "ping"}]},
    )
    assert len(received) > 0


@pytest.mark.asyncio
async def test_inject_system_prompt_applied():
    from app.core.llm import LLMService
    from app.core.config import settings

    svc = LLMService()
    result = svc._inject_system_prompt([{"role": "user", "content": "hi"}])
    assert result[0]["role"] == "system"
    assert result[0]["content"] == settings.default_nlp_system_prompt


@pytest.mark.asyncio
async def test_inject_system_prompt_skipped_when_exists():
    from app.core.llm import LLMService

    svc = LLMService()
    result = svc._inject_system_prompt([
        {"role": "system", "content": "Custom"},
        {"role": "user", "content": "hi"},
    ])
    assert result[0]["content"] == "Custom"
    assert len(result) == 2


@pytest.mark.asyncio
async def test_chat_completions_streaming_not_supported(client):
    resp = await client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={"messages": [{"role": "user", "content": "Hi"}], "stream": True},
    )
    assert resp.status_code == 501
    assert "Streaming" in resp.text


@pytest.mark.asyncio
async def test_chat_completions_missing_auth(client):
    resp = await client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "Hi"}]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_completions_custom_temperature(client, monkeypatch):
    from app.core.llm import LLMService

    received = {}

    async def capturing_completions(self, messages, **kwargs):
        received["temperature"] = kwargs.get("temperature")
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            "usage": {},
        }

    monkeypatch.setattr(LLMService, "chat_completions", capturing_completions)

    await client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={"messages": [{"role": "user", "content": "Hi"}], "temperature": 0.8},
    )
    assert received["temperature"] == 0.8


@pytest.mark.asyncio
async def test_chat_completions_temperature_zero(client, monkeypatch):
    from app.core.llm import LLMService

    received = {}

    async def capturing_completions(self, messages, **kwargs):
        received["temperature"] = kwargs.get("temperature")
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            "usage": {},
        }

    monkeypatch.setattr(LLMService, "chat_completions", capturing_completions)

    await client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={"messages": [{"role": "user", "content": "Hi"}], "temperature": 0.0},
    )
    assert received["temperature"] == 0.0


@pytest.mark.asyncio
async def test_chat_completions_custom_model(client, monkeypatch):
    from app.core.llm import LLMService

    received = {}

    async def capturing_completions(self, messages, **kwargs):
        received["model"] = kwargs.get("model")
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            "usage": {},
        }

    monkeypatch.setattr(LLMService, "chat_completions", capturing_completions)

    await client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={"messages": [{"role": "user", "content": "Hi"}], "model": "gpt-4"},
    )
    assert received["model"] == "gpt-4"


@pytest.mark.asyncio
async def test_chat_completions_with_max_tokens(client, monkeypatch):
    from app.core.llm import LLMService

    received = {}

    async def capturing_completions(self, messages, **kwargs):
        received["max_tokens"] = kwargs.get("max_tokens")
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            "usage": {},
        }

    monkeypatch.setattr(LLMService, "chat_completions", capturing_completions)

    await client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={"messages": [{"role": "user", "content": "Hi"}], "max_tokens": 100},
    )
    assert received["max_tokens"] == 100


@pytest.mark.asyncio
async def test_chat_completions_with_response_format(client, monkeypatch):
    from app.core.llm import LLMService

    received = {}

    async def capturing_completions(self, messages, **kwargs):
        received["response_format"] = kwargs.get("response_format")
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "{}"}, "finish_reason": "stop"}],
            "usage": {},
        }

    monkeypatch.setattr(LLMService, "chat_completions", capturing_completions)

    await client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={
            "messages": [{"role": "user", "content": "JSON please"}],
            "response_format": {"type": "json_object"},
        },
    )
    assert received["response_format"] == {"type": "json_object"}
