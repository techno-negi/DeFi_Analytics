"""
Base connector class for exchange integrations
Provides common interface and functionality
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import asyncio
import aiohttp
from datetime import datetime
from decimal import Decimal
import logging

from src.core.data_models import PriceData, ExchangeType
from src.core.exceptions import ConnectionError, APIError, RateLimitError


logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Base class for all exchange connectors"""
    
    def __init__(
        self,
        exchange_name: str,
        exchange_type: ExchangeType,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        rate_limit: int = 10
    ):
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.api_key = api_key
        self.secret_key = secret_key
        self.rate_limit = rate_limit
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = asyncio.Semaphore(rate_limit)
        self._is_connected = False
        
        logger.info(f"Initialized {exchange_name} connector")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Establish connection to exchange"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            self._is_connected = True
            logger.info(f"Connected to {self.exchange_name}")
    
    async def disconnect(self) -> None:
        """Close connection to exchange"""
        if self.session:
            await self.session.close()
            self._is_connected = False
            logger.info(f"Disconnected from {self.exchange_name}")
    
    @abstractmethod
    async def get_price(self, symbol: str) -> PriceData:
        """Get current price for a symbol"""
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get orderbook for a symbol"""
        pass
    
    @abstractmethod
    async def get_24h_volume(self, symbol: str) -> Decimal:
        """Get 24h trading volume"""
        pass
    
    @abstractmethod
    async def subscribe_to_price_updates(self, symbols: List[str], callback):
        """Subscribe to real-time price updates via WebSocket"""
        pass
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Any:
        """Make HTTP request with rate limiting and error handling"""
        if not self.session:
            await self.connect()
        
        async with self._rate_limiter:
            try:
                url = f"{self._get_base_url()}{endpoint}"
                
                async with self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=headers or {}
                ) as response:
                    if response.status == 429:
                        raise RateLimitError(f"Rate limit exceeded for {self.exchange_name}")
                    
                    if response.status >= 400:
                        error_text = await response.text()
                        raise APIError(
                            f"API error from {self.exchange_name}: {response.status} - {error_text}"
                        )
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                raise ConnectionError(f"Connection error to {self.exchange_name}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error in {self.exchange_name}: {str(e)}")
                raise
    
    @abstractmethod
    def _get_base_url(self) -> str:
        """Get base URL for API requests"""
        pass
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol format (override in subclasses if needed)"""
        return symbol.upper().replace("-", "").replace("/", "")
    
    @property
    def is_connected(self) -> bool:
        """Check if connector is connected"""
        return self._is_connected
