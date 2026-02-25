import type { FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useStoredUser } from '../hooks/useStoredUser'
import '../styles/lobby.css'

const ROOM_CODE_KEY = 'tienlen.room_code'
const ROOM_PLAYER_KEY = 'tienlen.room_player_id'

const Lobby = () => {
    const { user } = useStoredUser()
    const navigate = useNavigate()

    const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        if (!user) {
            return
        }
        const formData = new FormData(event.currentTarget)
        const maxPlayers = Number(formData.get('max_players') ?? 4)
        const password = String(formData.get('password') ?? '').trim()
        const apiBase =
            import.meta.env.VITE_API_BASE ?? `http://${window.location.hostname}:8000`

        const payload: { user_id: string; max_players: number; password?: string } = {
            user_id: user.id,
            max_players: maxPlayers,
        }
        if (password) {
            payload.password = password
        }

        try {
            const response = await fetch(`${apiBase}/rooms`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
            if (!response.ok) {
                console.error('Create room failed', await response.json())
                return
            }
            const data = (await response.json()) as {
                room: { code: string }
                player_id: string
            }
            sessionStorage.setItem(ROOM_CODE_KEY, data.room.code)
            sessionStorage.setItem(ROOM_PLAYER_KEY, data.player_id)
            navigate(`/room?code=${data.room.code}`)
        } catch (error) {
            console.error('Create room error', error)
        }
    }

    const handleJoin = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        if (!user) {
            return
        }
        const formData = new FormData(event.currentTarget)
        const code = String(formData.get('code') ?? '').trim().toUpperCase()
        const password = String(formData.get('password') ?? '').trim()
        if (!code) {
            return
        }
        const apiBase =
            import.meta.env.VITE_API_BASE ?? `http://${window.location.hostname}:8000`

        const payload: { user_id: string; password?: string } = {
            user_id: user.id,
        }
        if (password) {
            payload.password = password
        }

        try {
            const response = await fetch(`${apiBase}/rooms/${code}/join`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
            if (!response.ok) {
                console.error('Join room failed', await response.json())
                return
            }
            const data = (await response.json()) as {
                room: { code: string }
                player_id: string
            }
            sessionStorage.setItem(ROOM_CODE_KEY, data.room.code)
            sessionStorage.setItem(ROOM_PLAYER_KEY, data.player_id)
            navigate(`/room?code=${data.room.code}`)
        } catch (error) {
            console.error('Join room error', error)
        }
    }

    if (!user) {
        return <Navigate to="/" replace />
    }

    return (
        <div className="app lobby-shell">
            <div className="sparkle-field" aria-hidden="true">
                <span className="sparkle s1" />
                <span className="sparkle s2" />
                <span className="sparkle s3" />
                <span className="sparkle s4" />
                <span className="sparkle s5" />
                <span className="sparkle s6" />
            </div>

            <header className="lobby-header">
                <p className="lobby-title">LOBBY</p>
                <p className="lobby-subtitle">Create a room or join with a code</p>
            </header>

            <section className="lobby-panel">

                <form className="lobby-section" onSubmit={handleJoin}>
                    <h2>Join room</h2>
                    <label className="lobby-label">
                        Room code
                        <input name="code" placeholder="ABC123" maxLength={8} required />
                    </label>
                    <label className="lobby-label">
                        Password (optional)
                        <input name="password" placeholder="••••••" type="password" />
                    </label>
                    <button className="lobby-button" type="submit">
                        Join
                    </button>
                </form>

                <div className="lobby-divider">
                    <span>or</span>
                </div>

                <form className="lobby-section" onSubmit={handleCreate}>
                    <h2>Create room</h2>
                    <label className="lobby-label">
                        Number of players
                        <select name="max_players" defaultValue="4">
                            <option value="2">2 players</option>
                            <option value="3">3 players</option>
                            <option value="4">4 players</option>
                        </select>
                    </label>
                    <label className="lobby-label">
                        Room password (optional)
                        <input name="password" placeholder="Enter room password" type="password" />
                    </label>
                    <button className="lobby-button" type="submit">
                        Create room
                    </button>
                </form>
            </section>
        </div>
    )
}

export default Lobby
