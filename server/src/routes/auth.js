import { Router } from 'express'
import bcrypt from 'bcryptjs'
import jwt from 'jsonwebtoken'
import { z, ZodError } from 'zod'
import nodemailer from 'nodemailer'
import crypto from 'crypto'
import User from '../models/User.js'
import Otp from '../models/Otp.js'

const router = Router()

// JWT Secret validation - enforce strong secrets
const JWT_SECRET = (() => {
	const secret = process.env.JWT_SECRET
	if (!secret) {
		if (process.env.NODE_ENV === 'production') {
			throw new Error('JWT_SECRET environment variable is required in production')
		}
		console.warn('⚠️  WARNING: Using fallback JWT secret for development. Set JWT_SECRET env var for production.')
		return 'dev-fallback-secret-' + crypto.randomBytes(32).toString('hex')
	}
	if (secret.length < 32) {
		throw new Error('JWT_SECRET must be at least 32 characters long')
	}
	return secret
})()

// CSRF Token storage (in production, use Redis or database)
const csrfTokens = new Map()

// Generate CSRF token
function generateCSRFToken() {
	return crypto.randomBytes(32).toString('hex')
}

// CSRF Token validation middleware
function validateCSRF(req, res, next) {
	// Handle case-insensitive headers
	const token = req.headers['x-csrf-token'] || req.headers['X-CSRF-Token']
	const sessionId = req.headers['x-session-id'] || req.headers['X-Session-Id'] || req.ip
	
	console.log('CSRF Validation:', { token: token ? 'present' : 'missing', sessionId, storedTokens: Array.from(csrfTokens.keys()) })
	
	if (!token) {
		return res.status(403).json({ error: 'CSRF token required' })
	}
	
	const storedToken = csrfTokens.get(sessionId)
	if (!storedToken || storedToken !== token) {
		console.log('CSRF token mismatch:', { provided: token, stored: storedToken, sessionId })
		return res.status(403).json({ error: 'Invalid CSRF token' })
	}
	
	next()
}

// Get CSRF token endpoint
router.get('/csrf-token', (req, res) => {
	const sessionId = req.headers['x-session-id'] || req.headers['X-Session-Id'] || req.ip
	const token = generateCSRFToken()
	
	console.log('Generating CSRF token for session:', sessionId)
	
	// Store token with expiration (5 minutes)
	csrfTokens.set(sessionId, token)
	setTimeout(() => {
		csrfTokens.delete(sessionId)
		console.log('CSRF token expired for session:', sessionId)
	}, 5 * 60 * 1000)
	
	res.json({ csrfToken: token })
})

const registerSchema = z.object({
	name: z.string().min(2, 'Name must be at least 2 characters'),
	email: z.string().email('Please enter a valid email'),
	password: z.string().min(6, 'Password must be at least 6 characters')
})

const loginSchema = z.object({
	email: z.string().email('Please enter a valid email'),
	password: z.string().min(6, 'Password must be at least 6 characters')
})

const otpSchema = z.object({
	email: z.string().email('Please enter a valid email')
})

const verifyOtpSchema = z.object({
	email: z.string().email('Please enter a valid email'),
	code: z.string().min(4, 'Invalid code')
})

async function createEtherealTransporter() {
	if (process.env.ETHEREAL_USER && process.env.ETHEREAL_PASS) {
		const transporter = nodemailer.createTransport({
			host: 'smtp.ethereal.email',
			port: 587,
			secure: false,
			auth: { user: process.env.ETHEREAL_USER, pass: process.env.ETHEREAL_PASS },
		})
		return { transporter, sender: process.env.ETHEREAL_USER }
	}
	const testAccount = await nodemailer.createTestAccount()
	const transporter = nodemailer.createTransport({
		host: 'smtp.ethereal.email',
		port: 587,
		secure: false,
		auth: { user: testAccount.user, pass: testAccount.pass },
	})
	return { transporter, sender: testAccount.user }
}

router.post('/register', validateCSRF, async (req, res) => {
	try {
		const { name, email, password } = registerSchema.parse(req.body)
		const existing = await User.findOne({ email })
		if (existing) return res.status(409).json({ error: 'Email already in use' })
		const passwordHash = await bcrypt.hash(password, 12)
		await User.create({ name, email, passwordHash })
		return res.status(201).json({ ok: true })
	} catch (err) {
		if (err instanceof ZodError) {
			return res.status(400).json({
				error: 'Validation failed',
				issues: err.errors.map(e => ({ path: e.path.join('.'), message: e.message }))
			})
		}
		return res.status(400).json({ error: 'Request failed' })
	}
})

