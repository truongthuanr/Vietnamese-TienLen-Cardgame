import os
from typing import Optional

import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ROOMS_ACTIVE_KEY = "rooms:active"
ROOM_TTL_SECONDS = 24 * 60 * 60
USER_TTL_SECONDS = 7 * 24 * 60 * 60

_redis: Optional[redis.Redis] = None


def room_meta_key(code: str) -> str:
    return f"room:{code}:meta"


def room_players_key(code: str) -> str:
    return f"room:{code}:players"


def room_state_key(code: str) -> str:
    return f"room:{code}:state"


def room_hands_key(code: str) -> str:
    return f"room:{code}:hands"


def user_key(user_id: str) -> str:
    return f"user:{user_id}"


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis
