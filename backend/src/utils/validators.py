"""
Input validation utilities
"""
from typing import Any, List, Optional
from decimal import Decimal
from pydantic import BaseModel, validator, ValidationError
import re


class PriceValidator(BaseModel):
    """Validate price data"""
    price: Decimal
    volume: Decimal
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v
    
    @validator('volume')
    def volume_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Volume must be non-negative')
        return v


class AddressValidator:
    """Validate blockchain addresses"""
    
    @staticmethod
    def validate_ethereum_address(address: str) -> bool:
        """Validate Ethereum address format"""
        if not address:
            return False
        
        # Check format
        if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            return False
        
        return True
    
    @staticmethod
    def validate_cosmos_address(address: str, prefix: str = "cosmos") -> bool:
        """Validate Cosmos address format"""
        if not address:
            return False
        
        # Cosmos addresses start with prefix (cosmos, osmo, etc.)
        if not address.startswith(prefix):
            return False
        
        # Check length (bech32 format)
        if len(address) < 39 or len(address) > 45:
            return False
        
        return True


class SymbolValidator:
    """Validate trading symbols"""
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """Validate trading pair symbol"""
        if not symbol:
            return False
        
        # Allow alphanumeric and /
        if not re.match(r'^[A-Z0-9/]+$', symbol):
            return False
        
        return True
    
    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """Normalize symbol to standard format"""
        symbol = symbol.upper().strip()
        
        # Convert BTCUSDT to BTC/USDT if needed
        if '/' not in symbol and len(symbol) > 4:
            # Try to split at common quote currencies
            for quote in ['USDT', 'USDC', 'USD', 'BTC', 'ETH']:
                if symbol.endswith(quote):
                    base = symbol[:-len(quote)]
                    return f"{base}/{quote}"
        
        return symbol


class RangeValidator:
    """Validate numeric ranges"""
    
    @staticmethod
    def validate_percentage(value: float, min_val: float = 0.0, max_val: float = 100.0) -> bool:
        """Validate percentage value"""
        return min_val <= value <= max_val
    
    @staticmethod
    def validate_positive(value: float) -> bool:
        """Validate positive number"""
        return value > 0
    
    @staticmethod
    def validate_non_negative(value: float) -> bool:
        """Validate non-negative number"""
        return value >= 0
    
    @staticmethod
    def validate_risk_score(score: float) -> bool:
        """Validate risk score (0-10 scale)"""
        return 0 <= score <= 10


class APIRequestValidator:
    """Validate API request parameters"""
    
    @staticmethod
    def validate_pagination(page: int, limit: int, max_limit: int = 200) -> tuple[int, int]:
        """
        Validate and sanitize pagination parameters
        
        Returns:
            Tuple of (validated_page, validated_limit)
        """
        page = max(1, page)
        limit = max(1, min(limit, max_limit))
        return (page, limit)
    
    @staticmethod
    def validate_time_range(
        start_time: Optional[int],
        end_time: Optional[int],
        max_range_days: int = 90
    ) -> bool:
        """Validate time range"""
        if start_time and end_time:
            if start_time > end_time:
                return False
            
            # Check max range
            range_seconds = end_time - start_time
            max_range_seconds = max_range_days * 24 * 60 * 60
            
            if range_seconds > max_range_seconds:
                return False
        
        return True


def validate_arbitrage_params(
    min_profit: float,
    max_slippage: float,
    min_liquidity: float
) -> dict:
    """
    Validate arbitrage detection parameters
    
    Returns:
        Dictionary with validation results and sanitized values
    """
    errors = []
    
    # Validate min_profit (0.1% to 50%)
    if not (0.1 <= min_profit <= 50.0):
        errors.append("min_profit must be between 0.1 and 50.0")
        min_profit = max(0.1, min(min_profit, 50.0))
    
    # Validate max_slippage (0% to 10%)
    if not (0.0 <= max_slippage <= 10.0):
        errors.append("max_slippage must be between 0.0 and 10.0")
        max_slippage = max(0.0, min(max_slippage, 10.0))
    
    # Validate min_liquidity (must be positive)
    if min_liquidity < 0:
        errors.append("min_liquidity must be non-negative")
        min_liquidity = 0
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "params": {
            "min_profit": min_profit,
            "max_slippage": max_slippage,
            "min_liquidity": min_liquidity
        }
    }


def validate_portfolio_allocation(allocations: dict, total_capital: Decimal) -> dict:
    """
    Validate portfolio allocation parameters
    
    Returns:
        Dictionary with validation results
    """
    errors = []
    
    # Check total allocation
    total_allocated = sum(Decimal(str(v)) for v in allocations.values())
    
    if total_allocated > total_capital:
        errors.append(f"Total allocation ({total_allocated}) exceeds capital ({total_capital})")
    
    # Check individual allocations
    for pool, amount in allocations.items():
        if Decimal(str(amount)) < 0:
            errors.append(f"Negative allocation for pool {pool}")
        
        if Decimal(str(amount)) > total_capital:
            errors.append(f"Allocation for {pool} exceeds total capital")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "total_allocated": float(total_allocated),
        "remaining": float(total_capital - total_allocated)
    }