router.post('/login', validateCSRF, async (req, res) => {
	try {
		const { email, password } = loginSchema.parse(req.body)
		const user = await User.findOne({ email })
		if (!user) return res.status(401).json({ error: 'Invalid email or password' })
		const valid = await bcrypt.compare(password, user.passwordHash)
		if (!valid) return res.status(401).json({ error: 'Invalid email or password' })
		const code = String(Math.floor(100000 + Math.random() * 900000))
		await Otp.deleteMany({ email })
		await Otp.create({ email, code })
		const { transporter, sender } = await createEtherealTransporter()
		const info = await transporter.sendMail({
			from: `Resume CUA <${sender}>`,
			to: email,
			subject: 'Your login OTP',
			text: `Your verification code is ${code}. It expires in 10 minutes.`,
			html: `<p>Your verification code is <b>${code}</b>. It expires in 10 minutes.</p>`
		})
		const previewUrl = nodemailer.getTestMessageUrl(info)
		const tempToken = jwt.sign({ stage: 'otp', email }, JWT_SECRET, { expiresIn: '10m' })
		return res.json({ step: 'otp', tempToken, previewUrl })
	} catch (err) {
		if (err instanceof ZodError) {
			return res.status(400).json({
				error: 'Validation failed',
				issues: err.errors.map(e => ({ path: e.path.join('.'), message: e.message }))
			})
		}
		return res.status(400).json({ error: 'Request failed' })
	}
})

router.post('/verify-otp', validateCSRF, async (req, res) => {
	try {
		const { email, code } = verifyOtpSchema.parse(req.body)
		const record = await Otp.findOne({ email })
		if (!record || record.code !== code) return res.status(401).json({ error: 'Invalid or expired code' })
		await Otp.deleteMany({ email })
		const user = await User.findOne({ email })
		if (!user) return res.status(404).json({ error: 'User not found' })
		const payload = { sub: user._id.toString(), email: user.email }
		const token = jwt.sign(payload, JWT_SECRET, { expiresIn: '10m' })
		const expiresAt = Date.now() + (10 * 60 * 1000) // 10 minutes from now
		return res.json({ token, expiresAt, user: { id: user._id, name: user.name, email: user.email } })
	} catch (err) {
		if (err instanceof ZodError) {
			return res.status(400).json({
				error: 'Validation failed',
				issues: err.errors.map(e => ({ path: e.path.join('.'), message: e.message }))
			})
		}
		return res.status(400).json({ error: 'Request failed' })
	}
})

// Token verification middleware
function verifyToken(req, res, next) {
	const authHeader = req.headers.authorization
	if (!authHeader || !authHeader.startsWith('Bearer ')) {
		return res.status(401).json({ error: 'No token provided' })
	}
	
	const token = authHeader.substring(7)
	try {
		const decoded = jwt.verify(token, JWT_SECRET)
		req.user = decoded
		next()
	} catch (err) {
		return res.status(401).json({ error: 'Invalid or expired token' })
	}
}

// Token validation endpoint
router.post('/verify-token', verifyToken, async (req, res) => {
	try {
		const user = await User.findById(req.user.sub)
		if (!user) return res.status(404).json({ error: 'User not found' })
		return res.json({ valid: true, user: { id: user._id, name: user.name, email: user.email } })
	} catch (err) {
		return res.status(400).json({ error: 'Token verification failed' })
	}
})

// Token refresh endpoint
router.post('/refresh-token', verifyToken, async (req, res) => {
	try {
		const user = await User.findById(req.user.sub)
		if (!user) return res.status(404).json({ error: 'User not found' })
		const payload = { sub: user._id.toString(), email: user.email }
		const token = jwt.sign(payload, JWT_SECRET, { expiresIn: '10m' })
		const expiresAt = Date.now() + (10 * 60 * 1000)
		return res.json({ token, expiresAt, user: { id: user._id, name: user.name, email: user.email } })
	} catch (err) {
		return res.status(400).json({ error: 'Token refresh failed' })
	}
})

export default router
