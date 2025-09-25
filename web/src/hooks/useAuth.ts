import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const API_AUTH = import.meta.env.VITE_AUTH_BASE || 'http://127.0.0.1:4000'

interface User {
  id: string
  name: string
  email: string
}

interface AuthState {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  expiresAt: number | null
}

export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    token: null,
    expiresAt: null
  })
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    localStorage.removeItem('auth_expires_at')
    setAuthState({
      isAuthenticated: false,
      user: null,
      token: null,
      expiresAt: null
    })
    // Use setTimeout to avoid navigation issues during render
    setTimeout(() => navigate('/login'), 0)
  }, [navigate])

  const login = useCallback((token: string, user: User, expiresAt: number) => {
    localStorage.setItem('auth_token', token)
    localStorage.setItem('auth_user', JSON.stringify(user))
    localStorage.setItem('auth_expires_at', expiresAt.toString())
    setAuthState({
      isAuthenticated: true,
      user,
      token,
      expiresAt
    })
  }, [])

  const checkTokenExpiry = useCallback(() => {
    const expiresAt = authState.expiresAt
    if (expiresAt && Date.now() >= expiresAt) {
      console.log('Token expired, logging out...')
      logout()
      return false
    }
    return true
  }, [authState.expiresAt, logout])

  const refreshToken = useCallback(async () => {
    if (!authState.token) return false

    try {
      const response = await axios.post(`${API_AUTH}/auth/refresh-token`, {}, {
        headers: { Authorization: `Bearer ${authState.token}` }
      })

      const { token, expiresAt, user } = response.data
      login(token, user, expiresAt)
      return true
    } catch (error) {
      console.log('Token refresh failed, logging out...')
      logout()
      return false
    }
  }, [authState.token, login, logout])

  // Initialize auth state from localStorage
  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    const userStr = localStorage.getItem('auth_user')
    const expiresAtStr = localStorage.getItem('auth_expires_at')

    if (token && userStr && expiresAtStr) {
      const user = JSON.parse(userStr)
      const expiresAt = parseInt(expiresAtStr)

      // Check if token is expired
      if (Date.now() >= expiresAt) {
        logout()
      } else {
        setAuthState({
          isAuthenticated: true,
          user,
          token,
          expiresAt
        })
      }
    }
    setIsLoading(false)
  }, [logout])

  // Set up automatic token expiry checking
  useEffect(() => {
    if (!authState.isAuthenticated || !authState.expiresAt) return

    const timeUntilExpiry = authState.expiresAt - Date.now()

    // If token expires in less than 30 seconds, try to refresh
    if (timeUntilExpiry < 30000 && timeUntilExpiry > 0) {
      refreshToken()
      return
    }

    // Set timeout to check expiry
    const timeout = setTimeout(() => {
      checkTokenExpiry()
    }, Math.max(timeUntilExpiry, 1000))

    return () => clearTimeout(timeout)
  }, [authState.isAuthenticated, authState.expiresAt, checkTokenExpiry, refreshToken])

  // Set up periodic token refresh (every 8 minutes)
  useEffect(() => {
    if (!authState.isAuthenticated) return

    const interval = setInterval(() => {
      if (authState.expiresAt && Date.now() < authState.expiresAt - 60000) { // Refresh 1 minute before expiry
        refreshToken()
      }
    }, 8 * 60 * 1000) // Check every 8 minutes

    return () => clearInterval(interval)
  }, [authState.isAuthenticated, authState.expiresAt, refreshToken])

  return {
    ...authState,
    isLoading,
    login,
    logout,
    checkTokenExpiry,
    refreshToken
  }
}