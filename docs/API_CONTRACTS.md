# TerraQora AI — Frontend / Backend API Contracts (`/api/v1`)

Base URL: `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`).  
Authentication: `Authorization: Bearer <access_token>` (JWT).  
TypeScript types matching these contracts live in [api.ts](../frontend/src/types/api.ts), PostgreSQL DDL lives in [schema.sql](../database/schema.sql), and Phase 4 FastAPI routes live in [backend/app/api/v1/](../backend/app/api/v1/router.py).

> [!NOTE]
> Live endpoints currently active across Phases 4–7: Phase 4 (`/health`, `/auth/*`, `/profile`, `/farms/*`, `/admin/*`), Phase 5 (`/predictions/yield`, `/predictions/yield/history`), Phase 5b (`/recommendations/crop`, `/recommendations/crop/history`, `/recommendations/fertilizer`, `/recommendations/fertilizer/history`), Phase 6 (`/chat/sessions`, `/chat/sessions/{id}/messages`), and Phase 7 (`/disease/detect`, `/disease/history`, `/weather/irrigation`, `/weather/irrigation/history`). When using Instant UI Preview Sandbox or when the backend is offline (`status = 0`), or when querying Phase 8 endpoints (`/analytics/*`, `/reports/*` -> `404`/`501`) in `auto` mode, [services.ts](../frontend/src/api/services.ts) falls back cleanly to `demo_preview`. Live validation (`413`/`415`/`422`), authorization (`401`/`403`), rate limit (`429`), provider timeout/stale (`502`/`503`/`504`), and missing-model (`503`) responses from live endpoints always surface directly to the user rather than falling back silently. Setting `localStorage.tq_api_mode = "live_only"` disables all fallbacks.

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

