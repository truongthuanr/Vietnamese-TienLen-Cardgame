import { Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import HomeChoice from './pages/HomeChoice'
import Home from './pages/Home'
import Lobby from './pages/Lobby'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/create" element={<Home />} />
      <Route path="/home" element={<HomeChoice />} />
      <Route path="/lobby" element={<Lobby />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
