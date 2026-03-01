"""Tests for admin/monitoring endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from cashu_mint.main import app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "mint" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_root_endpoint() -> None:
    """The /health endpoint (without /v1 prefix) should also be available."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_metrics_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/metrics")
    assert response.status_code == 200
    body = response.text
    assert "cashu_mint_total_issued" in body
    assert "cashu_mint_active_keysets" in body