### 3.2 Plant Disease Detection (CV — **Phase 7 Live**)
- `POST /disease/detect` (Bearer, `multipart/form-data`, rate limit `20/minute`)
- `GET /disease/history?limit=10` (Bearer — returns current farmer's saved scans newest first)
- **Form Fields**: `file` (`image/jpeg`, `image/png`, `image/webp`, `<= 5 MB` — verified by MIME header AND true Pillow byte decoding), `crop_hint` (optional string), `farm_id` (optional UUID)
- **Response (`DiseaseDetectionResponse`)**: `{ id, farm_id?, crop_hint?, image_filename, predicted_label, crop_name, disease_name, is_healthy, confidence, top2_margin?, is_uncertain, uncertainty_reason, top_predictions[], treatment_summary, prevention_notes, next_steps[], limitations[], supported_scope_note, model_version, created_at, source_mode }`
- **Guardrails**: Temperature-calibrated softmax predictions below `0.65` confidence, with `(p1 - p2) < 0.15` top-2 margin, low-detail/blank frames, or unsupported crop hints (`Rice`, `Wheat`, `Cotton`, `Sugarcane`, `Coconut`) set `is_uncertain: true`, abstain from definitive diagnosis, and return photography/KVK guidance without fabricating pesticide dosages. See [DISEASE_DETECTION_ML.md](DISEASE_DETECTION_ML.md).

### 3.3 Smart Fertilizer Recommendation (**Phase 5b Live**)
- `POST /recommendations/fertilizer` (Bearer, rate limit `20/minute`)
- `GET /recommendations/fertilizer/history?limit=10` (Bearer — returns current farmer's saved assessments newest first)
- **Request (`FertilizerRequest`, `extra="forbid"`)**: `{ farm_id?, nitrogen, phosphorus, potassium, soil_ph, soil_type, crop_type, location? }`
- **Guardrails**:
  - Evaluates ICAR soil sufficiency (`N: 40–95`, `P: 30–65`, `K: 30–75`) and `pH` (`< 5.8` / `> 7.8` qualitative guidance) prior to ML inference. When all N/P/K readings meet sufficiency thresholds, returns `recommendation_mode = "agronomic_sufficiency_guardrail"` (`ml_predicted_grade = null`) without pushing chemical fertilizers.
  - Otherwise projects proportional deficits onto the 3-NPK classifier (`Urea`, `DAP`, `28-28`, `14-35-14`, `20-20`, `17-17-17`, `10-26-26`), discloses out-of-domain crop/soil mappings and absent straight MOP (`0-0-60`), and **strictly never invents chemical dosages (`kg/ha` or `g/plant`)**.
- **Response (`FertilizerResponse`)**: `{ id, farm_id?, nitrogen, phosphorus, potassium, soil_ph, soil_type, crop_type, location?, recommended_fertilizer, confidence, ml_predicted_grade?, recommendation_mode, dataset_coverage_note, nutrient_levels[], ph_assessment, advisory_notes, expert_disclaimer, model_version, created_at, source_mode }`

### 3.4 Crop Recommendation (22 Crops — **Phase 5b Live**)
- `POST /recommendations/crop` (Bearer, rate limit `20/minute`)
- `GET /recommendations/crop/history?limit=10` (Bearer — returns current farmer's saved suitability runs newest first)
- **Request (`CropRecommendationRequest`, `extra="forbid"`)**: `{ farm_id?, nitrogen, phosphorus, potassium, temperature_c, humidity_pct, soil_ph, rainfall_mm, season?, region? }`
- **Guardrails**: Probabilities are ranked strictly from the 7 validated soil & climate features in `Crop_recommendation.csv`; optional `season`/`region` are recorded as agronomic context only. Verifies optional `farm_id` ownership (`404`/`403`) and fails closed (`503`) if `.joblib` is unavailable.
- **Response (`CropRecommendationResponse`)**: `{ id, farm_id?, nitrogen, phosphorus, potassium, temperature_c, humidity_pct, soil_ph, rainfall_mm, season?, region?, recommended_crop, top_candidates[], soil_climate_summary, model_version, created_at, source_mode }`. See [RECOMMENDATION_ML.md](RECOMMENDATION_ML.md).

---

## 4. Weather & Irrigation Advisory (**Phase 7 Live**)

- `POST /weather/irrigation` (Bearer, rate limit `60/minute`)
- `GET /weather/irrigation/history?limit=10` (Bearer — returns saved complete advisories newest first)
- **Request (`WeatherIrrigationRequest`, `extra="forbid"`)**: `{ farm_id?, location_name?, latitude?, longitude?, crop_type?, growth_stage?, soil_type?, irrigation_type?, soil_moisture_pct? }`
- **Response (`WeatherIrrigationResponse`)**: Includes `saved_to_history`, `provider_attribution`, `observation_time`, `forecast_generated_at`, `observation_age_minutes`, `freshness_status`, `cache_hit`, `units_summary`, `current_temp_c`, `current_humidity_pct`, `wind_speed_kmh`, `forecast_rainfall_7d_mm`, `estimated_et0_mm`, `recommended_water_mm` (`float | null`), `schedule_status`, `irrigation_urgency`, `is_sensor_backed: false`, `sensor_notice`, `missing_inputs[]`, `assumptions[]`, `advisory_notes`, `alerts[]`, `forecast_7d[]`, `source_mode`.
- **Transparency & Failure Guardrails**: Live Open-Meteo primary provider (CC BY 4.0) with backend-only optional OpenWeatherMap provider, 15-minute coordinate cache, stale-observation cutoff (`503`), upstream timeout (`504`), rate-limit (`429`), and strict abstention (`recommended_water_mm = null`, `saved_to_history = false`) whenever `crop_type`, `growth_stage`, `soil_type`, or `irrigation_type` is missing. Explicitly returns `is_sensor_backed: false` (never simulates IoT probes). See [WEATHER_IRRIGATION.md](WEATHER_IRRIGATION.md).

---

## 5. GenAI Farming Assistant (Multilingual RAG + Gemini — Phase 6 Live)

| Method | Path | Auth | Request Body | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/chat/sessions` | Bearer | — | `ChatSessionOut[]` (ordered by `updated_at DESC`, includes `message_count`) |
| `POST` | `/chat/sessions` | Bearer | `{ language, title?, farm_id? }` | `ChatSessionOut` (`201 Created`) |
| `PATCH` | `/chat/sessions/{id}` | Bearer | `{ title?, language?, farm_id? }` | `ChatSessionOut` |
| `DELETE` | `/chat/sessions/{id}` | Bearer | — | `204 No Content` |
| `GET` | `/chat/sessions/{id}/messages` | Bearer | — | `ChatMessageOut[]` |
| `POST` | `/chat/sessions/{id}/messages` | Bearer (`20/minute`) | `{ content, language: en\|ta\|ml\|hi\|te\|auto, include_farm_context? }` | `{ session, user_message, assistant_message, resolved_language, language_auto_detected, source_mode }` |
| `DELETE` | `/chat/sessions/{id}/messages` | Bearer | — | `204 No Content` |

- **Guardrails**: Uses server-side `GEMINI_API_KEY` (`google-genai`), returns explicit `503` when unconfigured, protects against prompt/secret exfiltration, attaches grounded `citations[]`, and distinguishes RAG vs saved Farm/ML records. See [GENAI_ASSISTANT.md](GENAI_ASSISTANT.md).

---

## 6. Admin Telemetry, Operational Analytics & AI PDF Reports (Phase 8 Live)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| `GET` | `/admin/overview` | Bearer (`admin` role) | Returns `403` for non-admin; real DB counts, active/inactive user breakdown, 5-module activity counts, services health matrix, sanitized recent events & model registry status (`AdminOverviewResponse`) |
| `GET` | `/admin/users` | Bearer (`admin` role) | Platform users directory with `farms_count` and `predictions_count` |
| `PATCH` | `/admin/users/{user_id}` | Bearer (`admin` role) | Update user `role` or `is_active` (blocks self-deactivation/demotion with `400`) |
| `GET` | `/analytics/operational` | Bearer | Real operational telemetry across user's farms & predictions; params: `range_days` (default 30), `farm_id` -> `UserOperationalAnalyticsResponse` |
| `GET` | `/analytics/dataset` | Bearer | Macro agriculture dataset analytics; params: `crop`, `state`, `season`, `year_start`, `year_end` -> `DatasetAnalyticsResponse` |
| `GET` | `/analytics/overview` | Bearer | Dual-mode analytics; returns operational or dataset analytics depending on query params |
| `GET` | `/reports` | Bearer | List generated reports for authenticated farmer -> `GeneratedReport[]` |
| `POST` | `/reports` | Bearer | Generate publication-quality report across 6 types (`combined_intelligence`, `crop_yield`, `crop_recommendation`, `fertilizer_recommendation`, `disease_detection`, `weather_irrigation`) -> `GeneratedReport` |
| `GET` | `/reports/{id}` | Bearer (owner/admin) | Get report metadata and analysis payload |
| `GET` | `/reports/{id}/download` | Bearer (owner/admin) | Binary `application/pdf` ReportLab document download with `Content-Disposition: attachment` |
| `GET` | `/reports/{id}/pdf` | Bearer (owner/admin) | Binary `application/pdf` ReportLab document stream for inline preview |

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
