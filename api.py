import os
import io
import secrets
from typing import List, Dict, Any, Optional

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import jwt as pyjwt

from src.resume_cua.readers import read_text_from_file
from src.resume_cua.extractors import extract_resume_fields
from src.resume_cua.scoring import compute_relevancy_score

app = FastAPI(
	title="Resume Parser API",
	docs_url="/docs" if os.getenv('ENVIRONMENT') != 'production' else None,  # Disable docs in production
	redoc_url="/redoc" if os.getenv('ENVIRONMENT') != 'production' else None
)

# Security: Trusted Host middleware
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*.localhost"]
if os.getenv('ENVIRONMENT') == 'production':
	# Add production domains here
	ALLOWED_HOSTS = ["yourdomain.com", "*.yourdomain.com"]

app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# CSRF Protection: Restrict CORS to specific origins
ALLOWED_ORIGINS = [
	"http://localhost:5173",  # Vite dev server
	"http://127.0.0.1:5173",  # Alternative localhost
	"http://localhost:3000",  # Alternative React dev server
	# Add production domains here when deploying
]

app.add_middleware(
	CORSMiddleware,
	allow_origins=ALLOWED_ORIGINS,  # Restricted origins for CSRF protection
	allow_credentials=True,
	allow_methods=["GET", "POST"],  # Only needed methods
	allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Session-Id"],  # Specific headers
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
	response = await call_next(request)
	
	# Security headers
	response.headers["X-Content-Type-Options"] = "nosniff"
	response.headers["X-Frame-Options"] = "DENY"
	response.headers["X-XSS-Protection"] = "1; mode=block"
	response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
	response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
	
	# Content Security Policy
	csp = (
		"default-src 'self'; "
		"script-src 'self'; "
		"style-src 'self' 'unsafe-inline'; "
		"img-src 'self' data:; "
		"connect-src 'self'; "
		"font-src 'self'; "
		"object-src 'none'; "
		"base-uri 'self'; "
		"form-action 'self'"
	)
	response.headers["Content-Security-Policy"] = csp
	
	# HSTS (only in production with HTTPS)
	if os.getenv('ENVIRONMENT') == 'production':
		response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
	
	return response

# Enforce strong JWT secret - fail if not provided in production
JWT_SECRET = os.getenv('JWT_SECRET')
if not JWT_SECRET:
    if os.getenv('ENVIRONMENT') == 'production':
        raise ValueError("JWT_SECRET environment variable is required in production")
    else:
        # Generate a random secret for development
        import secrets
        JWT_SECRET = secrets.token_urlsafe(64)
        print("⚠️  WARNING: Using auto-generated JWT secret for development. Set JWT_SECRET env var for production.")

# Rate limiting storage (in production, use Redis)
from collections import defaultdict
import time

rate_limit_storage = defaultdict(list)

def rate_limit(max_requests: int = 10, window_seconds: int = 60):
	"""Rate limiting decorator"""
	def decorator(func):
		async def wrapper(*args, **kwargs):
			# Get client IP from request
			request = None
			for arg in args:
				if hasattr(arg, 'client'):
					request = arg
					break
			
			if not request:
				return await func(*args, **kwargs)
			
			client_ip = request.client.host
			current_time = time.time()
			
			# Clean old requests
			rate_limit_storage[client_ip] = [
				req_time for req_time in rate_limit_storage[client_ip]
				if current_time - req_time < window_seconds
			]
			
			# Check rate limit
			if len(rate_limit_storage[client_ip]) >= max_requests:
				raise HTTPException(
					status_code=429,
					detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds} seconds"
				)
			
			# Add current request
			rate_limit_storage[client_ip].append(current_time)
			
			return await func(*args, **kwargs)
		return wrapper
	return decorator

# CSRF Token storage (in production, use Redis or database)
csrf_tokens = {}

def verify_token(authorization: Optional[str] = Header(None)):
	"""Optional token verification - returns user info if token is valid, None otherwise"""
	if not authorization or not authorization.startswith('Bearer '):
		return None
	
	token = authorization[7:]
	try:
		decoded = pyjwt.decode(token, JWT_SECRET, algorithms=['HS256'])
		return decoded
	except pyjwt.ExpiredSignatureError:
		raise HTTPException(status_code=401, detail="Token has expired")
	except pyjwt.InvalidTokenError:
		raise HTTPException(status_code=401, detail="Invalid token")
	except Exception:
		return None

