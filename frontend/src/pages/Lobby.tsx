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
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">TL</span>
          <div>
            <p className="brand-title">Tien Len Lobby</p>
            <p className="brand-subtitle">Nhanh, nhe, khong can tai khoan</p>
          </div>
        </div>
        <div className="header-actions">
          <div className="user-chip">User: {user.name || 'Guest'}</div>
          <button className="ghost-button" type="button">
            How to play
          </button>
          <button className="primary-button" type="button">
            Create room
          </button>
        </div>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">San choi danh bai truc tuyen</p>
          <h1>
            Lap phong nhanh,
            <span> vao tran chi voi 1 ma phong.</span>
          </h1>
          <p className="hero-copy">
            Chon so nguoi choi, dat mat khau tuy chon, va san sang danh Tien Len
            voi ban be trong vai giay.
          </p>
          <div className="hero-tags">
            <span>2-4 nguoi</span>
            <span>Ma phong 6-8 ky tu</span>
            <span>Trang thai waiting - ready</span>
          </div>
        </div>
        <div className="hero-panel">
          <div className="stat">
            <p>Rooms online</p>
            <strong>24</strong>
          </div>
          <div className="stat">
            <p>Average join</p>
            <strong>12s</strong>
          </div>
          <div className="stat">
            <p>Latency</p>
            <strong>Low</strong>
          </div>
        </div>
      </section>

      <section className="lobby-grid">
        <form className="panel" onSubmit={handleCreate}>
          <div className="panel-header">
            <h2>Tao phong moi</h2>
            <span className="pill">Host</span>
          </div>
          <label>
            Ten nguoi choi
            <input placeholder="VD: Minh, An, Linh" defaultValue={user.name} required />
          </label>
          <label>
            So luong nguoi choi
            <select defaultValue="4">
              <option value="2">2 nguoi</option>
              <option value="3">3 nguoi</option>
              <option value="4">4 nguoi</option>
            </select>
          </label>
          <label>
            Mat khau (tuy chon)
            <input placeholder="De trong neu khong can" type="password" />
          </label>
          <button className="primary-button" type="submit">
            Tao phong va nhan ma
          </button>
          <p className="panel-note">
            Sau khi tao, ban se la host va co the bat dau van khi du nguoi.
          </p>
        </form>

        <form className="panel highlight" onSubmit={handleJoin}>
          <div className="panel-header">
            <h2>Tham gia phong</h2>
            <span className="pill">Join</span>
          </div>
          <label>
            Ten nguoi choi
            <input placeholder="VD: Huy, Phuong" defaultValue={user.name} required />
          </label>
          <label>
            Ma phong
            <input placeholder="ABC123" maxLength={8} required />
          </label>
          <label>
            Mat khau phong (neu co)
            <input placeholder="••••••" type="password" />
          </label>
          <button className="primary-button" type="submit">
            Vao phong ngay
          </button>
          <p className="panel-note">
            Neu phong day, hay tao phong moi hoac thu ma khac.
          </p>
        </form>

        <div className="panel info">
          <h3>Quy trinh nhanh</h3>
          <ul>
            <li>Tao phong, nhan ma 6-8 ky tu.</li>
            <li>Gui ma phong cho ban be.</li>
            <li>Du 2-4 nguoi, host bat dau van.</li>
          </ul>
          <div className="info-footer">
            <p>Tuong thich mobile va desktop.</p>
            <button className="ghost-button" type="button">
              Xem luat co ban
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Lobby
