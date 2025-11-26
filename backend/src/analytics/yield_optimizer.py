"""
Yield Optimizer - Finds and ranks best yield farming opportunities
Analyzes APY, risks, and optimal allocation strategies
"""
import asyncio
from typing import List, Dict, Tuple, Any
from decimal import Decimal
from datetime import datetime
import numpy as np
from scipy.optimize import minimize

from src.core.data_models import YieldOpportunity, Chain, PoolData
from src.storage.redis_manager import RedisManager
import logging


logger = logging.getLogger(__name__)


class YieldOptimizer:
    """
    Yield farming optimizer with portfolio allocation
    """
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        
        # Risk factors for different protocols
        self.protocol_risk_scores = {
            "Aave": 2.0,
            "Compound": 2.5,
            "Curve": 3.0,
            "Uniswap_V3": 4.0,
            "SushiSwap": 4.5,
            "PancakeSwap": 5.0,
            "Osmosis": 3.5,
            "Unknown": 7.0
        }
        
        logger.info("Yield optimizer initialized")
    
    async def analyze_yield_opportunities(
        self,
        pool_data_list: List[PoolData]
    ) -> List[YieldOpportunity]:
        """
        Analyze pools and create yield opportunities
        """
        opportunities = []
        
        for pool in pool_data_list:
            try:
                # Calculate impermanent loss risk
                il_risk = self._calculate_il_risk(pool)
                
                # Determine entry barrier (minimum investment)
                entry_barrier = self._calculate_entry_barrier(pool)
                
                # Get reward tokens (simplified - would query protocol)
                rewards_tokens = self._get_reward_tokens(pool.protocol)
                
                opportunity = YieldOpportunity(
                    protocol_name=pool.protocol,
                    pool_address=pool.pool_id,
                    chain=pool.chain,
                    token_pair=[pool.token0, pool.token1],
                    apy=pool.apy,
                    tvl=pool.total_liquidity,
                    daily_volume=pool.volume_24h,
                    rewards_tokens=rewards_tokens,
                    impermanent_loss_risk=il_risk,
                    liquidity_depth=pool.total_liquidity,
                    entry_barrier=entry_barrier,
                    timestamp=datetime.utcnow()
                )
                
                opportunities.append(opportunity)
                
            except Exception as e:
                logger.warning(f"Error analyzing pool {pool.pool_id}: {str(e)}")
                continue
        
        # Sort by risk-adjusted return
        sorted_opportunities = sorted(
            opportunities,
            key=lambda x: self._calculate_risk_adjusted_return(x),
            reverse=True
        )
        
        logger.info(f"Analyzed {len(sorted_opportunities)} yield opportunities")
        
        return sorted_opportunities
    
    def _calculate_il_risk(self, pool: PoolData) -> float:
        """
        Calculate impermanent loss risk based on:
        - Token price volatility
        - Pool reserves ratio
        - Historical IL data
        """
        # Simplified calculation
        # In production, would use historical volatility data
        
        # Calculate reserve ratio
        reserve_ratio = float(pool.reserve0 / pool.reserve1) if pool.reserve1 > 0 else 1.0
        
        # Higher deviation from 1:1 = higher IL risk
        ratio_deviation = abs(np.log(reserve_ratio))
        
        # Base IL risk (0-10 scale)
        il_risk = min(ratio_deviation * 3, 10.0)
        
        return round(il_risk, 2)
    
    def _calculate_entry_barrier(self, pool: PoolData) -> Decimal:
        """Calculate minimum reasonable investment"""
        # Base minimum on pool size and gas costs
        min_investment = max(
            pool.total_liquidity * Decimal("0.0001"),  # 0.01% of pool
            Decimal("100")  # Absolute minimum $100
        )
        
        return min_investment
    
    def _get_reward_tokens(self, protocol: str) -> List[str]:
        """Get reward tokens for protocol"""
        reward_map = {
            "Aave": ["AAVE"],
            "Compound": ["COMP"],
            "Curve": ["CRV", "CVX"],
            "Uniswap_V3": ["UNI"],
            "SushiSwap": ["SUSHI"],
            "PancakeSwap": ["CAKE"],
            "Osmosis": ["OSMO"]
        }
        
        return reward_map.get(protocol, [])
    
    def _calculate_risk_adjusted_return(self, opportunity: YieldOpportunity) -> float:
        """
        Calculate risk-adjusted return (Sharpe-like ratio)
        Higher is better
        """
        # Get protocol risk
        protocol_risk = self.protocol_risk_scores.get(
            opportunity.protocol_name,
            7.0
        )
        
        # Total risk = protocol risk + IL risk
        total_risk = (protocol_risk + opportunity.impermanent_loss_risk) / 2
        
        # Risk-adjusted return
        if total_risk > 0:
            return opportunity.apy / total_risk
        else:
            return opportunity.apy
    
    async def optimize_portfolio_allocation(
        self,
        opportunities: List[YieldOpportunity],
        total_capital: Decimal,
        risk_tolerance: float = 5.0  # 0-10 scale
    ) -> Dict[str, Decimal]:
        """
        Optimize capital allocation across yield opportunities
        Uses mean-variance optimization
        
        Returns: Dict mapping pool_address to allocation amount
        """
        if not opportunities:
            return {}
        
        # Extract returns and risks
        returns = np.array([opp.apy for opp in opportunities])
        risks = np.array([
            (self.protocol_risk_scores.get(opp.protocol_name, 7.0) +
             opp.impermanent_loss_risk) / 2
            for opp in opportunities
        ])
        
        n_assets = len(opportunities)
        
        # Objective: Maximize return for given risk tolerance
        def objective(weights):
            portfolio_return = np.sum(returns * weights)
            portfolio_risk = np.sum(risks * weights)
            
            # Penalize if risk exceeds tolerance
            risk_penalty = max(0, portfolio_risk - risk_tolerance) ** 2
            
            return -(portfolio_return - risk_penalty * 10)
        
        # Constraints: weights sum to 1, all weights >= 0
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        ]
        bounds = [(0, 1) for _ in range(n_assets)]
        
        # Initial guess: equal weights
        initial_weights = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if not result.success:
            logger.warning("Portfolio optimization did not converge")
            # Fall back to equal weights
            optimal_weights = initial_weights
        else:
            optimal_weights = result.x
        
        # Calculate allocations
        allocations = {}
        for i, opp in enumerate(opportunities):
            allocation = total_capital * Decimal(str(optimal_weights[i]))
            if allocation >= opp.entry_barrier:
                allocations[opp.pool_address] = allocation
        
        logger.info(f"Optimized portfolio allocation across {len(allocations)} pools")
        
        return allocations
    
    async def calculate_expected_returns(
        self,
        allocations: Dict[str, Decimal],
        opportunities: List[YieldOpportunity],
        time_horizon_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate expected returns for given allocations
        """
        opp_map = {opp.pool_address: opp for opp in opportunities}
        
        total_invested = sum(allocations.values())
        expected_return = Decimal(0)
        expected_risk = 0.0
        
        for pool_address, amount in allocations.items():
            if pool_address in opp_map:
                opp = opp_map[pool_address]
                
                # Annual return
                annual_return = amount * Decimal(str(opp.apy / 100))
                
                # Pro-rate for time horizon
                period_return = annual_return * Decimal(str(time_horizon_days / 365))
                
                expected_return += period_return
                
                # Weighted risk
                weight = float(amount / total_invested) if total_invested > 0 else 0
                pool_risk = (self.protocol_risk_scores.get(opp.protocol_name, 7.0) +
                           opp.impermanent_loss_risk) / 2
                expected_risk += weight * pool_risk
        
        return {
            "total_invested": total_invested,
            "expected_return": expected_return,
            "expected_return_percent": float(expected_return / total_invested * 100) if total_invested > 0 else 0,
            "expected_risk_score": round(expected_risk, 2),
            "time_horizon_days": time_horizon_days,
            "num_positions": len(allocations)
        }
