"""
Tests for exchange connectors
"""
import pytest
import asyncio
from decimal import Decimal

from src.connectors.cex.binance import BinanceConnector
from src.connectors.dex.uniswap import UniswapV3Connector
from src.connectors.cosmos.osmosis import OsmosisConnector
from src.core.data_models import Chain


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_binance_connector_initialization():
    """Test Binance connector initialization"""
    connector = BinanceConnector()
    
    assert connector.exchange_name == "Binance"
    assert connector.BASE_URL == "https://api.binance.com"
    assert not connector.is_connected


@pytest.mark.asyncio
async def test_binance_connection():
    """Test Binance connection"""
    async with BinanceConnector() as connector:
        assert connector.is_connected
        assert connector.session is not None


@pytest.mark.asyncio
async def test_binance_get_price():
    """Test fetching price from Binance"""
    async with BinanceConnector() as connector:
        price_data = await connector.get_price("BTCUSDT")
        
        assert price_data.symbol == "BTCUSDT"
        assert price_data.exchange == "Binance"
        assert isinstance(price_data.price, Decimal)
        assert price_data.price > 0
        assert price_data.bid is not None
        assert price_data.ask is not None


@pytest.mark.asyncio
async def test_binance_get_orderbook():
    """Test fetching orderbook from Binance"""
    async with BinanceConnector() as connector:
        orderbook = await connector.get_orderbook("BTCUSDT", depth=10)
        
        assert "bids" in orderbook
        assert "asks" in orderbook
        assert len(orderbook["bids"]) <= 10
        assert len(orderbook["asks"]) <= 10
        
        # Check format
        if orderbook["bids"]:
            bid = orderbook["bids"][0]
            assert len(bid) == 2  # (price, quantity)
            assert isinstance(bid[0], Decimal)
            assert isinstance(bid[1], Decimal)


@pytest.mark.asyncio
async def test_uniswap_connector_initialization():
    """Test Uniswap V3 connector initialization"""
    connector = UniswapV3Connector(Chain.ETHEREUM)
    
    assert connector.exchange_name == "Uniswap_V3"
    assert connector.chain == Chain.ETHEREUM
    assert connector.w3 is not None


@pytest.mark.asyncio
async def test_osmosis_connector_initialization():
    """Test Osmosis connector initialization"""
    connector = OsmosisConnector()
    
    assert connector.exchange_name == "Osmosis"
    assert connector.BASE_URL == "https://api-osmosis.imperator.co"


@pytest.mark.asyncio
async def test_osmosis_get_all_pools():
    """Test fetching all pools from Osmosis"""
    async with OsmosisConnector() as connector:
        pools = await connector.get_all_pools()
        
        assert isinstance(pools, list)
        assert len(pools) > 0
        
        # Check first pool structure
        pool = pools[0]
        assert hasattr(pool, 'pool_id')
        assert hasattr(pool, 'protocol')
        assert hasattr(pool, 'chain')
        assert pool.protocol == "Osmosis"
        assert pool.chain == Chain.OSMOSIS


@pytest.mark.asyncio
async def test_connector_error_handling():
    """Test connector error handling for invalid symbols"""
    async with BinanceConnector() as connector:
        with pytest.raises(Exception):
            await connector.get_price("INVALIDSYMBOL12345")
