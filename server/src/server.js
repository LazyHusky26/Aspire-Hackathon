import express from 'express'
import cors from 'cors'
import mongoose from 'mongoose'
import dotenv from 'dotenv'
import helmet from 'helmet'
import rateLimit from 'express-rate-limit'
import authRouter from './routes/auth.js'

dotenv.config()

const app = express()

// Security: Helmet for security headers
app.use(helmet({
	contentSecurityPolicy: {
		directives: {
			defaultSrc: ["'self'"],
			styleSrc: ["'self'", "'unsafe-inline'"],
			scriptSrc: ["'self'"],
			imgSrc: ["'self'", "data:"],
			connectSrc: ["'self'"],
			fontSrc: ["'self'"],
			objectSrc: ["'none'"],
			mediaSrc: ["'self'"],
			frameSrc: ["'none'"],
		},
	},
	hsts: process.env.NODE_ENV === 'production' ? {
		maxAge: 31536000,
		includeSubDomains: true,
		preload: true
	} : false
}))

// Rate limiting
const limiter = rateLimit({
	windowMs: 15 * 60 * 1000, // 15 minutes
	max: 100, // Limit each IP to 100 requests per windowMs
	message: 'Too many requests from this IP, please try again later.',
	standardHeaders: true,
	legacyHeaders: false,
})
app.use(limiter)

// Stricter rate limiting for auth endpoints
const authLimiter = rateLimit({
	windowMs: 15 * 60 * 1000, // 15 minutes
	max: 10, // Limit each IP to 10 auth requests per windowMs
	message: 'Too many authentication attempts, please try again later.',
	skipSuccessfulRequests: true,
})

// CSRF Protection: Restrict CORS to specific origins
const ALLOWED_ORIGINS = [
	'http://localhost:5173',  // Vite dev server
	'http://127.0.0.1:5173',  // Alternative localhost
	'http://localhost:3000',  // Alternative React dev server
	// Add production domains here when deploying
]

app.use(cors({ 
	origin: ALLOWED_ORIGINS,  // Restricted origins for CSRF protection
	credentials: true,
	methods: ['GET', 'POST'],  // Only needed methods
	allowedHeaders: ['Authorization', 'Content-Type', 'X-CSRF-Token', 'X-Session-Id']  // Specific headers
}))

app.use(express.json({ limit: '10mb' })) // Limit JSON payload size

// Secure MongoDB connection
const MONGO_URI = process.env.MONGO_URI
if (!MONGO_URI) {
	if (process.env.NODE_ENV === 'production') {
		throw new Error('MONGO_URI environment variable is required in production')
	}
	console.warn('⚠️  WARNING: Using default MongoDB connection for development. Set MONGO_URI env var for production.')
}

const mongoUri = MONGO_URI || 'mongodb://127.0.0.1:27017/resume_cua'

// MongoDB connection options for security
const mongoOptions = {
	maxPoolSize: 10,
	serverSelectionTimeoutMS: 5000,
	socketTimeoutMS: 45000,
	bufferCommands: false
}

await mongoose.connect(mongoUri, mongoOptions)

app.get('/health', (req, res) => res.json({ ok: true }))
app.use('/auth', authLimiter, authRouter)  // Apply auth rate limiting

const PORT = process.env.PORT || 4000
app.listen(PORT, () => console.log(`Auth server listening on http://127.0.0.1:${PORT}`))


