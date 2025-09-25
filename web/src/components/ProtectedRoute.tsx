import React, { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthContext } from '../contexts/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, checkTokenExpiry } = useAuthContext()

  useEffect(() => {
    if (isAuthenticated) {
      checkTokenExpiry()
    }
  }, [isAuthenticated, checkTokenExpiry])

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <div>Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}