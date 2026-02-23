import type { FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useStoredUser } from '../hooks/useStoredUser'

const Lobby = () => {
    const { user } = useStoredUser()

    const handleCreate = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
    }

    const handleJoin = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
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
                        <input placeholder="ABC123" maxLength={8} required />
                    </label>
                    <label className="lobby-label">
                        Password (optional)
                        <input placeholder="••••••" type="password" />
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
                        <select defaultValue="4">
                            <option value="2">2 players</option>
                            <option value="3">3 players</option>
                            <option value="4">4 players</option>
                        </select>
                    </label>
                    <label className="lobby-label">
                        Room password (optional)
                        <input placeholder="Enter room password" type="password" />
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
