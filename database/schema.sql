-- ============================================================
-- TerraQora AI — PostgreSQL Schema Design (Phase 2 Blueprint)
-- Compatible with PostgreSQL 15+ (Render Managed PostgreSQL)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Automatic updated_at trigger function
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'farmer'
        CHECK (role IN ('farmer', 'admin')),
    preferred_language VARCHAR(8) NOT NULL DEFAULT 'en'
        CHECK (preferred_language IN ('en', 'ta', 'ml', 'hi', 'te')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 2. FARMER PROFILES (1:1 with users)
CREATE TABLE IF NOT EXISTS farmer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    phone VARCHAR(24),
    state VARCHAR(80),
    district VARCHAR(80),
    experience_years INTEGER CHECK (experience_years IS NULL OR experience_years >= 0),
    primary_soil_type VARCHAR(60),
    preferred_units VARCHAR(20) NOT NULL DEFAULT 'metric'
        CHECK (preferred_units IN ('metric', 'imperial')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_farmer_profiles_updated_at
    BEFORE UPDATE ON farmer_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 3. FARMS (1:N with users)
CREATE TABLE IF NOT EXISTS farms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    state VARCHAR(80) NOT NULL,
    district VARCHAR(80),
    latitude DOUBLE PRECISION CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),
    longitude DOUBLE PRECISION CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180)),
    area_hectares DOUBLE PRECISION NOT NULL CHECK (area_hectares > 0),
    soil_type VARCHAR(60),
    soil_ph DOUBLE PRECISION CHECK (soil_ph IS NULL OR (soil_ph >= 0 AND soil_ph <= 14)),
    irrigation_type VARCHAR(40)
        CHECK (irrigation_type IS NULL OR irrigation_type IN ('rainfed', 'drip', 'sprinkler', 'canal', 'borewell', 'mixed')),
    primary_crop VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_farms_user_id ON farms (user_id);
CREATE INDEX IF NOT EXISTS ix_farms_state ON farms (state);

