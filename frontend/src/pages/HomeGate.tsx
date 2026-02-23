import { Navigate } from 'react-router-dom'
import { useStoredUser } from '../hooks/useStoredUser'

const HomeGate = () => {
  const { user } = useStoredUser()

  if (user) {
    return <Navigate to="/home" replace />
  }

  return <Navigate to="/create" replace />
}

export default HomeGate
