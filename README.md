# AI-Powered Resume Parser & Research Agent

A comprehensive web application that combines resume parsing and AI research capabilities with secure authentication.

## 🚀 Features

### 📄 Resume Parser
- **Batch processing** of resumes (PDF, DOCX, TXT)
- **Smart extraction**: Name, Email, Phone, LinkedIn/GitHub, Education, Experience, Skills
- **Enhanced accuracy** with improved regex patterns and spaCy NER
- **CSV/Excel export** with clean, structured data
- **Relevancy scoring** based on keywords
- **Security hardened** with CSRF protection and rate limiting

### 🤖 AI Research Agent
- **Web search** using DuckDuckGo (no API key needed)
- **AI analysis** powered by Google Gemini 1.5 Flash
- **Comprehensive reports** with sources and citations
- **Markdown export** for research reports
- **Real-time research** with progress indicators

### 🔐 Security Features
- **JWT authentication** with 10-minute sessions
- **2FA via email OTP** using Ethereal SMTP
- **CSRF protection** with token validation
- **Rate limiting** on all endpoints
- **Security headers** (HSTS, CSP, XSS protection)
- **Input validation** and sanitization

## 🛠️ Quick Start

### 1. Environment Setup
```bash
# Clone and setup Python environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or: source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 2. Configuration
Create `.env` file in root directory:
```env
# Security
JWT_SECRET=your-super-secure-jwt-secret-at-least-32-characters-long

# Database (optional)
MONGO_URI=mongodb://127.0.0.1:27017/resume_cua

# AI Research (required for research functionality)
GEMINI_API_KEY=your-gemini-api-key-from-ai.google.dev

# Email (optional - for OTP)
ETHEREAL_USER=your-ethereal-username
ETHEREAL_PASS=your-ethereal-password
```

### 3. Get API Keys
- **Gemini API**: Get free key at [ai.google.dev](https://ai.google.dev)
- **MongoDB**: Use local instance or MongoDB Atlas
- **Ethereal Email**: Auto-generated or get at [ethereal.email](https://ethereal.email)

### 4. Start Services

**Terminal 1 - Authentication Server:**
```bash
cd server
npm install
npm run dev
# Runs on http://127.0.0.1:4000
```

**Terminal 2 - Resume Parser API:**
```bash
python api.py
# Runs on http://127.0.0.1:8000
```

**Terminal 3 - Research Agent API:**
```bash
python research_api.py
# Runs on http://127.0.0.1:8001
```

**Terminal 4 - Web Frontend:**
```bash
cd web
npm install
npm run dev
# Runs on http://127.0.0.1:5173
```

## 🎯 Usage

### Web Application
1. **Visit**: `http://127.0.0.1:5173`
2. **Register/Login** with email and password
3. **Verify OTP** sent to your email
4. **Choose tool**:
   - **📄 Resume Parser**: Upload and parse resumes
   - **🤖 AI Research**: Ask questions and get research reports

### CLI Usage (Resume Parser)
```bash
python main.py --input "path/to/resumes" --output candidates.xlsx --use-spacy --keywords "python, react, 3+ years"
```

## 📁 Project Structure

```
├── 📄 main.py              # CLI resume parser
├── 🔌 api.py               # Resume parser API (port 8000)
├── 🤖 research_api.py      # AI research API (port 8001)
├── 📊 src/resume_cua/      # Resume parsing core logic
├── 🔐 server/              # Authentication server (port 4000)
│   ├── src/models/         # User & OTP models
│   ├── src/routes/         # Auth routes
│   └── src/server.js       # Express server
├── 🌐 web/                 # React frontend (port 5173)
│   ├── src/pages/          # Login, Register, App, Research
│   ├── src/components/     # Reusable components
│   ├── src/hooks/          # Auth hooks
│   └── src/services/       # CSRF service
└── 📋 requirements.txt     # Python dependencies
```

## 🔧 Development

### Install spaCy Model (Optional)
```bash
python -m spacy download en_core_web_sm
```

### Environment Variables
- **Development**: Uses fallback values with warnings
- **Production**: Requires all security variables to be set

### API Endpoints
- **Auth**: `http://127.0.0.1:4000/auth/*`
- **Resume Parser**: `http://127.0.0.1:8000/*`
- **AI Research**: `http://127.0.0.1:8001/*`
- **Frontend**: `http://127.0.0.1:5173`

## 🛡️ Security

- **CSRF Protection**: Token-based validation
- **Rate Limiting**: Prevents abuse
- **JWT Tokens**: 10-minute expiration with auto-refresh
- **Input Validation**: Zod schemas and sanitization
- **Security Headers**: Helmet.js protection
- **CORS**: Restricted to specific origins

## 🎨 Themes

- **Resume Parser**: Blue theme (`/app`)
- **AI Research**: Green theme (`/research`)
- **Consistent UX**: Same authentication and navigation

## 📝 License

This project is for educational and development purposes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Built with**: Python, FastAPI, React, TypeScript, Node.js, MongoDB, Google Gemini AI

