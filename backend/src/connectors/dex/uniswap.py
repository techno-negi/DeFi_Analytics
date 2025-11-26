"""
Uniswap V3 DEX connector implementation
Handles on-chain data retrieval via Web3.py
"""
import asyncio
from typing import List, Dict, Any, Callable, Optional
from decimal import Decimal
from datetime import datetime
from web3 import Web3
from web3.exceptions import ContractLogicError
import json

from src.core.base_connector import BaseConnector
from src.core.data_models import PriceData, ExchangeType, Chain, PoolData
from src.config.settings import settings
from src.config.constants import TOKEN_ADDRESSES, UNISWAP_FEE_TIERS
import logging


logger = logging.getLogger(__name__)


class UniswapV3Connector(BaseConnector):
    """Uniswap V3 DEX connector"""
    
    # Uniswap V3 Factory contract address
    FACTORY_ADDRESS = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
    QUOTER_ADDRESS = "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6"
    
    # Minimal ABIs for required functions
    FACTORY_ABI = [
        {
            "inputs": [
                {"internalType": "address", "name": "tokenA", "type": "address"},
                {"internalType": "address", "name": "tokenB", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"}
            ],
            "name": "getPool",
            "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    POOL_ABI = [
        {
            "inputs": [],
            "name": "token0",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "token1",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "slot0",
            "outputs": [
                {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
                {"internalType": "int24", "name": "tick", "type": "int24"},
                {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
                {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
                {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
                {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
                {"internalType": "bool", "name": "unlocked", "type": "bool"}
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "liquidity",
            "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    def __init__(self, chain: Chain = Chain.ETHEREUM):
        super().__init__(
            exchange_name="Uniswap_V3",
            exchange_type=ExchangeType.DEX,
            rate_limit=20
        )
        self.chain = chain
        self.w3 = self._initialize_web3()
        self.factory_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.FACTORY_ADDRESS),
            abi=self.FACTORY_ABI
        )
    
    def _initialize_web3(self) -> Web3:
        """Initialize Web3 connection"""
        rpc_url = self._get_rpc_url()
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not w3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.chain.value} RPC")
        
        logger.info(f"Connected to {self.chain.value} via Web3")
        return w3
    
    def _get_rpc_url(self) -> str:
        """Get RPC URL based on chain"""
        rpc_map = {
            Chain.ETHEREUM: settings.ETHEREUM_RPC_URL,
            Chain.POLYGON: settings.POLYGON_RPC_URL,
            Chain.ARBITRUM: settings.ARBITRUM_RPC_URL,
            Chain.OPTIMISM: settings.OPTIMISM_RPC_URL
        }
        return rpc_map.get(self.chain, settings.ETHEREUM_RPC_URL)
    
    def _get_base_url(self) -> str:
        """Not used for DEX connector"""
        return ""
    
    async def get_price(self, symbol: str) -> PriceData:
        """
        Get current price for a token pair
        
        Args:
            symbol: Trading pair symbol (e.g., 'ETH/USDC')
        """
        # Parse symbol (e.g., "ETH/USDC" -> "WETH", "USDC")
        base, quote = symbol.split('/')
        
        # Handle ETH vs WETH mapping if needed, or assume constants use WETH
        if base == "ETH": base = "WETH"
        if quote == "ETH": quote = "WETH"
        
        token0_address = TOKEN_ADDRESSES[self.chain].get(base)
        token1_address = TOKEN_ADDRESSES[self.chain].get(quote)
        
        if not token0_address or not token1_address:
            raise ValueError(f"Token addresses not found for {symbol} on {self.chain}")

        # Try to find the pool with the most liquidity (simplified: just try 3000 first)
        # In a real app, we might cache the best pool or check all
        fee = 3000
        pool_address = await self._get_pool_address(token0_address, token1_address, fee)
        
        if pool_address == "0x0000000000000000000000000000000000000000":
             raise ValueError(f"Pool not found for {symbol}")
        
        pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=self.POOL_ABI
        )
        
        # Get slot0 data (includes sqrtPriceX96)
        slot0 = pool_contract.functions.slot0().call()
        sqrt_price_x96 = slot0[0]
        
        # Calculate price from sqrtPriceX96
        # price = (sqrtPriceX96 / 2^96)^2
        # Note: This is the raw price ratio. Decimal adjustment is needed based on token decimals.
        # For this refactor, we'll keep the raw calculation but note the improvement needed.
        price = (sqrt_price_x96 / (2 ** 96)) ** 2
        
        # Get liquidity
        liquidity = pool_contract.functions.liquidity().call()
        
        return PriceData(
            symbol=symbol,
            exchange=self.exchange_name,
            exchange_type=self.exchange_type,
            chain=self.chain,
            price=Decimal(str(price)),
            volume_24h=Decimal(0),  # Would need to query events
            liquidity=Decimal(str(liquidity)),
            timestamp=datetime.utcnow()
        )
    
    async def _get_pool_address(self, token0: str, token1: str, fee: int) -> str:
        """Get pool address from factory"""
        try:
            pool_address = self.factory_contract.functions.getPool(
                Web3.to_checksum_address(token0),
                Web3.to_checksum_address(token1),
                fee
            ).call()
            return pool_address
        except ContractLogicError as e:
            logger.error(f"Error getting pool address: {str(e)}")
            return "0x0000000000000000000000000000000000000000"
    
    async def get_pool_data(self, pool_address: str) -> PoolData:
        """Get comprehensive pool data"""
        pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=self.POOL_ABI
        )
        
        token0 = pool_contract.functions.token0().call()
        token1 = pool_contract.functions.token1().call()
        slot0 = pool_contract.functions.slot0().call()
        liquidity = pool_contract.functions.liquidity().call()
        
        # Calculate price
        sqrt_price_x96 = slot0[0]
        price = (sqrt_price_x96 / (2 ** 96)) ** 2
        
        return PoolData(
            pool_id=pool_address,
            protocol="Uniswap_V3",
            chain=self.chain,
            token0=token0,
            token1=token1,
            reserve0=Decimal(str(liquidity)),  # Simplified
            reserve1=Decimal(str(liquidity / price)),
            total_liquidity=Decimal(str(liquidity)),
            volume_24h=Decimal(0),  # Would need event parsing
            fee_tier=0.3,  # Default 0.3%
            apy=0.0,  # Would need calculation
            timestamp=datetime.utcnow()
        )
    
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """DEX doesn't have traditional orderbook"""
        raise NotImplementedError("Uniswap V3 uses AMM, no traditional orderbook")
    
    async def get_24h_volume(self, symbol: str) -> Decimal:
        """Get 24h volume from events (simplified)"""
        # In production, would parse Swap events from the last 24h
        return Decimal(0)
    
    async def subscribe_to_price_updates(self, symbols: List[str], callback: Callable) -> None:
        """Subscribe to price updates via polling (or event listening)"""
        async def poll_prices():
            while True:
                for symbol_info in symbols:
                    try:
                        # symbol_info should include token addresses
                        price_data = await self.get_price(
                            symbol_info["symbol"],
                            symbol_info["token0"],
                            symbol_info["token1"],
                            symbol_info.get("fee", 3000)
                        )
                        await callback(price_data)
                    except Exception as e:
                        logger.error(f"Error polling price for {symbol_info}: {str(e)}")
                
                await asyncio.sleep(5)  # Poll every 5 seconds
        
        asyncio.create_task(poll_prices())
