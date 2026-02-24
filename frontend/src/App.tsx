import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import './App.css'
import HomeChoice from './pages/HomeChoice'
import Home from './pages/Home'
import Lobby from './pages/Lobby'
import Room from './pages/Room'

function App() {
  const location = useLocation()

  useEffect(() => {
    console.log('[route]', location.pathname, '| window', window.location.pathname)
  }, [location.pathname])

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/home" element={<HomeChoice />} />
      <Route path="/lobby" element={<Lobby />} />
      <Route path="/room" element={<Room />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
