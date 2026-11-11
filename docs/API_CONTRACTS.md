# TerraQora AI — Frontend / Backend API Contracts (`/api/v1`)

Base URL: `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`).  
Authentication: `Authorization: Bearer <access_token>` (JWT).  
TypeScript types matching these contracts live in [api.ts](../frontend/src/types/api.ts), PostgreSQL DDL lives in [schema.sql](../database/schema.sql), and Phase 4 FastAPI routes live in [backend/app/api/v1/](../backend/app/api/v1/router.py).

> [!NOTE]
> Live endpoints currently active: Phase 4 (`/health`, `/auth/*`, `/profile`, `/farms/*`, `/admin/*`) and Phase 5 (`/predictions/yield`, `/predictions/yield/history`) authenticate, infer, and persist directly against the FastAPI + SQLAlchemy backend. When using Instant UI Preview Sandbox or when the backend is offline (`status = 0`), or when querying unimplemented Phase 5b–8 endpoints (`404`/`501`) in `auto` mode, [services.ts](../frontend/src/api/services.ts) falls back cleanly to `demo_preview`. Live validation (`422`), authorization (`401`/`403`), and missing-model (`503`) responses from `/predictions/yield` always surface directly to the user rather than falling back silently to preview numbers. Setting `localStorage.tq_api_mode = "live_only"` disables all fallbacks.

---

## 0. Health & Readiness (Phase 4 Live)

| Method | Path | Auth | Response (`200`) |
| --- | --- | --- | --- |
| `GET` | `/health` (root) | Public | `{ status: "ok", service, version, database: "connected" }` |
| `GET` | `/api/v1/health` | Public | `{ status: "ok", service, version, database: "connected" }` |

---

## 1. Authentication & User Session (Phase 4 Live)

| Method | Path | Auth | Request Body | Response (`200` / `201`) |
| --- | --- | --- | --- | --- |
| `POST` | `/auth/register` | Public | `{ email, password, full_name, preferred_language, state? }` | `AuthSession` (`access_token`, `token_type`, `user`) (`201`) |
| `POST` | `/auth/login` | Public | `{ email, password }` | `AuthSession` (`200`) |
| `GET` | `/auth/me` | Bearer | — | `User` (`200`) |

- `preferred_language` enum: `'en' | 'ta' | 'ml' | 'hi' | 'te'`
- `role` enum: `'farmer' | 'admin'` (public `/auth/register` always assigns `'farmer'`)

---

## 2. Profile & Farms CRUD (Phase 4 Live)

