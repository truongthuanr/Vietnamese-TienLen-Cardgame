from enum import Enum


class EventType(str, Enum):
    room_join = "room:join"
    room_leave = "room:leave"
    room_update = "room:update"
    game_start = "game:start"
    turn_play = "turn:play"
    turn_pass = "turn:pass"
    game_end = "game:end"
    error = "error"