CREATE TRIGGER trg_farms_updated_at
    BEFORE UPDATE ON farms
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 4. CROP PREDICTIONS (Module 1)
CREATE TABLE IF NOT EXISTS crop_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
    crop VARCHAR(80) NOT NULL,
    crop_year INTEGER NOT NULL CHECK (crop_year >= 1990 AND crop_year <= 2100),
    season VARCHAR(40) NOT NULL,
    state VARCHAR(80) NOT NULL,
    area_hectares DOUBLE PRECISION NOT NULL CHECK (area_hectares > 0),
    annual_rainfall_mm DOUBLE PRECISION NOT NULL CHECK (annual_rainfall_mm >= 0),
    fertilizer_kg DOUBLE PRECISION NOT NULL CHECK (fertilizer_kg >= 0),
    pesticide_kg DOUBLE PRECISION NOT NULL CHECK (pesticide_kg >= 0),
    predicted_yield DOUBLE PRECISION NOT NULL CHECK (predicted_yield >= 0),
    yield_unit VARCHAR(32) NOT NULL DEFAULT 'tonnes/hectare',
    estimated_total_production DOUBLE PRECISION,
    model_name VARCHAR(64) NOT NULL,
    model_version VARCHAR(32) NOT NULL,
    feature_importance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_crop_predictions_user_created
    ON crop_predictions (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_crop_predictions_crop_state
    ON crop_predictions (crop, state);

-- 5. DISEASE DETECTIONS (Module 2)
CREATE TABLE IF NOT EXISTS disease_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
    crop_hint VARCHAR(80),
    image_filename VARCHAR(255) NOT NULL,
    image_mime_type VARCHAR(64) NOT NULL,
    image_size_bytes INTEGER NOT NULL CHECK (image_size_bytes > 0),
    image_sha256 CHAR(64) NOT NULL,
    predicted_label VARCHAR(120) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    is_uncertain BOOLEAN NOT NULL DEFAULT FALSE,
    top_predictions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    treatment_summary TEXT NOT NULL,
    prevention_notes TEXT,
    model_version VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_disease_detections_user_created
    ON disease_detections (user_id, created_at DESC);

-- 6. FERTILIZER RECOMMENDATIONS (Module 4)
CREATE TABLE IF NOT EXISTS fertilizer_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
    nitrogen DOUBLE PRECISION NOT NULL CHECK (nitrogen >= 0),
    phosphorus DOUBLE PRECISION NOT NULL CHECK (phosphorus >= 0),
    potassium DOUBLE PRECISION NOT NULL CHECK (potassium >= 0),
    soil_ph DOUBLE PRECISION NOT NULL CHECK (soil_ph >= 0 AND soil_ph <= 14),
    soil_type VARCHAR(60) NOT NULL,
    crop_type VARCHAR(80) NOT NULL,
    location VARCHAR(120),
    recommended_fertilizer VARCHAR(100) NOT NULL,
    confidence DOUBLE PRECISION CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    nutrient_status_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    advisory_notes TEXT NOT NULL,
    expert_disclaimer TEXT NOT NULL,
    model_version VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_fertilizer_recs_user_created
    ON fertilizer_recommendations (user_id, created_at DESC);

-- 7. IRRIGATION RECOMMENDATIONS (Module 5)
CREATE TABLE IF NOT EXISTS irrigation_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
    location_name VARCHAR(120) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    crop_type VARCHAR(80) NOT NULL,
    growth_stage VARCHAR(40) NOT NULL DEFAULT 'mid_season',
    weather_provider VARCHAR(40) NOT NULL,
    weather_snapshot_json JSONB NOT NULL,
    forecast_rainfall_7d_mm DOUBLE PRECISION NOT NULL CHECK (forecast_rainfall_7d_mm >= 0),
    estimated_et0_mm DOUBLE PRECISION NOT NULL CHECK (estimated_et0_mm >= 0),
    recommended_water_mm DOUBLE PRECISION NOT NULL CHECK (recommended_water_mm >= 0),
    irrigation_urgency VARCHAR(24) NOT NULL
        CHECK (irrigation_urgency IN ('low', 'moderate', 'high', 'skip_rain_expected')),
    is_sensor_backed BOOLEAN NOT NULL DEFAULT FALSE,
    advisory_notes TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_irrigation_recs_user_created
    ON irrigation_recommendations (user_id, created_at DESC);

-- 8. CROP RECOMMENDATIONS (Module 6 persistence)
CREATE TABLE IF NOT EXISTS crop_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
    nitrogen DOUBLE PRECISION NOT NULL CHECK (nitrogen >= 0),
    phosphorus DOUBLE PRECISION NOT NULL CHECK (phosphorus >= 0),
    potassium DOUBLE PRECISION NOT NULL CHECK (potassium >= 0),
    temperature_c DOUBLE PRECISION NOT NULL,
    humidity_pct DOUBLE PRECISION NOT NULL CHECK (humidity_pct >= 0 AND humidity_pct <= 100),
    soil_ph DOUBLE PRECISION NOT NULL CHECK (soil_ph >= 0 AND soil_ph <= 14),
    rainfall_mm DOUBLE PRECISION NOT NULL CHECK (rainfall_mm >= 0),
    season VARCHAR(40),
    region VARCHAR(80),
    recommended_crop VARCHAR(80) NOT NULL,
    top_candidates_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_version VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_crop_recs_user_created
    ON crop_recommendations (user_id, created_at DESC);

-- 9. CHAT SESSIONS (Module 3)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
    title VARCHAR(160) NOT NULL DEFAULT 'New Farming Consultation',
    language VARCHAR(8) NOT NULL DEFAULT 'en'
        CHECK (language IN ('en', 'ta', 'ml', 'hi', 'te')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_updated
    ON chat_sessions (user_id, updated_at DESC);

CREATE TRIGGER trg_chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 10. CHAT MESSAGES (Module 3)
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    provider VARCHAR(32),
    model_name VARCHAR(64),
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_session_created
    ON chat_messages (session_id, created_at ASC);

-- 11. GENERATED REPORTS (Module 8)
CREATE TABLE IF NOT EXISTS generated_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    crop_prediction_id UUID REFERENCES crop_predictions(id) ON DELETE SET NULL,
    fertilizer_recommendation_id UUID REFERENCES fertilizer_recommendations(id) ON DELETE SET NULL,
    irrigation_recommendation_id UUID REFERENCES irrigation_recommendations(id) ON DELETE SET NULL,
    report_payload_json JSONB NOT NULL,
    ai_summary TEXT NOT NULL,
    pdf_filename VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_generated_reports_user_created
    ON generated_reports (user_id, created_at DESC);
