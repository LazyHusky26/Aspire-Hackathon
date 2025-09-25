import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import App from './App'
import Research from './pages/Research'
import Login from './pages/Login'
import Register from './pages/Register'

export default function AppRoutes() {
	return (
		<Routes>
			<Route path="/" element={<Navigate to="/login" replace />} />
			<Route path="/login" element={<Login />} />
			<Route path="/register" element={<Register />} />
			<Route 
				path="/app" 
				element={
					<ProtectedRoute>
						<App />
					</ProtectedRoute>
				} 
			/>
			<Route 
				path="/research" 
				element={
					<ProtectedRoute>
						<Research />
					</ProtectedRoute>
				} 
			/>
		</Routes>
	)
}