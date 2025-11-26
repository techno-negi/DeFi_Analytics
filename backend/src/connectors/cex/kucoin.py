"""
KuCoin CEX connector implementation
Handles KuCoin API integration with WebSocket support
Updated to latest API (v1 endpoints, dynamic WS token, proper auth)
"""
import asyncio
import json
import time
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

class KucoinConnector(BaseConnector):
    """KuCoin exchange connector"""
    BASE_URL = "https://api.kucoin.com"

    def __init__(self):
        super().__init__(
            exchange_name="KuCoin",
            exchange_type=ExchangeType.CEX,
            api_key=settings.KUCOIN_API_KEY,  # Updated to uppercase for consistency
            secret_key=settings.KUCOIN_SECRET_KEY,
            passphrase=settings.KUCOIN_PASSPHRASE,  # New: API passphrase
            rate_limit=10
        )
        self._ws_connections: Dict[str, Any] = {}

    def _get_base_url(self) -> str:
        return self.BASE_URL

    async def _make_authenticated_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, body: Any = None) -> Dict[str, Any]:
        """Helper for authenticated requests with proper signing"""
        if not self.api_key or not self.secret_key or not self.passphrase:
            raise ValueError("API key, secret, and passphrase required for authenticated operations")

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        body_str = json.dumps(body) if body else ""
        query_str = urlencode(params) if params else ""
        message = timestamp + method + endpoint + query_str + body_str

        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "KC-API-KEY": self.api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }

        return await self._make_request(method, endpoint, params=params, body=body, headers=headers)

    async def get_price(self, symbol: str) -> PriceData:
        """Get current price for a symbol"""
        normalized_symbol = self._normalize_symbol(symbol)
        endpoint = "/api/v1/market/orderbook/level1"  # Latest for snapshot ticker
        data = await self._make_request("GET", endpoint, params={"symbol": normalized_symbol})
        return PriceData(
            symbol=symbol,
            exchange=self.exchange_name,
            exchange_type=self.exchange_type,
            price=Decimal(data["price"]),
            bid=Decimal(data["bestBid"]),
            ask=Decimal(data["bestAsk"]),
            volume_24h=await self.get_24h_volume(symbol),
            timestamp=datetime.utcnow()
        )

    async def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get orderbook for a symbol"""
        normalized_symbol = self._normalize_symbol(symbol)
        endpoint = "/api/v1/market/orderbook/level2"
        params = {"symbol": normalized_symbol, "size": depth}  # 'size' param in latest
        data = await self._make_request("GET", endpoint, params=params)
        return {
            "bids": [(Decimal(bid[0]), Decimal(bid[1])) for bid in data["bids"][:depth]],
            "asks": [(Decimal(ask[0]), Decimal(ask[1])) for ask in data["asks"][:depth]],
            "timestamp": datetime.utcnow()
        }

    async def get_24h_volume(self, symbol: str) -> Decimal:
        """Get 24h trading volume"""
        normalized_symbol = self._normalize_symbol(symbol)
        endpoint = "/api/v1/market/stats"
        params = {"symbol": normalized_symbol}
        data = await self._make_request("GET", endpoint, params=params)
        return Decimal(data["vol"])  # 'vol' for base volume

    async def get_account_balance(self) -> Dict[str, Decimal]:
        """Get account balances (authenticated endpoint)"""
        endpoint = "/api/v1/accounts"
        data = await self._make_authenticated_request("GET", endpoint)
        balances = {}
        for balance in data:
            asset = balance["currency"]
            available = Decimal(balance["available"])
            holds = Decimal(balance["holds"])
            if available > 0 or holds > 0:
                balances[asset] = available + holds
        return balances

    async def _get_websocket_token(self) -> str:
        """Fetch dynamic WS token for public spot"""
        endpoint = "/api/v1/bullet-public"
        response = await self._make_request("POST", endpoint)
        data = response.get("data", {})
        token = data.get("token")
        if not token:
            raise ValueError("Failed to fetch WS token")
        return token, data.get("instanceServers", [{}])[0].get("endpoint", "wss://ws-api-spot.kucoin.com")

    async def subscribe_to_price_updates(
        self,
        symbols: List[str],
        callback: Callable[[PriceData], Any]
    ) -> None:
        """Subscribe to real-time price updates via WebSocket"""
        normalized_symbols = [self._normalize_symbol(s).upper() for s in symbols]  # KuCoin uses UPPER
        topics = [f"/market/bookTicker:{sym}" for sym in normalized_symbols]

        async def handle_websocket():
            while True:
                try:
                    token, ws_host = await self._get_websocket_token()
                    stream_url = f"{ws_host}?token={token}"
                    logger.info(f"Connecting to KuCoin WS: {stream_url} for {len(topics)} symbols")

                    async with websockets.connect(stream_url) as ws:
                        # Subscribe
                        subscribe_msg = {
                            "id": int(time.time() * 1000),
                            "type": "subscribe",
                            "topic": topics,  # Batch subscribe to multiple
                            "response": True
                        }
                        await ws.send(json.dumps(subscribe_msg))
                        logger.info(f"Subscribed to KuCoin topics: {topics}")

                        async for message in ws:
                            data = json.loads(message)
                            if data.get("type") == "message" and "topic" in data and "data" in data:
                                topic_data = data["data"]
                                symbol = topic_data["s"]
                                price_data = PriceData(
                                    symbol=symbol,
                                    exchange=self.exchange_name,
                                    exchange_type=self.exchange_type,
                                    price=Decimal(topic_data["b"]) if "b" in topic_data else Decimal(topic_data["c"]),  # Best bid or close
                                    bid=Decimal(topic_data["b"]),
                                    ask=Decimal(topic_data["a"]),
                                    volume_24h=Decimal("0"),  # Not in bookTicker; fetch separately if needed
                                    timestamp=datetime.utcnow()
                                )
                                await callback(price_data)
                            elif data.get("type") == "pong":
                                logger.debug("Received pong")
                            # Handle welcome/ack/subscribe response if needed

                            # Send ping every 30s for keep-alive
                            await asyncio.sleep(30)
                            await ws.send(json.dumps({"id": int(time.time() * 1000), "type": "ping"}))

                except websockets.ConnectionClosed:
                    logger.warning("KuCoin WebSocket connection closed, reconnecting in 5s...")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Error in KuCoin WebSocket: {str(e)}")
                    await asyncio.sleep(5)

        asyncio.create_task(handle_websocket())