from dataclasses import dataclass
from typing import Awaitable, Callable, Dict
from uuid import UUID

from starlette.websockets import WebSocket, WebSocketDisconnect

from events import EventType
from game_service import get_game_state, pass_turn, play_turn, start_game
from room_hub import RoomHub
from room_service import get_room, remove_player

room_hub = RoomHub()

Handler = Callable[[WebSocket, dict, "ConnectionState"], Awaitable[None]]
_EVENT_HANDLERS: Dict[str, Handler] = {}


@dataclass
class ConnectionState:
    current_room: str | None = None
    current_player: UUID | None = None


def register_event(event_type: EventType):
    def decorator(func: Handler) -> Handler:
        _EVENT_HANDLERS[event_type.value] = func
        return func

    return decorator


@register_event(EventType.room_join)
async def _handle_room_join(websocket: WebSocket, payload: dict, state: ConnectionState) -> None:
    code = payload.get("code")
    player_id = payload.get("player_id")
    if not code or not player_id:
        await _send_error(websocket, "Missing code or player_id")
        return
    room = await get_room(code)
    if room is None:
        await _send_error(websocket, "Room not found")
        return
    if player_id not in {str(p.id) for p in room.players}:
        await _send_error(websocket, "Player not in room")
        return
    await room_hub.connect(websocket, code)
    state.current_room = code
    state.current_player = _parse_uuid(player_id)
    await room_hub.broadcast(
        code,
        {
            "type": EventType.room_update.value,
            "payload": {"room": room.model_dump(mode="json", exclude={"password_hash"})},
        },
    )
    room_state = await get_game_state(code)
    if room_state is not None:
        await websocket.send_json(
            {"type": EventType.game_start.value, "payload": {"state": room_state.model_dump(mode="json")}}
        )


@register_event(EventType.room_leave)
async def _handle_room_leave(websocket: WebSocket, payload: dict, state: ConnectionState) -> None:
    code = payload.get("code")
    player_id = payload.get("player_id")
    if not code or not player_id:
        await _send_error(websocket, "Missing code or player_id")
        return
    updated_room = await remove_player(code, _parse_uuid(player_id))
    await room_hub.disconnect(websocket, code)
    state.current_room = None
    state.current_player = None
    await room_hub.broadcast(
        code,
        {
            "type": EventType.room_update.value,
            "payload": {
                "room": updated_room.model_dump(mode="json", exclude={"password_hash"}) if updated_room else None
            },
        },
    )


@register_event(EventType.room_sync)
async def _handle_room_sync(websocket: WebSocket, payload: dict, state: ConnectionState) -> None:
    code = payload.get("code")
    player_id = payload.get("player_id")
    if not code or not player_id:
        await _send_error(websocket, "Missing code or player_id")
        return
    room = await get_room(code)
    if room is None:
        await _send_error(websocket, "Room not found")
        return
    if player_id not in {str(p.id) for p in room.players}:
        await _send_error(websocket, "Player not in room")
        return
    await websocket.send_json(
        {
            "type": EventType.room_update.value,
            "payload": {"room": room.model_dump(mode="json", exclude={"password_hash"})},
        }
    )
    room_state = await get_game_state(code)
    if room_state is not None:
        await websocket.send_json(
            {"type": EventType.game_start.value, "payload": {"state": room_state.model_dump(mode="json")}}
        )


@register_event(EventType.game_start)
async def _handle_game_start(websocket: WebSocket, payload: dict, state: ConnectionState) -> None:
    code = payload.get("code")
    player_id = payload.get("player_id")
    if not code or not player_id:
        await _send_error(websocket, "Missing code or player_id")
        return
    room = await get_room(code)
    if room is None:
        await _send_error(websocket, "Room not found")
        return
    if str(room.host_id) != player_id:
        await _send_error(websocket, "Only host can start")
        return
    room_state = await start_game(code)
    await room_hub.broadcast(
        code,
        {"type": EventType.game_start.value, "payload": {"state": room_state.model_dump(mode="json")}},
    )


@register_event(EventType.turn_play)
async def _handle_turn_play(websocket: WebSocket, payload: dict, state: ConnectionState) -> None:
    code = payload.get("code")
    player_id = payload.get("player_id")
    cards = payload.get("cards")
    if not code or not player_id or not cards:
        await _send_error(websocket, "Missing code, player_id, or cards")
        return
    room_state = await play_turn(code, _parse_uuid(player_id), cards)
    await room_hub.broadcast(
        code,
        {"type": EventType.turn_play.value, "payload": {"state": room_state.model_dump(mode="json")}},
    )
    if room_state.status.value == "finished":
        await room_hub.broadcast(
            code,
            {"type": EventType.game_end.value, "payload": {"state": room_state.model_dump(mode="json")}},
        )


@register_event(EventType.turn_pass)
async def _handle_turn_pass(websocket: WebSocket, payload: dict, state: ConnectionState) -> None:
    code = payload.get("code")
    player_id = payload.get("player_id")
    if not code or not player_id:
        await _send_error(websocket, "Missing code or player_id")
        return
    room_state = await pass_turn(code, _parse_uuid(player_id))
    await room_hub.broadcast(
        code,
        {"type": EventType.turn_pass.value, "payload": {"state": room_state.model_dump(mode="json")}},
    )


async def websocket_endpoint(websocket):
    await websocket.accept()
    state = ConnectionState()
    try:
        while True:
            message = await websocket.receive_json()
            event_type = message.get("type")
            payload = message.get("payload") or {}

            handler = _EVENT_HANDLERS.get(event_type)
            if not handler:
                await _send_error(websocket, "Unknown event type")
                continue
            await handler(websocket, payload, state)
    except WebSocketDisconnect:
        if state.current_room:
            if state.current_player:
                updated_room = await remove_player(state.current_room, state.current_player)
                await room_hub.broadcast(
                    state.current_room,
                    {
                        "type": EventType.room_update.value,
                        "payload": {
                            "room": updated_room.model_dump(mode="json", exclude={"password_hash"})
                            if updated_room
                            else None
                        },
                    },
                )
            await room_hub.disconnect(websocket, state.current_room)
    except Exception as exc:
        await _send_error(websocket, str(exc))
        if state.current_room:
            await room_hub.disconnect(websocket, state.current_room)


def _parse_uuid(value: str) -> UUID:
    return UUID(value)


async def _send_error(websocket, message: str):
    await websocket.send_json({"type": EventType.error.value, "payload": {"message": message}})
