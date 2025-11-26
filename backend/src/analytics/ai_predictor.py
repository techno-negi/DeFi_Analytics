"""
AI-driven prediction for arbitrage and yield opportunities
Uses simple ML models for opportunity scoring and prediction
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class SimpleMovingAverage:
    """Simple Moving Average predictor"""
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.data = deque(maxlen=window_size)
    
    def update(self, value: float):
        """Add new value to the window"""
        self.data.append(value)
    
    def predict(self) -> float:
        """Predict next value based on SMA"""
        if not self.data:
            return 0.0
        return sum(self.data) / len(self.data)
    
    def get_trend(self) -> str:
        """Get trend direction"""
        if len(self.data) < 2:
            return "neutral"
        
        recent_avg = sum(list(self.data)[-5:]) / min(5, len(self.data))
        older_avg = sum(list(self.data)[:-5]) / max(1, len(self.data) - 5)
        
        if recent_avg > older_avg * 1.02:
            return "up"
        elif recent_avg < older_avg * 0.98:
            return "down"
        return "neutral"


class ExponentialMovingAverage:
    """Exponential Moving Average predictor"""
    
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.ema: Optional[float] = None
    
    def update(self, value: float):
        """Update EMA with new value"""
        if self.ema is None:
            self.ema = value
        else:
            self.ema = self.alpha * value + (1 - self.alpha) * self.ema
    
    def predict(self) -> float:
        """Predict next value"""
        return self.ema if self.ema is not None else 0.0


class OpportunityPredictor:
    """
    AI-driven predictor for DeFi opportunities
    Combines multiple indicators for scoring
    """
    
    def __init__(self):
        self.price_predictors: Dict[str, SimpleMovingAverage] = {}
        self.volume_predictors: Dict[str, ExponentialMovingAverage] = {}
        self.profit_history: deque = deque(maxlen=100)
        self.success_rate_history: deque = deque(maxlen=50)
        
    def update_price_data(self, symbol: str, price: float):
        """Update price predictor with new data"""
        if symbol not in self.price_predictors:
            self.price_predictors[symbol] = SimpleMovingAverage(window_size=20)
        
        self.price_predictors[symbol].update(price)
    
    def update_volume_data(self, symbol: str, volume: float):
        """Update volume predictor"""
        if symbol not in self.volume_predictors:
            self.volume_predictors[symbol] = ExponentialMovingAverage(alpha=0.2)
        
        self.volume_predictors[symbol].update(volume)
    
    def predict_price_movement(self, symbol: str) -> Dict[str, any]:
        """
        Predict price movement for a symbol
        
        Returns:
            Dictionary with prediction, confidence, and trend
        """
        if symbol not in self.price_predictors:
            return {
                "predicted_price": 0.0,
                "confidence": 0.0,
                "trend": "neutral"
            }
        
        predictor = self.price_predictors[symbol]
        
        return {
            "predicted_price": predictor.predict(),
            "confidence": min(len(predictor.data) / predictor.window_size, 1.0),
            "trend": predictor.get_trend()
        }
    
    def score_arbitrage_opportunity(
        self,
        token_symbol: str,
        profit_percent: float,
        liquidity: float,
        gas_cost: float,
        historical_success: float = 0.7
    ) -> float:
        """
        Score an arbitrage opportunity using AI-driven approach
        
        Args:
            token_symbol: Token symbol
            profit_percent: Expected profit percentage
            liquidity: Available liquidity
            gas_cost: Estimated gas cost
            historical_success: Historical success rate (0-1)
        
        Returns:
            Confidence score (0-1)
        """
        scores = []
        
        # 1. Profit score (normalized)
        profit_score = min(profit_percent / 5.0, 1.0)  # Cap at 5%
        scores.append(profit_score * 0.35)
        
        # 2. Liquidity score
        liquidity_score = min(np.log1p(liquidity) / 15.0, 1.0)  # Log scale
        scores.append(liquidity_score * 0.25)
        
        # 3. Cost efficiency score
        net_profit = profit_percent - (gas_cost / 1000 * 100)  # Rough estimate
        cost_score = max(net_profit / profit_percent, 0.0) if profit_percent > 0 else 0
        scores.append(cost_score * 0.20)
        
        # 4. Historical success rate
        scores.append(historical_success * 0.15)
        
        # 5. Price trend score (if available)
        if token_symbol in self.price_predictors:
            trend = self.price_predictors[token_symbol].get_trend()
            trend_score = 1.0 if trend == "up" else 0.5 if trend == "neutral" else 0.3
            scores.append(trend_score * 0.05)
        else:
            scores.append(0.025)  # Neutral
        
        total_score = sum(scores)
        return min(max(total_score, 0.0), 1.0)
    
    def predict_opportunity_lifespan(
        self,
        profit_percent: float,
        market_volatility: float = 0.5
    ) -> int:
        """
        Predict how long an opportunity will remain valid (in seconds)
        
        Args:
            profit_percent: Profit percentage
            market_volatility: Market volatility (0-1 scale)
        
        Returns:
            Expected lifespan in seconds
        """
        # Base lifespan inversely proportional to profit
        # High profit opportunities close faster
        base_lifespan = 60  # 1 minute base
        
        if profit_percent > 3.0:
            lifespan = base_lifespan * 0.3  # 18 seconds
        elif profit_percent > 2.0:
            lifespan = base_lifespan * 0.5  # 30 seconds
        elif profit_percent > 1.0:
            lifespan = base_lifespan * 0.8  # 48 seconds
        else:
            lifespan = base_lifespan  # 60 seconds
        
        # Adjust for volatility
        volatility_factor = 1.0 - (market_volatility * 0.5)
        lifespan *= volatility_factor
        
        return int(lifespan)
    
    def calculate_execution_probability(
        self,
        opportunity: Dict,
        current_gas_price: float,
        network_congestion: float = 0.5
    ) -> float:
        """
        Calculate probability of successful execution
        
        Args:
            opportunity: Arbitrage opportunity dict
            current_gas_price: Current gas price in gwei
            network_congestion: Network congestion (0-1)
        
        Returns:
            Execution probability (0-1)
        """
        factors = []
        
        # 1. Profit margin after gas
        estimated_gas_cost = current_gas_price * 150000 / 1e9  # Rough estimate
        profit_margin = opportunity.get('profit_percent', 0) - (estimated_gas_cost / 1000 * 100)
        
        if profit_margin > 1.0:
            factors.append(0.9)
        elif profit_margin > 0.5:
            factors.append(0.7)
        elif profit_margin > 0:
            factors.append(0.5)
        else:
            return 0.0  # Not profitable
        
        # 2. Network congestion impact
        congestion_factor = 1.0 - (network_congestion * 0.4)
        factors.append(congestion_factor)
        
        # 3. Liquidity sufficiency
        liquidity = opportunity.get('volume_available', 0)
        if liquidity > 10000:
            factors.append(0.95)
        elif liquidity > 1000:
            factors.append(0.80)
        else:
            factors.append(0.60)
        
        # 4. Historical success rate
        avg_success = np.mean(self.success_rate_history) if self.success_rate_history else 0.7
        factors.append(avg_success)
        
        # Calculate weighted average
        probability = np.mean(factors)
        
        return min(max(probability, 0.0), 1.0)
    
    def record_execution_result(self, success: bool, profit: float):
        """Record execution result for learning"""
        self.success_rate_history.append(1.0 if success else 0.0)
        if success:
            self.profit_history.append(profit)
    
    def get_performance_metrics(self) -> Dict:
        """Get predictor performance metrics"""
        if not self.success_rate_history:
            return {
                "success_rate": 0.0,
                "average_profit": 0.0,
                "total_executions": 0
            }
        
        return {
            "success_rate": np.mean(self.success_rate_history),
            "average_profit": np.mean(self.profit_history) if self.profit_history else 0.0,
            "total_executions": len(self.success_rate_history),
            "profit_volatility": np.std(self.profit_history) if len(self.profit_history) > 1 else 0.0
        }
