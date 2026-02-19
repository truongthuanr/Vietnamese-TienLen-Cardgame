# Implementation Plan

## 1) Setup repo & tooling
- Create `frontend/` (Vite + React + TS) và `backend/` (Starlette).
- Add basic lint/format, env config, and dev scripts.

## 2) Core game model (backend)
- Data models: `Card`, `Hand`, `Player`, `Room`, `GameState`.
- Rule engine: validate move, compare hands, detect win.
- Unit tests cho rule engine.

## 3) Room management
- Create/join/leave room (REST).
- Room code + optional password.
- In-memory store + Redis option for scaling.

## 4) WebSocket realtime
- WS connect -> join room -> broadcast roster.
- Events: `room:update`, `game:start`, `turn:play`, `turn:pass`, `game:end`.
- Server authority for game state.

## 5) Frontend basic UI
- Lobby (create/join room).
- Room screen (roster + start button).
- Game table (hand, current trick, turn indicator).

## 6) Gameplay loop
- Deal cards, manage turns, enforce valid moves.
- Handle pass / reset trick.
- End game -> results.

## 7) Polish & reliability
- Reconnect handling.
- AFK timeout / kick.
- Error states + toasts.

## 8) Deploy MVP
- Docker compose (backend + Redis + frontend).
- Basic monitoring/logging.
