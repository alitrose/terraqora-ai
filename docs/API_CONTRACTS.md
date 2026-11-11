# TerraQora AI — Frontend / Backend API Contracts (`/api/v1`)

Base URL: `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`).  
Authentication: `Authorization: Bearer <access_token>` (JWT).  
TypeScript types matching these contracts live in [api.ts](../frontend/src/types/api.ts), and PostgreSQL persistence tables live in [schema.sql](../database/schema.sql).

> [!NOTE]
> During Phase 3 frontend verification, when `http://localhost:8000/api/v1` is unreachable (`status = 0`), [services.ts](../frontend/src/api/services.ts) falls back automatically in `auto` mode to synthetic demonstration data flagged with `source_mode: "demo_preview"`. Setting `localStorage.tq_api_mode = "live_only"` disables fallback.

---

## 1. Authentication & User Session

| Method | Path | Auth | Request Body | Response (`200` / `201`) |
| --- | --- | --- | --- | --- |
| `POST` | `/auth/register` | Public | `{ email, password, full_name, preferred_language, state? }` | `AuthSession` (`access_token`, `token_type`, `user`) |
| `POST` | `/auth/login` | Public | `{ email, password }` | `AuthSession` |
| `GET` | `/auth/me` | Bearer | — | `User` |

- `preferred_language` enum: `'en' | 'ta' | 'ml' | 'hi' | 'te'`
- `role` enum: `'farmer' | 'admin'`

---

## 2. Profile & Farms CRUD

| Method | Path | Auth | Request Body | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/profile` | Bearer | — | `FarmerProfile` |
| `PUT` | `/profile` | Bearer | `Partial<FarmerProfile>` (`phone`, `state`, `district`, `experience_years`, `primary_soil_type`, `preferred_units`) | `FarmerProfile` |
| `GET` | `/farms` | Bearer | — | `Farm[]` |
| `POST` | `/farms` | Bearer | `{ name, state, district?, latitude?, longitude?, area_hectares, soil_type?, soil_ph?, irrigation_type?, primary_crop? }` | `Farm` (`201`) |
| `DELETE` | `/farms/{farm_id}` | Bearer (owner) | — | `204 No Content` |

Validation rules:
- `area_hectares > 0`
- `soil_ph` in `[0, 14]`
- `irrigation_type` enum: `'rainfed' | 'drip' | 'sprinkler' | 'canal' | 'borewell' | 'mixed'`

---

## 3. Machine Learning & Computer Vision Modules

### 3.1 Crop Yield Prediction (Leak-Free)
- `POST /predictions/yield` (Bearer)
- **Request (`CropYieldRequest`)**: `{ farm_id?, crop, crop_year, season, state, area_hectares, annual_rainfall_mm, fertilizer_kg, pesticide_kg }`
- **Guardrail**: Post-harvest `Production` is **strictly omitted** from the request schema to prevent target leakage (`r = 0.9965` leak in raw data).
- **Response (`CropYieldResponse`)**: `{ id, crop, state, season, crop_year, area_hectares, predicted_yield, yield_unit, estimated_total_production, production_unit, model_name, model_version, feature_drivers[], advisory_note, created_at, source_mode }`
- Note: `Coconut` yields report `yield_unit = "nuts/hectare"`; all other 54 crops report `"tonnes/hectare"`.

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

## 4. Weather & Irrigation Advisory

- `POST /weather/irrigation` (Bearer)
- **Request (`WeatherIrrigationRequest`)**: `{ farm_id?, location_name, latitude, longitude, crop_type, growth_stage }`
- **Response (`WeatherIrrigationResponse`)**: Includes `current_temp_c`, `current_humidity_pct`, `wind_speed_kmh`, `forecast_rainfall_7d_mm`, `estimated_et0_mm`, `recommended_water_mm`, `irrigation_urgency`, `is_sensor_backed: false`, `sensor_notice`, `alerts[]`, `forecast_7d[]`, `source_mode`.
- Transparency contract: Backend returns `is_sensor_backed: false` explicitly indicating meteorological estimation rather than physical soil probe hardware.

---

## 5. GenAI Farming Assistant (Multilingual RAG)

| Method | Path | Auth | Request Body | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/chat/sessions` | Bearer | — | `ChatSession[]` |
| `POST` | `/chat/sessions` | Bearer | `{ language, title?, farm_id? }` | `ChatSession` |
| `GET` | `/chat/sessions/{id}/messages` | Bearer | — | `ChatMessage[]` |
| `POST` | `/chat/sessions/{id}/messages` | Bearer | `{ content, language }` | `{ user_message, assistant_message }` |
| `DELETE` | `/chat/sessions/{id}/messages` | Bearer | — | `204 No Content` |

---

## 6. Dataset Analytics, AI Reports & Admin

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| `GET` | `/analytics/overview` | Bearer | Query params: `crop`, `state`, `season`, `year_start`, `year_end` → `AnalyticsResponse` |
| `GET` | `/reports` | Bearer | Returns `GeneratedReport[]` |
| `POST` | `/reports` | Bearer | `ReportCreateRequest` → `GeneratedReport` |
| `GET` | `/reports/{id}/pdf` | Bearer | Binary `application/pdf` ReportLab download (`Phase 6`) |
| `GET` | `/admin/overview` | Bearer (`admin` role) | Returns `403` for non-admin; `AdminOverviewResponse` |

---

## 7. Standard Error Envelope

FastAPI HTTP errors follow:
```json
{
  "detail": "Human-readable validation or authorization error message"
}
```
Frontend `ApiError` extracts `detail` cleanly across `400`, `401`, `403`, `404`, `413`, `422`, `429`, and `500` status codes.
