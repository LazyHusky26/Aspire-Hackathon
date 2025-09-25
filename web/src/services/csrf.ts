import axios from 'axios'

const API_AUTH = import.meta.env.VITE_AUTH_BASE || 'http://127.0.0.1:4000'
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

class CSRFService {
  private authToken: string | null = null
  private apiToken: string | null = null
  private sessionId: string

  constructor() {
    // Generate a session ID for this browser session
    this.sessionId = this.generateSessionId()
  }

  private generateSessionId(): string {
    return 'session_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36)
  }

  async getAuthCSRFToken(): Promise<string> {
    if (this.authToken) {
      console.log('Using cached auth CSRF token')
      return this.authToken
    }

    try {
      console.log('Fetching new auth CSRF token for session:', this.sessionId)
      const response = await axios.get(`${API_AUTH}/auth/csrf-token`, {
        headers: { 'X-Session-Id': this.sessionId }
      })
      this.authToken = response.data.csrfToken
      console.log('Got auth CSRF token:', this.authToken ? 'success' : 'failed')
      return this.authToken
    } catch (error) {
      console.error('Failed to get auth CSRF token:', error)
      throw new Error('Failed to get CSRF token')
    }
  }

  async getApiCSRFToken(): Promise<string> {
    if (this.apiToken) return this.apiToken

    try {
      const response = await axios.get(`${API_BASE}/csrf-token`, {
        headers: { 'X-Session-Id': this.sessionId }
      })
      this.apiToken = response.data.csrfToken
      return this.apiToken
    } catch (error) {
      console.error('Failed to get API CSRF token:', error)
      throw new Error('Failed to get CSRF token')
    }
  }

  getAuthHeaders(): Record<string, string> {
    const headers = {
      'X-Session-Id': this.sessionId,
      ...(this.authToken && { 'X-CSRF-Token': this.authToken })
    }
    console.log('Auth headers:', headers)
    return headers
  }

  getApiHeaders(): Record<string, string> {
    return {
      'X-Session-Id': this.sessionId,
      ...(this.apiToken && { 'X-CSRF-Token': this.apiToken })
    }
  }

  clearTokens(): void {
    this.authToken = null
    this.apiToken = null
  }
}

export const csrfService = new CSRFService()