# TerraQora AI — Deployment Plan & Free-Tier Analysis

## 1. Hosting Architecture
- **Frontend:** Vercel (Vite React static/SPA production build with `vercel.json` SPA rewrites)
- **Backend API:** Render Web Service (Python FastAPI + Uvicorn / Gunicorn)
- **Database:** Render Managed PostgreSQL (connected via `DATABASE_URL` with SSL)

## 2. Verified Render Free-Tier Limitations & Mitigations

During Phase 2 planning, current Render free-tier boundaries were verified so the architecture avoids runtime surprises:

| Resource | Render Free-Tier Constraint | TerraQora AI Mitigation |
| --- | --- | --- |
| **Web Service RAM** | **512 MB RAM**, shared `~0.1` CPU | Keep serialized tabular models `< 15 MB` (no `139.8 MB` RF bloat); train CNN in TensorFlow/Keras and serve compact quantized `.tflite` / lightweight runtime in production, or load models lazily to stay safely under 512 MB RSS. |
| **Web Service Sleep** | Spins down after **15 minutes** of inactivity; **30–60s cold start** | Expose lightweight `/api/v1/health` endpoint; display clean cold-start wake-up UX on frontend login/first request. |
| **Monthly Hours** | **750 free instance hours/month** across workspace | Run a single unified FastAPI service (serving REST, ML/CV inference, GenAI, and PDF exports together). |
| **PostgreSQL Storage & Expiry** | **256 MB RAM**, **1 GB storage**, **expires 30 days after creation** (+ 14-day grace period before deletion) | Ideal for project review/demo window; keep Alembic migrations & `seed.py` idempotent for instant re-provisioning, or upgrade to Render Basic/Starter DB (`$7/mo`) / external persistent Postgres if long-term retention is required. |

## 3. Environment Variable Separation
- Local dev uses `.env` (gitignored, copied from `.env.example`).
- Vercel stores `VITE_API_BASE_URL` in Project Environment Variables.
- Render stores `DATABASE_URL`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`, `CORS_ORIGINS` (exact Vercel production origin), and optional `OPENWEATHER_API_KEY` in Render Environment Groups.
