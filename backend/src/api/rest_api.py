"""
FastAPI REST API - Main HTTP endpoints
Provides RESTful access to analytics, arbitrage, and yield data
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

from src.config.settings import settings
from src.core.data_models import (
    ArbitrageOpportunity,
    YieldOpportunity,
    RiskMetrics,
    PriceData,
    MarketSnapshot
)
from src.storage.redis_manager import RedisManager
from src.storage.postgres_manager import PostgresManager
from src.storage.cache_manager import CacheManager
from src.analytics.arbitrage_detector import ArbitrageDetector
from src.analytics.yield_optimizer import YieldOptimizer
from src.analytics.risk_analyzer import RiskAnalyzer
from src.api.middleware import (
    rate_limit_middleware,
    logging_middleware,
    cors_middleware,
    error_handling_middleware,
    auth_middleware
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add middleware to app (after CORS middleware)
app.middleware("http")(error_handling_middleware)
app.middleware("http")(logging_middleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(cors_middleware)
# app.middleware("http")(auth_middleware)  # Uncomment to enable auth

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Global managers (initialized in lifespan)
redis_manager: Optional[RedisManager] = None
postgres_manager: Optional[PostgresManager] = None
cache_manager: Optional[CacheManager] = None
arbitrage_detector: Optional[ArbitrageDetector] = None
yield_optimizer: Optional[YieldOptimizer] = None
risk_analyzer: Optional[RiskAnalyzer] = None


# ===== Lifespan Events =====

@app.on_event("startup")
async def startup_event():
    """Initialize connections and services"""
    global redis_manager, postgres_manager, cache_manager
    global arbitrage_detector, yield_optimizer, risk_analyzer
    
    logger.info("Starting up DeFi Analytics API...")
    
    # Initialize storage
    redis_manager = RedisManager()
    await redis_manager.connect()
    
    postgres_manager = PostgresManager()
    await postgres_manager.connect()
    
    cache_manager = CacheManager(redis_manager)
    
    # Initialize analytics engines
    arbitrage_detector = ArbitrageDetector(
        redis_manager,
        cache_manager,
        min_profit_percent=settings.ARBITRAGE_MIN_PROFIT_PERCENT
    )
    
    yield_optimizer = YieldOptimizer(redis_manager)
    risk_analyzer = RiskAnalyzer(postgres_manager)
    
    logger.info("DeFi Analytics API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup connections"""
    logger.info("Shutting down DeFi Analytics API...")
    
    if redis_manager:
        await redis_manager.disconnect()
    
    if postgres_manager:
        await postgres_manager.disconnect()
    
    logger.info("DeFi Analytics API shut down successfully")


# ===== Health Check =====

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "services": {
            "redis": redis_manager.is_connected if redis_manager else False,
            "postgres": postgres_manager.is_connected if postgres_manager else False
        }
    }


# ===== Arbitrage Endpoints =====

