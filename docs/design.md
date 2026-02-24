# Design Notes

## App Function
- Online phòng chơi có host, room code/pw, đủ người thì vào ván.
- Host tạo phòng, nhận room code, tùy chọn password.
- Người chơi join bằng code (+ pw nếu có).
- Phòng có trạng thái: waiting → ready → in-game.
- Khi đủ người (2–4), host bấm start.

## Architecture
- Frontend: lobby + room + game table.
- Backend: REST cho tạo/join phòng; WebSocket cho realtime (join/leave, start game, turns).
- State: in-memory + Redis (nếu scale); hoặc DB nếu cần lưu lịch sử.

## Redis
- Store room state and support pub/sub when running multiple backend instances.

## RoomHub (WebSocket connection manager)
- Keep mapping `room_code -> set(websocket)` for active connections.
- API: `connect(ws, room_code)`, `disconnect(ws, room_code)`, `broadcast(room_code, event)`.
- WS handler validates actions (join/play/pass/start), updates state via services, then calls `broadcast`.
- If multi-instance: publish event to Redis pub/sub; each instance subscribes and broadcasts locally.

## Realtime Event Flow
- Client sends action (HTTP/WS) → service mutates Redis → service calls `room_hub.broadcast(room_code, event)`.
- RoomHub only emits when explicitly called; Redis changes alone do not trigger WS updates.
- Broadcast payloads should be minimal and safe (e.g., no other players' hands), include `room_code` and `ts`.
- Event naming: `room.updated`, `player.joined`, `player.left`, `game.started`, `game.state`, `game.turn`, `game.finished`.

## User + Room TTL (lightweight sessions)
- No JWT/auth for MVP; client stores `user_id` + `name` in browser storage.
- User store: `user:{id}` -> JSON `{id, name, created_at, last_joined_at}` with TTL 7 days.
- Room store: `room:{code}:*` keys with TTL 24 hours.
- On join room, update `last_joined_at` and extend user TTL.
- If room/user expired, client must re-create user or re-join room.

## Data Model / Schema
### Core types
- Card: `{ rank: 3..15, suit: "S|C|D|H" }` where J=11, Q=12, K=13, A=14, 2=15.
- Hand: `{ cards: Card[] }`
- Player: `{ id, name, seat, is_host, is_ready, hand_count, status }`

### Room
- Room: `{ id, code, password_hash?, max_players, status, host_id, players, created_at }`
- Room status: `waiting | ready | in_game | finished`

### Game state
- GameState: `{ room_id, deck, players_order, current_turn, last_play, pass_count, winner_id? }`
- LastPlay (current trick): `{ type, cards, by_player_id }`
- Move: `{ type: "play|pass", cards?, by_player_id, ts }`

### Combination type
- ComboType: `single | pair | triple | straight | consecutive_pairs | four_kind`

### Redis keys (example)
- `room:{code}:meta` -> Room meta (JSON)
- `room:{code}:players` -> hash of `player_id` -> Player (JSON)
- `room:{code}:state` -> GameState (JSON)
- `rooms:active` -> set of active room codes
- `pubsub:room:{code}` -> WS broadcast channel

## Main Flow
- Homepage: if browser has no saved user info (no auth needed), show user creation screen (enter name only; backend generates `user_id`) and store `user_id` + name in browser.
- Homepage: if user info stored in browser is valid (backend verifies `user_id` not expired), show options: continue with name (go to Lobby) or create user (enter name).
- Lobby: main actions are Create room or Join room.
- Create room → generate code → set `host_id` from stored `user_id` → store room state → auto-join room (extend TTL).
- Join room → validate code/pw → re-verify `user_id` and extend TTL (if invalid, clear user info and redirect to homepage) → add player → broadcast roster.
- After create/join: frontend navigates to Room and opens WebSocket → send `room_join` with `{ code, player_id }` to subscribe for realtime updates.
- Start game → deal cards → turn loop.

## Security Basics
- Room code ngẫu nhiên 6–8 ký tự.
- Password hash (nếu dùng).
- Throttle join, limit room count per IP.

## Stack Decision
- Frontend: Vite + React + TypeScript (fast dev iteration).
- Backend: Starlette (async) + WebSocket for realtime gameplay.

## Rationale
- Vite keeps local dev and build time fast for UI iteration.
- React + TypeScript provides strong typing and component reuse.
- Starlette is lightweight and supports async WebSocket handling.

## Game Rules (MVP)
- Deck: standard 52 cards, no jokers.
- Rank order: 3 < 4 < ... < 10 < J < Q < K < A < 2.
- Valid sets: single, pair, triple, straight (3+ cards, no 2), consecutive pairs (3+ pairs).
- Turn: play same type and higher, or pass; when all pass, last player starts.
- Beat rules:
  - Four of a kind beats a single 2 or pair of 2s.
  - 3 consecutive pairs beat a single 2.
  - 4 consecutive pairs beat a single 2 or pair of 2s.
- First turn: player with 3 of spades (or smallest 3) starts.
- End: first player to empty hand wins.

## Game Rules (Detailed)
### Card ordering
- Rank strength: 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A < 2.
- Suit strength for singles (if enabled): spades < clubs < diamonds < hearts.

### Valid combinations
- Single (Quân đơn - Rác): any 1 card.
- Pair (Đôi): 2 cards of the same rank.
- Triple (Sám - 3 Con): 3 cards of the same rank.
- Straight (Sảnh): 3 or more cards of consecutive ranks, same suit not required, no 2 allowed.
- Consecutive pairs (Đôi thông): 3 or more pairs in consecutive ranks (e.g., 33 44 55, 77 88 99).
- Four of a kind (Tứ Quý): 4 cards of the same rank (used for beating rules).

### Turn rules
- A player must play the same type and a higher combination than the current trick.
- A player may pass; passing does not remove cards.
- When all other players pass, the last player who played a valid combo starts a new trick.

### Comparison rules
- Singles: higher rank wins; if rank equal and suit ordering enabled, higher suit wins.
- Pairs/Triples/Four of a kind: compare by rank only.
- Straights: compare by highest card rank in the straight.
- Consecutive pairs: compare by highest pair rank.

### Beating 2s and special beats
- Four of a kind can beat a single 2 or a pair of 2s.
- 3 consecutive pairs can beat a single 2.
- 4 consecutive pairs can beat a single 2 or a pair of 2s.
- If 4 consecutive pairs beating four of a kind is enabled, it can also beat four of a kind.

### First turn and end of game
- First game: player holding 3 of spades (or the smallest 3) starts.
- Subsequent games: previous winner starts.
- Game ends when a player has no cards left.

## Game Options (Decide Early)
- Use suit ordering for singles (spades < clubs < diamonds < hearts).
- Allow 4 consecutive pairs to beat four of a kind.
- Allow A-2-3 straight (default: no).
- Penalty rules for remaining 2s/strong sets.
