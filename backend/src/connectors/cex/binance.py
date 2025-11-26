"""
Binance CEX connector implementation
Handles Binance API integration with WebSocket support
"""
import asyncio
import json
import websockets
from typing import List, Dict, Any, Callable
from decimal import Decimal
from datetime import datetime
import hmac
import hashlib
from urllib.parse import urlencode

from src.core.base_connector import BaseConnector
from src.core.data_models import PriceData, ExchangeType
from src.config.settings import settings
import logging


logger = logging.getLogger(__name__)


class BinanceConnector(BaseConnector):
    """Binance exchange connector"""
    
    BASE_URL = "https://api.binance.com"
    WS_URL = "wss://stream.binance.com:9443/ws"
    
    def __init__(self):
        super().__init__(
            exchange_name="Binance",
            exchange_type=ExchangeType.CEX,
            api_key=settings.BINANCE_API_KEY,
            secret_key=settings.BINANCE_SECRET_KEY,
            rate_limit=10
        )
        self._ws_connections: Dict[str, Any] = {}
    
    def _get_base_url(self) -> str:
        return self.BASE_URL
    
    async def get_price(self, symbol: str) -> PriceData:
        """Get current price for a symbol"""
        normalized_symbol = self._normalize_symbol(symbol)
        
        endpoint = "/api/v3/ticker/bookTicker"
        params = {"symbol": normalized_symbol}
        
        data = await self._make_request("GET", endpoint, params=params)
        
        return PriceData(
            symbol=symbol,
            exchange=self.exchange_name,
            exchange_type=self.exchange_type,
            price=Decimal(data["bidPrice"]),
            bid=Decimal(data["bidPrice"]),
            ask=Decimal(data["askPrice"]),
            volume_24h=await self.get_24h_volume(symbol),
            timestamp=datetime.utcnow()
        )
    
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get orderbook for a symbol"""
        normalized_symbol = self._normalize_symbol(symbol)
        
        endpoint = "/api/v3/depth"
        params = {"symbol": normalized_symbol, "limit": depth}
        
        data = await self._make_request("GET", endpoint, params=params)
        
        return {
            "bids": [(Decimal(price), Decimal(qty)) for price, qty in data["bids"]],
            "asks": [(Decimal(price), Decimal(qty)) for price, qty in data["asks"]],
            "timestamp": datetime.utcnow()
        }
    
    async def get_24h_volume(self, symbol: str) -> Decimal:
        """Get 24h trading volume"""
        normalized_symbol = self._normalize_symbol(symbol)
        
        endpoint = "/api/v3/ticker/24hr"
        params = {"symbol": normalized_symbol}
        
        data = await self._make_request("GET", endpoint, params=params)
        
        return Decimal(data["volume"])
    
    async def subscribe_to_price_updates(
        self,
        symbols: List[str],
        callback: Callable
    ) -> None:
        """Subscribe to real-time price updates via WebSocket"""
        streams = [f"{self._normalize_symbol(s).lower()}@bookTicker" for s in symbols]
        stream_url = f"{self.WS_URL}/{'/'.join(streams)}"
        
        async def handle_websocket():
            while True:
                try:
                    async with websockets.connect(stream_url) as ws:
                        logger.info(f"WebSocket connected to Binance for {len(symbols)} symbols")
                        
                        while True:
                            message = await ws.recv()
                            data = json.loads(message)
                            
                            # Handle single or multiple streams
                            if "stream" in data:
                                data = data["data"]
                            
                            price_data = PriceData(
                                symbol=data["s"],
                                exchange=self.exchange_name,
                                exchange_type=self.exchange_type,
                                price=Decimal(data["b"]),
                                bid=Decimal(data["b"]),
                                ask=Decimal(data["a"]),
                                volume_24h=Decimal(0),  # Not provided in ticker
                                timestamp=datetime.utcnow()
                            )
                            
                            await callback(price_data)
                            
                except websockets.ConnectionClosed:
                    logger.warning("Binance WebSocket connection closed, reconnecting...")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Error in Binance WebSocket: {str(e)}")
                    await asyncio.sleep(5)
        
        asyncio.create_task(handle_websocket())
    
    def _sign_request(self, params: Dict[str, Any]) -> str:
        """Sign request with HMAC SHA256"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def get_account_balance(self) -> Dict[str, Decimal]:
        """Get account balances (authenticated endpoint)"""
        if not self.api_key or not self.secret_key:
            raise ValueError("API key and secret required for account operations")
        
        endpoint = "/api/v3/account"
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        
        params = {"timestamp": timestamp}
        params["signature"] = self._sign_request(params)
        
        headers = {"X-MBX-APIKEY": self.api_key}
        
        data = await self._make_request("GET", endpoint, params=params, headers=headers)
        
        balances = {}
        for balance in data["balances"]:
            asset = balance["asset"]
            free = Decimal(balance["free"])
            locked = Decimal(balance["locked"])
            if free > 0 or locked > 0:
                balances[asset] = free + locked
        
        return balances
