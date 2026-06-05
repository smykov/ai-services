import pytest


@pytest.mark.asyncio
async def test_mcp_initialize(client):
    resp = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"]["serverInfo"]["name"] == "ecosystem-ai-services"


@pytest.mark.asyncio
async def test_mcp_list_tools(client):
    resp = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
    })
    assert resp.status_code == 200
    tools = resp.json()["result"]["tools"]
    names = {t["name"] for t in tools}
    assert names == {"transcribe_audio", "synthesize_speech", "extract_text"}


@pytest.mark.asyncio
async def test_mcp_call_tool(client):
    resp = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "transcribe_audio",
            "arguments": {"audio_url": "http://example.com/test.wav"},
        },
    })
    assert resp.status_code == 200
    result = resp.json()["result"]
    content = result["content"][0]["text"]
    assert "pending" in content


@pytest.mark.asyncio
async def test_mcp_unknown_tool(client):
    resp = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "nonexistent",
            "arguments": {},
        },
    })
    assert resp.status_code == 200
    assert resp.json()["error"]["code"] == -32602


@pytest.mark.asyncio
async def test_mcp_unknown_method(client):
    resp = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 5,
        "method": "foobar",
    })
    assert resp.status_code == 200
    assert resp.json()["error"]["code"] == -32601
