# TerraQora AI — Local Development & Installation Guide

**Tagline:** Intelligence for Every Acre.  
**Prerequisites:** Python 3.11+, Node.js 18+, Git.

---

## 1. Clone & Workspace Setup

```bash
# 1. Clone repository
git clone https://github.com/alitrose/terraqora-ai.git
cd terraqora-ai

# 2. Checkout development branch
git checkout dev
```

---

## 2. Backend Setup (FastAPI + Python)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv

# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# 2. Install backend dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env to set your JWT_SECRET_KEY, DATABASE_URL, and GEMINI_API_KEY (optional)

# 4. Run database migrations (SQLite or PostgreSQL)
cd backend
python -m alembic upgrade head
cd ..

# 5. Start the FastAPI development server
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Backend will be available at: `http://localhost:8000`  
Interactive API Docs (development mode): `http://localhost:8000/docs`

---

## 3. Frontend Setup (React + Vite + Tailwind)

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start Vite development server
npm run dev
```
Frontend will be available at: `http://localhost:5173`

---

## 4. Running Automated Test Suites

### Backend Test Suite
```bash
# Run all 42 automated tests with verbose output
python -m pytest -v
```

### Frontend Test Suite
```bash
cd frontend

# Run Vitest test suite
npm test -- --run

# Run TypeScript type check
npx tsc --noEmit

# Run production Vite build
npm run build
```

---

## 5. Offline Demonstration Mode

If running without a backend server or database, the frontend automatically activates **Instant UI Preview Sandbox** (`demo_preview`), providing complete demonstration mock data across all 12 modules with realistic agronomic figures.