def verify_csrf_token(x_csrf_token: Optional[str] = Header(None), x_session_id: Optional[str] = Header(None)):
	"""Verify CSRF token for state-changing operations"""
	if not x_csrf_token:
		raise HTTPException(status_code=403, detail="CSRF token required")
	
	session_id = x_session_id or "default"
	stored_token = csrf_tokens.get(session_id)
	
	if not stored_token or stored_token != x_csrf_token:
		raise HTTPException(status_code=403, detail="Invalid CSRF token")
	
	return True

@app.get("/csrf-token")
@rate_limit(max_requests=5, window_seconds=60)  # 5 requests per minute
async def get_csrf_token(request: Request, x_session_id: Optional[str] = Header(None)):
	"""Generate and return CSRF token"""
	session_id = x_session_id or "default"
	token = secrets.token_hex(32)
	csrf_tokens[session_id] = token
	return {"csrfToken": token}


@app.post("/parse")
@rate_limit(max_requests=10, window_seconds=300)  # 10 requests per 5 minutes
async def parse(
	request: Request,
	files: List[UploadFile] = File(...), 
	use_spacy: bool = Form(True), 
	keywords: str = Form(""),
	authorization: Optional[str] = Header(None),
	x_csrf_token: Optional[str] = Header(None),
	x_session_id: Optional[str] = Header(None)
):
	# Verify CSRF token for state-changing operations
	verify_csrf_token(x_csrf_token, x_session_id)
	
	# Verify JWT token if provided
	user = verify_token(authorization)
	
	rows: List[Dict[str, Any]] = []
	kw = [k.strip() for k in (keywords or "").split(",") if k.strip()]
	# Input validation
	if len(files) > 50:  # Limit number of files
		raise HTTPException(status_code=400, detail="Too many files. Maximum 50 files allowed.")
	
	for uf in files:
		# Validate file extension
		if not uf.filename:
			continue
		ext = os.path.splitext(uf.filename)[1].lower()
		if ext not in {".pdf", ".docx", ".txt"}:
			continue
		
		# Validate file size (10MB limit)
		content = await uf.read()
		if len(content) > 10 * 1024 * 1024:  # 10MB
			raise HTTPException(status_code=400, detail=f"File {uf.filename} is too large. Maximum 10MB allowed.")
		
		# Sanitize filename
		safe_filename = "".join(c for c in uf.filename if c.isalnum() or c in "._-")
		if not safe_filename:
			safe_filename = f"file_{secrets.token_hex(8)}{ext}"
		
		tmp_path = os.path.join(".tmp_uploads", safe_filename)
		os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
		with open(tmp_path, "wb") as f:
			f.write(content)
		try:
			text = read_text_from_file(tmp_path)
			data = extract_resume_fields(text, use_spacy=use_spacy)
			if kw:
				data["RelevancyScore"] = compute_relevancy_score(text, kw)
			data["SourceFile"] = uf.filename
			rows.append(data)
		finally:
			try:
				os.remove(tmp_path)
			except Exception:
				pass
	return {"rows": rows}


@app.post("/export/csv")
async def export_csv(rows: List[Dict[str, Any]], authorization: Optional[str] = Header(None)):
	# Verify token if provided
	user = verify_token(authorization)
	
	df = pd.DataFrame(rows)
	buf = io.StringIO()
	df.to_csv(buf, index=False)
	buf.seek(0)
	return StreamingResponse(iter([buf.getvalue().encode("utf-8")]), media_type="text/csv", headers={
		"Content-Disposition": "attachment; filename=candidates.csv"
	})


@app.post("/export/xlsx")
async def export_xlsx(rows: List[Dict[str, Any]], authorization: Optional[str] = Header(None)):
	# Verify token if provided
	user = verify_token(authorization)
	
	df = pd.DataFrame(rows)
	buf = io.BytesIO()
	df.to_excel(buf, index=False)
	buf.seek(0)
	return StreamingResponse(iter([buf.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={
		"Content-Disposition": "attachment; filename=candidates.xlsx"
	})
