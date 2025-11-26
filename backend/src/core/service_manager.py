"""
Service Manager for dependency injection and lifecycle management
"""
import asyncio
import logging
from typing import Optional

from src.storage.redis_manager import RedisManager
from src.storage.postgres_manager import PostgresManager
from src.storage.cache_manager import CacheManager
from src.connectors.cex.binance import BinanceConnector
from src.connectors.dex.uniswap import UniswapV3Connector
from src.connectors.cosmos.osmosis import OsmosisConnector
from src.analytics.arbitrage_detector import ArbitrageDetector
from src.analytics.yield_optimizer import YieldOptimizer
from src.analytics.risk_analyzer import RiskAnalyzer
from src.api.websocket_server import init_websocket_manager
from src.core.data_models import Chain
from src.config.settings import settings

logger = logging.getLogger(__name__)

class ServiceManager:
    _instance = None
    
    def __init__(self):
        # Storage
        self.redis_manager: Optional[RedisManager] = None
        self.postgres_manager: Optional[PostgresManager] = None
        self.cache_manager: Optional[CacheManager] = None
        
        # Connectors
        self.binance: Optional[BinanceConnector] = None
        self.uniswap: Optional[UniswapV3Connector] = None
        self.osmosis: Optional[OsmosisConnector] = None
        
        # Analytics
        self.arbitrage_detector: Optional[ArbitrageDetector] = None
        self.yield_optimizer: Optional[YieldOptimizer] = None
        self.risk_analyzer: Optional[RiskAnalyzer] = None
        
        # WebSocket
        self.ws_manager = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ServiceManager()
        return cls._instance

    async def initialize(self):
        """Initialize all services"""
        logger.info("Initializing services...")
        
        # Storage
        self.redis_manager = RedisManager()
        await self.redis_manager.connect()
        
        self.postgres_manager = PostgresManager()
        await self.postgres_manager.connect()
        
        self.cache_manager = CacheManager(self.redis_manager)
        
        # WebSocket manager
        self.ws_manager = init_websocket_manager(self.redis_manager)
        await self.ws_manager.start()
        
        # Connectors
        self.binance = BinanceConnector()
        await self.binance.connect()
        
        self.uniswap = UniswapV3Connector(Chain.ETHEREUM)
        await self.uniswap.connect()
        
        self.osmosis = OsmosisConnector()
        await self.osmosis.connect()
        
        # Analytics
        self.arbitrage_detector = ArbitrageDetector(
            self.redis_manager,
            self.cache_manager,
            min_profit_percent=settings.ARBITRAGE_MIN_PROFIT_PERCENT
        )
        
        self.yield_optimizer = YieldOptimizer(self.redis_manager)
        self.risk_analyzer = RiskAnalyzer(self.postgres_manager)
        
        logger.info("All services initialized successfully")

    async def cleanup(self):
        """Cleanup all services"""
        logger.info("Cleaning up services...")
        
        if self.ws_manager:
            await self.ws_manager.stop()
        
        if self.binance:
            await self.binance.disconnect()
        
        if self.uniswap:
            await self.uniswap.disconnect()
        
        if self.osmosis:
            await self.osmosis.disconnect()
        
        if self.redis_manager:
            await self.redis_manager.disconnect()
        
        if self.postgres_manager:
            await self.postgres_manager.disconnect()
        
        logger.info("Cleanup completed")
