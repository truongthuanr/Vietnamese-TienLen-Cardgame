import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import '../styles/room.css'

const ROOM_CODE_KEY = 'tienlen.room_code'
const ROOM_PLAYER_KEY = 'tienlen.room_player_id'
const USER_STORAGE_KEY = 'tienlen.user'

type RoomPlayer = {
  id: string
  user_id: string
  name: string
  seat: number
  is_host: boolean
  is_ready: boolean
  hand_count: number
  score: number
  status: string
}

type RoomPayload = {
  id: string
  code: string
  host_id: string
  status: 'waiting' | 'ready' | 'in_game' | 'finished'
  max_players: number
  max_games: number
  players: RoomPlayer[]
  created_at: string
  games_played: number
}

type GameStatePayload = {
  room_id: string
  status: 'waiting' | 'playing' | 'finished'
  players_order: string[]
  current_turn: string
  last_play: unknown
  pass_count: number
  winner_id: string | null
  first_game: boolean
  first_turn_required: boolean
}

const Room = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const socketRef = useRef<WebSocket | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const [room, setRoom] = useState<RoomPayload | null>(null)
  const [gameState, setGameState] = useState<GameStatePayload | null>(null)
  const [maxGames, setMaxGames] = useState(12)
  const [maxGamesTouched, setMaxGamesTouched] = useState(false)
  const roomCode = useMemo(() => {
    const params = new URLSearchParams(location.search)
    return params.get('code') ?? sessionStorage.getItem(ROOM_CODE_KEY) ?? ''
  }, [location.search])
  const [playerId, setPlayerId] = useState(
    () => sessionStorage.getItem(ROOM_PLAYER_KEY) ?? '',
  )
  const players = room?.players ?? []
  const isHost = room?.host_id === playerId
  const currentPlayer = players.find((player) => player.id === playerId)
  const activePlayer =
    players.find((player) => player.id === gameState?.current_turn) ?? players[0]
  const roomStatus = room?.status ?? 'waiting'
  const gameStatus = gameState?.status
  const effectiveStatus =
    gameStatus === 'playing' ? 'in_game' : gameStatus === 'finished' ? 'finished' : roomStatus
  const isWaiting = effectiveStatus === 'waiting' || effectiveStatus === 'ready'
  const sendRoomEvent = (type: string, payload: Record<string, unknown>) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn('[ws] not connected')
      return
    }
    socket.send(JSON.stringify({ type, payload }))
  }

  const handleMissingRoom = () => {
    sessionStorage.removeItem(ROOM_CODE_KEY)
    sessionStorage.removeItem(ROOM_PLAYER_KEY)
    window.alert('Room not found.')
    navigate('/lobby', { replace: true })
  }

  const handleCopyRoomCode = async () => {
    const code = room?.code ?? roomCode
    if (!code) {
      return
    }
    try {
      await navigator.clipboard.writeText(code)
      window.alert('Copied room code.')
    } catch (error) {
      console.warn('Copy failed', error)
      window.prompt('Copy room code:', code)
    }
  }

  // Start WS sync when we have both roomCode and playerId.
  useEffect(() => {
    if (!roomCode || !playerId) {
      return
    }
    const apiBase =
      import.meta.env.VITE_API_BASE ?? `http://${window.location.hostname}:8000`
    const wsUrl = apiBase.replace(/^http/, 'ws') + '/ws'
    const socket = new WebSocket(wsUrl)
    socketRef.current = socket

    socket.addEventListener('open', () => {
      socket.send(
        JSON.stringify({
          type: 'room:join',
          payload: { code: roomCode, player_id: playerId },
        }),
      )
      socket.send(
        JSON.stringify({
          type: 'room:sync',
          payload: { code: roomCode, player_id: playerId },
        }),
      )
    })

    socket.addEventListener('message', (event) => {
      try {
        const message = JSON.parse(event.data)
        switch (message.type) {
          case 'room:update':
            if (!message.payload?.room) {
              handleMissingRoom()
              return
            }
            setRoom(message.payload.room)
            if (message.payload.room.status === 'waiting') {
              setGameState(null)
            }
            break
          case 'game:start':
          case 'turn:play':
          case 'turn:pass':
          case 'game:end':
            if (message.payload?.state) {
              setGameState(message.payload.state)
            }
            break
          case 'error':
            if (message.payload?.message === 'Room not found') {
              handleMissingRoom()
            }
            break
          default:
            break
        }
      } catch (error) {
        console.error('[ws] invalid message', error)
      }
    })

    socket.addEventListener('error', (event) => {
      console.error('[ws] error', event)
    })

    return () => {
      socketRef.current = null
      socket.close()
    }
  }, [roomCode, playerId, navigate])

  useEffect(() => {
    if (room?.max_games && !maxGamesTouched) {
      setMaxGames(room.max_games)
    }
  }, [room?.max_games, maxGamesTouched])

  // Rejoin flow: only when roomCode exists but playerId is missing.
  useEffect(() => {
    if (!roomCode || playerId) {
      return
    }
    const rawUser = localStorage.getItem(USER_STORAGE_KEY)
    if (!rawUser) {
      handleMissingRoom()
      return
    }
    let userId = ''
    try {
      const parsed = JSON.parse(rawUser) as { id?: string }
      userId = parsed?.id ?? ''
    } catch {
      handleMissingRoom()
      return
    }
    if (!userId) {
      handleMissingRoom()
      return
    }
    const apiBase =
      import.meta.env.VITE_API_BASE ?? `http://${window.location.hostname}:8000`
    const payload = { user_id: userId }
    const join = async () => {
      try {
        const response = await fetch(`${apiBase}/rooms/${roomCode}/join`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        if (!response.ok) {
          console.error('Rejoin room failed', await response.json())
          handleMissingRoom()
          return
        }
        const data = (await response.json()) as {
          room: { code: string }
          player_id: string
        }
        sessionStorage.setItem(ROOM_CODE_KEY, data.room.code)
        sessionStorage.setItem(ROOM_PLAYER_KEY, data.player_id)
        setPlayerId(data.player_id)
      } catch (error) {
        console.error('Rejoin room error', error)
        handleMissingRoom()
      }
    }
    join()
  }, [roomCode, playerId, navigate])

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
        <p className="room-subtitle">
          Room {room?.code ?? roomCode} • {players.length}/{room?.max_players ?? 4} players
        </p>
        <span className={`room-status ${effectiveStatus}`}>{effectiveStatus}</span>
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
          {isHost ? (
            <div className="room-menu-section">
              <p className="room-menu-title">Host</p>
              <button
                type="button"
                onClick={() =>
                  sendRoomEvent('game:start', {
                    code: roomCode,
                    player_id: playerId,
                    max_games: maxGames,
                  })
                }
              >
                Start game
              </button>

              <button type="button">Close room</button>
            </div>
          ) : null}
          <div className="room-menu-section">
            <p className="room-menu-title">Player</p>
            {!isHost ? <button type="button">Ready</button> : null}
            <button type="button">Change name</button>
            <button type="button">Leave room</button>
          </div>
        </aside>
      </div>

      {/* ================================
      Waiting screen 
      ===================================*/}
      {isWaiting ? (
        <section className="room-waiting">
          <div className="room-waiting-card">
            <p className="room-waiting-title">Waiting room</p>
            <div className="room-code">
              <span>Room code</span>
              <strong>{room?.code ?? roomCode}</strong>
            </div>
            <div className="room-waiting-actions">
              <button type="button" onClick={handleCopyRoomCode}>
                Copy code
              </button>

              {isHost ? (
                <button
                  type="button"
                  className="primary"
                  onClick={() =>
                    sendRoomEvent('game:start', {
                      code: roomCode,
                      player_id: playerId,
                      max_games: maxGames,
                    })
                  }
                >
                  Start game
                </button>
              ) : (
                <button
                  type="button"
                  className={`primary${currentPlayer?.is_ready ? ' ready' : ''}`}
                  disabled={currentPlayer?.is_ready}
                  onClick={() =>
                    sendRoomEvent('player:ready', {
                      code: roomCode,
                      player_id: playerId,
                      is_ready: true,
                    })
                  }
                >
                  {currentPlayer?.is_ready ? 'Ready ✓' : 'Ready'}
                </button>
              )}
            </div>
            <p className="room-waiting-note">
              Waiting for players to join. Host can start when ready.
            </p>
          </div>

          {isHost ? (
            <div className="room-config">
              <label>
                Number of games
                <input
                  type="number"
                  min={1}
                  max={99}
                  value={maxGames}
                  onChange={(event) => {
                    setMaxGamesTouched(true)
                    setMaxGames(Number(event.target.value) || 1)
                  }}
                />
              </label>
            </div>
          ) : null}

          <div className="room-waiting-list">
            {players.map((player) => (
              <div key={player.id} className="room-waiting-player">
                <div>
                  <p className="room-player-name">{player.name}</p>
                  <p className="room-player-chip">{player.score} coins</p>
                </div>
                <span className={`room-waiting-pill ${player.is_ready ? 'ready' : ''}`}>
                  {player.is_ready ? 'Ready' : 'Waiting'}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : (
        // Gameplay screen
        <>
          <section className="room-players">
            {players
              .filter((player) => player.id !== playerId)
              .map((player) => (
              <article
                key={player.id}
                className={`room-player${player.id === gameState?.current_turn ? ' active' : ''}`}
              >
                <div>
                  <p className="room-player-name">{player.name}</p>
                  <p className="room-player-chip">{player.score} coins</p>
                </div>
                {player.id === gameState?.current_turn ? (
                  <span className="room-player-turn" aria-label="Current turn">
                    Turn
                  </span>
                ) : null}
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
            <p className="room-current-label">Your player</p>
            <div className="room-current-card">
                <div>
                    <p className="room-player-name">{currentPlayer?.name ?? 'You'}</p>
                    <p className="room-player-chip">{currentPlayer?.score ?? 0} coins</p>
                </div>
                {currentPlayer?.id === gameState?.current_turn ? (
                    <span className="room-current-pill">Turn</span>
                ) : null}
                <span className="room-current-pill">You</span>
            </div>
          </section>
        </>
      )}
    </div>
  )
}

export default Room
