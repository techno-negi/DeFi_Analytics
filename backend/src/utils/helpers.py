"""
Utility helper functions
"""
import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timezone
import json


def calculate_hash(data: str, algorithm: str = "sha256") -> str:
    """Calculate hash of data"""
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data.encode('utf-8'))
    return hash_obj.hexdigest()


def create_signature(message: str, secret: str) -> str:
    """Create HMAC signature"""
    return hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def get_timestamp_ms() -> int:
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)


def decimal_to_float(obj: Any) -> Any:
    """Convert Decimal objects to float recursively"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with default value"""
    if denominator == 0:
        return default
    return numerator / denominator


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100


def parse_symbol(symbol: str) -> tuple[str, str]:
    """
    Parse trading pair symbol
    
    Examples:
        'BTC/USDT' -> ('BTC', 'USDT')
        'BTCUSDT' -> ('BTC', 'USDT')
    """
    if '/' in symbol:
        return tuple(symbol.split('/'))
    
    # Common quote currencies
    quotes = ['USDT', 'USDC', 'USD', 'BTC', 'ETH', 'BNB']
    
    for quote in quotes:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            return (base, quote)
    
    # Default: last 4 chars as quote
    return (symbol[:-4], symbol[-4:])


def format_large_number(num: float) -> str:
    """
    Format large numbers with K, M, B suffixes
    
    Examples:
        1500 -> '1.5K'
        1500000 -> '1.5M'
    """
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.2f}K"
    return f"{num:.2f}"


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: Dict) -> Dict:
    """Merge multiple dictionaries"""
    result = {}
    for d in dicts:
        result.update(d)
    return result


def get_utc_now() -> datetime:
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


def to_unix_timestamp(dt: datetime) -> int:
    """Convert datetime to unix timestamp"""
    return int(dt.timestamp())


def from_unix_timestamp(timestamp: int) -> datetime:
    """Convert unix timestamp to datetime"""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def sanitize_string(text: str, max_length: int = 100) -> str:
    """Sanitize string for safe storage/display"""
    # Remove control characters
    sanitized = ''.join(char for char in text if char.isprintable())
    # Truncate
    return sanitized[:max_length]


def is_valid_address(address: str) -> bool:
    """Check if string is valid Ethereum address"""
    if not address.startswith('0x'):
        return False
    if len(address) != 42:
        return False
    try:
        int(address, 16)
        return True
    except ValueError:
        return False


def calculate_slippage(
    expected_price: Decimal,
    actual_price: Decimal
) -> float:
    """Calculate slippage percentage"""
    if expected_price == 0:
        return 0.0
    
    slippage = abs((actual_price - expected_price) / expected_price) * 100
    return float(slippage)


def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff delay"""
    delay = min(base_delay * (2 ** attempt), max_delay)
    return delay


def retry_with_backoff(max_attempts: int = 3):
    """Decorator for retrying with exponential backoff"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    delay = exponential_backoff(attempt)
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
