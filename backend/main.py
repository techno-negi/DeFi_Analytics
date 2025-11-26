"""
Main application entry point
Starts FastAPI server, WebSocket server, and background tasks
"""
import asyncio
import uvicorn
from contextlib import asynccontextmanager
import logging

from src.config.logging_config import setup_logging
from src.api.rest_api import app
from src.api.websocket_server import websocket_endpoint
from src.config.settings import settings
from src.core.service_manager import ServiceManager
from src.workers.ingestion import data_ingestion_worker
from src.workers.yield_analysis import yield_analysis_worker

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

async def start_background_tasks():
    """Start all background tasks"""
    asyncio.create_task(data_ingestion_worker())
    asyncio.create_task(yield_analysis_worker())
    logger.info("Background tasks started")


# Add WebSocket route
app.add_api_websocket_route("/ws", websocket_endpoint)


@asynccontextmanager
async def lifespan(app):
    """Application lifespan manager"""
    # Startup
    service_manager = ServiceManager.get_instance()
    await service_manager.initialize()
    
    await start_background_tasks()
    
    yield
    
    # Shutdown
    await service_manager.cleanup()


# Update app with lifespan
app.router.lifespan_context = lifespan


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
