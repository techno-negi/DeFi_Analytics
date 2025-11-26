"""
Constants and static configuration for the DeFi Analytics platform
"""
from src.core.data_models import Chain

# Token Mappings (Symbol -> Address)
# These are examples and should be expanded/externalized in a real production env
TOKEN_ADDRESSES = {
    Chain.ETHEREUM: {
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    }
}

# Standard Fee Tiers for Uniswap V3
UNISWAP_FEE_TIERS = [500, 3000, 10000]  # 0.05%, 0.3%, 1%

# Default Pairs to Monitor
MONITORED_PAIRS = [
    "BTC/USDT",
    "ETH/USDT",
    "ETH/USDC",
    "WBTC/USDC"
]
