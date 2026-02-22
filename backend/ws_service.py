from starlette.websockets import WebSocketDisconnect

from .events import EventType
from .game_service import get_game_state, pass_turn, play_turn, start_game
from .room_hub import RoomHub
from .room_service import get_room, remove_player

room_hub = RoomHub()


async def websocket_endpoint(websocket):
    await websocket.accept()
    current_room = None
    current_player = None
    try:
        while True:
            message = await websocket.receive_json()
            event_type = message.get("type")
            payload = message.get("payload") or {}

            if event_type == EventType.room_join.value:
                code = payload.get("code")
                player_id = payload.get("player_id")
                if not code or not player_id:
                    await _send_error(websocket, "Missing code or player_id")
                    continue
                room = await get_room(code)
                if room is None:
                    await _send_error(websocket, "Room not found")
                    continue
                if player_id not in {str(p.id) for p in room.players}:
                    await _send_error(websocket, "Player not in room")
                    continue
                await room_hub.connect(websocket, code)
                current_room = code
                current_player = _parse_uuid(player_id)
                await room_hub.broadcast(
                    code,
                    {
                        "type": EventType.room_update.value,
                        "payload": {"room": room.model_dump(mode="json", exclude={"password_hash"})},
                    },
                )
                state = await get_game_state(code)
                if state is not None:
                    await websocket.send_json(
                        {"type": EventType.game_start.value, "payload": {"state": state.model_dump(mode="json")}}
                    )
                continue

            if event_type == EventType.room_leave.value:
                code = payload.get("code")
                player_id = payload.get("player_id")
                if not code or not player_id:
                    await _send_error(websocket, "Missing code or player_id")
                    continue
                updated_room = await remove_player(code, _parse_uuid(player_id))
                await room_hub.disconnect(websocket, code)
                current_room = None
                current_player = None
                await room_hub.broadcast(
                    code,
                    {
                        "type": EventType.room_update.value,
                        "payload": {
                            "room": updated_room.model_dump(mode="json", exclude={"password_hash"})
                            if updated_room
                            else None
                        },
                    },
                )
                continue

            if event_type == EventType.game_start.value:
                code = payload.get("code")
                player_id = payload.get("player_id")
                if not code or not player_id:
                    await _send_error(websocket, "Missing code or player_id")
                    continue
                room = await get_room(code)
                if room is None:
                    await _send_error(websocket, "Room not found")
                    continue
                if str(room.host_id) != player_id:
                    await _send_error(websocket, "Only host can start")
                    continue
                state = await start_game(code)
                await room_hub.broadcast(
                    code,
                    {"type": EventType.game_start.value, "payload": {"state": state.model_dump(mode="json")}},
                )
                continue

            if event_type == EventType.turn_play.value:
                code = payload.get("code")
                player_id = payload.get("player_id")
                cards = payload.get("cards")
                if not code or not player_id or not cards:
                    await _send_error(websocket, "Missing code, player_id, or cards")
                    continue
                state = await play_turn(code, _parse_uuid(player_id), cards)
                await room_hub.broadcast(
                    code,
                    {"type": EventType.turn_play.value, "payload": {"state": state.model_dump(mode="json")}},
                )
                if state.status.value == "finished":
                    await room_hub.broadcast(
                        code,
                        {"type": EventType.game_end.value, "payload": {"state": state.model_dump(mode="json")}},
                    )
                continue

            if event_type == EventType.turn_pass.value:
                code = payload.get("code")
                player_id = payload.get("player_id")
                if not code or not player_id:
                    await _send_error(websocket, "Missing code or player_id")
                    continue
                state = await pass_turn(code, _parse_uuid(player_id))
                await room_hub.broadcast(
                    code,
                    {"type": EventType.turn_pass.value, "payload": {"state": state.model_dump(mode="json")}},
                )
                continue

            await _send_error(websocket, "Unknown event type")
    except WebSocketDisconnect:
        if current_room:
            if current_player:
                updated_room = await remove_player(current_room, current_player)
                await room_hub.broadcast(
                    current_room,
                    {
                        "type": EventType.room_update.value,
                        "payload": {
                            "room": updated_room.model_dump(mode="json", exclude={"password_hash"})
                            if updated_room
                            else None
                        },
                    },
                )
            await room_hub.disconnect(websocket, current_room)
    except Exception as exc:
        await _send_error(websocket, str(exc))
        if current_room:
            await room_hub.disconnect(websocket, current_room)


def _parse_uuid(value: str):
    from uuid import UUID

    return UUID(value)


async def _send_error(websocket, message: str):
    await websocket.send_json({"type": EventType.error.value, "payload": {"message": message}})
