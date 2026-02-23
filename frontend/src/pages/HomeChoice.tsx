import { Navigate, useNavigate } from 'react-router-dom'
import { useStoredUser } from '../hooks/useStoredUser'

const HomeChoice = () => {
  const navigate = useNavigate()
  const { user, clearUser } = useStoredUser()

  if (!user) {
    return <Navigate to="/create" replace />
  }

  return (
    <div className="app home-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">TL</span>
          <div>
            <p className="brand-title">Tien Len</p>
            <p className="brand-subtitle">Chon cach vao san</p>
          </div>
        </div>
      </header>

      <section className="home-choice">
        <div className="panel">
          <div className="panel-header">
            <h2>Tiep tuc</h2>
            <span className="pill">Saved</span>
          </div>
          <div className="home-user">
            <div>
              <p className="home-user-label">Ten hien tai</p>
              <strong>{user.name}</strong>
            </div>
            <button
              className="primary-button"
              type="button"
              onClick={() => navigate('/lobby')}
            >
              Continue
            </button>
          </div>
          <p className="panel-note">
            Tiep tuc voi ten nay de vao sanh va tao hoac join phong.
          </p>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Tao user moi</h2>
            <span className="pill">New</span>
          </div>
          <p className="panel-note">
            Doi ten, tao user khac de choi voi ban be.
          </p>
          <button
            className="ghost-button"
            type="button"
            onClick={() => {
              clearUser()
              navigate('/create')
            }}
          >
            Tao user
          </button>
        </div>
      </section>
    </div>
  )
}

export default HomeChoice
