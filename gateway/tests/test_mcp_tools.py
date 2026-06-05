import asyncio

import pytest

from app.mcp.tools import dispatch, list_tools


def test_list_tools():
    tools = list_tools()
    names = {t["name"] for t in tools}
    assert len(tools) >= 4
    assert "transcribe_audio" in names
    assert "synthesize_speech" in names
    assert "extract_text" in names
    assert "preprocess_query" in names


def test_tools_have_schemas():
    for tool in list_tools():
        assert "inputSchema" in tool
        assert "properties" in tool["inputSchema"]
        assert "required" in tool["inputSchema"]


def test_dispatch_unknown_tool():
    with pytest.raises(ValueError, match="Unknown tool"):
        asyncio.run(dispatch("nonexistent", {}))


@pytest.mark.asyncio
async def test_dispatch_preprocess_query():
    result = await dispatch("preprocess_query", {
        "messages": [{"role": "user", "content": "test query"}],
    })
    assert "content" in result
    assert "usage" in result
    assert result["content"] == '{"intent": "test"}'


@pytest.mark.asyncio
async def test_dispatch_preprocess_query_with_temperature():
    result = await dispatch("preprocess_query", {
        "messages": [{"role": "user", "content": "test"}],
        "temperature": 0.8,
    })
    assert "content" in result

