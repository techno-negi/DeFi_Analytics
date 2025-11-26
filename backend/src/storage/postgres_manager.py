"""
PostgreSQL Manager - Handles persistent data storage
Stores historical data, user info, transactions, and analytics results
"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncpg
from asyncpg.pool import Pool

from src.config.settings import settings
import logging


logger = logging.getLogger(__name__)


class PostgresManager:
    """
    PostgreSQL manager for persistent storage
    """
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        self._connected = False
    
    async def connect(self):
        """Create connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            self._connected = True
            
            # Initialize schema
            await self._initialize_schema()
            
            logger.info(f"Connected to PostgreSQL at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self._connected = False
            logger.info("Disconnected from PostgreSQL")
    
    async def _initialize_schema(self):
        """Create tables if they don't exist"""
        schema = """
        -- Price history table
        CREATE TABLE IF NOT EXISTS price_history (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            exchange VARCHAR(50) NOT NULL,
            exchange_type VARCHAR(20),
            chain VARCHAR(20),
            price NUMERIC(20, 8) NOT NULL,
            volume_24h NUMERIC(20, 2),
            liquidity NUMERIC(20, 2),
            timestamp TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_price_symbol_exchange 
        ON price_history(symbol, exchange, timestamp DESC);
        
        -- Arbitrage opportunities table
        CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
            id SERIAL PRIMARY KEY,
            opportunity_id VARCHAR(50) UNIQUE NOT NULL,
            token_symbol VARCHAR(20) NOT NULL,
            buy_exchange VARCHAR(50) NOT NULL,
            buy_price NUMERIC(20, 8) NOT NULL,
            sell_exchange VARCHAR(50) NOT NULL,
            sell_price NUMERIC(20, 8) NOT NULL,
            profit_percent NUMERIC(10, 4) NOT NULL,
            profit_absolute NUMERIC(20, 8) NOT NULL,
            volume_available NUMERIC(20, 2),
            estimated_gas_cost NUMERIC(20, 8),
            net_profit NUMERIC(20, 8),
            execution_path JSONB,
            confidence_score NUMERIC(3, 3),
            risk_score NUMERIC(3, 2),
            timestamp TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            executed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_arb_timestamp 
        ON arbitrage_opportunities(timestamp DESC);
        
        -- Yield opportunities table
        CREATE TABLE IF NOT EXISTS yield_opportunities (
            id SERIAL PRIMARY KEY,
            protocol_name VARCHAR(50) NOT NULL,
            pool_address VARCHAR(100) NOT NULL,
            chain VARCHAR(20) NOT NULL,
            token_pair JSONB NOT NULL,
            apy NUMERIC(10, 4) NOT NULL,
            tvl NUMERIC(20, 2) NOT NULL,
            daily_volume NUMERIC(20, 2),
            rewards_tokens JSONB,
            impermanent_loss_risk NUMERIC(3, 2),
            liquidity_depth NUMERIC(20, 2),
            entry_barrier NUMERIC(20, 2),
            timestamp TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_yield_protocol 
        ON yield_opportunities(protocol_name, timestamp DESC);
        
        -- Risk assessments table
        CREATE TABLE IF NOT EXISTS risk_assessments (
            id SERIAL PRIMARY KEY,
            asset_symbol VARCHAR(50) NOT NULL,
            protocol_name VARCHAR(50) NOT NULL,
            overall_risk_score NUMERIC(3, 2) NOT NULL,
            smart_contract_risk NUMERIC(3, 2),
            liquidity_risk NUMERIC(3, 2),
            volatility_risk NUMERIC(3, 2),
            market_risk NUMERIC(3, 2),
            concentration_risk NUMERIC(3, 2),
            audit_status BOOLEAN,
            exploits_history INTEGER DEFAULT 0,
            time_in_market_days INTEGER,
            recommendations JSONB,
            timestamp TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_risk_protocol 
        ON risk_assessments(protocol_name, timestamp DESC);
        
        -- User portfolios table
        CREATE TABLE IF NOT EXISTS user_portfolios (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            portfolio_name VARCHAR(100),
            allocations JSONB NOT NULL,
            total_value NUMERIC(20, 2),
            risk_tolerance NUMERIC(3, 2),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_user_portfolios 
        ON user_portfolios(user_id);
        
        -- Transactions log table
        CREATE TABLE IF NOT EXISTS transactions_log (
            id SERIAL PRIMARY KEY,
            tx_hash VARCHAR(100) UNIQUE,
            user_id VARCHAR(100),
            transaction_type VARCHAR(50) NOT NULL,
            chain VARCHAR(20) NOT NULL,
            from_address VARCHAR(100),
            to_address VARCHAR(100),
            value NUMERIC(20, 8),
            gas_used INTEGER,
            gas_price NUMERIC(20, 8),
            status VARCHAR(20),
            block_number BIGINT,
            timestamp TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_tx_hash 
        ON transactions_log(tx_hash);
        
        -- Analytics cache table (for expensive computations)
        CREATE TABLE IF NOT EXISTS analytics_cache (
            id SERIAL PRIMARY KEY,
            cache_key VARCHAR(200) UNIQUE NOT NULL,
            result JSONB NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_cache_key 
        ON analytics_cache(cache_key, expires_at);
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(schema)
        
        logger.info("PostgreSQL schema initialized")
    
    # ===== Price History Operations =====
    
    async def insert_price_history(self, price_data: Dict[str, Any]) -> int:
        """Insert price data into history"""
        query = """
        INSERT INTO price_history 
        (symbol, exchange, exchange_type, chain, price, volume_24h, liquidity, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                price_data['symbol'],
                price_data['exchange'],
                price_data.get('exchange_type'),
                price_data.get('chain'),
                price_data['price'],
                price_data.get('volume_24h'),
                price_data.get('liquidity'),
                price_data['timestamp']
            )
            return row['id']
    
    async def get_price_history(
        self,
        symbol: str,
        exchange: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get historical price data"""
        conditions = ["symbol = $1"]
        params = [symbol]
        param_count = 1
        
        if exchange:
            param_count += 1
            conditions.append(f"exchange = ${param_count}")
            params.append(exchange)
        
        if from_time:
            param_count += 1
            conditions.append(f"timestamp >= ${param_count}")
            params.append(from_time)
        
        if to_time:
            param_count += 1
            conditions.append(f"timestamp <= ${param_count}")
            params.append(to_time)
        
        where_clause = " AND ".join(conditions)
        param_count += 1
        
        query = f"""
        SELECT * FROM price_history
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT ${param_count}
        """
        
        params.append(limit)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    # ===== Arbitrage Opportunities Operations =====
    
    async def insert_arbitrage_opportunity(self, opportunity: Dict[str, Any]) -> int:
        """Insert arbitrage opportunity"""
        query = """
        INSERT INTO arbitrage_opportunities
        (opportunity_id, token_symbol, buy_exchange, buy_price, sell_exchange, sell_price,
         profit_percent, profit_absolute, volume_available, estimated_gas_cost, net_profit,
         execution_path, confidence_score, risk_score, timestamp, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
        ON CONFLICT (opportunity_id) DO UPDATE SET
            profit_percent = EXCLUDED.profit_percent,
            net_profit = EXCLUDED.net_profit,
            timestamp = EXCLUDED.timestamp
        RETURNING id
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                opportunity['opportunity_id'],
                opportunity['token_symbol'],
                opportunity['buy_exchange'],
                float(opportunity['buy_price']),
                opportunity['sell_exchange'],
                float(opportunity['sell_price']),
                opportunity['profit_percent'],
                float(opportunity['profit_absolute']),
                float(opportunity.get('volume_available', 0)),
                float(opportunity.get('estimated_gas_cost', 0)),
                float(opportunity['net_profit']),
                opportunity['execution_path'],
                opportunity['confidence_score'],
                opportunity['risk_score'],
                opportunity['timestamp'],
                opportunity['expires_at']
            )
            return row['id']
    
    async def get_recent_arbitrage_opportunities(
        self,
        limit: int = 50,
        min_profit: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Get recent arbitrage opportunities"""
        query = """
        SELECT * FROM arbitrage_opportunities
        WHERE profit_percent >= $1 AND expires_at > NOW()
        ORDER BY timestamp DESC
        LIMIT $2
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, min_profit, limit)
            return [dict(row) for row in rows]
    
    # ===== Yield Opportunities Operations =====
    
    async def insert_yield_opportunity(self, opportunity: Dict[str, Any]) -> int:
        """Insert yield opportunity"""
        query = """
        INSERT INTO yield_opportunities
        (protocol_name, pool_address, chain, token_pair, apy, tvl, daily_volume,
         rewards_tokens, impermanent_loss_risk, liquidity_depth, entry_barrier, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING id
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                opportunity['protocol_name'],
                opportunity['pool_address'],
                opportunity['chain'],
                opportunity['token_pair'],
                opportunity['apy'],
                float(opportunity['tvl']),
                float(opportunity.get('daily_volume', 0)),
                opportunity.get('rewards_tokens', []),
                opportunity['impermanent_loss_risk'],
                float(opportunity['liquidity_depth']),
                float(opportunity['entry_barrier']),
                opportunity['timestamp']
            )
            return row['id']
    
    async def get_top_yield_opportunities(
        self,
        chain: Optional[str] = None,
        min_apy: float = 0.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get top yield opportunities"""
        conditions = ["apy >= $1"]
        params = [min_apy]
        param_count = 1
        
        if chain:
            param_count += 1
            conditions.append(f"chain = ${param_count}")
            params.append(chain)
        
        where_clause = " AND ".join(conditions)
        param_count += 1
        
        query = f"""
        SELECT DISTINCT ON (pool_address) *
        FROM yield_opportunities
        WHERE {where_clause}
        ORDER BY pool_address, timestamp DESC
        LIMIT ${param_count}
        """
        
        params.append(limit)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    # ===== Risk Assessments Operations =====
    
    async def insert_risk_assessment(self, assessment: Dict[str, Any]) -> int:
        """Insert risk assessment"""
        query = """
        INSERT INTO risk_assessments
        (asset_symbol, protocol_name, overall_risk_score, smart_contract_risk,
         liquidity_risk, volatility_risk, market_risk, concentration_risk,
         audit_status, exploits_history, time_in_market_days, recommendations, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        RETURNING id
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                assessment['asset_symbol'],
                assessment['protocol_name'],
                assessment['overall_risk_score'],
                assessment['smart_contract_risk'],
                assessment['liquidity_risk'],
                assessment['volatility_risk'],
                assessment['market_risk'],
                assessment['concentration_risk'],
                assessment['audit_status'],
                assessment['exploits_history'],
                assessment['time_in_market_days'],
                assessment['recommendations'],
                assessment['timestamp']
            )
            return row['id']
    
    # ===== Analytics Cache Operations =====
    
    async def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analytics result"""
        query = """
        SELECT result FROM analytics_cache
        WHERE cache_key = $1 AND expires_at > NOW()
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, cache_key)
            return row['result'] if row else None
    
    async def set_cached_result(
        self,
        cache_key: str,
        result: Dict[str, Any],
        ttl_seconds: int = 300
    ) -> None:
        """Cache analytics result"""
        query = """
        INSERT INTO analytics_cache (cache_key, result, expires_at)
        VALUES ($1, $2, NOW() + INTERVAL '%s seconds')
        ON CONFLICT (cache_key) DO UPDATE SET
            result = EXCLUDED.result,
            expires_at = EXCLUDED.expires_at
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(query % ttl_seconds, cache_key, result)
    
    @property
    def is_connected(self) -> bool:
        return self._connected
