## AI-Powered Resume Parser (Computer Usage Agent)

A Python CUA that parses resumes (PDF, DOCX, TXT) from a folder, extracts candidate information, and exports a clean CSV/Excel.

### Features
- Batch processing of a folder of resumes
- File types: PDF, DOCX, TXT
- Extracts: Name, Email, Phone, LinkedIn/GitHub URLs, Education, Experience, Skills
- Robust regex + heuristics, optional spaCy NER
- Standardized phone numbers and cleaned text
- CSV/Excel export
- Optional relevancy scoring from keywords
- Web UI: React (modern) or Streamlit (simple)

### Setup (Python)
```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

### Run the Backend API (FastAPI)
```bash
uvicorn api:app --reload --port 8000
```

### Run the React Web UI
```bash
cd web
npm install
npm run dev
```
- Default API base: `http://127.0.0.1:8000` (override with `VITE_API_BASE` in `.env`)

### CLI Usage
```bash
python main.py --input "C:/path/to/resumes" --output candidates.xlsx --use-spacy --open \
  --keywords "python, api, 3+ years"
```

### Streamlit (Optional)
```bash
streamlit run app.py
```

### Notes
- Install spaCy model if using `--use-spacy`:
```bash
python -m spacy download en_core_web_sm
```
- PDF parsing uses PyMuPDF with pdfplumber fallback.

### Developer
- Source in `src/resume_cua/`
- Entry points: `main.py` (CLI) and `app.py` (web)

## Backend (Node.js + Express + MongoDB) for Auth

Setup:
```bash
cd server
npm install
# create .env with:
# MONGO_URI=mongodb://127.0.0.1:27017/resume_cua
# JWT_SECRET=your-strong-secret
npm run dev
```

React frontend expects:
- Auth API base at `http://127.0.0.1:4000` (override `VITE_AUTH_BASE`)
- Parser API base at `http://127.0.0.1:8000` (override `VITE_API_BASE`)

Set env for web (create `web/.env`):
```
VITE_API_BASE=http://127.0.0.1:8000
VITE_AUTH_BASE=http://127.0.0.1:4000
```

### 2FA via Email OTP (Ethereal)
- Backend uses Ethereal SMTP for test emails. Either set credentials:
```
ETHEREAL_USER=your_user
ETHEREAL_PASS=your_pass
```
- Or let the server create a test account automatically; it returns a preview URL in `/auth/login` response when sending OTP.
- Flow: POST `/auth/login` (valid creds) → server emails OTP and returns `previewUrl` → client calls `/auth/verify-otp` with `{ email, code }` to receive JWT.

