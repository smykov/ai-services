import pytest
from app.core.auth import verify_api_key
from app.core.config import settings
from fastapi import HTTPException
from httpx import ConnectError, HTTPStatusError, Request


@pytest.mark.asyncio
async def test_verify_api_key_no_keys(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", set())
    result = await verify_api_key("some-key")
    assert result is None


@pytest.mark.asyncio
async def test_verify_api_key_valid():
    result = await verify_api_key("test-key-123")
    assert result == "test-key-123"


@pytest.mark.asyncio
async def test_verify_api_key_invalid():
    with pytest.raises(HTTPException) as exc:
        await verify_api_key("wrong-key")
    assert exc.value.status_code == 401


# --- LLMService tests ---

from app.core.llm import LLMService


async def mock_response(status_code: int = 200, text: str = '{"ok": true}'):
    """Build a minimal httpx Response-like object for testing."""
    from httpx import Response
    return Response(status_code=status_code, text=text, request=Request("POST", "http://test"))


def test_llm_build_headers_with_key():
    svc = LLMService(api_key="sk-test")
    assert svc._build_headers() == {"Authorization": "Bearer sk-test"}


def test_llm_build_headers_without_key():
    svc = LLMService(api_key="")
    assert svc._build_headers() == {}


def test_llm_inject_system_prompt_with_di():
    svc = LLMService(default_system_prompt="Custom NLP prompt")
    result = svc._inject_system_prompt([{"role": "user", "content": "hi"}])
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "Custom NLP prompt"


def test_llm_inject_system_prompt_skipped_when_exists():
    svc = LLMService(default_system_prompt="Default")
    result = svc._inject_system_prompt([
        {"role": "system", "content": "Existing custom prompt"},
        {"role": "user", "content": "hi"},
    ])
    assert result[0]["content"] == "Existing custom prompt"
    assert len(result) == 2


def test_llm_inject_system_prompt_empty_disabled():
    svc = LLMService(default_system_prompt="")
    result = svc._inject_system_prompt([{"role": "user", "content": "hi"}])
    assert result[0]["role"] == "user"
    assert len(result) == 1


@pytest.mark.real_llm
@pytest.mark.asyncio
async def test_llm_chat_completions_http_error(monkeypatch):
    svc = LLMService(base_url="http://test", api_key="")

    async def mock_post(url, **kwargs):
        req = Request("POST", url)
        resp = await mock_response(status_code=502, text="Bad Gateway")
        raise HTTPStatusError("Bad Gateway", request=req, response=resp)

    monkeypatch.setattr(svc._client, "post", mock_post)
    with pytest.raises(RuntimeError, match="LLM backend error \\(502\\)"):
        await svc.chat_completions([{"role": "user", "content": "hi"}])


@pytest.mark.real_llm
@pytest.mark.asyncio
async def test_llm_chat_completions_connect_error(monkeypatch):
    svc = LLMService(base_url="http://test", api_key="")

    async def mock_post(url, **kwargs):
        raise ConnectError("Connection refused")

    monkeypatch.setattr(svc._client, "post", mock_post)
    with pytest.raises(RuntimeError, match="LLM backend unavailable"):
        await svc.chat_completions([{"role": "user", "content": "hi"}])


@pytest.mark.real_llm
@pytest.mark.asyncio
async def test_llm_chat_completions_model_override(monkeypatch):
    svc = LLMService(base_url="http://test", model="qwen2.5:7b")

    captured = {}

    async def capturing_post(url, json=None, **kwargs):
        captured["model"] = json.get("model")
        resp = await mock_response()
        return resp

    monkeypatch.setattr(svc._client, "post", capturing_post)
    await svc.chat_completions([{"role": "user", "content": "hi"}], model="gpt-4")
    assert captured["model"] == "gpt-4"


@pytest.mark.real_llm
@pytest.mark.asyncio
async def test_llm_chat_completions_default_model(monkeypatch):
    svc = LLMService(base_url="http://test", model="qwen2.5:7b")

    captured = {}

    async def capturing_post(url, json=None, **kwargs):
        captured["model"] = json.get("model")
        resp = await mock_response()
        return resp

    monkeypatch.setattr(svc._client, "post", capturing_post)
    await svc.chat_completions([{"role": "user", "content": "hi"}])
    assert captured["model"] == "qwen2.5:7b"
