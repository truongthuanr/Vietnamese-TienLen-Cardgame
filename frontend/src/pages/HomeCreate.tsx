import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { createUserId, useStoredUser } from '../hooks/useStoredUser'

const HomeCreate = () => {
  const navigate = useNavigate()
  const { saveUser } = useStoredUser()

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
    <div className="app home-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">TL</span>
          <div>
            <p className="brand-title">Tien Len</p>
            <p className="brand-subtitle">Tao user nhanh de vao san</p>
          </div>
        </div>
      </header>

      <section className="home-card">
        <div className="home-copy">
          <p className="eyebrow">Bat dau trong 10 giay</p>
          <h1>
            Tao user,
            <span> roi vao san choi.</span>
          </h1>
          <p className="hero-copy">
            Chi can nhap ten. Backend se tao user_id tu dong va luu tren trinh
            duyet cua ban.
          </p>
        </div>
        <form className="panel" onSubmit={handleCreateUser}>
          <div className="panel-header">
            <h2>Tao user</h2>
            <span className="pill">New</span>
          </div>
          <label>
            Ten nguoi choi
            <input name="name" placeholder="VD: Khoa, Nhi" required />
          </label>
          <button className="primary-button" type="submit">
            Luu ten va vao sanh
          </button>
          <p className="panel-note">
            Neu da co user, ban co the tiep tuc tu man hinh truoc.
          </p>
        </form>
      </section>
    </div>
  )
}

export default HomeCreate
