"""
Configuration settings for DeFi Analytics Platform
Manages environment variables and application settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Application
    APP_NAME: str = "DeFi Analytics Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://dashboard.example.com"]
    
    # Security
    SECRET_KEY: str = "VIgPQEZMK7RFN0EFRaM9xF6DykU4EIEZu9kgvmwxtYHu3P5cT3ut2fTj1NBLHh0BIfvx1qDOjPrlo6fT7sNVmw=="
    JWT_SECRET: str = "M47kp+M6Nkis78WLnI7BGJYq9WjnSYKFkqfwx48+rQGyuiMTWBQF/0XJy+yAZArqFMucZVPWVSl898Qq2Hh5Zw=="
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database - PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "defi_user"
    POSTGRES_PASSWORD: str = "defi_password_123"
    POSTGRES_DB: str = "defi_analytics"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_TIMESERIES_RETENTION: int = 86400000  # 24 hours in ms
    
    # Exchange API Keys - CEX
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None
    COINBASE_API_KEY: Optional[str] = None
    COINBASE_SECRET_KEY: Optional[str] = None
    KRAKEN_API_KEY: Optional[str] = None
    KRAKEN_SECRET_KEY: Optional[str] = None
    
    # Blockchain RPC Endpoints
    ETHEREUM_RPC_URL: Optional[str] = None
    BSC_RPC_URL: Optional[str] = None
    POLYGON_RPC_URL: Optional[str] = None
    ARBITRUM_RPC_URL: Optional[str] = None
    OPTIMISM_RPC_URL: Optional[str] = None
    
    # Cosmos Network
    COSMOS_RPC_URL: str = "https://rpc.cosmos.network"
    OSMOSIS_RPC_URL: str = "https://rpc.osmosis.zone"
    
    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 1000
    WS_MESSAGE_QUEUE_SIZE: int = 10000
    
    # Analytics Configuration
    ARBITRAGE_MIN_PROFIT_PERCENT: float = 0.5
    ARBITRAGE_MAX_SLIPPAGE_PERCENT: float = 0.3
    RISK_CALCULATION_INTERVAL: int = 60  # seconds
    YIELD_UPDATE_INTERVAL: int = 300  # seconds
    
    # AI Model Configuration
    MODEL_UPDATE_INTERVAL: int = 3600  # 1 hour
    PREDICTION_CONFIDENCE_THRESHOLD: float = 0.75
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
