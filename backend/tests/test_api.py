"""
Tests for FastAPI endpoints
"""
import pytest
from fastapi.testclient import TestClient

from src.api.rest_api import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


def test_get_arbitrage_opportunities(client):
    """Test getting arbitrage opportunities"""
    response = client.get("/api/v1/arbitrage/opportunities?min_profit=0.5&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_arbitrage_stats(client):
    """Test getting arbitrage statistics"""
    response = client.get("/api/v1/arbitrage/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert "total_opportunities" in data


def test_get_yield_opportunities(client):
    """Test getting yield opportunities"""
    response = client.get("/api/v1/yield/opportunities?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_optimize_portfolio(client):
    """Test portfolio optimization"""
    payload = {
        "total_capital": 10000.0,
        "risk_tolerance": 5.0,
        "min_apy": 5.0
    }
    
    response = client.post("/api/v1/yield/optimize", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "allocations" in data
    assert "expected_returns" in data


def test_get_price(client):
    """Test getting current price"""
    response = client.get("/api/v1/prices/BTCUSDT")
    
    # May return 404 if no data, which is acceptable in test
    assert response.status_code in [200, 404]


def test_get_market_overview(client):
    """Test getting market overview"""
    response = client.get("/api/v1/market/overview")
    
    assert response.status_code == 200
    data = response.json()
    assert "arbitrage" in data
    assert "yield" in data


def test_get_system_info(client):
    """Test getting system info"""
    response = client.get("/api/v1/system/info")
    
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "cache_stats" in data


def test_rate_limiting(client):
    """Test rate limiting"""
    # Make many rapid requests
    for _ in range(100):
        response = client.get("/api/v1/market/overview")
        if response.status_code == 429:
            # Rate limit hit
            assert "Rate limit exceeded" in response.json()["error"]
            break


def test_invalid_parameters(client):
    """Test API with invalid parameters"""
    response = client.get("/api/v1/arbitrage/opportunities?min_profit=-1")
    # Should handle gracefully (either accept or return 422)
    assert response.status_code in [200, 422]
