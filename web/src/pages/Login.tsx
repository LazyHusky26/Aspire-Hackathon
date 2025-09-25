import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuthContext } from '../contexts/AuthContext'
import { csrfService } from '../services/csrf'

const API_AUTH = import.meta.env.VITE_AUTH_BASE || 'http://127.0.0.1:4000'

type Step = 'creds' | 'otp'

export default function Login() {
	const [step, setStep] = useState<Step>('creds')
	const [email, setEmail] = useState('')
	const [password, setPassword] = useState('')
	const [otp, setOtp] = useState('')
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState('')
	const [previewUrl, setPreviewUrl] = useState('')
	const { login, isAuthenticated } = useAuthContext()
	const navigate = useNavigate()

	// Redirect if already authenticated
	useEffect(() => {
		if (isAuthenticated) {
			navigate('/app')
		}
	}, [isAuthenticated, navigate])

	async function submitCreds(e: React.FormEvent) {
		e.preventDefault()
		setLoading(true)
		setError('')
		try {
			// Get CSRF token before making the request
			await csrfService.getAuthCSRFToken()
			
			const res = await axios.post(`${API_AUTH}/auth/login`, 
				{ email, password },
				{ 
					headers: {
						'Content-Type': 'application/json',
						...csrfService.getAuthHeaders()
					}
				}
			)
			setStep('otp')
			setPreviewUrl(res.data.previewUrl || '')
		} catch (err: any) {
			const resp = err?.response?.data
			console.error('Login error:', err)
			setError(resp?.error || 'Login failed')
		} finally {
			setLoading(false)
		}
	}

	async function submitOtp(e: React.FormEvent) {
		e.preventDefault()
		setLoading(true)
		setError('')
		try {
			const res = await axios.post(`${API_AUTH}/auth/verify-otp`, 
				{ email, code: otp },
				{ 
					headers: {
						'Content-Type': 'application/json',
						...csrfService.getAuthHeaders()
					}
				}
			)
			login(res.data.token, res.data.user, res.data.expiresAt)
			navigate('/app')
		} catch (err: any) {
			const resp = err?.response?.data
			console.error('OTP verification error:', err)
			setError(resp?.error || 'Verification failed')
		} finally {
			setLoading(false)
		}
	}

	return (
		<div className="auth-page">
			<div className="auth-card">
				<div className="auth-title">Sign in</div>
				{error && <div className="error">{error}</div>}
				{step === 'creds' ? (
					<form onSubmit={submitCreds} className="auth-form">
						<label>Email</label>
						<input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
						<label>Password</label>
						<input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
						<button className="upload" type="submit" disabled={loading}>{loading ? 'Continue...' : 'Continue'}</button>
					</form>
				) : (
					<form onSubmit={submitOtp} className="auth-form">
						<label>Verification code sent to {email}</label>
						<input value={otp} onChange={e => setOtp(e.target.value)} placeholder="Enter 6-digit code" required />
						{previewUrl && (
							<a href={previewUrl} target="_blank" rel="noreferrer" style={{ color: '#8f9bff' }}>Open Ethereal preview</a>
						)}
						<button className="upload" type="submit" disabled={loading}>{loading ? 'Verifying...' : 'Verify & Sign in'}</button>
					</form>
				)}
				<div className="auth-switch">Don't have an account? <Link to="/register">Create one</Link></div>
			</div>
		</div>
	)
}
