import json
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from .redis_store import USER_TTL_SECONDS, get_redis, user_key


class User(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    last_joined_at: datetime


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1)


async def create_user(request: Request):
    try:
        payload = CreateUserRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse({"error": exc.errors()}, status_code=400)

    now = datetime.utcnow()
    user = User(id=uuid4(), name=payload.name, created_at=now, last_joined_at=now)
    client = await get_redis()
    await client.set(user_key(str(user.id)), json.dumps(user.model_dump(mode="json")), ex=USER_TTL_SECONDS)
    return JSONResponse({"user": user.model_dump(mode="json")})


async def get_user_handler(request: Request):
    user_id = request.path_params["user_id"]
    user = await get_user(user_id)
    if user is None:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return JSONResponse({"user": user.model_dump(mode="json")})


async def get_user(user_id: str) -> Optional[User]:
    client = await get_redis()
    raw = await client.get(user_key(user_id))
    if raw is None:
        return None
    return User.model_validate(json.loads(raw))


async def touch_user_on_join(user_id: str) -> Optional[User]:
    user = await get_user(user_id)
    if user is None:
        return None
    user.last_joined_at = datetime.utcnow()
    client = await get_redis()
    await client.set(user_key(user_id), json.dumps(user.model_dump(mode="json")), ex=USER_TTL_SECONDS)
    return user
