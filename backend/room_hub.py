import asyncio
from typing import Dict, Set

from starlette.websockets import WebSocket


class RoomHub:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_code: str) -> None:
        async with self._lock:
            self._rooms.setdefault(room_code, set()).add(websocket)

    async def disconnect(self, websocket: WebSocket, room_code: str) -> None:
        async with self._lock:
            room = self._rooms.get(room_code)
            if not room:
                return
            room.discard(websocket)
            if not room:
                self._rooms.pop(room_code, None)

    async def broadcast(self, room_code: str, event: dict) -> None:
        async with self._lock:
            targets = list(self._rooms.get(room_code, set()))
        for websocket in targets:
            try:
                await websocket.send_json(event)
            except Exception:
                await self.disconnect(websocket, room_code)
