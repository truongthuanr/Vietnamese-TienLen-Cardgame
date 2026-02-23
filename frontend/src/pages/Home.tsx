import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { createUserId, useStoredUser } from '../hooks/useStoredUser'

const Home = () => {
  const navigate = useNavigate()
  const { user, saveUser } = useStoredUser()

  const handleCreateUser = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const name = String(formData.get('name') ?? '').trim()
    if (!name) {
      return
    }
    const nextUser = { id: createUserId(), name }
    saveUser(nextUser)
    navigate('/lobby')
  }

  return (
    <div className="app home-create">
      <div className="sparkle-field" aria-hidden="true">
        <span className="sparkle s1" />
        <span className="sparkle s2" />
        <span className="sparkle s3" />
        <span className="sparkle s4" />
        <span className="sparkle s5" />
        <span className="sparkle s6" />
      </div>
      <header className="home-create-header">
        <p className="home-create-title">WEBGAME</p>
      </header>

      <section className="home-create-panel">
        {user ? (
          <div className="home-create-saved">
            <p className="home-create-saved-label">Play as</p>
            <div className="home-create-saved-row">
              <strong>{user.name}</strong>
              <button
                className="home-create-secondary"
                type="button"
                onClick={() => navigate('/lobby')}
              >
                Play
              </button>
            </div>
            <div className="home-create-divider">
              <span>or</span>
            </div>
          </div>
        ) : null}
        <h2>CREATE USERNAME</h2>
        <form className="home-create-form" onSubmit={handleCreateUser}>
          <label className="home-create-label" htmlFor="username">
            Enter username
          </label>
          <input id="username" name="name" placeholder="Enter username" required />
          <button className="home-create-button" type="submit">
            PLAY
          </button>
        </form>
      </section>
    </div>
  )
}

export default Home
