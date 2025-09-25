import React, { useState, useMemo } from 'react'
import axios from 'axios'
import { useAuthContext } from '../contexts/AuthContext'

const API_BASE = 'http://127.0.0.1:8001'

interface ResearchResult {
    question: string
    report: string
    sources: string[]
    timestamp: string
}

export default function Research() {
    const [question, setQuestion] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<ResearchResult | null>(null)
    const [error, setError] = useState('')
    const { user, logout, expiresAt } = useAuthContext()

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

    async function handleResearch() {
        if (!question.trim()) return

        setLoading(true)
        setError('')
        setResult(null)

        try {
            const response = await axios.post(`${API_BASE}/research`, {
                question: question.trim()
            })
            setResult(response.data)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Research failed. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    function handleKeyPress(e: React.KeyboardEvent) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleResearch()
        }
    }

    function clearResults() {
        setResult(null)
        setError('')
        setQuestion('')
    }

    function downloadReport() {
        if (!result) return

        const content = `# Research Report\n\n**Question:** ${result.question}\n\n**Generated:** ${new Date(result.timestamp).toLocaleString()}\n\n---\n\n${result.report}\n\n## Sources\n\n${result.sources.map((source, i) => `${i + 1}. ${source}`).join('\n')}`

        const blob = new Blob([content], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `research_report_${Date.now()}.md`
        a.click()
        URL.revokeObjectURL(url)
    }

    // Simple markdown renderer for basic formatting
    function renderMarkdown(text: string) {
        return text
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^\* (.*$)/gim, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
            .replace(/\n/g, '<br>')
    }

    return (
        <div className="page research-page">
            <header className="header">
                <div className="header-left">
                    <div className="title">AI Research Agent</div>
                    <a href="/app" className="parser-btn-header">📄 Resume Parser</a>
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

            <div className="content research-content">
                <section className="panel panel-input">
                    <div className="panel-head">
                        <div className="panel-title">Research Question</div>
                        {result && (
                            <button className="btn-secondary" onClick={clearResults}>New Question</button>
                        )}
                    </div>

                    <div className="input-section">
                        <textarea
                            className="question-input"
                            placeholder="What would you like me to research? (e.g., 'What are the latest AI trends?', 'Benefits of renewable energy', 'How does blockchain work?')"
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            onKeyPress={handleKeyPress}
                            disabled={loading}
                            rows={3}
                        />
                        <button
                            className="research-btn"
                            onClick={handleResearch}
                            disabled={loading || !question.trim()}
                        >
                            {loading ? '🔍 Researching...' : '🚀 Start Research'}
                        </button>
                    </div>

                    {error && (
                        <div className="error-message">
                            ❌ {error}
                        </div>
                    )}
                </section>

                {loading && (
                    <section className="panel panel-loading">
                        <div className="loading-content">
                            <div className="loading-spinner"></div>
                            <div className="loading-text">
                                <div className="loading-title">🔍 Researching your question...</div>
                                <div className="loading-steps">
                                    <div>📋 Planning research strategy</div>
                                    <div>🕵️ Gathering information from web sources</div>
                                    <div>🤖 Analyzing data with AI</div>
                                    <div>📝 Writing comprehensive report</div>
                                </div>
                            </div>
                        </div>
                    </section>
                )}

                {result && (
                    <section className="panel panel-results">
                        <div className="panel-head">
                            <div className="panel-title">Research Report</div>
                            <div className="result-actions">
                                <button className="btn-secondary" onClick={downloadReport}>
                                    💾 Download Report
                                </button>
                                <div className="timestamp">
                                    Generated: {new Date(result.timestamp).toLocaleString()}
                                </div>
                            </div>
                        </div>

                        <div className="question-display">
                            <strong>Question:</strong> {result.question}
                        </div>

                        <div className="report-content">
                            <div dangerouslySetInnerHTML={{ __html: renderMarkdown(result.report) }} />
                        </div>

                        {result.sources.length > 0 && (
                            <div className="sources-section">
                                <h3>📚 Sources</h3>
                                <ul className="sources-list">
                                    {result.sources.map((source, index) => (
                                        <li key={index}>
                                            <a href={source} target="_blank" rel="noopener noreferrer">
                                                {source}
                                            </a>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </section>
                )}

                {!loading && !result && !error && (
                    <section className="panel panel-examples">
                        <div className="panel-title">💡 Example Questions</div>
                        <div className="examples-grid">
                            {[
                                "What are the latest developments in artificial intelligence?",
                                "How does climate change affect global agriculture?",
                                "What are the benefits and risks of cryptocurrency?",
                                "How do electric vehicles compare to traditional cars?",
                                "What are the most effective renewable energy sources?",
                                "How does machine learning work in healthcare?"
                            ].map((example, index) => (
                                <button
                                    key={index}
                                    className="example-btn"
                                    onClick={() => setQuestion(example)}
                                >
                                    {example}
                                </button>
                            ))}
                        </div>
                    </section>
                )}
            </div>
        </div>
    )
}