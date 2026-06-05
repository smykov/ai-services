import asyncio

import pytest

from app.mcp.tools import dispatch, list_tools


def test_list_tools():
    tools = list_tools()
    assert len(tools) == 3
    names = {t["name"] for t in tools}
    assert names == {"transcribe_audio", "synthesize_speech", "extract_text"}


def test_tools_have_schemas():
    for tool in list_tools():
        assert "inputSchema" in tool
        assert "properties" in tool["inputSchema"]
        assert "required" in tool["inputSchema"]


def test_dispatch_unknown_tool():
    with pytest.raises(ValueError, match="Unknown tool"):
        asyncio.run(dispatch("nonexistent", {}))
