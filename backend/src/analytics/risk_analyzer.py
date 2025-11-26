"""
Risk Analyzer - Comprehensive risk assessment for DeFi protocols
Analyzes smart contract, liquidity, market, and systemic risks
"""
import asyncio
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import numpy as np

from src.core.data_models import RiskMetrics, PoolData, Chain
from src.storage.postgres_manager import PostgresManager
import logging


logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """
    Comprehensive risk analysis for DeFi protocols and assets
    """
    
    def __init__(self, postgres_manager: PostgresManager):
        self.postgres_manager = postgres_manager
        
        # Known audited protocols
        self.audited_protocols = {
            "Aave": True,
            "Compound": True,
            "Uniswap_V3": True,
            "Curve": True,
            "SushiSwap": True,
            "Osmosis": True
        }
        
        # Known exploit history
        self.exploit_history = {
            "Aave": 0,
            "Compound": 0,
            "Uniswap_V3": 0,
            "Curve": 1,
            "SushiSwap": 0,
            "Osmosis": 0
        }
        
        logger.info("Risk analyzer initialized")
    
    async def analyze_protocol_risk(
        self,
        protocol_name: str,
        pool_data: PoolData,
        price_history: Optional[List[Dict]] = None
    ) -> RiskMetrics:
        """
        Comprehensive risk analysis for a protocol/pool
        """
        # 1. Smart contract risk
        smart_contract_risk = self._assess_smart_contract_risk(protocol_name)
        
        # 2. Liquidity risk
        liquidity_risk = self._assess_liquidity_risk(pool_data)
        
        # 3. Volatility risk
        volatility_risk = await self._assess_volatility_risk(
            pool_data.token0,
            pool_data.token1,
            price_history
        )
        
        # 4. Market risk
        market_risk = self._assess_market_risk(pool_data)
        
        # 5. Concentration risk
        concentration_risk = await self._assess_concentration_risk(pool_data)
        
        # Calculate overall risk score (weighted average)
        overall_risk = (
            smart_contract_risk * 0.25 +
            liquidity_risk * 0.20 +
            volatility_risk * 0.25 +
            market_risk * 0.15 +
            concentration_risk * 0.15
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            smart_contract_risk,
            liquidity_risk,
            volatility_risk,
            market_risk,
            concentration_risk
        )
        
        # Time in market
        time_in_market = await self._get_time_in_market(protocol_name)
        
        return RiskMetrics(
            asset_symbol=f"{pool_data.token0}/{pool_data.token1}",
            protocol_name=protocol_name,
            overall_risk_score=round(overall_risk, 2),
            smart_contract_risk=round(smart_contract_risk, 2),
            liquidity_risk=round(liquidity_risk, 2),
            volatility_risk=round(volatility_risk, 2),
            market_risk=round(market_risk, 2),
            concentration_risk=round(concentration_risk, 2),
            audit_status=self.audited_protocols.get(protocol_name, False),
            exploits_history=self.exploit_history.get(protocol_name, 0),
            time_in_market_days=time_in_market,
            recommendations=recommendations,
            timestamp=datetime.utcnow()
        )
    
    def _assess_smart_contract_risk(self, protocol_name: str) -> float:
        """
        Assess smart contract risk (0-10 scale)
        Based on: audits, exploits, code complexity
        """
        risk = 5.0  # Base risk
        
        # Reduce risk if audited
        if self.audited_protocols.get(protocol_name, False):
            risk -= 2.0
        
        # Increase risk based on exploit history
        exploits = self.exploit_history.get(protocol_name, 0)
        risk += exploits * 2.0
        
        # Well-known protocols get lower risk
        trusted_protocols = ["Aave", "Compound", "Uniswap_V3"]
        if protocol_name in trusted_protocols:
            risk -= 1.5
        
        return max(0.0, min(risk, 10.0))
    
    def _assess_liquidity_risk(self, pool_data: PoolData) -> float:
        """
        Assess liquidity risk (0-10 scale)
        Based on: TVL, volume/TVL ratio, depth
        """
        tvl = float(pool_data.total_liquidity)
        volume_24h = float(pool_data.volume_24h)
        
        # Calculate volume/TVL ratio
        if tvl > 0:
            volume_ratio = volume_24h / tvl
        else:
            volume_ratio = 0
        
        # Base risk from TVL (lower TVL = higher risk)
        if tvl < 100000:  # < $100k
            tvl_risk = 8.0
        elif tvl < 1000000:  # < $1M
            tvl_risk = 6.0
        elif tvl < 10000000:  # < $10M
            tvl_risk = 4.0
        else:
            tvl_risk = 2.0
        
        # Adjust for volume ratio
        if volume_ratio < 0.01:  # Very low volume
            volume_risk = 3.0
        elif volume_ratio < 0.1:
            volume_risk = 1.0
        else:
            volume_risk = 0.0
        
        total_risk = (tvl_risk + volume_risk) / 2
        
        return max(0.0, min(total_risk, 10.0))
    
    async def _assess_volatility_risk(
        self,
        token0: str,
        token1: str,
        price_history: Optional[List[Dict]] = None
    ) -> float:
        """
        Assess volatility risk (0-10 scale)
        Based on: historical price volatility, correlation
        """
        if not price_history:
            # Default moderate risk if no history
            return 5.0
        
        # Calculate returns
        prices = np.array([p['price'] for p in price_history])
        returns = np.diff(prices) / prices[:-1]
        
        # Calculate volatility (standard deviation of returns)
        volatility = np.std(returns)
        
        # Annualize volatility
        annual_volatility = volatility * np.sqrt(365)
        
        # Map to 0-10 scale
        # Volatility < 20% = low risk (2)
        # Volatility 20-50% = medium risk (5)
        # Volatility > 50% = high risk (8+)
        if annual_volatility < 0.2:
            risk = 2.0
        elif annual_volatility < 0.5:
            risk = 2.0 + (annual_volatility - 0.2) * 10  # Scale 2-5
        else:
            risk = 5.0 + min((annual_volatility - 0.5) * 6, 5.0)  # Scale 5-10
        
        return max(0.0, min(risk, 10.0))
    
    def _assess_market_risk(self, pool_data: PoolData) -> float:
        """
        Assess market risk (0-10 scale)
        Based on: market conditions, chain risk
        """
        # Chain-specific risks
        chain_risks = {
            Chain.ETHEREUM: 2.0,  # Most established
            Chain.BSC: 4.0,       # Centralization concerns
            Chain.POLYGON: 3.0,
            Chain.ARBITRUM: 3.5,
            Chain.OPTIMISM: 3.5,
            Chain.COSMOS: 4.0,
            Chain.OSMOSIS: 4.5
        }
        
        chain_risk = chain_risks.get(pool_data.chain, 5.0)
        
        # Fee tier risk (very low or very high fees = higher risk)
        fee_risk = 0.0
        if pool_data.fee_tier < 0.001:  # < 0.1%
            fee_risk = 1.0
        elif pool_data.fee_tier > 0.01:  # > 1%
            fee_risk = 1.0
        
        total_risk = (chain_risk + fee_risk) / 1.5
        
        return max(0.0, min(total_risk, 10.0))
    
    async def _assess_concentration_risk(self, pool_data: PoolData) -> float:
        """
        Assess concentration risk (0-10 scale)
        Based on: large holder concentration, pool dominance
        """
        # Simplified - in production would query on-chain data
        
        # If pool is very large relative to protocol, lower concentration risk
        tvl = float(pool_data.total_liquidity)
        
        if tvl > 50000000:  # > $50M
            return 2.0
        elif tvl > 10000000:  # > $10M
            return 4.0
        elif tvl > 1000000:  # > $1M
            return 6.0
        else:
            return 8.0
    
    async def _get_time_in_market(self, protocol_name: str) -> int:
        """Get days since protocol launch"""
        # Hardcoded launch dates (in production, query from database)
        launch_dates = {
            "Aave": datetime(2020, 1, 1),
            "Compound": datetime(2019, 5, 1),
            "Uniswap_V3": datetime(2021, 5, 1),
            "Curve": datetime(2020, 8, 1),
            "SushiSwap": datetime(2020, 9, 1),
            "Osmosis": datetime(2021, 6, 1)
        }
        
        launch_date = launch_dates.get(protocol_name, datetime(2023, 1, 1))
        days = (datetime.utcnow() - launch_date).days
        
        return max(days, 0)
    
    def _generate_recommendations(
        self,
        smart_contract_risk: float,
        liquidity_risk: float,
        volatility_risk: float,
        market_risk: float,
        concentration_risk: float
    ) -> List[str]:
        """Generate risk mitigation recommendations"""
        recommendations = []
        
        if smart_contract_risk > 6.0:
            recommendations.append(
                "⚠️ High smart contract risk - verify audit status and limit exposure"
            )
        
        if liquidity_risk > 6.0:
            recommendations.append(
                "⚠️ Low liquidity detected - expect higher slippage and exit difficulty"
            )
        
        if volatility_risk > 7.0:
            recommendations.append(
                "⚠️ High volatility - significant impermanent loss risk, consider stablecoin pairs"
            )
        
        if market_risk > 6.0:
            recommendations.append(
                "⚠️ Elevated market risk - monitor chain health and market conditions"
            )
        
        if concentration_risk > 7.0:
            recommendations.append(
                "⚠️ High concentration risk - diversify across multiple pools"
            )
        
        # Overall risk assessment
        overall = (smart_contract_risk + liquidity_risk + volatility_risk +
                  market_risk + concentration_risk) / 5
        
        if overall < 3.0:
            recommendations.append("✅ Overall low risk - suitable for conservative strategies")
        elif overall < 6.0:
            recommendations.append("⚡ Moderate risk - appropriate for balanced portfolios")
        else:
            recommendations.append("🔥 High risk - only for experienced users with high risk tolerance")
        
        return recommendations
