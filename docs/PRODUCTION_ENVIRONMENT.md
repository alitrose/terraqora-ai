# TerraQora AI — Production Environment Specification & Constraints

**Document Status:** Complete & Verified  
**Branch:** `dev`  
**Author:** DevSecOps & Cloud Architecture

---

## 1. Production Environment Variables Reference

| Variable Name | Required | Default / Format | Description & Security Guidelines |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | No | `TerraQora AI` | Human-readable application branding. |
| `APP_ENV` | **Yes** | `production` | Enables production guardrails: hides Swagger `/docs`, enables HSTS, enforces strict CORS. |
| `DEBUG` | **Yes** | `false` | Must always be `false` in production to prevent stack trace leaks. |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`INFO` or `WARNING` in production). |
| `API_V1_PREFIX` | No | `/api/v1` | URL prefix for REST endpoints. |
| `JWT_SECRET_KEY` | **Yes** | `[64-char string]` | High-entropy secret for signing JWT access tokens. Generate via `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `JWT_ALGORITHM` | No | `HS256` | Cryptographic algorithm for JWT signatures. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Lifespan of JWT access token. |
| `DATABASE_URL` | **Yes** | `postgresql+psycopg://...` | Connection string to PostgreSQL instance with SSL mode required. |
| `CORS_ORIGINS` | **Yes** | `https://terraqora-ai.vercel.app` | Comma-separated list of allowed frontend origins (never use wildcard `*`). |
| `LLM_PROVIDER` | No | `gemini` | Language model provider abstraction (`gemini`). |
| `GEMINI_API_KEY` | **Yes** | `AIza...` | Google AI Studio API key for Gemini 2.5 Flash GenAI Advisor. |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model variant. |
| `WEATHER_PROVIDER` | No | `open_meteo` | Meteorological telemetry provider (`open_meteo` primary). |
| `WEATHER_TIMEOUT_SECONDS` | No | `10` | Timeout threshold for external weather HTTP calls. |
| `WEATHER_CACHE_TTL_SECONDS` | No | `900` | In-memory cache TTL for weather coordinates (15 minutes). |
| `MAX_UPLOAD_IMAGE_MB` | No | `5` | Maximum permissible leaf image size for Plant Pathology vision. |
| `RATE_LIMIT_DEFAULT` | No | `60/minute` | Default endpoint rate limit per IP. |
| `RATE_LIMIT_AI` | No | `20/minute` | Rate limit for computationally expensive ML/AI endpoints. |
| `VITE_API_BASE_URL` | **Yes** (Frontend) | `https://api.terraqora.ai/api/v1` | Backend API URL configured in Vercel environment. |

---

## 2. Cloud Provider Constraints & Architected Mitigations

### A. Render Free-Tier Web Service (Backend)
1. **512 MB Memory Budget Limit:**
   - *Constraint:* Render terminates free-tier instances that exceed 512 MB RAM with an Out-Of-Memory (OOM) error.
   - *Mitigation:* Combined ML models footprint was engineered down to **~23.4 MB** using MobileNetV3-Small (15.7 MB) and Quantile/Naive Bayes estimators (<8 MB). Uvicorn runs with a single worker (`--workers 1`), consuming <140 MB total RSS memory under load.
2. **Cold Starts / Idle Spin-Down:**
   - *Constraint:* Free-tier services spin down after 15 minutes of inactivity. First request takes ~45–60 seconds to resume.
   - *Mitigation:* Frontend displays an animated "Connecting to agricultural intelligence engine..." message rather than timing out.
3. **Ephemeral Storage:**
   - *Constraint:* Render containers have ephemeral disks; files saved to disk are wiped upon redeploy or instance restart.
   - *Mitigation:* All critical operational data (predictions, advisories, chat logs, user profiles, report metadata) are persisted immediately to PostgreSQL. Generated PDF reports can be regenerated on-demand from database records.

### B. Vercel (Frontend SPA)
1. **Edge CDN & Caching:**
   - Assets bundled in `dist/assets/` are content-hashed for immutable caching (`Cache-Control: public, max-age=31536000, immutable`).
2. **SPA Routing:**
   - `frontend/vercel.json` rewrites all non-file requests to `/index.html` to allow React Router HTML5 pushState navigation without 404 errors.

### C. Managed PostgreSQL (Database)
1. **Connection Pooling:**
   - Free tier databases often restrict concurrent connections to 20–50.
   - SQLAlchemy engine is configured with `pool_size=10` and `max_overflow=10`, automatically recycling idle connections after 1800 seconds to prevent leaked zombie connections.
