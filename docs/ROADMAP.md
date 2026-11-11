# TerraQora AI — 10-Phase Implementation Roadmap

| Phase | Scope | Exit Criteria / Tests | Status |
| --- | --- | --- | --- |
| **Phase 1** | Audit existing GitHub repo, notebooks, datasets, security & environment | Complete audit report & plan | **Completed** |
| **Phase 2** | Architecture, Brand Identity (SVG logo/favicon/tokens), Repo Structure, Git `main`/`dev` + Local Backup, PostgreSQL DDL + ER diagram, Deployment plan | Foundation test suite passes; zero secrets committed | **Current** |
| **Phase 3** | Build React + TypeScript + Tailwind + Recharts frontend (13 responsive pages + brand assets + typed API client) | `tsc --noEmit`, `npm run build`, Vitest component & layout tests | Planned |
| **Phase 4** | Build FastAPI backend, SQLAlchemy 2.0 models, Alembic migrations, JWT auth + RBAC, rate limiting, CORS, health endpoint | `pytest` API, Auth, DB schema & migration tests | Planned |
| **Phase 5** | Clean datasets, run EDA, train & benchmark Yield (LR/DT/RF/XGBoost), Crop Recommendation, and Fertilizer models; integrate ML inference APIs | `pytest` ML integrity, zero-leakage & prediction tests | Planned |
| **Phase 6** | Implement `LLMProvider` abstraction (`GeminiProvider` via `google-genai`), agricultural RAG corpus, 5-language SSE chat, and ReportLab PDF export | `pytest` RAG grounding, streaming, rate-limit & PDF tests | Planned |
| **Phase 7** | Acquire PlantVillage dataset, train & calibrate Transfer-Learning CNN (`TensorFlow/Keras` + `OpenCV`), implement Open-Meteo/OpenWeather irrigation service | `pytest` upload validation, CNN accuracy/uncertainty & weather tests | Planned |
| **Phase 8** | End-to-end integration testing across frontend, backend, DB, ML, CV, GenAI, Auth, and responsive desktop/tablet/mobile viewports | Full test suite green; zero critical bugs | Planned |
| **Phase 9** | Create/sync `alitrose/terraqora-ai`, write polished `README.md`, API docs, model evaluation cards, screenshots; secret scan | Clean `dev` -> `main` merge; zero secrets or large blobs | Planned |
| **Phase 10** | Deploy Frontend (Vercel), Backend (Render), Managed PostgreSQL (Render); run live migrations and verify live URLs | Live `/health`, auth, predictions, chat, and UI verified end-to-end | Planned |
