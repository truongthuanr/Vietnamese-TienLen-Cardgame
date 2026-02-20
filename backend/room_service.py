import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from .schemas import Player, Room, RoomStatus

ROOMS_BY_CODE: Dict[str, Room] = {}


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
    return room.model_dump(exclude={"password_hash"})


async def create_room(request: Request):
    try:
        payload = CreateRoomRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse({"error": exc.errors()}, status_code=400)

    code = _generate_room_code()
    while code in ROOMS_BY_CODE:
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
    ROOMS_BY_CODE[code] = room

    return JSONResponse({"room": _room_payload(room), "player_id": str(host_id)})


async def join_room(request: Request):
    code = request.path_params["code"].upper()
    room = ROOMS_BY_CODE.get(code)
    if room is None:
        return JSONResponse({"error": "Room not found"}, status_code=404)

    try:
        payload = JoinRoomRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse({"error": exc.errors()}, status_code=400)

    if room.password_hash:
        if not payload.password or _hash_password(payload.password) != room.password_hash:
            return JSONResponse({"error": "Invalid password"}, status_code=403)

    if len(room.players) >= room.max_players:
        return JSONResponse({"error": "Room is full"}, status_code=409)

    seat = next(
        (index for index in range(room.max_players) if index not in {p.seat for p in room.players}),
        len(room.players),
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
    room.players.append(player)

    return JSONResponse({"room": _room_payload(room), "player_id": str(player_id)})


async def leave_room(request: Request):
    code = request.path_params["code"].upper()
    room = ROOMS_BY_CODE.get(code)
    if room is None:
        return JSONResponse({"error": "Room not found"}, status_code=404)

    try:
        payload = LeaveRoomRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse({"error": exc.errors()}, status_code=400)

    player = next((p for p in room.players if p.id == payload.player_id), None)
    if player is None:
        return JSONResponse({"error": "Player not found"}, status_code=404)

    room.players = [p for p in room.players if p.id != payload.player_id]
    if not room.players:
        del ROOMS_BY_CODE[code]
        return JSONResponse({"room": None})

    if player.is_host:
        new_host = room.players[0]
        new_host.is_host = True
        room.host_id = new_host.id

    return JSONResponse({"room": _room_payload(room)})
