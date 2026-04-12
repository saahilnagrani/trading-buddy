"""WebSocket endpoint for real-time order updates.

Subscribes to Redis pub/sub channel and forwards order status changes to connected clients.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.redis import get_redis
from app.tasks.order_monitor import PUBSUB_CHANNEL

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/orders")
async def order_updates_ws(websocket: WebSocket):
    await websocket.accept()
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(PUBSUB_CHANNEL)

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe(PUBSUB_CHANNEL)
        await pubsub.aclose()
        await r.aclose()
