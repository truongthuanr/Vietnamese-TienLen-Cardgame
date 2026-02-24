from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Suit(str, Enum):
    spades = "S"
    clubs = "C"
    diamonds = "D"
    hearts = "H"


class ComboType(str, Enum):
    single = "single"
    pair = "pair"
    triple = "triple"
    straight = "straight"
    consecutive_pairs = "consecutive_pairs"
    four_kind = "four_kind"


class RoomStatus(str, Enum):
    waiting = "waiting"
    ready = "ready"
    in_game = "in_game"
    finished = "finished"


class GameStatus(str, Enum):
    waiting = "waiting"
    playing = "playing"
    finished = "finished"


class Card(BaseModel):
    rank: int = Field(ge=3, le=15, description="J=11, Q=12, K=13, A=14, 2=15")
    suit: Suit


class Hand(BaseModel):
    cards: List[Card]


class Player(BaseModel):
    id: UUID
    name: str
    seat: int
    is_host: bool = False
    is_ready: bool = False
    hand_count: int = 0
    score: int = 0
    status: str = "active"


class Room(BaseModel):
    id: UUID
    code: str
    password_hash: Optional[str] = None
    host_id: UUID
    status: RoomStatus = RoomStatus.waiting
    max_players: int = 4
    players: List[Player] = []
    created_at: datetime
    games_played: int = 0


class LastPlay(BaseModel):
    type: ComboType
    cards: List[Card]
    by_player_id: UUID


class Move(BaseModel):
    type: str = Field(description="play|pass")
    cards: Optional[List[Card]] = None
    by_player_id: UUID
    ts: datetime


class GameState(BaseModel):
    room_id: UUID
    status: GameStatus = GameStatus.waiting
    deck: List[Card] = []
    players_order: List[UUID] = []
    current_turn: UUID
    last_play: Optional[LastPlay] = None
    pass_count: int = 0
    winner_id: Optional[UUID] = None
    first_game: bool = False
    first_turn_required: bool = False
