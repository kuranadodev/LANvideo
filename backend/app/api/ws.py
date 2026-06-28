from __future__ import annotations

import asyncio
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/events")
async def events(websocket: WebSocket, request: Request) -> None:
    await websocket.accept()
    queue = request.app.state.event_bus.subscribe()
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
    finally:
        request.app.state.event_bus.unsubscribe(queue)
