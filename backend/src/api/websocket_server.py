"""
WebSocket Server - Real-time data streaming
Broadcasts price updates, arbitrage opportunities, and alerts
"""
import asyncio
import json
from typing import Set, Dict, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

from src.storage.redis_manager import RedisManager
from src.core.data_models import PriceData, ArbitrageOpportunity
import logging


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Set[str]] = defaultdict(set)
        self._message_queue = asyncio.Queue(maxsize=10000)
        self._broadcast_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start background tasks"""
        self._broadcast_task = asyncio.create_task(self._broadcast_worker())
        
        # Subscribe to Redis channels
        asyncio.create_task(self._subscribe_to_redis_channels())
        
        logger.info("WebSocket ConnectionManager started")
    
    async def stop(self):
        """Stop background tasks"""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        logger.info("WebSocket ConnectionManager stopped")
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def subscribe(self, websocket: WebSocket, channels: list):
        """Subscribe connection to specific channels"""
        for channel in channels:
            self.subscriptions[websocket].add(channel)
        
        logger.debug(f"WebSocket subscribed to channels: {channels}")
    
    async def unsubscribe(self, websocket: WebSocket, channels: list):
        """Unsubscribe connection from channels"""
        for channel in channels:
            self.subscriptions[websocket].discard(channel)
        
        logger.debug(f"WebSocket unsubscribed from channels: {channels}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
            await self.disconnect(websocket)
    
    async def broadcast(self, message: dict, channel: str = "all"):
        """Queue message for broadcasting"""
        try:
            self._message_queue.put_nowait({
                "message": message,
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat()
            })
        except asyncio.QueueFull:
            logger.warning("Broadcast queue full, dropping message")
    
    async def _broadcast_worker(self):
        """Background worker that processes broadcast queue"""
        while True:
            try:
                item = await self._message_queue.get()
                message = item["message"]
                channel = item["channel"]
                
                # Send to subscribed connections
                disconnected = set()
                
                for websocket in self.active_connections:
                    # Check if connection is subscribed to this channel
                    if channel == "all" or channel in self.subscriptions.get(websocket, set()):
                        try:
                            await websocket.send_json(message)
                        except WebSocketDisconnect:
                            disconnected.add(websocket)
                        except Exception as e:
                            logger.error(f"Error broadcasting to WebSocket: {str(e)}")
                            disconnected.add(websocket)
                
                # Clean up disconnected
                for ws in disconnected:
                    await self.disconnect(ws)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broadcast worker: {str(e)}")
                await asyncio.sleep(1)
    
    async def _subscribe_to_redis_channels(self):
        """Subscribe to Redis Pub/Sub channels"""
        async def handle_price_updates(message):
            """Handle price update messages from Redis"""
            await self.broadcast({
                "type": "price_update",
                "data": message
            }, channel="prices")
        
        async def handle_arbitrage_alerts(message):
            """Handle arbitrage alert messages from Redis"""
            await self.broadcast({
                "type": "arbitrage_alert",
                "data": message
            }, channel="arbitrage")
        
        async def handle_yield_updates(message):
            """Handle yield update messages from Redis"""
            await self.broadcast({
                "type": "yield_update",
                "data": message
            }, channel="yield")
        
        # Subscribe to channels
        asyncio.create_task(
            self.redis_manager.subscribe("price_updates", handle_price_updates)
        )
        asyncio.create_task(
            self.redis_manager.subscribe("arbitrage_alerts", handle_arbitrage_alerts)
        )
        asyncio.create_task(
            self.redis_manager.subscribe("yield_updates", handle_yield_updates)
        )
        
        logger.info("Subscribed to Redis Pub/Sub channels")
    
    async def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "queue_size": self._message_queue.qsize(),
            "subscriptions": {
                channel: sum(1 for subs in self.subscriptions.values() if channel in subs)
                for channel in {"prices", "arbitrage", "yield", "all"}
            }
        }


# Global connection manager
manager: Optional[ConnectionManager] = None


def init_websocket_manager(redis_manager: RedisManager):
    """Initialize WebSocket manager"""
    global manager
    manager = ConnectionManager(redis_manager)
    return manager


async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint handler"""
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "message": "Connected to DeFi Analytics WebSocket",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "subscribe":
                channels = data.get("channels", [])
                await manager.subscribe(websocket, channels)
                await manager.send_personal_message({
                    "type": "subscribed",
                    "channels": channels
                }, websocket)
            
            elif message_type == "unsubscribe":
                channels = data.get("channels", [])
                await manager.unsubscribe(websocket, channels)
                await manager.send_personal_message({
                    "type": "unsubscribed",
                    "channels": channels
                }, websocket)
            
            elif message_type == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            
            else:
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }, websocket)
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await manager.disconnect(websocket)
