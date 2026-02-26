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
- First game: bắt buộc đánh 3♠.
- Handle pass / reset trick.
- End game -> rank scoring (+2, +1, -1, -2), update player scores.
- Special scoring on chops:
  - Heo đen bị chặt -1, heo đỏ -2 (nhiều heo cộng dồn), người chặt + tương ứng.
  - Chặt 3 đôi thông -2; tứ quý bị chặt -2; 4 đôi thông bị chặt -4.
- Multi-game series: host config `number of games` ở waiting screen; auto start next game; hết số ván thì reset về waiting.
  - Waiting: host set `max_games`; broadcast room update.
  - Start game: shuffle/deal; set `current_turn` theo 3♠ (game 1), reset `last_play`, `pass_count`.
  - Play turn: validate lượt + combo; apply chop scoring; update hand + `last_play`; advance turn.
  - Pass: increment `pass_count`; nếu đủ vòng thì reset trick và trả lượt cho người vừa đánh.
  - End game: xác định thứ hạng theo số lá còn lại; cộng/trừ điểm; broadcast `game:end`.
  - Next game: nếu chưa đủ `max_games` thì auto `game:start`; nếu đủ thì clear state/hands và về waiting.

## 7) Polish & reliability
- Reconnect handling.
- AFK timeout / kick.
- Error states + toasts.

## 8) Deploy MVP
- Docker compose (backend + Redis + frontend).
- Basic monitoring/logging.
