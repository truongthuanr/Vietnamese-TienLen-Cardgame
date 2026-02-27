import asyncio
from typing import Dict, Set

from starlette.websockets import WebSocket


class RoomHub:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._rooms: Dict[str, Dict[str, Set[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, room_code: str, player_id: str) -> None:
        async with self._lock:
            room = self._rooms.setdefault(room_code, {})
            room.setdefault(player_id, set()).add(websocket)

    async def disconnect(self, websocket: WebSocket, room_code: str, player_id: str | None = None) -> None:
        async with self._lock:
            room = self._rooms.get(room_code)
            if not room:
                return
            player_ids = [player_id] if player_id else list(room.keys())
            for pid in player_ids:
                sockets = room.get(pid)
                if not sockets:
                    continue
                sockets.discard(websocket)
                if not sockets:
                    room.pop(pid, None)
            if not room:
                self._rooms.pop(room_code, None)

    async def broadcast(self, room_code: str, event: dict) -> None:
        async with self._lock:
            room = self._rooms.get(room_code, {})
            targets = [ws for sockets in room.values() for ws in sockets]
        for websocket in targets:
            try:
                await websocket.send_json(event)
            except Exception:
                await self.disconnect(websocket, room_code)

    async def send_to_player(self, room_code: str, player_id: str, event: dict) -> None:
        async with self._lock:
            room = self._rooms.get(room_code, {})
            targets = list(room.get(player_id, set()))
        for websocket in targets:
            try:
                await websocket.send_json(event)
            except Exception:
                await self.disconnect(websocket, room_code, player_id)
