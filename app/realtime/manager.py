import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from fastapi import WebSocket

logger = logging.getLogger(__name__)
SendJSON = Callable[[WebSocket, dict], Awaitable[None]]


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def connect(self, conversation_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.connections[conversation_id].append(websocket)

        logger.info(
            "websocket_connected conversation_id=%s active_connections=%s",
            conversation_id,
            len(self.connections[conversation_id]),
        )

    async def disconnect(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if conversation_id in self.connections and websocket in self.connections[conversation_id]:
                self.connections[conversation_id].remove(websocket)
                if not self.connections[conversation_id]:
                    del self.connections[conversation_id]

        logger.info("websocket_disconnected conversation_id=%s", conversation_id)

    async def broadcast(self, conversation_id: str, payload: dict) -> None:
        await self.broadcast_local(conversation_id, payload, self._send_json)

    async def broadcast_local(
        self,
        conversation_id: str,
        payload: dict,
        sender: SendJSON,
    ) -> None:
        async with self._lock:
            targets = list(self.connections.get(conversation_id, []))

        logger.info(
            "websocket_broadcast conversation_id=%s targets=%s",
            conversation_id,
            len(targets),
        )

        stale: list[WebSocket] = []

        for websocket in targets:
            try:
                await sender(websocket, payload)
            except Exception:
                logger.exception(
                    "websocket_send_failed conversation_id=%s",
                    conversation_id,
                )
                stale.append(websocket)

        for websocket in stale:
            await self.disconnect(conversation_id, websocket)

    async def close_all(self) -> None:
        async with self._lock:
            all_items = [
                (conversation_id, websocket)
                for conversation_id, websockets in self.connections.items()
                for websocket in websockets
            ]
            self.connections.clear()

        for _, websocket in all_items:
            try:
                await websocket.close(code=1001, reason="Server shutdown")
            except Exception:
                logger.exception("websocket_close_failed")

    @staticmethod
    async def _send_json(websocket: WebSocket, payload: dict) -> None:
        await websocket.send_json(payload)