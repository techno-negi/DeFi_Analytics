"""
Custom exceptions for the DeFi Analytics Platform
"""


class DeFiAnalyticsException(Exception):
    """Base exception for all custom exceptions"""
    
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ConnectionError(DeFiAnalyticsException):
    """Raised when connection to exchange/blockchain fails"""
    pass


class APIError(DeFiAnalyticsException):
    """Raised when API request fails"""
    pass


class RateLimitError(DeFiAnalyticsException):
    """Raised when rate limit is exceeded"""
    pass


class DataValidationError(DeFiAnalyticsException):
    """Raised when data validation fails"""
    pass


class InsufficientLiquidityError(DeFiAnalyticsException):
    """Raised when liquidity is insufficient for operation"""
    pass


class ArbitrageExecutionError(DeFiAnalyticsException):
    """Raised when arbitrage execution fails"""
    pass


class ChainNotSupportedError(DeFiAnalyticsException):
    """Raised when blockchain is not supported"""
    pass


class ContractError(DeFiAnalyticsException):
    """Raised when smart contract interaction fails"""
    pass


class CacheError(DeFiAnalyticsException):
    """Raised when cache operation fails"""
    pass


class DatabaseError(DeFiAnalyticsException):
    """Raised when database operation fails"""
    pass


class AuthenticationError(DeFiAnalyticsException):
    """Raised when authentication fails"""
    pass


class AuthorizationError(DeFiAnalyticsException):
    """Raised when user is not authorized"""
    pass
