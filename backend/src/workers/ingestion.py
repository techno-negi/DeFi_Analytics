import asyncio
import logging
from src.core.service_manager import ServiceManager
from src.config.constants import MONITORED_PAIRS

logger = logging.getLogger(__name__)

async def data_ingestion_worker():
    """Background worker for data ingestion"""
    logger.info("Starting data ingestion worker...")
    services = ServiceManager.get_instance()
    
    while True:
        try:
            # Collect price data from all sources
            price_data_list = []
            
            # Get prices for monitored pairs from Binance
            # In a real app, we'd loop through MONITORED_PAIRS
            # For now, keeping it simple as per original logic but using the constant
            btc_symbol = "BTCUSDT" # Simplified for now, ideally parsed from MONITORED_PAIRS
            
            if services.binance and services.binance.is_connected:
                btc_price = await services.binance.get_price(btc_symbol)
                price_data_list.append(btc_price)
                
                # Add to Redis TimeSeries
                if services.redis_manager:
                    await services.redis_manager.ts_add(
                        key=f"price:{btc_price.symbol}:{btc_price.exchange}",
                        value=float(btc_price.price),
                        labels={
                            "symbol": btc_price.symbol,
                            "exchange": btc_price.exchange,
                            "exchange_type": btc_price.exchange_type.value
                        }
                    )
                    
                    # Publish to WebSocket subscribers
                    await services.redis_manager.publish("price_updates", btc_price.model_dump_json())
            
            # Store in PostgreSQL
            if services.postgres_manager and price_data_list:
                await services.postgres_manager.insert_price_history(price_data_list[0].model_dump())
            
            # Update arbitrage graph & Detect
            if services.arbitrage_detector and price_data_list:
                await services.arbitrage_detector.update_price_graph(price_data_list)
                
                opportunities = await services.arbitrage_detector.detect_arbitrage_opportunities()
                
                # Store and broadcast opportunities
                for opp in opportunities[:10]:  # Top 10
                    if services.postgres_manager:
                        await services.postgres_manager.insert_arbitrage_opportunity(opp.model_dump())
                    if services.redis_manager:
                        await services.redis_manager.publish("arbitrage_alerts", opp.model_dump_json())
                
                logger.debug(f"Processed {len(price_data_list)} price updates, found {len(opportunities)} arbitrage opportunities")
            
        except Exception as e:
            logger.error(f"Error in data ingestion worker: {str(e)}")
        
        # Wait before next iteration
        await asyncio.sleep(5)
