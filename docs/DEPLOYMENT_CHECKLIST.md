# TerraQora AI — Production Deployment Checklist

**Phase:** Phase 9 Preparation (Ready for Phase 10 Execution)  
**Target Environments:** Vercel (Frontend SPA) + Render (FastAPI Backend + Managed PostgreSQL)  
**Branch Policy:** Deploys originate exclusively from `main` after formal review and merge.

---

## 1. Pre-Deployment Verification Matrix

| Checklist Item | Requirement / Target | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **Git Working Tree** | Clean working tree on `dev`; zero uncommitted changes | `git status` | **READY** |
| **Branch Safety** | `main` branch untouched until user approval for Phase 10 | `git log main` | **READY** |
| **Secrets & Keys** | Zero hardcoded keys or real secrets in repo or git history | Automated secret regex scan | **VERIFIED CLEAN** |
| **Python Dependencies** | `backend/requirements.txt` pinned and verified | `.venv/Scripts/pip check` | **VERIFIED CLEAN** |
| **Node Dependencies** | `frontend/package.json` installs cleanly | `npm audit` / lockfile check | **VERIFIED CLEAN** |
| **Backend Test Suite** | 42 of 42 pytest tests green across all modules | `pytest -v` | **PASSED (100%)** |
| **Frontend Test Suite** | 14 of 14 Vitest tests green | `npm test -- --run` | **PASSED (100%)** |
| **TypeScript Validation**| 0 compiler errors | `npx tsc --noEmit` | **PASSED (0 Errors)** |
| **Frontend Production Build** | Vite bundles into `frontend/dist/` under 1.2 MB total | `npm run build` | **PASSED** |
| **PostgreSQL DDL** | Clean migration DDL compilation | `alembic upgrade head --sql` | **VERIFIED** |
| **Security Headers** | ASGI & Vercel headers configured | `add_security_headers` middleware | **CONFIGURED** |

---

## 2. Infrastructure Deployment Steps (For Phase 10)

### Step 1: Managed Database Provisioning (Render PostgreSQL)
1. Provision a PostgreSQL 16 instance on Render (`terraqora-db`) via [render.yaml](file:///c:/Users/alitr/OneDrive/Desktop/TerraQora%20AI/render.yaml).
2. Copy the Internal Connection String:
   `postgresql+psycopg://user:password@terraqora-db:5432/terraqora_ai?sslmode=require`
3. Execute migrations from CI/CD or initial startup command:
   `alembic upgrade head`

### Step 2: Backend API Service Deployment (Render Web Service)
1. Connect `alitrose/terraqora-ai` repository to Render.
2. Configure build command:
   `python -m pip install --upgrade pip && pip install -r backend/requirements.txt`
3. Configure start command:
   `cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
4. Configure environment variables (see `docs/PRODUCTION_ENVIRONMENT.md`).
5. Verify health check at `https://terraqora-ai-api.onrender.com/health`.

### Step 3: Frontend Deployment (Vercel)
1. Import repository on Vercel with Root Directory set to `frontend`.
2. Framework Preset: **Vite**.
3. Build Command: `npm run build`.
4. Output Directory: `dist`.
5. Environment Variable:
   `VITE_API_BASE_URL=https://terraqora-ai-api.onrender.com/api/v1`
6. Verify deployment and SPA route navigation (`/`, `/dashboard`, `/yield-prediction`, etc.).

---

## 3. Post-Deployment Smoke Tests (Phase 10)
- [ ] Root health check returns `status: "ok"` and `database: "connected"`.
- [ ] New user registration creates database record and issues valid JWT.
- [ ] Farmer profile update and farm plot CRUD execute cleanly.
- [ ] Crop yield prediction returns valid yield estimate.
- [ ] Crop recommendation returns top suitability matches.
- [ ] Fertilizer recommendation generates ICAR-compliant formulation.
- [ ] Plant disease screening analyzes leaf upload and persists findings.
- [ ] Live weather advisory fetches 7-day forecast from Open-Meteo.
- [ ] ReportLab PDF download generates valid PDF binary.
- [ ] Admin console displays live platform metrics and service health.
