"""
Osmosis DEX connector for Cosmos ecosystem
Handles Osmosis-specific API calls
"""
import asyncio
from typing import List, Dict, Any, Callable, Optional
from decimal import Decimal
from datetime import datetime
import aiohttp

from src.core.base_connector import BaseConnector
from src.core.data_models import PriceData, ExchangeType, Chain, PoolData
from src.config.settings import settings
import logging


logger = logging.getLogger(__name__)


class OsmosisConnector(BaseConnector):
    """Osmosis DEX connector"""
    
    BASE_URL = "https://api-osmosis.imperator.co"
    LCD_URL = "https://lcd.osmosis.zone"
    
    def __init__(self):
        super().__init__(
            exchange_name="Osmosis",
            exchange_type=ExchangeType.COSMOS_DEX,
            rate_limit=10
        )
    
    def _get_base_url(self) -> str:
        return self.BASE_URL
    
    async def get_price(self, symbol: str, pool_id: Optional[int] = None) -> PriceData:
        """Get current price for a token"""
        endpoint = f"/tokens/v2/{symbol}"
        
        data = await self._make_request("GET", endpoint)
        
        if not data:
            raise ValueError(f"No price data found for {symbol}")
        
        return PriceData(
            symbol=symbol,
            exchange=self.exchange_name,
            exchange_type=self.exchange_type,
            chain=Chain.OSMOSIS,
            price=Decimal(str(data[0]["price"])),
            volume_24h=Decimal(str(data[0].get("volume_24h", 0))),
            liquidity=Decimal(str(data[0].get("liquidity", 0))),
            timestamp=datetime.utcnow()
        )
    
    async def get_pool_data(self, pool_id: int) -> PoolData:
        """Get pool information"""
        endpoint = f"/pools/v2/{pool_id}"
        
        data = await self._make_request("GET", endpoint)
        
        return PoolData(
            pool_id=str(pool_id),
            protocol="Osmosis",
            chain=Chain.OSMOSIS,
            token0=data["pool_assets"][0]["token"]["denom"],
            token1=data["pool_assets"][1]["token"]["denom"],
            reserve0=Decimal(data["pool_assets"][0]["token"]["amount"]),
            reserve1=Decimal(data["pool_assets"][1]["token"]["amount"]),
            total_liquidity=Decimal(data.get("liquidity", 0)),
            volume_24h=Decimal(data.get("volume_24h", 0)),
            fee_tier=float(data.get("pool_params", {}).get("swap_fee", 0)),
            apy=float(data.get("apy", 0)),
            timestamp=datetime.utcnow()
        )
    
    async def get_all_pools(self) -> List[PoolData]:
        """Get all Osmosis pools"""
        endpoint = "/pools/v2/all"
        
        data = await self._make_request("GET", endpoint)
        
        pools = []
        for pool in data:
            try:
                pool_data = PoolData(
                    pool_id=str(pool["pool_id"]),
                    protocol="Osmosis",
                    chain=Chain.OSMOSIS,
                    token0=pool["pool_assets"][0]["token"]["denom"],
                    token1=pool["pool_assets"][1]["token"]["denom"],
                    reserve0=Decimal(pool["pool_assets"][0]["token"]["amount"]),
                    reserve1=Decimal(pool["pool_assets"][1]["token"]["amount"]),
                    total_liquidity=Decimal(pool.get("liquidity", 0)),
                    volume_24h=Decimal(pool.get("volume_24h", 0)),
                    fee_tier=float(pool.get("pool_params", {}).get("swap_fee", 0)),
                    apy=float(pool.get("apy", 0)),
                    timestamp=datetime.utcnow()
                )
                pools.append(pool_data)
            except Exception as e:
                logger.warning(f"Error parsing pool {pool.get('pool_id')}: {str(e)}")
                continue
        
        return pools
    
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Osmosis uses AMM, no traditional orderbook"""
        raise NotImplementedError("Osmosis uses AMM, no traditional orderbook")
    
    async def get_24h_volume(self, symbol: str) -> Decimal:
        """Get 24h volume for a token"""
        price_data = await self.get_price(symbol)
        return price_data.volume_24h
    
    async def subscribe_to_price_updates(self, symbols: List[str], callback: Callable) -> None:
        """Subscribe to price updates via polling"""
        async def poll_prices():
            while True:
                for symbol in symbols:
                    try:
                        price_data = await self.get_price(symbol)
                        await callback(price_data)
                    except Exception as e:
                        logger.error(f"Error polling Osmosis price for {symbol}: {str(e)}")
                
                await asyncio.sleep(10)  # Poll every 10 seconds
        
        asyncio.create_task(poll_prices())
