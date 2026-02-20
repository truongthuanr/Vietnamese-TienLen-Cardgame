import hashlib
import json
import os
import secrets
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

import redis.asyncio as redis
from pydantic import BaseModel, Field, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from .schemas import Player, Room, RoomStatus

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ROOMS_ACTIVE_KEY = "rooms:active"

_redis: Optional[redis.Redis] = None


class CreateRoomRequest(BaseModel):
    host_name: str = Field(min_length=1)
    max_players: int = Field(default=4, ge=2, le=4)
    password: Optional[str] = Field(default=None, min_length=1)


class JoinRoomRequest(BaseModel):
    name: str = Field(min_length=1)
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


def _room_meta_key(code: str) -> str:
    return f"room:{code}:meta"


def _room_players_key(code: str) -> str:
    return f"room:{code}:players"


def _room_state_key(code: str) -> str:
    return f"room:{code}:state"


def _serialize_model(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"))


def _deserialize_player(raw: str) -> Player:
    return Player.model_validate(json.loads(raw))


def _deserialize_room(meta_raw: str, players: list[Player]) -> Room:
    meta = json.loads(meta_raw)
    meta["players"] = players
    return Room.model_validate(meta)


async def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def create_room(request: Request):
    try:
        payload = CreateRoomRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse({"error": exc.errors()}, status_code=400)

    client = await _get_redis()
    code = _generate_room_code()
    while await client.exists(_room_meta_key(code)):
        code = _generate_room_code()

    host_id = uuid4()
    host = Player(
        id=host_id,
        name=payload.host_name,
        seat=0,
        is_host=True,
        is_ready=False,
        hand_count=0,
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
    pipeline.set(_room_meta_key(code), json.dumps(room_meta))
    pipeline.hset(_room_players_key(code), str(host_id), _serialize_model(host))
    pipeline.sadd(ROOMS_ACTIVE_KEY, code)
    await pipeline.execute()

    return JSONResponse({"room": _room_payload(room), "player_id": str(host_id)})


async def join_room(request: Request):
    code = request.path_params["code"].upper()
    client = await _get_redis()
    meta_raw = await client.get(_room_meta_key(code))
    if meta_raw is None:
        return JSONResponse({"error": "Room not found"}, status_code=404)

    try:
        payload = JoinRoomRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse({"error": exc.errors()}, status_code=400)

    meta = json.loads(meta_raw)
    password_hash = meta.get("password_hash")
    if password_hash:
        if not payload.password or _hash_password(payload.password) != password_hash:
            return JSONResponse({"error": "Invalid password"}, status_code=403)

    players_raw = await client.hgetall(_room_players_key(code))
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
        name=payload.name,
        seat=seat,
        is_host=False,
        is_ready=False,
        hand_count=0,
        status="active",
    )
    await client.hset(_room_players_key(code), str(player_id), _serialize_model(player))

    room = _deserialize_room(meta_raw, players + [player])
    return JSONResponse({"room": _room_payload(room), "player_id": str(player_id)})


async def leave_room(request: Request):
    code = request.path_params["code"].upper()
    client = await _get_redis()
    meta_raw = await client.get(_room_meta_key(code))
    if meta_raw is None:
        return JSONResponse({"error": "Room not found"}, status_code=404)

    try:
        payload = LeaveRoomRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse({"error": exc.errors()}, status_code=400)

    players_raw = await client.hgetall(_room_players_key(code))
    players = [_deserialize_player(raw) for raw in players_raw.values()]
    player = next((p for p in players if p.id == payload.player_id), None)
    if player is None:
        return JSONResponse({"error": "Player not found"}, status_code=404)

    remaining_players = [p for p in players if p.id != payload.player_id]
    if not remaining_players:
        pipeline = client.pipeline()
        pipeline.delete(_room_meta_key(code))
        pipeline.delete(_room_players_key(code))
        pipeline.delete(_room_state_key(code))
        pipeline.srem(ROOMS_ACTIVE_KEY, code)
        await pipeline.execute()
        return JSONResponse({"room": None})

    meta = json.loads(meta_raw)
    if player.is_host:
        new_host = sorted(remaining_players, key=lambda p: p.seat)[0]
        new_host.is_host = True
        meta["host_id"] = str(new_host.id)
        pipeline = client.pipeline()
        pipeline.hset(_room_players_key(code), str(new_host.id), _serialize_model(new_host))
        pipeline.set(_room_meta_key(code), json.dumps(meta))
        pipeline.hdel(_room_players_key(code), str(payload.player_id))
        await pipeline.execute()
    else:
        await client.hdel(_room_players_key(code), str(payload.player_id))

    room = _deserialize_room(json.dumps(meta), remaining_players)
    return JSONResponse({"room": _room_payload(room)})
