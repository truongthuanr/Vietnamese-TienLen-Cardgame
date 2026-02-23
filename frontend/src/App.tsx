import { Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import HomeChoice from './pages/HomeChoice'
import HomeCreate from './pages/HomeCreate'
import HomeGate from './pages/HomeGate'
import Lobby from './pages/Lobby'

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeGate />} />
      <Route path="/create" element={<HomeCreate />} />
      <Route path="/home" element={<HomeChoice />} />
      <Route path="/lobby" element={<Lobby />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
