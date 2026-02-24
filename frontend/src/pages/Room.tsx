import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import '../styles/room.css'

const ROOM_CODE_KEY = 'tienlen.room_code'
const ROOM_PLAYER_KEY = 'tienlen.room_player_id'

const Room = () => {
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const roomStatus: 'waiting' | 'ready' | 'in_game' | 'finished' = 'waiting'
  const players = [
    { id: 'p1', name: 'Player 1', chips: 500, active: false, ready: true },
    { id: 'p2', name: 'Player 2', chips: 300, active: true, ready: true },
    { id: 'p3', name: 'Player 3', chips: 240, active: false, ready: false },
  ]
  const activePlayer = players.find((player) => player.active) ?? players[0]
  const isWaiting = roomStatus === 'waiting' || roomStatus === 'ready'
  const roomCode = useMemo(() => {
    const params = new URLSearchParams(location.search)
    return params.get('code') ?? sessionStorage.getItem(ROOM_CODE_KEY) ?? ''
  }, [location.search])
  const playerId = useMemo(
    () => sessionStorage.getItem(ROOM_PLAYER_KEY) ?? '',
    [],
  )

  useEffect(() => {
    if (!roomCode || !playerId) {
      return
    }
    const apiBase =
      import.meta.env.VITE_API_BASE ?? `http://${window.location.hostname}:8000`
    const wsUrl = apiBase.replace(/^http/, 'ws') + '/ws'
    const socket = new WebSocket(wsUrl)

    socket.addEventListener('open', () => {
      socket.send(
        JSON.stringify({
          type: 'room:join',
          payload: { code: roomCode, player_id: playerId },
        }),
      )
    })

    socket.addEventListener('message', (event) => {
      console.log('[ws]', event.data)
    })

    socket.addEventListener('error', (event) => {
      console.error('[ws] error', event)
    })

    return () => {
      socket.close()
    }
  }, [roomCode, playerId])

  return (
    <div className="app room-shell">
      <div className="sparkle-field" aria-hidden="true">
        <span className="sparkle s1" />
        <span className="sparkle s2" />
        <span className="sparkle s3" />
        <span className="sparkle s4" />
        <span className="sparkle s5" />
        <span className="sparkle s6" />
      </div>

      <header className="room-header">
        <p className="room-title">TIEN LEN</p>
        <p className="room-subtitle">Room 9XK3 • 3/4 players</p>
        <span className={`room-status ${roomStatus}`}>{roomStatus}</span>
      </header>

      <button
        className="room-menu-toggle"
        type="button"
        aria-label={menuOpen ? 'Close menu' : 'Open menu'}
        onClick={() => setMenuOpen((prev) => !prev)}
      >
        <span />
        <span />
        <span />
      </button>

      <div className={`room-menu-backdrop${menuOpen ? ' open' : ''}`}>
        <aside className="room-menu" aria-hidden={!menuOpen}>
          <div className="room-menu-header">
            <p>Menu</p>
            <button
              className="room-menu-close"
              type="button"
              onClick={() => setMenuOpen(false)}
            >
              Close
            </button>
          </div>
          <div className="room-menu-section">
            <p className="room-menu-title">Host</p>
            <button type="button">Start game</button>
            <button type="button">Invite players</button>
            <button type="button">Close room</button>
          </div>
          <div className="room-menu-section">
            <p className="room-menu-title">Player</p>
            <button type="button">Ready</button>
            <button type="button">Change name</button>
            <button type="button">Leave room</button>
          </div>
        </aside>
      </div>

      {isWaiting ? (
        <section className="room-waiting">
          <div className="room-waiting-card">
            <p className="room-waiting-title">Waiting room</p>
            <div className="room-code">
              <span>Room code</span>
              <strong>9XK3</strong>
            </div>
            <div className="room-waiting-actions">
              <button type="button">Copy code</button>
              <button type="button">Invite</button>
              <button type="button" className="primary">
                Start game
              </button>
            </div>
            <p className="room-waiting-note">
              Waiting for players to join. Host can start when ready.
            </p>
          </div>

          <div className="room-waiting-list">
            {players.map((player) => (
              <div key={player.id} className="room-waiting-player">
                <div>
                  <p className="room-player-name">{player.name}</p>
                  <p className="room-player-chip">{player.chips} coins</p>
                </div>
                <span className={`room-waiting-pill ${player.ready ? 'ready' : ''}`}>
                  {player.ready ? 'Ready' : 'Waiting'}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : (
        <>
          <section className="room-players">
            {players.map((player) => (
              <article
                key={player.id}
                className={`room-player${player.active ? ' active' : ''}`}
              >
                <div>
                  <p className="room-player-name">{player.name}</p>
                  <p className="room-player-chip">{player.chips} coins</p>
                </div>
              </article>
            ))}
          </section>

          <section className="room-table">
            <div className="room-trick">
              <div className="room-card">
                <span className="room-card-corner">
                  7
                  <span className="room-card-corner-suit">&clubs;</span>
                </span>
                <span className="room-card-center-suit club">&clubs;</span>
              </div>
              <div className="room-card">
                <span className="room-card-corner">
                  7
                  <span className="room-card-corner-suit">&hearts;</span>
                </span>
                <span className="room-card-center-suit heart">&hearts;</span>
              </div>
            </div>
          </section>

          <section className="room-hand">
            <div className="room-hand-cards">
              {[
                { value: '10', suit: 'spade' },
                { value: '10', suit: 'diamond' },
                { value: '9', suit: 'spade' },
                { value: '8', suit: 'heart' },
                { value: '8', suit: 'diamond' },
                { value: '3', suit: 'club' },
              ].map((card, index) => (
                <div
                  key={`${card.value}-${card.suit}`}
                  className={`room-card small ${index === 3 ? 'selected' : ''}`}
                >
                  <span className="room-card-corner">
                    {card.value}
                    <span className={`room-card-corner-suit ${card.suit}`}>
                      {card.suit === 'spade' && <span>&spades;</span>}
                      {card.suit === 'diamond' && <span>&diams;</span>}
                      {card.suit === 'heart' && <span>&hearts;</span>}
                      {card.suit === 'club' && <span>&clubs;</span>}
                    </span>
                  </span>
                  <span className={`room-card-center-suit ${card.suit}`}>
                    {card.suit === 'spade' && <span>&spades;</span>}
                    {card.suit === 'diamond' && <span>&diams;</span>}
                    {card.suit === 'heart' && <span>&hearts;</span>}
                    {card.suit === 'club' && <span>&clubs;</span>}
                  </span>
                </div>
              ))}
            </div>
            <button className="room-hand-sort" type="button" aria-label="Sort cards">
              ↻
            </button>
          </section>

          <section className="room-actions">
            <button className="room-action ghost" type="button">
              BO LUOT
            </button>
            <button className="room-action primary" type="button">
              DANH
            </button>
          </section>

          <section className="room-current">
            <p className="room-current-label">Current player</p>
            <div className="room-current-card">
              <div>
                <p className="room-player-name">{activePlayer.name}</p>
                <p className="room-player-chip">{activePlayer.chips} coins</p>
              </div>
              <span className="room-current-pill">Your turn</span>
            </div>
          </section>
        </>
      )}
    </div>
  )
}

export default Room
