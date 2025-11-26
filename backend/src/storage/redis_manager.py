"""
Redis Manager - Handles Redis connections and TimeSeries operations
Real-time data storage with automatic expiration
"""
import asyncio
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.commands.timeseries import TimeSeries
from decimal import Decimal

from src.config.settings import settings
import logging


logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis manager with TimeSeries support for financial data
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connected = False
        
    async def connect(self):
        """Establish Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self._connected = False
            logger.info("Disconnected from Redis")
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """
        Set a key-value pair with optional expiration
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if dict/list)
            expire: Expiration time in seconds
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            
            await self.redis_client.set(key, value)
            
            if expire:
                await self.redis_client.expire(key, expire)
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting Redis key {key}: {str(e)}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        try:
            value = await self.redis_client.get(key)
            
            if value is None:
                return None
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.error(f"Error getting Redis key {key}: {str(e)}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete a key"""
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting Redis key {key}: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking Redis key existence {key}: {str(e)}")
            return False
    
    # ===== TimeSeries Operations =====
    
    async def ts_create(
        self,
        key: str,
        retention_ms: Optional[int] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Create a new TimeSeries
        
        Args:
            key: TimeSeries key
            retention_ms: Retention period in milliseconds
            labels: Labels for the TimeSeries
        """
        try:
            retention = retention_ms or settings.REDIS_TIMESERIES_RETENTION
            
            # Check if already exists
            if await self.exists(key):
                return True
            
            # Create TimeSeries
            command = ["TS.CREATE", key, "RETENTION", retention]
            
            if labels:
                for label_key, label_value in labels.items():
                    command.extend(["LABELS", label_key, label_value])
            
            await self.redis_client.execute_command(*command)
            
            logger.debug(f"Created TimeSeries: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating TimeSeries {key}: {str(e)}")
            return False
    
    async def ts_add(
        self,
        key: str,
        timestamp: Optional[int] = None,
        value: float = 0.0,
        retention_ms: Optional[int] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Add a sample to TimeSeries (creates if not exists)
        
        Args:
            key: TimeSeries key
            timestamp: Unix timestamp in milliseconds (None = current time)
            value: Value to add
            retention_ms: Retention period
            labels: Labels (used if creating new series)
        """
        try:
            if timestamp is None:
                timestamp = int(datetime.utcnow().timestamp() * 1000)
            
            # Add sample (creates if not exists with ON_DUPLICATE LAST)
            command = ["TS.ADD", key, timestamp, value]
            
            if retention_ms:
                command.extend(["RETENTION", retention_ms])
            
            if labels:
                command.append("LABELS")
                for label_key, label_value in labels.items():
                    command.extend([label_key, label_value])
            
            await self.redis_client.execute_command(*command)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding to TimeSeries {key}: {str(e)}")
            return False
    
    async def ts_range(
        self,
        key: str,
        from_timestamp: int,
        to_timestamp: int,
        aggregation_type: Optional[str] = None,
        bucket_size_ms: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """
        Query TimeSeries data range
        
        Args:
            key: TimeSeries key
            from_timestamp: Start timestamp (ms)
            to_timestamp: End timestamp (ms)
            aggregation_type: avg, sum, min, max, etc.
            bucket_size_ms: Bucket size for aggregation
        """
        try:
            command = ["TS.RANGE", key, from_timestamp, to_timestamp]
            
            if aggregation_type and bucket_size_ms:
                command.extend(["AGGREGATION", aggregation_type, bucket_size_ms])
            
            result = await self.redis_client.execute_command(*command)
            
            # Parse result [(timestamp, value), ...]
            return [(int(ts), float(val)) for ts, val in result]
            
        except Exception as e:
            logger.error(f"Error querying TimeSeries range {key}: {str(e)}")
            return []
    
    async def ts_get(self, key: str) -> Optional[Tuple[int, float]]:
        """Get latest sample from TimeSeries"""
        try:
            result = await self.redis_client.execute_command("TS.GET", key)
            
            if result:
                return (int(result[0]), float(result[1]))
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting TimeSeries sample {key}: {str(e)}")
            return None
    
    async def ts_mget(
        self,
        filters: List[str],
        with_labels: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get latest samples from multiple TimeSeries matching filters
        
        Args:
            filters: List of label filters (e.g., ["exchange=Binance", "symbol=BTC/USDT"])
            with_labels: Include labels in response
        """
        try:
            command = ["TS.MGET"]
            
            if with_labels:
                command.append("WITHLABELS")
            
            command.append("FILTER")
            command.extend(filters)
            
            result = await self.redis_client.execute_command(*command)
            
            # Parse result
            parsed = []
            for item in result:
                key = item[0]
                labels = dict(zip(item[1][::2], item[1][1::2])) if with_labels and len(item) > 2 else {}
                timestamp, value = item[-1]
                
                parsed.append({
                    "key": key,
                    "labels": labels,
                    "timestamp": int(timestamp),
                    "value": float(value)
                })
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error in TS.MGET: {str(e)}")
            return []
    
    # ===== Pub/Sub Operations =====
    
    async def publish(self, channel: str, message: Any) -> int:
        """
        Publish message to channel
        
        Returns: Number of subscribers that received the message
        """
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message, default=str)
            
            result = await self.redis_client.publish(channel, message)
            return result
            
        except Exception as e:
            logger.error(f"Error publishing to channel {channel}: {str(e)}")
            return 0
    
    async def subscribe(self, channel: str, callback):
        """
        Subscribe to channel and call callback for each message
        
        Args:
            channel: Channel name
            callback: Async function to call with message
        """
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel)
            
            logger.info(f"Subscribed to Redis channel: {channel}")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                    except json.JSONDecodeError:
                        data = message['data']
                    
                    await callback(data)
                    
        except Exception as e:
            logger.error(f"Error in Redis subscription to {channel}: {str(e)}")
    
    # ===== Sorted Set Operations (for leaderboards, rankings) =====
    
    async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """Add members to sorted set"""
        try:
            return await self.redis_client.zadd(key, mapping)
        except Exception as e:
            logger.error(f"Error in ZADD {key}: {str(e)}")
            return 0
    
    async def zrange(
        self,
        key: str,
        start: int = 0,
        end: int = -1,
        desc: bool = False,
        withscores: bool = False
    ) -> List:
        """Get range from sorted set"""
        try:
            return await self.redis_client.zrange(
                key,
                start,
                end,
                desc=desc,
                withscores=withscores
            )
        except Exception as e:
            logger.error(f"Error in ZRANGE {key}: {str(e)}")
            return []
    
    @property
    def is_connected(self) -> bool:
        return self._connected
