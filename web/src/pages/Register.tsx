import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { csrfService } from '../services/csrf'

const API_AUTH = import.meta.env.VITE_AUTH_BASE || 'http://127.0.0.1:4000'

export default function Register() {
	const [name, setName] = useState('')
	const [email, setEmail] = useState('')
	const [password, setPassword] = useState('')
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState('')
	const [issues, setIssues] = useState<{ path: string; message: string }[]>([])
	const navigate = useNavigate()

	async function submit(e: React.FormEvent) {
		e.preventDefault()
		setLoading(true)
		setError('')
		setIssues([])
		try {
			// Get CSRF token before making the request
			await csrfService.getAuthCSRFToken()
			
			await axios.post(`${API_AUTH}/auth/register`, 
				{ name, email, password },
				{ 
					headers: {
						'Content-Type': 'application/json',
						...csrfService.getAuthHeaders()
					}
				}
			)
			navigate('/login')
		} catch (err: any) {
			const resp = err?.response?.data
			console.error('Registration error:', err)
			setError(resp?.error || 'Registration failed')
			setIssues(resp?.issues || [])
		} finally {
			setLoading(false)
		}
	}

	return (
		<div className="auth-page">
			<div className="auth-card">
				<div className="auth-title">Create account</div>
				{error && <div className="error">{error}</div>}
				{issues.length > 0 && (
					<div className="error">
						<ul style={{ margin: 0, paddingLeft: 18 }}>
							{issues.map((i, idx) => (
								<li key={idx}>{i.message}</li>
							))}
						</ul>
					</div>
				)}
				<form onSubmit={submit} className="auth-form">
					<label>Name</label>
					<input value={name} onChange={e => setName(e.target.value)} required />
					<label>Email</label>
					<input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
					<label>Password</label>
					<input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
					<button className="upload" type="submit" disabled={loading}>{loading ? 'Creating...' : 'Create account'}</button>
				</form>
				<div className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></div>
			</div>
		</div>
	)
}
