# TerraQora AI — FastAPI Backend (Phases 4–5B)

Modular FastAPI backend built on SQLAlchemy 2.0, Alembic migrations, PostgreSQL (with SQLite local dev/test support), Pydantic v2 validation, bcrypt password hashing, JWT authentication, Farmer/Admin RBAC, live Phase 5 leak-free Crop Yield ML inference, and Phase 5B Crop & Fertilizer Recommendation ML inference.

---

## Folder Structure

```text
backend/
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 71b32d16b077_initial_terraqora_schema.py
├── requirements.txt
└── app/
    ├── __init__.py
    ├── main.py                     # FastAPI app, CORS, rate limiting, error handlers, /health
    ├── api/
    │   ├── deps.py                 # Bearer JWT auth & require_roles(...) RBAC dependencies
    │   └── v1/
    │       ├── router.py           # /api/v1 router + /api/v1/health
    │       ├── auth.py             # /auth/register, /auth/login, /auth/me
    │       ├── profile.py          # /profile (GET, PUT)
    │       ├── farms.py            # /farms CRUD (GET list, POST, GET/{id}, PUT/{id}, PATCH/{id}, DELETE/{id})
    │       ├── predictions.py      # Phase 5: POST /predictions/yield & GET /predictions/yield/history
    │       ├── recommendations.py  # Phase 5B: /recommendations/crop (+ /history) & /recommendations/fertilizer (+ /history)
    │       └── admin.py            # /admin/overview (incl. live ML registry), /admin/users, PATCH /admin/users/{id}
    ├── core/
    │   ├── config.py               # Environment settings & production security guardrails
    │   ├── logging_config.py
    │   ├── rate_limit.py           # SlowAPI rate limiter
    │   └── security.py             # bcrypt hashing + PyJWT access tokens
    ├── db/
    │   ├── base.py
    │   └── session.py              # Engine builder (PostgreSQL pool_pre_ping / SQLite FK enforcement)
    ├── models/                     # All 11 Phase 2 SQLAlchemy 2.0 ORM tables
    ├── schemas/                    # Pydantic v2 schemas (auth, farm, predictions, recommendations, admin)
    └── services/
        ├── crop_yield_service.py   # Phase 5 Crop Yield ML loader, TreeSHAP drivers & DB persistence
        ├── crop_rec_service.py     # Phase 5B Crop Recommendation ML loader & DB persistence
        └── fertilizer_service.py   # Phase 5B Fertilizer grade classifier + ICAR guardrails & persistence
```

---

## Local Setup (Using Workspace `.venv`)

> [!IMPORTANT]
> Always install and run Python tooling inside the workspace virtual environment (`.\.venv`), never global `pip`.

1. **Create virtual environment & install dependencies** (from repository root):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
   ```

2. **Generate all Phase 5 & 5B ML model artifacts** (required once after fresh clone because `*.joblib` binaries are gitignored):
   ```powershell
   .\.venv\Scripts\python.exe -m ml.training.train_crop_yield
   .\.venv\Scripts\python.exe -m ml.training.train_crop_recommendation
   .\.venv\Scripts\python.exe -m ml.training.train_fertilizer
   ```

3. **Configure `.env`** (never commit `.env`):
   Copy `.env.example` to `.env` at the repository root and set:
   - `JWT_SECRET_KEY` (generate via `.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"`)
   - `DATABASE_URL` (e.g., `postgresql+psycopg://postgres:<password>@localhost:5432/terraqora_ai`, or omit during local development to use local SQLite `terraqora_dev.db`)
   - `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`

4. **Run Alembic database migrations** (from `backend/`):
   ```powershell
   cd backend
   ..\.venv\Scripts\alembic.exe upgrade head
   ```

5. **Start FastAPI server**:
   ```powershell
   cd backend
   ..\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
   ```
   - OpenAPI Docs (non-production): `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/health` and `http://localhost:8000/api/v1/health`

---

## Promoting an Admin User Locally

Public `/api/v1/auth/register` always creates accounts with `role='farmer'` to prevent privilege escalation, and no default admin passwords are hardcoded in source code. To promote a registered account to `admin` in local PostgreSQL/SQLite:

```sql
UPDATE users SET role = 'admin' WHERE email = 'your-admin@example.com';
```

---

## Running Automated Backend Tests

From repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

`tests/test_phase4_backend.py` runs completely isolated against temporary SQLite databases in pytest `tmp_path` by applying real Alembic `upgrade head` / `downgrade base` migrations cleanly on each test run.