@app.get("/api/v1/arbitrage/opportunities", response_model=List[ArbitrageOpportunity])
async def get_arbitrage_opportunities(
    min_profit: float = Query(0.5, ge=0, description="Minimum profit percentage"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results")
):
    """Get current arbitrage opportunities"""
    try:
        opportunities = await postgres_manager.get_recent_arbitrage_opportunities(
            limit=limit,
            min_profit=min_profit
        )
        
        return [ArbitrageOpportunity(**opp) for opp in opportunities]
        
    except Exception as e:
        logger.error(f"Error fetching arbitrage opportunities: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/arbitrage/opportunities/{opportunity_id}", response_model=ArbitrageOpportunity)
async def get_arbitrage_opportunity(opportunity_id: str):
    """Get specific arbitrage opportunity by ID"""
    try:
        # Try Redis first (for active opportunities)
        key = f"arbitrage:{opportunity_id}"
        cached = await redis_manager.get(key)
        
        if cached:
            return ArbitrageOpportunity.model_validate_json(cached)
        
        raise HTTPException(status_code=404, detail="Opportunity not found or expired")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/arbitrage/stats")
async def get_arbitrage_stats():
    """Get arbitrage statistics"""
    try:
        # Get cached stats or compute
        cache_key = "arbitrage_stats"
        cached = await cache_manager.get(cache_key)
        
        if cached:
            return cached
        
        # Compute stats
        opportunities = await postgres_manager.get_recent_arbitrage_opportunities(limit=100)
        
        if not opportunities:
            return {
                "total_opportunities": 0,
                "average_profit": 0,
                "best_opportunity": None
            }
        
        total = len(opportunities)
        avg_profit = sum(o['profit_percent'] for o in opportunities) / total
        best = max(opportunities, key=lambda x: x['net_profit'])
        
        stats = {
            "total_opportunities": total,
            "average_profit_percent": round(avg_profit, 2),
            "best_opportunity": {
                "token": best['token_symbol'],
                "profit_percent": float(best['profit_percent']),
                "net_profit": float(best['net_profit'])
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache for 30 seconds
        await cache_manager.set(cache_key, stats, ttl_seconds=30)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error computing arbitrage stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ===== Yield Endpoints =====

@app.get("/api/v1/yield/opportunities", response_model=List[YieldOpportunity])
async def get_yield_opportunities(
    chain: Optional[str] = Query(None, description="Filter by blockchain"),
    min_apy: float = Query(0, ge=0, description="Minimum APY percentage"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results")
):
    """Get yield farming opportunities"""
    try:
        opportunities = await postgres_manager.get_top_yield_opportunities(
            chain=chain,
            min_apy=min_apy,
            limit=limit
        )
        
        return [YieldOpportunity(**opp) for opp in opportunities]
        
    except Exception as e:
        logger.error(f"Error fetching yield opportunities: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


class PortfolioAllocationRequest(BaseModel):
    total_capital: float
    risk_tolerance: float = 5.0  # 0-10 scale
    min_apy: float = 0.0


@app.post("/api/v1/yield/optimize")
async def optimize_yield_portfolio(request: PortfolioAllocationRequest):
    """Optimize portfolio allocation across yield opportunities"""
    try:
        # Get opportunities
        opportunities_data = await postgres_manager.get_top_yield_opportunities(
            min_apy=request.min_apy,
            limit=20
        )
        
        opportunities = [YieldOpportunity(**opp) for opp in opportunities_data]
        
        # Optimize allocation
        from decimal import Decimal
        allocations = await yield_optimizer.optimize_portfolio_allocation(
            opportunities,
            Decimal(str(request.total_capital)),
            risk_tolerance=request.risk_tolerance
        )
        
        # Calculate expected returns
        expected = await yield_optimizer.calculate_expected_returns(
            allocations,
            opportunities,
            time_horizon_days=30
        )
        
        # Format response
        allocation_details = []
        for pool_address, amount in allocations.items():
            opp = next((o for o in opportunities if o.pool_address == pool_address), None)
            if opp:
                allocation_details.append({
                    "protocol": opp.protocol_name,
                    "pool_address": pool_address,
                    "chain": opp.chain,
                    "token_pair": opp.token_pair,
                    "allocated_amount": float(amount),
                    "apy": opp.apy,
                    "risk_score": (
                        risk_analyzer.protocol_risk_scores.get(opp.protocol_name, 5.0) +
                        opp.impermanent_loss_risk
                    ) / 2
                })
        
        return {
            "allocations": allocation_details,
            "expected_returns": {
                "total_invested": float(expected['total_invested']),
                "expected_return": float(expected['expected_return']),
                "expected_return_percent": expected['expected_return_percent'],
                "expected_risk_score": expected['expected_risk_score'],
                "time_horizon_days": expected['time_horizon_days']
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Risk Endpoints =====

@app.get("/api/v1/risk/assessment/{protocol_name}")
async def get_risk_assessment(protocol_name: str):
    """Get risk assessment for a protocol"""
    try:
        # Get latest assessment from database
        query = """
        SELECT * FROM risk_assessments
        WHERE protocol_name = $1
        ORDER BY timestamp DESC
        LIMIT 1
        """
        
        async with postgres_manager.pool.acquire() as conn:
            row = await conn.fetchrow(query, protocol_name)
        
        if not row:
            raise HTTPException(status_code=404, detail="Risk assessment not found")
        
        return RiskMetrics(**dict(row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching risk assessment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ===== Price Endpoints =====

@app.get("/api/v1/prices/{symbol}")
async def get_price(
    symbol: str,
    exchange: Optional[str] = None
):
    """Get current price for a symbol"""
    try:
        # Get from Redis TimeSeries
        filters = [f"symbol={symbol}"]
        if exchange:
            filters.append(f"exchange={exchange}")
        
        results = await redis_manager.ts_mget(filters, with_labels=True)
        
        if not results:
            raise HTTPException(status_code=404, detail="Price data not found")
        
        return {
            "symbol": symbol,
            "prices": [
                {
                    "exchange": r['labels'].get('exchange'),
                    "price": r['value'],
                    "timestamp": datetime.fromtimestamp(r['timestamp'] / 1000).isoformat()
                }
                for r in results
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/prices/{symbol}/history")
async def get_price_history(
    symbol: str,
    exchange: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168, description="Hours of history")
):
    """Get price history"""
    try:
        to_time = datetime.utcnow()
        from_time = to_time - timedelta(hours=hours)
        
        history = await postgres_manager.get_price_history(
            symbol=symbol,
            exchange=exchange,
            from_time=from_time,
            to_time=to_time,
            limit=1000
        )
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "from": from_time.isoformat(),
            "to": to_time.isoformat(),
            "data": history
        }
        
    except Exception as e:
        logger.error(f"Error fetching price history: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ===== Market Overview =====

@app.get("/api/v1/market/overview")
async def get_market_overview():
    """Get comprehensive market overview"""
    try:
        cache_key = "market_overview"
        cached = await cache_manager.get(cache_key)
        
        if cached:
            return cached
        
        # Get various stats
        arb_opportunities = await postgres_manager.get_recent_arbitrage_opportunities(limit=10)
        yield_opportunities = await postgres_manager.get_top_yield_opportunities(limit=10)
        
        overview = {
            "arbitrage": {
                "count": len(arb_opportunities),
                "best_profit": max((o['profit_percent'] for o in arb_opportunities), default=0)
            },
            "yield": {
                "count": len(yield_opportunities),
                "best_apy": max((o['apy'] for o in yield_opportunities), default=0)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache for 60 seconds
        await cache_manager.set(cache_key, overview, ttl_seconds=60)
        
        return overview
        
    except Exception as e:
        logger.error(f"Error fetching market overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ===== System Info =====

@app.get("/api/v1/system/info")
async def get_system_info():
    """Get system information and statistics"""
    try:
        cache_stats = cache_manager.get_stats()
        
        return {
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "cache_stats": cache_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching system info: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
