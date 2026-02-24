import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStoredUser } from '../hooks/useStoredUser'
import '../styles/home.css'

const getApiBase = () =>
  import.meta.env.VITE_API_BASE ?? `http://${window.location.hostname}:8000`

const Home = () => {
  const navigate = useNavigate()
  const { user, saveUser, clearUser } = useStoredUser()
  const [isVerifying, setIsVerifying] = useState(false)

  useEffect(() => {
    if (!user) {
      return
    }

    let canceled = false

    const verifyUser = async () => {
      setIsVerifying(true)
      try {
        const response = await fetch(`${getApiBase()}/users/${user.id}`)
        if (!response.ok) {
          if (response.status === 404) {
            clearUser()
          } else {
            console.error('Verify user failed', await response.json())
          }
          return
        }
        const data = (await response.json()) as { user: { id: string; name: string } }
        if (canceled) {
          return
        }
        if (data?.user?.id && data?.user?.name) {
          if (data.user.id !== user.id || data.user.name !== user.name) {
            saveUser({ id: data.user.id, name: data.user.name })
          }
        }
      } catch (error) {
        if (!canceled) {
          console.error('Verify user error', error)
        }
      } finally {
        if (!canceled) {
          setIsVerifying(false)
        }
      }
    }

    verifyUser()

    return () => {
      canceled = true
    }
  }, [user, clearUser, saveUser])

  const handleCreateUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const name = String(formData.get('name') ?? '').trim()
    if (!name) {
      return
    }
    const apiBase = getApiBase()
    try {
      const response = await fetch(`${apiBase}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      if (!response.ok) {
        console.error('Create user failed', await response.json())
        return
      }
      const data = (await response.json()) as { user: { id: string; name: string } }
      saveUser({ id: data.user.id, name: data.user.name })
      navigate('/lobby')
    } catch (error) {
      console.error('Create user error', error)
    }
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
        {user && isVerifying ? (
          <p className="home-create-saved-label">Checking saved user...</p>
        ) : user ? (
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
