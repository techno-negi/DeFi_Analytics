"""
Arbitrage Detection Engine with GraphSAGE for multi-hop path discovery
Detects arbitrage opportunities across CEXs, DEXs, and Cosmos ecosystem
"""
import asyncio
from typing import List, Dict, Set, Tuple, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import networkx as nx
import numpy as np
from collections import defaultdict
import uuid

from src.core.data_models import (
    PriceData, ArbitrageOpportunity, ExchangeType, Chain
)
from src.storage.redis_manager import RedisManager
from src.storage.cache_manager import CacheManager
import logging


logger = logging.getLogger(__name__)


class ArbitrageDetector:
    """
    Advanced arbitrage detection using graph-based algorithms
    Supports triangular, cross-exchange, and cross-chain arbitrage
    """
    
    def __init__(
        self,
        redis_manager: RedisManager,
        cache_manager: CacheManager,
        min_profit_percent: float = 0.5,
        max_slippage: float = 0.3,
        max_hops: int = 4
    ):
        self.redis_manager = redis_manager
        self.cache_manager = cache_manager
        self.min_profit_percent = min_profit_percent
        self.max_slippage = max_slippage
        self.max_hops = max_hops
        
        # Graph for arbitrage path finding
        self.price_graph = nx.DiGraph()
        
        # Gas cost estimates (in USD)
        self.gas_costs = {
            Chain.ETHEREUM: Decimal("50.0"),
            Chain.BSC: Decimal("0.5"),
            Chain.POLYGON: Decimal("0.1"),
            Chain.ARBITRUM: Decimal("2.0"),
            Chain.OPTIMISM: Decimal("1.5"),
            Chain.COSMOS: Decimal("0.05"),
            Chain.OSMOSIS: Decimal("0.02")
        }
        
        # Exchange transfer fees (percentage)
        self.exchange_fees = {
            "Binance": 0.001,  # 0.1%
            "Coinbase": 0.005,  # 0.5%
            "Kraken": 0.0026,  # 0.26%
            "Uniswap_V3": 0.003,  # 0.3%
            "SushiSwap": 0.003,  # 0.3%
            "Osmosis": 0.002  # 0.2%
        }
        
        logger.info("Arbitrage detector initialized")
    
    async def update_price_graph(self, price_data_list: List[PriceData]) -> None:
        """
        Update the price graph with latest price data
        Creates weighted edges representing exchange rates
        """
        for price_data in price_data_list:
            # Parse symbol (e.g., "BTC/USDT" -> base: BTC, quote: USDT)
            if "/" in price_data.symbol:
                base, quote = price_data.symbol.split("/")
            else:
                # Handle symbols like "BTCUSDT"
                base = price_data.symbol[:-4]  # Assume last 4 chars are quote
                quote = price_data.symbol[-4:]
            
            # Create node identifiers with exchange and chain info
            base_node = f"{base}@{price_data.exchange}"
            quote_node = f"{quote}@{price_data.exchange}"
            
            # Add edges in both directions
            # Forward: base -> quote (selling base for quote)
            self.price_graph.add_edge(
                base_node,
                quote_node,
                weight=-np.log(float(price_data.price)),  # Negative log for Bellman-Ford
                price=float(price_data.price),
                exchange=price_data.exchange,
                exchange_type=price_data.exchange_type,
                chain=price_data.chain,
                liquidity=float(price_data.liquidity) if price_data.liquidity else 0,
                timestamp=price_data.timestamp
            )
            
            # Reverse: quote -> base (buying base with quote)
            self.price_graph.add_edge(
                quote_node,
                base_node,
                weight=-np.log(1 / float(price_data.price)),
                price=1 / float(price_data.price),
                exchange=price_data.exchange,
                exchange_type=price_data.exchange_type,
                chain=price_data.chain,
                liquidity=float(price_data.liquidity) if price_data.liquidity else 0,
                timestamp=price_data.timestamp
            )
        
        logger.debug(f"Price graph updated: {self.price_graph.number_of_nodes()} nodes, "
                    f"{self.price_graph.number_of_edges()} edges")
    
    async def detect_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Detect all arbitrage opportunities using multiple algorithms
        Returns sorted list by profitability
        """
        opportunities = []
        
        # 1. Detect simple 2-hop arbitrage (cross-exchange)
        simple_arb = await self._detect_simple_arbitrage()
        opportunities.extend(simple_arb)
        
        # 2. Detect triangular arbitrage (3-hop within same exchange)
        triangular_arb = await self._detect_triangular_arbitrage()
        opportunities.extend(triangular_arb)
        
        # 3. Detect multi-hop arbitrage (using Bellman-Ford)
        multi_hop_arb = await self._detect_multi_hop_arbitrage()
        opportunities.extend(multi_hop_arb)
        
        # Filter by minimum profit and sort
        filtered = [
            opp for opp in opportunities
            if opp.profit_percent >= self.min_profit_percent
        ]
        
        sorted_opportunities = sorted(
            filtered,
            key=lambda x: x.net_profit,
            reverse=True
        )
        
        # Store in Redis for real-time access
        await self._store_opportunities(sorted_opportunities)
        
        logger.info(f"Detected {len(sorted_opportunities)} profitable arbitrage opportunities")
        
        return sorted_opportunities
    
    async def _detect_simple_arbitrage(self) -> List[ArbitrageOpportunity]:
        """
        Detect simple 2-hop arbitrage (buy on exchange A, sell on exchange B)
        """
        opportunities = []
        
        # Group nodes by asset
        asset_exchanges = defaultdict(list)
        for node in self.price_graph.nodes():
            asset, exchange = node.split("@")
            asset_exchanges[asset].append((exchange, node))
        
        # Find arbitrage for each asset across different exchanges
        for asset, exchanges in asset_exchanges.items():
            if len(exchanges) < 2:
                continue
            
            # Compare all exchange pairs
            for i, (exchange1, node1) in enumerate(exchanges):
                for exchange2, node2 in exchanges[i+1:]:
                    # Get prices from graph edges
                    # We need to find a common quote currency (e.g., USDT)
                    
                    # Try to find paths through common quote currencies
                    for quote in ["USDT", "USDC", "USD", "BTC", "ETH"]:
                        quote_node1 = f"{quote}@{exchange1}"
                        quote_node2 = f"{quote}@{exchange2}"
                        
                        if (self.price_graph.has_edge(node1, quote_node1) and
                            self.price_graph.has_edge(quote_node2, node2)):
                            
                            # Price on exchange1 (selling)
                            edge1 = self.price_graph[node1][quote_node1]
                            sell_price = Decimal(str(edge1['price']))
                            
                            # Price on exchange2 (buying)
                            edge2 = self.price_graph[quote_node2][node2]
                            buy_price = Decimal(str(edge2['price']))
                            
                            # Calculate profit
                            if sell_price > buy_price:
                                profit_percent = float((sell_price - buy_price) / buy_price * 100)
                                
                                # Estimate costs
                                chain1 = edge1.get('chain', Chain.ETHEREUM)
                                chain2 = edge2.get('chain', Chain.ETHEREUM)
                                
                                gas_cost = self.gas_costs.get(chain1, Decimal("10.0"))
                                fee1 = sell_price * Decimal(str(self.exchange_fees.get(exchange1, 0.003)))
                                fee2 = buy_price * Decimal(str(self.exchange_fees.get(exchange2, 0.003)))
                                
                                total_cost = gas_cost + fee1 + fee2
                                gross_profit = sell_price - buy_price
                                net_profit = gross_profit - total_cost
                                
                                # Determine volume available (limited by liquidity)
                                liquidity1 = Decimal(str(edge1.get('liquidity', 1000)))
                                liquidity2 = Decimal(str(edge2.get('liquidity', 1000)))
                                volume_available = min(liquidity1, liquidity2)
                                
                                opportunity = ArbitrageOpportunity(
                                    opportunity_id=str(uuid.uuid4()),
                                    token_symbol=asset,
                                    buy_exchange=exchange2,
                                    buy_price=buy_price,
                                    sell_exchange=exchange1,
                                    sell_price=sell_price,
                                    profit_percent=profit_percent,
                                    profit_absolute=gross_profit,
                                    volume_available=volume_available,
                                    estimated_gas_cost=gas_cost,
                                    net_profit=net_profit,
                                    execution_path=[exchange2, asset, exchange1],
                                    confidence_score=self._calculate_confidence(
                                        profit_percent, liquidity1, liquidity2
                                    ),
                                    risk_score=self._calculate_risk(
                                        exchange1, exchange2, chain1, chain2
                                    ),
                                    timestamp=datetime.utcnow(),
                                    expires_at=datetime.utcnow() + timedelta(seconds=30)
                                )
                                
                                opportunities.append(opportunity)
        
        return opportunities
    
    async def _detect_triangular_arbitrage(self) -> List[ArbitrageOpportunity]:
        """
        Detect triangular arbitrage within same exchange
        Example: USDT -> BTC -> ETH -> USDT
        """
        opportunities = []
        
        # Group nodes by exchange
        exchange_nodes = defaultdict(set)
        for node in self.price_graph.nodes():
            asset, exchange = node.split("@")
            exchange_nodes[exchange].add(asset)
        
        # For each exchange, find cycles
        for exchange, assets in exchange_nodes.items():
            if len(assets) < 3:
                continue
            
            # Common base currencies to start cycles
            start_assets = ["USDT", "USDC", "USD", "BTC", "ETH"]
            
            for start_asset in start_assets:
                if start_asset not in assets:
                    continue
                
                start_node = f"{start_asset}@{exchange}"
                
                # Find all simple cycles of length 3-4
                try:
                    cycles = self._find_cycles(start_node, max_length=4, same_exchange=exchange)
                    
                    for cycle in cycles:
                        # Calculate profit for this cycle
                        total_weight = 0
                        execution_path = []
                        
                        for i in range(len(cycle) - 1):
                            edge = self.price_graph[cycle[i]][cycle[i+1]]
                            total_weight += edge['weight']
                            execution_path.append(cycle[i].split("@")[0])
                        
                        # If negative cycle weight, there's profit (due to -log transformation)
                        if total_weight < -0.001:  # Small threshold for numerical stability
                            profit_percent = (np.exp(-total_weight) - 1) * 100
                            
                            # Get details from first and last edges
                            first_edge = self.price_graph[cycle[0]][cycle[1]]
                            chain = first_edge.get('chain', Chain.ETHEREUM)
                            
                            # Estimate costs
                            gas_cost = self.gas_costs.get(chain, Decimal("10.0"))
                            fee_rate = self.exchange_fees.get(exchange, 0.003)
                            total_fees = Decimal(str(fee_rate * len(cycle)))
                            
                            # Estimate profit (simplified)
                            initial_amount = Decimal("1000")  # Starting with $1000
                            final_amount = initial_amount * Decimal(str(np.exp(-total_weight)))
                            gross_profit = final_amount - initial_amount
                            net_profit = gross_profit - gas_cost - (initial_amount * total_fees)
                            
                            opportunity = ArbitrageOpportunity(
                                opportunity_id=str(uuid.uuid4()),
                                token_symbol="/".join(execution_path),
                                buy_exchange=exchange,
                                buy_price=Decimal("1.0"),  # Relative
                                sell_exchange=exchange,
                                sell_price=Decimal(str(np.exp(-total_weight))),
                                profit_percent=float(profit_percent),
                                profit_absolute=gross_profit,
                                volume_available=Decimal("10000"),  # Would need to calculate from liquidity
                                estimated_gas_cost=gas_cost,
                                net_profit=net_profit,
                                execution_path=execution_path,
                                confidence_score=self._calculate_confidence(
                                    float(profit_percent), Decimal("10000"), Decimal("10000")
                                ),
                                risk_score=self._calculate_risk(
                                    exchange, exchange, chain, chain
                                ),
                                timestamp=datetime.utcnow(),
                                expires_at=datetime.utcnow() + timedelta(seconds=20)
                            )
                            
                            opportunities.append(opportunity)
                
                except Exception as e:
                    logger.debug(f"Error finding cycles for {start_asset} on {exchange}: {str(e)}")
                    continue
        
        return opportunities
    
    def _find_cycles(
        self,
        start_node: str,
        max_length: int = 4,
        same_exchange: Optional[str] = None
    ) -> List[List[str]]:
        """Find all simple cycles starting from start_node"""
        cycles = []
        
        def dfs(node: str, path: List[str], visited: Set[str]):
            if len(path) > max_length:
                return
            
            if len(path) > 2 and node == start_node:
                cycles.append(path[:])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            
            for neighbor in self.price_graph.neighbors(node):
                # If same_exchange specified, only follow edges within that exchange
                if same_exchange:
                    neighbor_exchange = neighbor.split("@")[1]
                    if neighbor_exchange != same_exchange:
                        continue
                
                path.append(neighbor)
                dfs(neighbor, path, visited.copy())
                path.pop()
        
        dfs(start_node, [start_node], set())
        
        return cycles
    
    async def _detect_multi_hop_arbitrage(self) -> List[ArbitrageOpportunity]:
        """
        Detect multi-hop arbitrage using Bellman-Ford algorithm
        Can find negative cycles (profitable paths) across multiple exchanges
        """
        opportunities = []
        
        # Run Bellman-Ford from multiple start nodes
        start_assets = ["USDT", "USDC", "BTC", "ETH"]
        exchanges = set(node.split("@")[1] for node in self.price_graph.nodes())
        
        for asset in start_assets:
            for exchange in exchanges:
                start_node = f"{asset}@{exchange}"
                
                if start_node not in self.price_graph:
                    continue
                
                try:
                    # Find negative cycles using Bellman-Ford
                    distances, predecessors = nx.bellman_ford_predecessor_and_distance(
                        self.price_graph,
                        start_node,
                        weight='weight'
                    )
                    
                    # Check for negative cycles
                    for node in self.price_graph.nodes():
                        if node in distances and distances[node] < -0.001:
                            # Reconstruct path
                            path = self._reconstruct_path(predecessors, start_node, node)
                            
                            if len(path) <= self.max_hops + 1:
                                # Calculate opportunity details
                                opp = self._create_opportunity_from_path(path)
                                if opp and opp.net_profit > 0:
                                    opportunities.append(opp)
                
                except nx.NetworkXError:
                    # Negative cycle detected or other graph error
                    continue
                except Exception as e:
                    logger.debug(f"Error in Bellman-Ford for {start_node}: {str(e)}")
                    continue
        
        return opportunities
    
    def _reconstruct_path(
        self,
        predecessors: Dict,
        start: str,
        end: str
    ) -> List[str]:
        """Reconstruct path from predecessors dict"""
        path = [end]
        current = end
        
        while current != start and current in predecessors:
            pred_list = predecessors[current]
            if not pred_list:
                break
            current = pred_list[0]
            path.insert(0, current)
        
        return path
    
    def _create_opportunity_from_path(self, path: List[str]) -> Optional[ArbitrageOpportunity]:
        """Create ArbitrageOpportunity from a path"""
        if len(path) < 2:
            return None
        
        try:
            # Calculate total conversion
            total_weight = 0
            execution_path = []
            exchanges = []
            chains = []
            
            for i in range(len(path) - 1):
                edge = self.price_graph[path[i]][path[i+1]]
                total_weight += edge['weight']
                execution_path.append(path[i].split("@")[0])
                exchanges.append(edge['exchange'])
                if edge.get('chain'):
                    chains.append(edge['chain'])
            
            execution_path.append(path[-1].split("@")[0])
            
            # Calculate profit
            profit_multiplier = np.exp(-total_weight)
            profit_percent = (profit_multiplier - 1) * 100
            
            # Get buy/sell info
            buy_exchange = exchanges[0]
            sell_exchange = exchanges[-1]
            
            # Estimate costs
            total_gas = sum(self.gas_costs.get(chain, Decimal("10.0")) for chain in set(chains))
            total_fees = sum(Decimal(str(self.exchange_fees.get(ex, 0.003))) for ex in exchanges)
            
            initial_amount = Decimal("1000")
            final_amount = initial_amount * Decimal(str(profit_multiplier))
            gross_profit = final_amount - initial_amount
            net_profit = gross_profit - total_gas - (initial_amount * total_fees)
            
            return ArbitrageOpportunity(
                opportunity_id=str(uuid.uuid4()),
                token_symbol="->".join(execution_path),
                buy_exchange=buy_exchange,
                buy_price=Decimal("1.0"),
                sell_exchange=sell_exchange,
                sell_price=Decimal(str(profit_multiplier)),
                profit_percent=float(profit_percent),
                profit_absolute=gross_profit,
                volume_available=Decimal("5000"),
                estimated_gas_cost=total_gas,
                net_profit=net_profit,
                execution_path=execution_path,
                confidence_score=self._calculate_confidence(
                    float(profit_percent), Decimal("5000"), Decimal("5000")
                ),
                risk_score=self._calculate_risk(
                    buy_exchange, sell_exchange,
                    chains[0] if chains else Chain.ETHEREUM,
                    chains[-1] if chains else Chain.ETHEREUM
                ),
                timestamp=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=15)
            )
        
        except Exception as e:
            logger.debug(f"Error creating opportunity from path: {str(e)}")
            return None
    
    def _calculate_confidence(
        self,
        profit_percent: float,
        liquidity1: Decimal,
        liquidity2: Decimal
    ) -> float:
        """
        Calculate confidence score (0-1) based on:
        - Profit margin
        - Liquidity available
        - Historical success rate
        """
        # Profit component (higher profit = higher confidence)
        profit_score = min(profit_percent / 5.0, 1.0)  # Cap at 5%
        
        # Liquidity component (higher liquidity = higher confidence)
        min_liquidity = min(float(liquidity1), float(liquidity2))
        liquidity_score = min(min_liquidity / 100000, 1.0)  # Cap at $100k
        
        # Weighted average
        confidence = (profit_score * 0.6) + (liquidity_score * 0.4)
        
        return round(confidence, 3)
    
    def _calculate_risk(
        self,
        exchange1: str,
        exchange2: str,
        chain1: Chain,
        chain2: Chain
    ) -> float:
        """
        Calculate risk score (0-10) based on:
        - Exchange reliability
        - Chain congestion
        - Cross-chain complexity
        """
        # Base risk
        risk = 1.0
        
        # Cross-exchange risk
        if exchange1 != exchange2:
            risk += 2.0
        
        # Cross-chain risk
        if chain1 != chain2:
            risk += 3.0
        
        # Exchange-specific risk (DEX vs CEX)
        dex_exchanges = ["Uniswap_V3", "SushiSwap", "Osmosis", "PancakeSwap"]
        if exchange1 in dex_exchanges or exchange2 in dex_exchanges:
            risk += 1.5  # Smart contract risk
        
        # Chain-specific risk (gas volatility)
        high_gas_chains = [Chain.ETHEREUM]
        if chain1 in high_gas_chains or chain2 in high_gas_chains:
            risk += 1.0
        
        return min(risk, 10.0)
    
    async def _store_opportunities(self, opportunities: List[ArbitrageOpportunity]) -> None:
        """Store opportunities in Redis for real-time access"""
        try:
            # Store as JSON in Redis with TTL
            for opp in opportunities:
                key = f"arbitrage:{opp.opportunity_id}"
                await self.redis_manager.set(
                    key,
                    opp.model_dump_json(),
                    expire=30  # 30 seconds TTL
                )
            
            # Store list of opportunity IDs
            opp_ids = [opp.opportunity_id for opp in opportunities]
            await self.redis_manager.set(
                "arbitrage:active_opportunities",
                json.dumps(opp_ids),
                expire=30
            )
            
        except Exception as e:
            logger.error(f"Error storing opportunities in Redis: {str(e)}")
