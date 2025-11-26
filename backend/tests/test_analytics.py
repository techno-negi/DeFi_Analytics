"""
Tests for analytics engines
"""
import pytest
import asyncio
from decimal import Decimal
from datetime import datetime

from src.analytics.arbitrage_detector import ArbitrageDetector
from src.analytics.yield_optimizer import YieldOptimizer
from src.analytics.risk_analyzer import RiskAnalyzer
from src.core.data_models import PriceData, PoolData, Chain, ExchangeType
from src.storage.redis_manager import RedisManager
from src.storage.postgres_manager import PostgresManager
from src.storage.cache_manager import CacheManager


@pytest.fixture
async def redis_manager():
    """Create Redis manager for testing"""
    manager = RedisManager()
    await manager.connect()
    yield manager
    await manager.disconnect()


@pytest.fixture
async def postgres_manager():
    """Create PostgreSQL manager for testing"""
    manager = PostgresManager()
    await manager.connect()
    yield manager
    await manager.disconnect()


@pytest.fixture
def cache_manager(redis_manager):
    """Create cache manager for testing"""
    return CacheManager(redis_manager)


@pytest.mark.asyncio
async def test_arbitrage_detector_initialization(redis_manager, cache_manager):
    """Test arbitrage detector initialization"""
    detector = ArbitrageDetector(
        redis_manager,
        cache_manager,
        min_profit_percent=0.5
    )
    
    assert detector.min_profit_percent == 0.5
    assert detector.price_graph is not None


@pytest.mark.asyncio
async def test_arbitrage_detector_update_graph(redis_manager, cache_manager):
    """Test updating price graph"""
    detector = ArbitrageDetector(redis_manager, cache_manager)
    
    # Create sample price data
    price_data_list = [
        PriceData(
            symbol="BTC/USDT",
            exchange="Binance",
            exchange_type=ExchangeType.CEX,
            price=Decimal("50000"),
            volume_24h=Decimal("1000000"),
            timestamp=datetime.utcnow()
        ),
        PriceData(
            symbol="BTC/USDT",
            exchange="Coinbase",
            exchange_type=ExchangeType.CEX,
            price=Decimal("50100"),
            volume_24h=Decimal("800000"),
            timestamp=datetime.utcnow()
        )
    ]
    
    await detector.update_price_graph(price_data_list)
    
    assert detector.price_graph.number_of_nodes() > 0
    assert detector.price_graph.number_of_edges() > 0


@pytest.mark.asyncio
async def test_yield_optimizer_initialization(redis_manager):
    """Test yield optimizer initialization"""
    optimizer = YieldOptimizer(redis_manager)
    
    assert optimizer.protocol_risk_scores is not None
    assert "Aave" in optimizer.protocol_risk_scores


@pytest.mark.asyncio
async def test_yield_optimizer_analyze_opportunities(redis_manager):
    """Test analyzing yield opportunities"""
    optimizer = YieldOptimizer(redis_manager)
    
    # Create sample pool data
    pools = [
        PoolData(
            pool_id="pool_1",
            protocol="Aave",
            chain=Chain.ETHEREUM,
            token0="USDC",
            token1="DAI",
            reserve0=Decimal("1000000"),
            reserve1=Decimal("1000000"),
            total_liquidity=Decimal("2000000"),
            volume_24h=Decimal("100000"),
            fee_tier=0.01,
            apy=15.5,
            timestamp=datetime.utcnow()
        )
    ]
    
    opportunities = await optimizer.analyze_yield_opportunities(pools)
    
    assert len(opportunities) == 1
    assert opportunities[0].protocol_name == "Aave"
    assert opportunities[0].apy == 15.5


@pytest.mark.asyncio
async def test_risk_analyzer_initialization(postgres_manager):
    """Test risk analyzer initialization"""
    analyzer = RiskAnalyzer(postgres_manager)
    
    assert analyzer.audited_protocols is not None
    assert analyzer.exploit_history is not None


@pytest.mark.asyncio
async def test_risk_analyzer_assess_protocol_risk(postgres_manager):
    """Test risk assessment"""
    analyzer = RiskAnalyzer(postgres_manager)
    
    pool_data = PoolData(
        pool_id="pool_test",
        protocol="Aave",
        chain=Chain.ETHEREUM,
        token0="USDC",
        token1="DAI",
        reserve0=Decimal("5000000"),
        reserve1=Decimal("5000000"),
        total_liquidity=Decimal("10000000"),
        volume_24h=Decimal("500000"),
        fee_tier=0.01,
        apy=12.0,
        timestamp=datetime.utcnow()
    )
    
    risk_metrics = await analyzer.analyze_protocol_risk("Aave", pool_data)
    
    assert risk_metrics.protocol_name == "Aave"
    assert 0 <= risk_metrics.overall_risk_score <= 10
    assert risk_metrics.audit_status == True
    assert len(risk_metrics.recommendations) > 0


def test_calculate_confidence():
    """Test confidence calculation"""
    detector = ArbitrageDetector(None, None)
    
    # High profit, high liquidity
    confidence = detector._calculate_confidence(
        profit_percent=5.0,
        liquidity1=Decimal("100000"),
        liquidity2=Decimal("100000")
    )
    
    assert 0 <= confidence <= 1
    assert confidence > 0.5  # Should be high confidence


def test_calculate_risk():
    """Test risk calculation"""
    detector = ArbitrageDetector(None, None)
    
    # Same exchange, same chain = low risk
    risk = detector._calculate_risk(
        exchange1="Binance",
        exchange2="Binance",
        chain1=Chain.ETHEREUM,
        chain2=Chain.ETHEREUM
    )
    
    assert 0 <= risk <= 10
    assert risk < 5  # Should be relatively low risk
    
    # Different exchange, different chain = higher risk
    risk_cross = detector._calculate_risk(
        exchange1="Binance",
        exchange2="Uniswap_V3",
        chain1=Chain.ETHEREUM,
        chain2=Chain.BSC
    )
    
    assert risk_cross > risk  # Cross-chain should be riskier