| Method | Path | Auth | Request Body | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/profile` | Bearer | — | `FarmerProfile` (`200`) |
| `PUT` | `/profile` | Bearer | `Partial<FarmerProfile>` (`phone`, `state`, `district`, `experience_years`, `primary_soil_type`, `preferred_units`, `preferred_language?`) | `FarmerProfile` (`200`) |
| `GET` | `/farms` | Bearer | — | `Farm[]` (`200`) |
| `POST` | `/farms` | Bearer | `{ name, state, district?, latitude?, longitude?, area_hectares, soil_type?, soil_ph?, irrigation_type?, primary_crop? }` | `Farm` (`201`) |
| `GET` | `/farms/{farm_id}` | Bearer (owner / admin) | — | `Farm` (`200`) |
| `PUT` | `/farms/{farm_id}` | Bearer (owner / admin) | Partial / full `Farm` fields | `Farm` (`200`) |
| `PATCH` | `/farms/{farm_id}` | Bearer (owner / admin) | Partial `Farm` fields | `Farm` (`200`) |
| `DELETE` | `/farms/{farm_id}` | Bearer (owner / admin) | — | `204 No Content` |

Validation rules:
- `area_hectares > 0` (`<= 100000`)
- `latitude` in `[-90, 90]`, `longitude` in `[-180, 180]`
- `soil_ph` in `[0, 14]`
- `experience_years` in `[0, 90]`
- `irrigation_type` enum: `'rainfed' | 'drip' | 'sprinkler' | 'canal' | 'borewell' | 'mixed'`

---

## 3. Machine Learning & Computer Vision Modules (Phases 5 & 7)

### 3.1 Crop Yield Prediction (Leak-Free — **Phase 5 Live**)
- `POST /predictions/yield` (Bearer, rate limit `20/minute`)
- `GET /predictions/yield/history?limit=10` (Bearer — returns current farmer's persisted predictions newest first)
- **Request (`CropYieldRequest`, `extra="forbid"`)**: `{ farm_id?, crop, crop_year, season, state, area_hectares, annual_rainfall_mm, fertilizer_kg, pesticide_kg }`
- **Guardrails**:
  - Post-harvest `Production` (and any unknown extra fields such as `production`, `Production`, `yield`) are **strictly rejected with HTTP `422`** (`extra="forbid"`) to prevent target leakage (`r = 0.9965` leak in raw data).
  - Canonicalizes `crop` (`55` crops), `state` (`30` regions), and `season` (`6` seasons); verifies optional `farm_id` ownership (`404` if missing, `403` if owned by another farmer).
  - Missing or corrupted `.joblib` artifact returns safe HTTP `503 Service Unavailable` without leaking server paths or tracebacks.
- **Response (`CropYieldResponse`)**: `{ id, farm_id?, crop, state, season, crop_year, area_hectares, predicted_yield, yield_unit, estimated_total_production, production_unit, model_name, model_version, feature_drivers[], advisory_note, created_at, source_mode }`
- Note: `Coconut` yields report `yield_unit = "nuts/hectare"`; all other 54 crops report `"tonnes/hectare"`. `feature_drivers[]` contains per-prediction normalized **Saabas decision-path / TreeSHAP** percentages (`positive` / `negative` / `neutral`). See [CROP_YIELD_ML.md](CROP_YIELD_ML.md).

### 3.2 Plant Disease Detection (CV)
- `POST /disease/detect` (Bearer, `multipart/form-data`)
- **Form Fields**: `file` (`image/jpeg`, `image/png`, `image/webp`, `<= 5 MB`), `crop_hint` (optional string)
- **Response (`DiseaseDetectionResponse`)**: `{ id, image_filename, predicted_label, crop_name, disease_name, is_healthy, confidence, is_uncertain, uncertainty_reason, top_predictions[], treatment_summary, prevention_notes, model_version, created_at, source_mode }`
- Guardrail: Predictions with `confidence < 0.65` set `is_uncertain: true` and return an actionable photography/expert consultation warning.

### 3.3 Smart Fertilizer Recommendation
- `POST /recommendations/fertilizer` (Bearer)
- **Request (`FertilizerRequest`)**: `{ farm_id?, nitrogen, phosphorus, potassium, soil_ph, soil_type, crop_type, location }`
- **Response (`FertilizerResponse`)**: `{ id, recommended_fertilizer, confidence, nutrient_levels[], ph_assessment, advisory_notes, expert_disclaimer, model_version, created_at, source_mode }`

### 3.4 Crop Recommendation (22 Crops)
- `POST /recommendations/crop` (Bearer)
- **Request (`CropRecommendationRequest`)**: `{ farm_id?, nitrogen, phosphorus, potassium, temperature_c, humidity_pct, soil_ph, rainfall_mm, season, region }`
- **Response (`CropRecommendationResponse`)**: `{ id, recommended_crop, top_candidates[], soil_climate_summary, model_version, created_at, source_mode }`

---

## 4. Weather & Irrigation Advisory (Phase 7)

- `POST /weather/irrigation` (Bearer)
- **Request (`WeatherIrrigationRequest`)**: `{ farm_id?, location_name, latitude, longitude, crop_type, growth_stage }`
- **Response (`WeatherIrrigationResponse`)**: Includes `current_temp_c`, `current_humidity_pct`, `wind_speed_kmh`, `forecast_rainfall_7d_mm`, `estimated_et0_mm`, `recommended_water_mm`, `irrigation_urgency`, `is_sensor_backed: false`, `sensor_notice`, `alerts[]`, `forecast_7d[]`, `source_mode`.
- Transparency contract: Backend returns `is_sensor_backed: false` explicitly indicating meteorological estimation rather than physical soil probe hardware.

---

## 5. GenAI Farming Assistant (Multilingual RAG — Phase 6)

| Method | Path | Auth | Request Body | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/chat/sessions` | Bearer | — | `ChatSession[]` |
| `POST` | `/chat/sessions` | Bearer | `{ language, title?, farm_id? }` | `ChatSession` |
| `GET` | `/chat/sessions/{id}/messages` | Bearer | — | `ChatMessage[]` |
| `POST` | `/chat/sessions/{id}/messages` | Bearer | `{ content, language }` | `{ user_message, assistant_message }` |
| `DELETE` | `/chat/sessions/{id}/messages` | Bearer | — | `204 No Content` |

---

## 6. Admin Telemetry (Phase 4 Live) & Dataset Analytics / AI Reports (Phases 5–8)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| `GET` | `/admin/overview` | Bearer (`admin` role) | Returns `403` for non-admin; real DB counts + model registry status (`AdminOverviewResponse`) |
| `GET` | `/admin/users` | Bearer (`admin` role) | Platform users directory with `farms_count` and `predictions_count` |
| `PATCH` | `/admin/users/{user_id}` | Bearer (`admin` role) | Update user `role` or `is_active` (blocks self-deactivation/demotion with `400`) |
| `GET` | `/analytics/overview` | Bearer (`Phase 5/8`) | Query params: `crop`, `state`, `season`, `year_start`, `year_end` -> `AnalyticsResponse` |
| `GET` | `/reports` | Bearer (`Phase 6/8`) | Returns `GeneratedReport[]` |
| `POST` | `/reports` | Bearer (`Phase 6/8`) | `ReportCreateRequest` -> `GeneratedReport` |
| `GET` | `/reports/{id}/pdf` | Bearer (`Phase 6/8`) | Binary `application/pdf` ReportLab download |

---

## 7. Standard Error Envelope

FastAPI HTTP errors follow:
```json
{
  "detail": "Human-readable validation or authorization error message"
}
```
Validation errors (`422`) additionally include structured field-level details:
```json
{
  "detail": "area_hectares: Input should be greater than 0",
  "errors": [
    {
      "field": "area_hectares",
      "message": "Input should be greater than 0",
      "type": "greater_than"
    }
  ]
}
```
Frontend `ApiError` extracts `detail` cleanly across `400`, `401`, `403`, `404`, `409`, `413`, `422`, `429`, `500`, and `503` status codes.
