"""
Data models for DeFi Analytics Platform
Uses Pydantic for validation and serialization
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal


class ExchangeType(str, Enum):
    """Exchange type enumeration"""
    CEX = "cex"
    DEX = "dex"
    COSMOS_DEX = "cosmos_dex"


class Chain(str, Enum):
    """Blockchain enumeration"""
    ETHEREUM = "ethereum"
    BSC = "bsc"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    COSMOS = "cosmos"
    OSMOSIS = "osmosis"


class PriceData(BaseModel):
    """Price data model"""
    symbol: str
    exchange: str
    exchange_type: ExchangeType
    chain: Optional[Chain] = None
    price: Decimal
    volume_24h: Decimal
    timestamp: datetime
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    liquidity: Optional[Decimal] = None
    
    @validator('price', 'volume_24h')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Must be positive')
        return v
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class ArbitrageOpportunity(BaseModel):
    """Arbitrage opportunity model"""
    opportunity_id: str
    token_symbol: str
    buy_exchange: str
    buy_price: Decimal
    sell_exchange: str
    sell_price: Decimal
    profit_percent: float
    profit_absolute: Decimal
    volume_available: Decimal
    estimated_gas_cost: Decimal
    net_profit: Decimal
    execution_path: List[str]
    confidence_score: float
    risk_score: float
    timestamp: datetime
    expires_at: datetime
    
    @validator('profit_percent')
    def validate_profit(cls, v):
        if v < 0:
            raise ValueError('Profit must be positive')
        return v


class YieldOpportunity(BaseModel):
    """Yield farming opportunity model"""
    protocol_name: str
    pool_address: str
    chain: Chain
    token_pair: List[str]
    apy: float
    tvl: Decimal
    daily_volume: Decimal
    rewards_tokens: List[str]
    impermanent_loss_risk: float
    liquidity_depth: Decimal
    entry_barrier: Decimal
    timestamp: datetime
    
    @validator('apy')
    def validate_apy(cls, v):
        if v < 0 or v > 10000:  # Max 10000% APY
            raise ValueError('APY out of reasonable range')
        return v


class RiskMetrics(BaseModel):
    """Risk assessment metrics"""
    asset_symbol: str
    protocol_name: str
    overall_risk_score: float = Field(ge=0, le=10)
    smart_contract_risk: float = Field(ge=0, le=10)
    liquidity_risk: float = Field(ge=0, le=10)
    volatility_risk: float = Field(ge=0, le=10)
    market_risk: float = Field(ge=0, le=10)
    concentration_risk: float = Field(ge=0, le=10)
    audit_status: bool
    exploits_history: int
    time_in_market_days: int
    recommendations: List[str]
    timestamp: datetime


class PoolData(BaseModel):
    """Liquidity pool data"""
    pool_id: str
    protocol: str
    chain: Chain
    token0: str
    token1: str
    reserve0: Decimal
    reserve1: Decimal
    total_liquidity: Decimal
    volume_24h: Decimal
    fee_tier: float
    apy: float
    timestamp: datetime


class Transaction(BaseModel):
    """Transaction model"""
    tx_hash: str
    chain: Chain
    from_address: str
    to_address: str
    value: Decimal
    gas_used: int
    gas_price: Decimal
    block_number: int
    timestamp: datetime
    status: bool


class MarketSnapshot(BaseModel):
    """Complete market snapshot"""
    timestamp: datetime
    prices: List[PriceData]
    arbitrage_opportunities: List[ArbitrageOpportunity]
    yield_opportunities: List[YieldOpportunity]
    total_tvl: Decimal
    total_volume_24h: Decimal
    active_protocols: int
