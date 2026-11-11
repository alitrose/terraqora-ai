# TerraQora AI — Frontend (`frontend/`)

**Tagline:** *Intelligence for Every Acre.*  
**Stack:** React 18 · TypeScript · Tailwind CSS · Recharts · Lucide Icons · React Router v6 · Vite

## Quick Start

```bash
npm install
npm run dev       # Starts Vite dev server on http://localhost:5173 (proxies /api -> localhost:8000)
```

## Verification Commands

```bash
npx tsc --noEmit  # Strict TypeScript check
npm test          # Vitest + React Testing Library suite (14 tests)
npm run build     # Production bundle into dist/
```

## Implemented Pages (13 Routes)

1. `/` — `LandingPage`
2. `/auth` — `AuthPage` (Login, Registration, Demo Sandbox Entry)
3. `/dashboard` — `FarmerDashboardPage`
4. `/yield-prediction` — `CropYieldPredictionPage` (Leak-free input contract; Coconut in nuts/ha)
5. `/disease-detection` — `PlantDiseaseDetectionPage` (MIME/5 MB validation + `< 65%` uncertainty notice)
6. `/fertilizer` — `FertilizerRecommendationPage`
7. `/crop-recommendation` — `CropRecommendationPage`
8. `/weather-irrigation` — `WeatherIrrigationPage` (`is_sensor_backed: false` transparency notice)
9. `/assistant` — `GenAIAssistantPage` (`en`, `ta`, `ml`, `hi`, `te` + RAG citations + clear chat)
10. `/analytics` — `AgricultureAnalyticsPage` (Filters + 5 Recharts views + Correlation Matrix)
11. `/reports` — `AIReportsPage` (Executive report builder, Print/PDF export)
12. `/profile` — `UserProfilePage` (Farmer preferences + Farm Plots CRUD)
13. `/admin` — `AdminDashboardPage` (Admin-guarded model registry & user directory)

## API & Preview Sandbox Mode

- API contracts are defined in [docs/API_CONTRACTS.md](../docs/API_CONTRACTS.md) and typed in `src/types/api.ts`.
- Configure `VITE_API_BASE_URL` in `.env` (defaults to `http://localhost:8000/api/v1`).
- When the FastAPI backend is offline in `auto` mode, `src/api/services.ts` serves labeled synthetic data (`source_mode: "demo_preview"`).

## Brand & Assets
- `public/terraqora-logo.svg` — Full brand lockup
- `public/terraqora-mark.svg` — Icon emblem
- `public/favicon.svg` — Browser favicon
- `design-tokens.json` — Palette, typography, radii, and chart color tokens
