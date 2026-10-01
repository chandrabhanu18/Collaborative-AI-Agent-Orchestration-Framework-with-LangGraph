"""
WebSocket handler for real-time streaming of task status updates.
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.services.redis_service import redis_service
from src.db.session import AsyncSessionLocal
from src.services.task_service import task_service

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/ws/tasks/{task_id}")
async def task_status_websocket(websocket: WebSocket, task_id: str):
    """
    Real-time WebSocket endpoint streaming status updates for a given task.
    Listens to Redis Pub/Sub channel and pushes updates immediately to connected clients.
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected for task {task_id}")

    # Immediately push current status from database if available
    try:
        async with AsyncSessionLocal() as session:
            current_task = await task_service.async_get_task(session, task_id)
            if current_task:
                await websocket.send_json({
                    "task_id": str(task_id),
                    "status": current_task.status,
                })
    except Exception as e:
        logger.warning(f"Could not send initial task status over WS: {e}")

    # Stream real-time events published to Redis Pub/Sub
    try:
        async for message in redis_service.subscribe_task_updates(task_id):
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_json({"task_id": str(task_id), "status": str(message)})
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected gracefully for task {task_id}")
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
