# TerraQora AI — Phase 7 Live Weather & Irrigation Intelligence

**Module:** Live Meteorological Retrieval & Farm-Aware Irrigation Guidance (`backend/app/services/weather_provider.py`, `weather_service.py`, `api/v1/weather.py`)  
**Transparency Mandate:** All irrigation outputs explicitly disclose `is_sensor_backed: false`, observation timestamps, provider attribution, units, assumptions, and missing field inputs. Missing agronomic fields withhold exact irrigation depths (`recommended_water_mm: null`) rather than fabricating numbers.

---

## 1. Weather API Provider Selection & Deployment Considerations

### Primary Provider: **Open-Meteo Forecast API** (`WEATHER_PROVIDER=open_meteo`)
- **Endpoint:** `https://api.open-meteo.com/v1/forecast`
- **Variables Retrieved:**
  - `current`: `temperature_2m` (°C), `relative_humidity_2m` (%), `wind_speed_10m` (km/h), `weather_code` (WMO), `precipitation` (mm), observation `time` (`utc_offset_seconds`)
  - `daily` (7 days): `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, `precipitation_probability_max`, `et0_fao_evapotranspiration`, `relative_humidity_2m_mean`
- **Authentication:** No API key required on the Open-Meteo open non-commercial tier.
- **License & Attribution:** **CC BY 4.0** for non-commercial open use — TerraQora displays `"Weather data by Open-Meteo.com (CC BY 4.0 non-commercial open API)"` inside responses and the UI.
- **Free-Tier Limits & Commercial Deployment Implications:**
  - Standard public tier allows up to **10,000 API calls/day** (5,000/hour, 600/minute) from a non-commercial host.
  - **Commercial Production Note:** Open-Meteo's free tier is restricted to non-commercial use. Prior to launching commercial paid tiers, either upgrade to an Open-Meteo Commercial Plan (`customer-api.open-meteo.com`) or configure an authenticated `OpenWeatherMap` subscription (`WEATHER_PROVIDER=openweather`).

### Optional Secondary Adapter: **OpenWeatherMap** (`WEATHER_PROVIDER=openweather`)
- Uses `https://api.openweathermap.org/data/2.5/forecast` with `OPENWEATHER_API_KEY` read strictly from backend environment variables (`Settings.resolved_openweather_api_key`).
- Never exposed to the frontend. Missing or placeholder keys raise HTTP `503 Service Unavailable`.
- Computes daily Hargreaves–Samani reference evapotranspiration ($ET_0$) when daily $ET_0$ is omitted by OpenWeatherMap 3-hour slices.

---

## 2. Caching, Timeouts, Rate Limiting & Stale-Data Controls

| Control | Env Variable | Default | Behavior |
| --- | --- | --- | --- |
| Request Timeout | `WEATHER_TIMEOUT_SECONDS` | `10` s | Upstream timeout returns HTTP `504` |
| Coordinate TTL Cache | `WEATHER_CACHE_TTL_SECONDS` | `900` s (15 min) | Deduplicates calls per `(provider, round(lat, 3), round(lon, 3))` |
| Stale Observation Cutoff | `WEATHER_STALE_MAX_AGE_MINUTES` | `180` min (3 hr) | Observations older than 3 hours raise HTTP `503` ("stale observation") |
| Endpoint Rate Limit | `RATE_LIMIT_DEFAULT` | `60/minute` | SlowAPI limiter on `POST /api/v1/weather/irrigation` |

- **No Fake Fallbacks in Live Mode:** Upstream errors (`429`, `502`, `503`, `504`) and stale weather snapshots return explicit HTTP errors to the UI (`ErrorAlert` + Retry) rather than substituting historical stubs as live weather.

---

## 3. Irrigation Guidance Methodology & Honest Assumptions

1. **Meteorological Water Balance:** Sums 7-day forecast rainfall ($\Sigma P_{7d}$, mm) and FAO-56 reference evapotranspiration ($\Sigma ET_{0,7d}$, mm).
2. **Required Agronomic Inputs Check:** Before calculating gross irrigation depth (`recommended_water_mm`), TerraQora checks whether `crop_type`, `growth_stage` (`!= 'unknown'`), `soil_type`, and `irrigation_type` are available (either from the linked owned `Farm` record or explicit request parameters).
   - **If ANY required agronomic input is missing:** `recommended_water_mm` is set to `null`, `schedule_status = "insufficient_agronomic_inputs"`, `irrigation_urgency = "insufficient_data"`, missing fields are itemized in `missing_inputs[]`, and the incomplete inquiry is **not** saved as a synthetic schedule (`saved_to_history = false`).
   - **If `irrigation_type == "rainfed"`:** `recommended_water_mm = 0.0`, `schedule_status = "rainfed_advisory"`, focusing on moisture conservation (bunding/mulching) or storm drainage.
   - **If all inputs are supplied:**
     $$\text{ET}_c = \Sigma ET_{0,7d} \times K_c(\text{crop}, \text{stage}), \quad P_{\text{eff}} = \Sigma P_{7d} \times \eta_{\text{soil}}, \quad \text{Gross Irrigation} = \frac{\max(0, \text{ET}_c - P_{\text{eff}})}{\eta_{\text{method}}}$$
3. **Soil Moisture Sensor Disclosure:** Because physical tensiometers / capacitive soil moisture probes are not integrated, `in_field_soil_moisture_sensor_reading` is explicitly flagged inside `missing_inputs[]` (unless entered manually by the farmer) alongside `is_sensor_backed: false`.
