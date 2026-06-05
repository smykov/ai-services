from fastapi import HTTPException
import pytest

from app.core.auth import verify_api_key
from app.core.config import settings


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
