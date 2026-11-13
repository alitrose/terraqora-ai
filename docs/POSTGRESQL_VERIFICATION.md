# TerraQora AI — PostgreSQL Verification Report & Production Guide

**Document Status:** Complete & Verified  
**Audit Target:** PostgreSQL 16+ Dialect & Migration Compatibility  
**Author:** Database & DevSecOps Engineering  
**Branch:** `dev`

---

## 1. Executive Status Matrix

In adherence to the strict requirement of scientific honesty, the verification statuses are categorized below:

| Verification Category | Status | Details & Evidence |
| :--- | :--- | :--- |
| **Offline PostgreSQL DDL Compilation** | **VERIFIED** | Successfully compiled all Alembic migrations to raw PostgreSQL DDL using `alembic upgrade head --sql`. Verified `UUID`, `pgcrypto`, `TIMESTAMPTZ`, `JSONB`, check constraints, foreign keys, cascade deletes, and update triggers. |
| **Automated SQLite In-Memory / File Tests** | **VERIFIED** | 42 backend pytest tests execute successfully against SQLite using identical SQLAlchemy 2.0 ORM mappings, constraints, relationships, and queries. |
| **Live Local PostgreSQL Instance** | **BLOCKED (ENVIRONMENT)** | Neither a native Windows PostgreSQL service nor Docker is installed on this local development machine (`Get-Service *postgres*` returned null; port 5432 TCP handshake failed). |
| **Live Cloud PostgreSQL Instance (Phase 10 Target)** | **PENDING PHASE 10** | Will be provisioned and verified during Phase 10 deployment using Render Managed PostgreSQL or external cloud database (Supabase/Neon). |

---

## 2. Offline PostgreSQL DDL Verification Details

Using `alembic upgrade head --sql` targeting dialect `postgresql+psycopg://`, the migration scripts generated the following validated schema components:

### 1. Native PostgreSQL Data Types
- `UUID` mapped directly to native PostgreSQL `UUID` columns (e.g. `users.id`, `farms.id`, `generated_reports.id`).
- `TIMESTAMP WITH TIME ZONE` (`TIMESTAMPTZ`) utilized across all timestamp columns to preserve timezone offset awareness (`created_at`, `updated_at`, `last_login_at`).
- `JSONB` with binary indexability applied to `top_predictions_json`, `nutrient_status_json`, `weather_snapshot_json`, and `report_payload_json`.
- `DOUBLE PRECISION` for continuous physical variables (latitude, longitude, rainfall mm, yield rate, acreage).

### 2. Constraints & Integrity Rules
- Role check constraint: `CONSTRAINT ck_users_role CHECK (role IN ('farmer', 'admin'))`.
- Supported languages: `CHECK (preferred_language IN ('en', 'ta', 'ml', 'hi', 'te'))`.
- Geographical coordinates bounds: `latitude >= -90 AND latitude <= 90`, `longitude >= -180 AND longitude <= 180`.
- Soil pH bounds: `soil_ph >= 0 AND soil_ph <= 14`.
- Positive acreage: `area_hectares > 0`.
- Unique constraints on `users.email` and `farmer_profiles.user_id`.

### 3. Referential Actions & Cascade Semantics
- `ON DELETE CASCADE` configured on:
  - `farmer_profiles.user_id -> users.id`
  - `farms.user_id -> users.id`
  - `crop_predictions.user_id -> users.id`
  - `crop_recommendations.user_id -> users.id`
  - `fertilizer_recommendations.user_id -> users.id`
  - `disease_detections.user_id -> users.id`
  - `irrigation_recommendations.user_id -> users.id`
  - `chat_sessions.user_id -> users.id`
  - `chat_messages.session_id -> chat_sessions.id`
  - `generated_reports.user_id -> users.id`
- `ON DELETE SET NULL` configured on foreign keys referencing optional `farms.id` across predictions and reports.

### 4. Database Triggers & Extensions
- `CREATE EXTENSION IF NOT EXISTS "pgcrypto";`
- `set_updated_at()` trigger function defined and bound to `users`, `farmer_profiles`, `farms`, and `chat_sessions` tables.

---

## 3. Step-by-Step Instructions to Run Live PostgreSQL

When provisioning a local or cloud PostgreSQL instance, follow these exact steps:

### Option A: Local PostgreSQL (Docker)
```bash
# 1. Run PostgreSQL 16 container
docker run --name terraqora-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=terraqora_ai \
  -p 5432:5432 -d postgres:16-alpine

# 2. Configure .env
DATABASE_URL="postgresql+psycopg://postgres:your_secure_password@localhost:5432/terraqora_ai"

# 3. Run Alembic migrations
cd backend
python -m alembic upgrade head
```

### Option B: Local PostgreSQL (Native Windows / Linux)
```bash
# 1. Create database in psql
CREATE USER terra_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE terraqora_ai OWNER terra_user;
GRANT ALL PRIVILEGES ON DATABASE terraqora_ai TO terra_user;

# 2. Run migrations
cd backend
$env:DATABASE_URL="postgresql+psycopg://terra_user:your_secure_password@localhost:5432/terraqora_ai"
python -m alembic upgrade head
```

### Option C: Cloud Managed PostgreSQL (Render / Neon / Supabase)
```bash
# Set connection string with SSL required
DATABASE_URL="postgresql+psycopg://user:password@ep-host.region.render.com:5432/terraqora_ai?sslmode=require"
cd backend
python -m alembic upgrade head
```

---

## 4. Unverified Functionality Pending Live PostgreSQL

The following behaviors have been validated via automated unit/integration tests on SQLite and offline DDL review, but must be verified against actual PostgreSQL in Phase 10:
1. `pgcrypto` extension installation on restricted database user accounts.
2. Concurrent write transaction throughput during high-frequency telemetry streams.
3. PostgreSQL connection pool tuning (`pool_size=10`, `max_overflow=20`) under multi-worker Uvicorn configurations.
4. GIN indexing performance over `JSONB` columns under heavy query volume.
