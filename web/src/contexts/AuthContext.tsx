import React, { createContext, useContext, ReactNode } from 'react'
import { useAuth } from '../hooks/useAuth'

interface User {
  id: string
  name: string
  email: string
}

interface AuthContextType {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  expiresAt: number | null
  isLoading: boolean
  login: (token: string, user: User, expiresAt: number) => void
  logout: () => void
  checkTokenExpiry: () => boolean
  refreshToken: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const auth = useAuth()
  
  return (
    <AuthContext.Provider value={auth}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider')
  }
  return context
}