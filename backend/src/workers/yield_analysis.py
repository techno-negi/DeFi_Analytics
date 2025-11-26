import asyncio
import logging
from datetime import datetime
from src.core.service_manager import ServiceManager
from src.config.settings import settings

logger = logging.getLogger(__name__)

async def yield_analysis_worker():
    """Background worker for yield analysis"""
    logger.info("Starting yield analysis worker...")
    services = ServiceManager.get_instance()
    
    while True:
        try:
            if services.osmosis and services.osmosis.is_connected:
                # Get pool data from Osmosis
                pools = await services.osmosis.get_all_pools()
                
                if services.yield_optimizer:
                    # Analyze yield opportunities
                    opportunities = await services.yield_optimizer.analyze_yield_opportunities(pools[:50])
                    
                    # Store top opportunities
                    if services.postgres_manager:
                        for opp in opportunities[:20]:
                            await services.postgres_manager.insert_yield_opportunity(opp.model_dump())
                    
                    # Publish updates
                    if services.redis_manager:
                        await services.redis_manager.publish("yield_updates", {
                            "count": len(opportunities),
                            "best_apy": max((o.apy for o in opportunities), default=0),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    logger.info(f"Analyzed {len(opportunities)} yield opportunities")
            
        except Exception as e:
            logger.error(f"Error in yield analysis worker: {str(e)}")
        
        # Wait before next iteration
        await asyncio.sleep(settings.YIELD_UPDATE_INTERVAL)
