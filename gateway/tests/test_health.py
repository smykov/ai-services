import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_metrics(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "ecosystem-ai-services"
    assert data["uptime_seconds"] >= 0
