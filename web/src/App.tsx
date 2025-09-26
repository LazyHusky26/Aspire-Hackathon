import React, { DragEvent, useMemo, useRef, useState } from 'react'
import axios from 'axios'
import { useAuthContext } from './contexts/AuthContext'
import { csrfService } from './services/csrf'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

type Row = Record<string, any>

type StagedFile = { file: File, path: string }

export default function App() {
	const [rows, setRows] = useState<Row[]>([])
	const [loading, setLoading] = useState(false)
	const [staged, setStaged] = useState<StagedFile[]>([])
	const [dragOver, setDragOver] = useState(false)
	const fileInputRef = useRef<HTMLInputElement | null>(null)
	const dirInputRef = useRef<HTMLInputElement | null>(null)
	const { user, logout, token, expiresAt } = useAuthContext()

	const headers = useMemo(() => {
		const allKeys = new Set<string>()
		rows.forEach(r => Object.keys(r).forEach(k => allKeys.add(k)))
		return Array.from(allKeys)
	}, [rows])

	function addFiles(list: FileList | null) {
		if (!list) return
		const accepted = Array.from(list).filter(f => /\.(pdf|docx|txt)$/i.test(f.name))
		const mapped: StagedFile[] = accepted.map(f => ({ file: f, path: (f as any).webkitRelativePath || f.name }))
		setStaged(prev => [...prev, ...mapped])
	}

	function onDrop(e: DragEvent<HTMLDivElement>) {
		e.preventDefault()
		setDragOver(false)
		addFiles(e.dataTransfer.files)
	}

	async function startParse() {
		if (staged.length === 0) return
		setLoading(true)
		try {
			// Get CSRF token for API request
			const csrfToken = await csrfService.getApiCSRFToken()
			
			const formData = new FormData()
			staged.forEach(sf => formData.append('files', sf.file, sf.path))
			formData.append('use_spacy', 'true')
			
			const res = await axios.post(`${API_BASE}/parse`, formData, {
				headers: { 
					'Content-Type': 'multipart/form-data',
					...(token && { 'Authorization': `Bearer ${token}` }),
					...csrfService.getApiHeaders()
				},
			})
			setRows(res.data.rows || [])
		} catch (error: any) {
			console.error('Parse error:', error)
			if (error.response?.status === 401) {
				logout() // Token expired, logout user
			} else if (error.response?.status === 403) {
				console.error('CSRF token validation failed')
				// Refresh CSRF token and retry
				csrfService.clearTokens()
			} else {
				// Show error to user
				alert(`Parse failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`)
			}
		} finally {
			setLoading(false)
		}
	}

	function clearStage() {
		setStaged([])
		setRows([])
	}

	// Calculate time remaining for display
	const timeRemaining = useMemo(() => {
		if (!expiresAt) return null
		const remaining = Math.max(0, expiresAt - Date.now())
		const minutes = Math.floor(remaining / 60000)
		const seconds = Math.floor((remaining % 60000) / 1000)
		return `${minutes}:${seconds.toString().padStart(2, '0')}`
	}, [expiresAt])

	// Update time remaining every second
	React.useEffect(() => {
		if (!expiresAt) return
		const interval = setInterval(() => {
			// Force re-render to update time display
		}, 1000)
		return () => clearInterval(interval)
	}, [expiresAt])

	async function download(type: 'csv' | 'xlsx') {
		if (rows.length === 0) return
		try {
			// Note: Export endpoints don't need CSRF tokens as they're read-only operations
			const url = type === 'csv' ? `${API_BASE}/export/csv` : `${API_BASE}/export/xlsx`
			const res = await axios.post(url, rows, { 
				responseType: 'blob',
				headers: {
					...(token && { 'Authorization': `Bearer ${token}` })
				}
			})
			const blob = new Blob([res.data])
			const a = document.createElement('a')
			a.href = URL.createObjectURL(blob)
			a.download = type === 'csv' ? 'candidates.csv' : 'candidates.xlsx'
			a.click()
			URL.revokeObjectURL(a.href)
		} catch (error: any) {
			if (error.response?.status === 401) {
				logout() // Token expired, logout user
			}
		}
	}

	return (
		<div className="page">
			<header className="header">
				<div className="header-left">
					<div className="title">Resume Parser</div>
					<a href="/research" className="research-btn-header">🤖 AI Research</a>
				</div>
				<div className="actions">
					<div className="user-info">
						<span className="user-name">Welcome, {user?.name}</span>
						{timeRemaining && (
							<span className="token-timer">Session: {timeRemaining}</span>
						)}
					</div>
					<button className="logout" onClick={logout}>Logout</button>
				</div>
			</header>

			<div className="content grid">
				<section className="panel panel-upload">
					<div className="panel-head">
						<div className="panel-title">Upload</div>
						<div>
							<button className="upload" onClick={() => fileInputRef.current?.click()} disabled={loading}>Add Files</button>
							<button className="btn" onClick={() => dirInputRef.current?.click()} disabled={loading}>Add Folder</button>
							<input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.txt" style={{ display:'none' }} onChange={e => addFiles(e.target.files)} />
							<input ref={dirInputRef} type="file" multiple style={{ display:'none' }} onChange={e => addFiles(e.target.files)} {...{ webkitdirectory: '' } as any} />
						</div>
					</div>
					<div
						className={`dropzone ${dragOver ? 'over' : ''}`}
						onDragOver={e => { e.preventDefault(); setDragOver(true) }}
						onDragLeave={() => setDragOver(false)}
						onDrop={onDrop}
					>
						<div className="dz-icon">⬆</div>
						<div className="dz-title">Drag & drop files here</div>
						<div className="dz-sub">or use Add Files / Add Folder</div>
					</div>
				</section>

				<section className="panel panel-results wide">
					<div className="panel-head">
						<div className="panel-title">Parsed Results {rows.length ? `(${rows.length})` : ''}</div>
						<button className="upload" onClick={startParse} disabled={loading || staged.length===0}>{loading ? 'Parsing...' : 'Start Parse'}</button>
					</div>
					{rows.length === 0 ? (
						<div className="empty">Results will appear here after parsing.</div>
					) : (
						<>
							<div className="toolbar">
								<button className="btn" onClick={() => download('csv')}>Download CSV</button>
								<button className="btn" onClick={() => download('xlsx')}>Download Excel</button>
								<div className="count">{rows.length} resumes</div>
							</div>
							<div className="table-wrap results">
								<table className="table">
									<thead>
										<tr>
											{headers.map(h => (
												<th key={h} className={/score|years|duration|count/i.test(h) ? 'num' : ''}>{h}</th>
											))}
										</tr>
									</thead>
									<tbody>
										{rows.map((r, i) => (
											<tr key={i}>
												{headers.map(h => (
													<td key={h} className={/score|years|duration|count/i.test(h) ? 'num' : ''}>{String(r[h] ?? '')}</td>
												))}
											</tr>
										))}
									</tbody>
								</table>
							</div>
						</>
					)}
				</section>

				<section className="panel panel-staged">
					<div className="panel-head">
						<div className="panel-title">Staged Files ({staged.length})</div>
						<button className="btn" onClick={clearStage} disabled={loading && staged.length===0}>Clear</button>
					</div>
					{staged.length === 0 ? (
						<div className="empty">Add files or a folder to stage for parsing</div>
					) : (
						<ul className="filelist">
							{staged.map((sf, i) => (
								<li key={i}>{sf.path}</li>
							))}
						</ul>
					)}
				</section>
			</div>
		</div>
	)
}
