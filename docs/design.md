App function:
Online phòng chơi có host, room code/pw, đủ người thì vào ván.

1 host tạo phòng, nhận room code, tùy chọn password.
Người chơi join bằng code (+ pw nếu có).
Phòng có trạng thái: waiting → ready → in‑game.
Khi đủ người (2–4), host bấm start.

Kiến trúc

Frontend: lobby + room + game table.
Backend: REST cho tạo/join phòng; WebSocket cho realtime (join/leave, start game, turns).
State: in‑memory + Redis (nếu scale); hoặc DB nếu cần lưu lịch sử.

Redis

Use Redis to store room state and support pub/sub when running multiple backend instances.


Main flow:

Create room → generate code → store room state.
Join room → validate code/pw → add player → broadcast roster.
Start game → deal cards → turn loop.

Bảo mật cơ bản

Room code ngẫu nhiên 6–8 ký tự.
Password hash (nếu dùng).
Throttle join, limit room count per IP.

Stack decision

Frontend: Vite + React + TypeScript (fast dev iteration).
Backend: Starlette (async) + WebSocket for realtime gameplay.

Rationale

Vite keeps local dev and build time fast for UI iteration.
React + TypeScript provides strong typing and component reuse.
Starlette is lightweight and supports async WebSocket handling.
