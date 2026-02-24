import hashlib
import json
import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from redis_store import (
    ROOMS_ACTIVE_KEY,
    ROOM_TTL_SECONDS,
    get_redis,
    room_meta_key,
    room_players_key,
    room_state_key,
)
from schemas import Player, Room, RoomStatus
from user_service import get_user, touch_user_on_join


class CreateRoomRequest(BaseModel):
    user_id: UUID
    max_players: int = Field(default=4, ge=2, le=4)
    password: Optional[str] = Field(default=None, min_length=1)


class JoinRoomRequest(BaseModel):
    user_id: UUID
    password: Optional[str] = Field(default=None, min_length=1)


class LeaveRoomRequest(BaseModel):
    player_id: UUID


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _generate_room_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def _room_payload(room: Room) -> dict:
    return room.model_dump(mode="json", exclude={"password_hash"})


def _serialize_model(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"))


def _deserialize_player(raw: str) -> Player:
    return Player.model_validate(json.loads(raw))


def _deserialize_room(meta_raw: str, players: list[Player]) -> Room:
    meta = json.loads(meta_raw)
    meta["players"] = players
    return Room.model_validate(meta)


async def create_room(request: Request):
    """
    ---
    summary: Create a room
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - user_id
            properties:
              user_id:
                type: string
                format: uuid
              max_players:
                type: integer
                minimum: 2
                maximum: 4
              password:
                type: string
    responses:
      200:
        description: OK
      400:
        description: Validation error
      404:
        description: User not found
    """
    try:
        payload = CreateRoomRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse({"error": exc.errors()}, status_code=400)

    client = await get_redis()
    code = _generate_room_code()
    while await client.exists(room_meta_key(code)):
        code = _generate_room_code()

    user = await get_user(str(payload.user_id))
    if user is None:
        return JSONResponse({"error": "User not found"}, status_code=404)

    host_id = uuid4()
    host = Player(
        id=host_id,
        name=user.name,
        seat=0,
        is_host=True,
        is_ready=False,
        hand_count=0,
        score=0,
        status="active",
    )

    password_hash = _hash_password(payload.password) if payload.password else None
    room = Room(
        id=uuid4(),
        code=code,
        password_hash=password_hash,
        host_id=host_id,
        status=RoomStatus.waiting,
        max_players=payload.max_players,
        players=[host],
        created_at=datetime.utcnow(),
    )

    room_meta = room.model_dump(mode="json", exclude={"players"})
    pipeline = client.pipeline()
    pipeline.set(room_meta_key(code), json.dumps(room_meta))
    pipeline.hset(room_players_key(code), str(host_id), _serialize_model(host))
    pipeline.sadd(ROOMS_ACTIVE_KEY, code)
    pipeline.expire(room_meta_key(code), ROOM_TTL_SECONDS)
    pipeline.expire(room_players_key(code), ROOM_TTL_SECONDS)
    await pipeline.execute()

    await touch_user_on_join(str(payload.user_id))
    return JSONResponse({"room": _room_payload(room), "player_id": str(host_id)})


async def join_room(request: Request):
    """
    ---
    summary: Join a room
    parameters:
      - in: path
        name: code
        required: true
        schema:
          type: string
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - user_id
            properties:
              user_id:
                type: string
                format: uuid
              password:
                type: string
    responses:
      200:
        description: OK
      400:
        description: Validation error
      403:
        description: Invalid password
      404:
        description: Room or user not found
      409:
        description: Room is full
    """
    code = request.path_params["code"].upper()
    client = await get_redis()
    meta_raw = await client.get(room_meta_key(code))
    if meta_raw is None:
        return JSONResponse({"error": "Room not found"}, status_code=404)

    try:
        payload = JoinRoomRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse({"error": exc.errors()}, status_code=400)

    user = await get_user(str(payload.user_id))
    if user is None:
        return JSONResponse({"error": "User not found"}, status_code=404)

    meta = json.loads(meta_raw)
    password_hash = meta.get("password_hash")
    if password_hash:
        if not payload.password or _hash_password(payload.password) != password_hash:
            return JSONResponse({"error": "Invalid password"}, status_code=403)

    players_raw = await client.hgetall(room_players_key(code))
    players = [_deserialize_player(raw) for raw in players_raw.values()]
    if len(players) >= meta["max_players"]:
        return JSONResponse({"error": "Room is full"}, status_code=409)

    occupied_seats = {player.seat for player in players}
    seat = next(
        (index for index in range(meta["max_players"]) if index not in occupied_seats),
        len(players),
    )
    player_id = uuid4()
    player = Player(
        id=player_id,
        name=user.name,
        seat=seat,
        is_host=False,
        is_ready=False,
        hand_count=0,
        score=0,
        status="active",
    )
    await client.hset(room_players_key(code), str(player_id), _serialize_model(player))
    await client.expire(room_meta_key(code), ROOM_TTL_SECONDS)
    await client.expire(room_players_key(code), ROOM_TTL_SECONDS)

    room = _deserialize_room(meta_raw, players + [player])
    await touch_user_on_join(str(payload.user_id))
    return JSONResponse({"room": _room_payload(room), "player_id": str(player_id)})


async def leave_room(request: Request):
    """
    ---
    summary: Leave a room
    parameters:
      - in: path
        name: code
        required: true
        schema:
          type: string
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - player_id
            properties:
              player_id:
                type: string
                format: uuid
    responses:
      200:
        description: OK
      400:
        description: Validation error
      404:
        description: Room or player not found
    """
    code = request.path_params["code"].upper()
    client = await get_redis()
    meta_raw = await client.get(room_meta_key(code))
    if meta_raw is None:
        return JSONResponse({"error": "Room not found"}, status_code=404)

    try:
        payload = LeaveRoomRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse({"error": exc.errors()}, status_code=400)

    players_raw = await client.hgetall(room_players_key(code))
    players = [_deserialize_player(raw) for raw in players_raw.values()]
    player = next((p for p in players if p.id == payload.player_id), None)
    if player is None:
        return JSONResponse({"error": "Player not found"}, status_code=404)

    remaining_players = [p for p in players if p.id != payload.player_id]
    if not remaining_players:
        pipeline = client.pipeline()
        pipeline.delete(room_meta_key(code))
        pipeline.delete(room_players_key(code))
        pipeline.delete(room_state_key(code))
        pipeline.srem(ROOMS_ACTIVE_KEY, code)
        await pipeline.execute()
        return JSONResponse({"room": None})

    meta = json.loads(meta_raw)
    if player.is_host:
        new_host = sorted(remaining_players, key=lambda p: p.seat)[0]
        new_host.is_host = True
        meta["host_id"] = str(new_host.id)
        pipeline = client.pipeline()
        pipeline.hset(room_players_key(code), str(new_host.id), _serialize_model(new_host))
        pipeline.set(room_meta_key(code), json.dumps(meta))
        pipeline.hdel(room_players_key(code), str(payload.player_id))
        await pipeline.execute()
    else:
        await client.hdel(room_players_key(code), str(payload.player_id))

    room = _deserialize_room(json.dumps(meta), remaining_players)
    return JSONResponse({"room": _room_payload(room)})


async def remove_player(code: str, player_id: UUID) -> Optional[Room]:
    code = code.upper()
    client = await get_redis()
    meta_raw = await client.get(room_meta_key(code))
    if meta_raw is None:
        return None

    players_raw = await client.hgetall(room_players_key(code))
    players = [_deserialize_player(raw) for raw in players_raw.values()]
    player = next((p for p in players if p.id == player_id), None)
    if player is None:
        return _deserialize_room(meta_raw, players)

    remaining_players = [p for p in players if p.id != player_id]
    if not remaining_players:
        pipeline = client.pipeline()
        pipeline.delete(room_meta_key(code))
        pipeline.delete(room_players_key(code))
        pipeline.delete(room_state_key(code))
        pipeline.srem(ROOMS_ACTIVE_KEY, code)
        await pipeline.execute()
        return None

    meta = json.loads(meta_raw)
    if player.is_host:
        new_host = sorted(remaining_players, key=lambda p: p.seat)[0]
        new_host.is_host = True
        meta["host_id"] = str(new_host.id)
        pipeline = client.pipeline()
        pipeline.hset(room_players_key(code), str(new_host.id), _serialize_model(new_host))
        pipeline.set(room_meta_key(code), json.dumps(meta))
        pipeline.hdel(room_players_key(code), str(player_id))
        await pipeline.execute()
    else:
        await client.hdel(room_players_key(code), str(player_id))

    return _deserialize_room(json.dumps(meta), remaining_players)


async def get_room(code: str) -> Optional[Room]:
    code = code.upper()
    client = await get_redis()
    meta_raw = await client.get(room_meta_key(code))
    if meta_raw is None:
        return None
    players_raw = await client.hgetall(room_players_key(code))
    players = [_deserialize_player(raw) for raw in players_raw.values()]
    return _deserialize_room(meta_raw, players)


async def get_players(code: str) -> list[Player]:
    code = code.upper()
    client = await get_redis()
    players_raw = await client.hgetall(room_players_key(code))
    return [_deserialize_player(raw) for raw in players_raw.values()]


async def update_player(code: str, player: Player) -> None:
    client = await get_redis()
    await client.hset(room_players_key(code.upper()), str(player.id), _serialize_model(player))
