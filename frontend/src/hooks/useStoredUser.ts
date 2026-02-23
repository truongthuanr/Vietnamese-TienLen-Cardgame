import { useState } from 'react'

export type UserInfo = {
  id: string
  name: string
}

const STORAGE_KEY = 'tienlen.user'

const readStoredUser = (): UserInfo | null => {
  if (typeof window === 'undefined') {
    return null
  }
  const stored = localStorage.getItem(STORAGE_KEY)
  if (!stored) {
    return null
  }
  try {
    const parsed = JSON.parse(stored) as UserInfo
    if (parsed?.id && parsed?.name) {
      return parsed
    }
  } catch {
    // Ignore parse errors and clear below.
  }
  localStorage.removeItem(STORAGE_KEY)
  return null
}

export const createUserId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `user_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

export const useStoredUser = () => {
  const [user, setUser] = useState<UserInfo | null>(() => readStoredUser())

  const saveUser = (next: UserInfo) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setUser(next)
  }

  const clearUser = () => {
    localStorage.removeItem(STORAGE_KEY)
    setUser(null)
  }

  return { user, saveUser, clearUser }
}
