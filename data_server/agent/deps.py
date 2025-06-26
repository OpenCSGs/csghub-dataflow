from typing import Optional
from .webSocketManager import WebSocketManager
from fastapi import HTTPException, status
from loguru import logger

_websocket_manager: Optional[WebSocketManager] = None


async def init_managers() -> None:
    """Initialize all manager instances"""
    global _websocket_manager

    logger.info("Initializing managers...")

    try:
        # Initialize connection manager
        _websocket_manager = WebSocketManager()
        logger.info("Connection manager initialized")

    except Exception as e:
        logger.error(f"Failed to initialize managers: {str(e)}")
        await cleanup_managers()  # Cleanup any partially initialized managers
        raise

async def cleanup_managers() -> None:
    """Cleanup and shutdown all manager instances"""
    global _websocket_manager

    logger.info("Cleaning up managers...")

    # Cleanup connection manager first to ensure all active connections are closed
    if _websocket_manager:
        try:
            await _websocket_manager.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up connection manager: {str(e)}")
        finally:
            _websocket_manager = None

    logger.info("All managers cleaned up")

async def get_websocket_manager() -> WebSocketManager:
    """Dependency provider for connection manager"""
    if not _websocket_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Connection manager not initialized"
        )
    return _websocket_manager