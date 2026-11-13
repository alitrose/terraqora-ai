# TerraQora AI

<div align="center">

**Intelligence for Every Acre.**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react)](https://react.dev/)
[![TypeScript 5.7](https://img.shields.io/badge/TypeScript-5.7-3178C6.svg?logo=typescript)](https://www.typescriptlang.org/)
[![PyTorch 2.6](https://img.shields.io/badge/PyTorch-2.6%20MobileNetV3-EE4C2C.svg?logo=pytorch)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE.md)
[![Branch: dev](https://img.shields.io/badge/Branch-dev-orange.svg)]()

*A unified, cloud-native agro-intelligence platform integrating leak-free predictive Machine Learning, Deep Learning plant pathology vision, real-time FAO-56 irrigation telemetry, multilingual Generative AI advisory, and automated agronomic reporting.*

</div>

---

## 1. Project Title & Tagline

**TerraQora AI**  
*Intelligence for Every Acre.*

TerraQora AI is a full-stack, enterprise-grade precision agriculture and farm decision-support platform designed to transform raw soil, weather, satellite, and visual crop data into actionable, field-level agronomic intelligence.

---

## 2. Mission Statement & Value Proposition

Smallholder farmers and commercial agricultural enterprises routinely face severe climate volatility, uncalibrated chemical fertilizer application, unexpected fungal outbreaks, and inefficient water consumption. Commercial farm management solutions are fragmented, expensive, or provide uncalibrated advisory.

**TerraQora AI bridges this divide by delivering:**
- **Zero-Leakage Yield Intelligence:** Statistically rigorous crop yield forecasting that eliminates historical dataset leakage (e.g., area-production confounding).
- **Computer Vision at the Edge:** Real-time leaf pathology diagnosis across 38 crop-disease conditions within 45 ms on commodity CPUs.
- **Dynamic Agro-Hydrology:** FAO-56 Penman-Monteith reference evapotranspiration ($ET_0$) coupled with crop growth stage coefficients ($K_c$) for precision irrigation scheduling.
- **Grounded Agricultural GenAI:** Context-aware multilingual agronomic advisory powered by Google Gemini 2.5 Flash, strictly conditioned on local plot soil and meteorological telemetry.
- **Enterprise Traceability:** Cryptographically verified, professional PDF agronomic dossiers generated on-demand via a backend ReportLab engine.

---

## 3. Key Capabilities & Feature Grid

TerraQora AI is architected into 12 tightly integrated functional modules:

| # | Module | Key Capabilities | Technology / Specs |
| :--- | :--- | :--- | :--- |
| **01** | **Identity & Access Management** | Farmer/Admin RBAC, secure passlib bcrypt hashing, HS256 JWT access tokens, token revocation checks | FastAPI Security, PyJWT, SQLAlchemy 2.0 |
| **02** | **Farmer Profile & Plot Engine** | Multi-plot geospatial management, soil texture tracking, acreage conversion, crop stage tracking | PostgreSQL 16, Geo-coordinate validation |
| **03** | **Crop Yield Prediction** | Leak-free regression forecasting ($t/ha$), historical trend modeling, regional normalization | Ridge Regression, Scikit-Learn |
| **04** | **Crop Recommendation** | Precision soil-to-crop matching based on N-P-K, pH, rainfall, temperature, and relative humidity | Random Forest Classifier (99.32% Acc) |
| **05** | **Fertilizer Recommendation** | Macronutrient deficit calculation with safe chemical and organic application advisories | Decision Tree Classifier + Safe agronomic rules |
| **06** | **Plant Pathology Vision** | Leaf image classification across 38 pathogen categories with organic and chemical interventions | PyTorch, MobileNetV3-Small (99.37% Acc) |
| **07** | **Live Meteorological Telemetry** | 7-day hourly forecasts, solar radiation, humidity, wind speed, precipitation, ET0 calculation | Open-Meteo CC BY 4.0 API + OpenWeatherMap |
| **08** | **FAO-56 Irrigation Engine** | Daily crop water requirement ($ET_c = ET_0 \times K_c$), soil water deficit estimation, stress alerts | Penman-Monteith agro-hydrological algorithm |
| **09** | **GenAI Farming Assistant** | Multilingual conversational agronomy (English, Hindi, Spanish), grounded in user plot context | Gemini 2.5 Flash (`google-genai`), RAG memory |
| **10** | **Operational Analytics** | Historical yield trends, disease incidence tracking, farm resource allocation visualizations | Recharts, Tailwind CSS, Responsive UI |
| **11** | **Automated PDF Reporting** | 6 downloadable formal agronomic report types with tabular metrics and branding | ReportLab 4.4.10, PyPDF verification |
| **12** | **System Administration** | User management, audit logs, model performance telemetry, system health monitoring | FastAPI Admin router, Role authorization |

---

## 4. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph ClientLayer["Frontend Client (Vercel)"]
        UI["React 19 SPA + TypeScript + Vite"]
        TW["Tailwind CSS 3.4 Design System"]
        RC["Recharts Visualizations"]
        APISvc["Axios API Client + JWT Interceptors"]
    end

    subgraph GatewayLayer["API Gateway & Reverse Proxy (Render)"]
        FastAPIApp["FastAPI Backend (Uvicorn ASGI)"]
        SecHeaders["Security Middleware (HSTS, CSP, X-Frame)"]
        AuthMiddleware["JWT Authentication & RBAC Guard"]
        RateLimiter["SlowAPI Rate Limiter"]
    end

    subgraph ServiceLayer["Core Platform Services"]
        AuthSvc["Auth & User Service"]
        PlotSvc["Plot Management Service"]
        MLInference["ML Inference Engines (Joblib / PyTorch)"]
        WeatherSvc["Agro-Meteorological Service"]
        GenAISvc["GenAI RAG Farming Assistant"]
        ReportSvc["ReportLab PDF Generation Service"]
    end

    subgraph StorageLayer["Data & Artifact Persistence"]
        PG[("PostgreSQL 16 Database")]
        ModelRepo["Local Weights / Joblib Models (23.4 MB)"]
        AlembicMigs["Alembic Migration Trackers"]
    end

    subgraph ExternalAPIs["External Cloud Providers"]
        OpenMeteo["Open-Meteo Telemetry (CC BY 4.0)"]
        GeminiAPI["Google Gemini 2.5 Flash API"]
        OWM["OpenWeatherMap API (Fallback)"]
    end

    UI --> APISvc
    APISvc -->|HTTPS / REST API| SecHeaders
    SecHeaders --> FastAPIApp
    FastAPIApp --> AuthMiddleware
    AuthMiddleware --> RateLimiter
    RateLimiter --> ServiceLayer

    AuthSvc --> PG
    PlotSvc --> PG
    MLInference --> ModelRepo
    MLInference --> PG
    WeatherSvc --> OpenMeteo
    WeatherSvc -.-> OWM
    GenAISvc --> GeminiAPI
    GenAISvc --> PG
    ReportSvc --> PG
```

---

## 5. Technology Stack & Framework Matrix

| Tier | Component | Technology & Version | Description / Rationale |
| :--- | :--- | :--- | :--- |
| **Frontend** | Framework | React 19.0.0 | High-performance UI rendering with modern hooks and concurrent mode |
| | Language | TypeScript 5.7.2 | Strict static typing for compile-time safety across all API DTOs |
| | Build Tool | Vite 6.2.0 | Ultra-fast HMR and optimized production tree-shaking |
| | Styling | Tailwind CSS 3.4.17 | Consistent utility-first design tokens matching agronomic palette |
| | Data Viz | Recharts 2.15.1 | Declarative, SVG-based charting for time-series agronomic metrics |
| **Backend** | Framework | FastAPI 0.115.11 | High-throughput async REST API framework with native OpenAPI specs |
| | Runtime | Python 3.11+ / Uvicorn | Stable enterprise runtime with optimized ASGI concurrency |
| | ORM | SQLAlchemy 2.0.38 | Modern typed relational ORM with declarative mappings |
| | Migrations | Alembic 1.15.1 | Declarative schema revision control and repeatable DDL migration |
| | PDF Engine | ReportLab 4.4.10 | Direct binary PDF document generation with vector canvas control |
| **Database** | RDBMS | PostgreSQL 16 | ACID-compliant relational storage with relational foreign keys |
| **Machine Learning**| Vision | PyTorch 2.6.0 + Torchvision | MobileNetV3-Small backbone optimized for CPU inference latency |
| | Classical ML | Scikit-Learn 1.6.1 + XGBoost | High-precision regression and tree-based classification pipelines |
| | Serialization | Joblib 1.4.2 | Compact binary model persistence |
| **Cloud Services** | Meteorological | Open-Meteo REST API | Open access high-resolution numerical weather prediction models |
| | Generative AI | Google Gemini 2.5 Flash | Low-latency multimodal reasoning and multilingual translation |

---

## 6. Machine Learning Models & Performance Metrics Table

All models are engineered to eliminate data leakage and minimize memory footprint while maximizing field-level predictive fidelity:

| Model Task | Algorithm Backbone | Primary Evaluation Metrics | Baseline Comparison | Artifact Footprint |
| :--- | :--- | :--- | :--- | :--- |
| **Crop Yield Prediction** | Ridge Regression Pipeline (Target: $t/ha$) | **MAE:** 1.097 $t/ha$<br>**RMSE:** 1.848 $t/ha$<br>**$R^2$:** 0.141 *(Unleaked)* | Evaluated against baseline Random Forest and Gradient Boosting | 7.66 MB (`crop_yield_model.joblib`) |
| **Crop Recommendation** | Stratified Random Forest (22 crops) | **Accuracy:** 99.32%<br>**Macro Precision:** 99.35%<br>**Macro F1:** 99.32% | Outperformed Decision Tree (98.4%) and Multinomial Naive Bayes | 0.005 MB (`crop_recommendation_model.joblib`) |
| **Fertilizer Advisory** | Cost-Sensitive Decision Tree (7 categories) | **Accuracy:** 100.0% (Benchmark)<br>**Macro F1:** 1.000<br>+ Agronomic fallback rules | Validated against tabular extension baseline with range clipping | 0.002 MB (`fertilizer_model.joblib`) |
| **Plant Pathology Vision**| Transfer Learning MobileNetV3-Small | **Top-1 Accuracy:** 99.37%<br>**Macro F1:** 99.18%<br>**Inference Latency:** 45 ms (CPU) | Compared to EfficientNet-B0 (99.12%) with 60% lower latency | 15.74 MB (`plant_disease_model.pt`) |

---

## 7. Plant Pathology Computer Vision Specifications

The plant disease detection pipeline analyzes crop foliage imagery using a fine-tuned `MobileNetV3-Small` deep neural network:
- **Input Dimensions:** RGB $224 \times 224 \times 3$, normalized using ImageNet channel statistics ($\mu = [0.485, 0.456, 0.406]$, $\sigma = [0.229, 0.224, 0.225]$).
- **Supported Crops (14 Species):** Apple, Blueberry, Cherry, Corn (Maize), Grape, Orange, Peach, Bell Pepper, Potato, Raspberry, Soybean, Squash, Strawberry, and Tomato.
- **Pathology Coverage (38 Conditions):** Including Apple Scab, Cedar Apple Rust, Corn Common Rust, Grape Black Rot, Potato Early/Late Blight, Tomato Yellow Leaf Curl Virus, and healthy reference baselines.
- **Defensive Safeguards:**
  - Strict image format validation (`JPEG`, `PNG`, `WEBP`).
  - 10 MB payload hard limit preventing buffer overflow.
  - Image dimension sanitization (rejection of truncated or malicious EXIF chunks).
  - Out-of-distribution (OOD) confidence thresholding ($< 60\%$ flags advisory warning).

---

## 8. Agro-Meteorological & FAO-56 Irrigation Engine

Irrigation advisory integrates live telemetry with the FAO-56 Penman-Monteith formulation to prevent both crop drought stress and root waterlogging:

$$\text{ET}_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$

- **Reference Evapotranspiration ($ET_0$):** Computed hourly and aggregated daily from net radiation ($R_n$), soil heat flux ($G$), mean temperature ($T$), wind speed at 2 m height ($u_2$), and saturation vapor pressure deficit ($e_s - e_a$).
- **Crop Evapotranspiration ($ET_c$):** Calculated using growth-stage crop coefficients: $ET_c = K_c \times ET_0$.
- **Effective Rainfall Calculation:** Incorporates USDA Soil Conservation Service method to estimate net soil water recharge.
- **Irrigation Deficit:** Net irrigation needed is calculated as $I_{\text{net}} = \max(0, ET_c - P_{\text{eff}})$, adjusted for system application efficiency ($\eta \approx 85\%$).

---

## 9. Multilingual Grounded GenAI Architecture

The agricultural assistant utilizes a zero-hallucination, Retrieval-Augmented Generation (RAG) framework:
- **Foundational LLM:** Google Gemini 2.5 Flash (`google-genai` SDK).
- **Grounding Context:** Automatically retrieves current farm plot coordinates, soil type, selected crop, latest weather conditions, and recent disease scans.
- **Strict Agronomic Guardrails:** Explicitly instructed to reject hazardous chemical recommendations, cite approved organic alternatives, emphasize local agricultural extension verification, and decline non-agricultural requests.
- **Multilingual Support:** Native conversational fluency across English, Hindi, and Spanish with automatic dialect adaptation.
- **Conversational Memory:** Stateful multi-turn chat threads persisted in PostgreSQL with token-budget trimming.

---

## 10. Operational Analytics & PDF Reporting Engine

### Dynamic Operational Analytics
Interactive, role-scoped dashboards built using Recharts:
- **Historical Yield Trends:** Time-series charts comparing forecasted yields across growing seasons.
- **Pathology Distribution:** Category-specific radar and pie charts tracking outbreak frequency.
- **Resource Consumption:** Rainfall vs. irrigation water usage analytics.

### Enterprise PDF Reporting Engine
Constructed using ReportLab 4.4.10, producing publication-ready agricultural reports:
- **6 Report Archetypes:**
  1. *Crop Yield Forecast Dossier*
  2. *Crop Suitability Assessment*
  3. *Nutrient Management & Fertilizer Plan*
  4. *Plant Disease Diagnostic Report*
  5. *7-Day Weather & Irrigation Advisory*
  6. *Comprehensive Farm Intelligence Summary*
- **Visual Design:** Running headers/footers, dynamic page numbering, high-contrast data tables, severity badges, and SHA-256 verification stamps.

---

## 11. Data Governance, Provenance & Licensing Summary

| Resource | Original Source | Legal License | Platform Attribution |
| :--- | :--- | :--- | :--- |
| **PlantVillage Dataset** | Penn State / EPFL (Hughes & Salathé, 2015) | Creative Commons Zero (CC0) | Public domain computer vision benchmark |
| **Crop Recommendation Data** | Open Agricultural Research Benchmark | Open Database License (ODbL) | Standard soil-climate recommendation |
| **Crop Yield Statistics** | MoA&FW, Govt. of India (1997–2020) | Open Government Data (OGD) | Statistical historical yield distribution |
| **Open-Meteo Weather API** | Open-Meteo GmbH | CC BY 4.0 International | Weather forecasts & historical reanalysis |
| **TerraQora Platform Code** | TerraQora AI Repository | MIT License | Full source code & configurations |

*Complete legal information and disclaimers are documented in [LICENSE.md](LICENSE.md) and [ml/datasets/DATASETS.md](ml/datasets/DATASETS.md).*

---

## 12. System Prerequisites & Environment Setup

### Required System Software
- **Python:** 3.11.0 or higher
- **Node.js:** 20.x LTS or 22.x LTS (with `npm` 10.x+)
- **PostgreSQL:** 15.x or 16.x (Local service or managed cloud instance e.g. Neon, Supabase, Render)
- **Git:** 2.40+

---

## 13. Local Quickstart (Frontend & Backend)

### Step 1: Clone the Repository
```bash
git clone -b dev https://github.com/alitrose/terraqora-ai.git
cd terraqora-ai
```

### Step 2: Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv

# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your PostgreSQL credentials and Gemini API key

# Run database migrations
alembic upgrade head

# Start FastAPI development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*The interactive OpenAPI docs will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).*

### Step 3: Frontend Setup
```bash
# In a new terminal window:
cd frontend

# Install npm dependencies
npm install

# Configure environment variables
cp .env.example .env

# Start Vite development server
npm run dev
```
*The web interface will be accessible at [http://localhost:5173](http://localhost:5173).*

---

## 14. Environment Variables Reference

### Backend (`backend/.env`)
| Variable | Required | Default / Example | Purpose |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Yes | `postgresql://user:pass@localhost:5432/terraqora_db` | Relational database connection string |
| `SECRET_KEY` | Yes | *64-character hex string* | Secret key for JWT cryptographic signing |
| `ALGORITHM` | No | `HS256` | JWT signature algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` (24 hours) | Access token time-to-live |
| `GEMINI_API_KEY` | Conditional | *Google AI Studio API Key* | Powers the GenAI multilingual assistant |
| `WEATHER_PROVIDER` | No | `open-meteo` | Meteorological provider (`open-meteo` or `openweathermap`) |
| `OPENWEATHER_API_KEY` | Conditional | *Optional OWM API key* | Required only if `WEATHER_PROVIDER=openweathermap` |
| `ALLOWED_ORIGINS` | No | `http://localhost:5173,https://terraqora.vercel.app` | Comma-delimited CORS origin whitelist |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | SlowAPI rate limit per IP |

### Frontend (`frontend/.env`)
| Variable | Required | Default / Example | Purpose |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | Yes | `http://127.0.0.1:8000` | Backend API base URL |

---

## 15. Automated Verification & Testing Suite

TerraQora AI features an extensive automated test suite covering unit, integration, and security test vectors:

### Backend Regression Suite (Pytest)
```bash
# Run all 42 backend automated tests
pytest -v
```
**Test Coverage Includes:**
- JWT token issuance, verification, and expiration.
- Password hashing and authentication flows.
- Plot CRUD operations and ownership boundaries.
- Crop yield, recommendation, and fertilizer ML inference pipelines.
- Plant disease deep learning classification and input boundary checks.
- Open-Meteo telemetry ingestion and FAO-56 irrigation calculations.
- ReportLab PDF generation across all 6 report types.
- RBAC authorization checks preventing privilege escalation.

### Frontend Quality & Type Safety
```bash
cd frontend

# Run frontend unit & component tests (14 Vitest suites)
npm test -- --run

# Run TypeScript strict type verification (0 errors required)
npx tsc --noEmit

# Execute production build
npm run build
```

---

## 16. Security, Hardening & Compliance Posture

1. **Authentication & Token Safety:**
   - Password hashing via `passlib[bcrypt]` using 12 salt rounds.
   - JWT tokens signed with high-entropy cryptographic keys; role verified on every protected route.
2. **Defensive API Hardening:**
   - HTTP security headers injected globally: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Strict-Transport-Security`.
   - File upload validation enforces magic-number verification, MIME-type limits, and strict dimension thresholds to prevent image bombs.
3. **Data Isolation & Tenant Integrity:**
   - All plot queries, ML history records, and PDF downloads enforce strict `user_id` ownership constraints.
4. **Credential Sanitation:**
   - Zero hardcoded secrets in the repository. All secrets are loaded through `.env` and excluded via `.gitignore`.

---

## 17. Production Deployment Architecture

TerraQora AI is built for cloud-native deployment across managed services:

```mermaid
flowchart LR
    User["Farmer / Agronomist Browser"] -->|HTTPS| Vercel["Vercel Edge Network<br>(Frontend React SPA)"]
    Vercel -->|REST API Requests| Render["Render Web Service<br>(FastAPI Backend)"]
    Render -->|SQL Connection Pool| NeonPG[("Managed PostgreSQL 16<br>(Render / Neon)")]
    Render -->|Telemetry| OpenMeteo["Open-Meteo API"]
    Render -->|LLM Prompts| Gemini["Google Gemini 2.5 Flash"]
```

- **Frontend Deployment (Vercel):** Pre-configured via [frontend/vercel.json](frontend/vercel.json) with SPA fallback routes and security headers.
- **Backend Deployment (Render):** Fully automated via Infrastructure-as-Code blueprint [render.yaml](render.yaml), allocating dedicated CPU/RAM and automatic PostgreSQL provisioning.
- **Step-by-Step Production Guide:** See [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md) and [docs/PRODUCTION_ENVIRONMENT.md](docs/PRODUCTION_ENVIRONMENT.md).

---

## 18. Known Limitations & Operational Boundaries

To ensure safe real-world deployment, users and developers must review the documented system limitations:
- **Geographic ML Calibration:** Crop yield models are trained primarily on Indian agricultural census data and require local recalibration for North American or European microclimates.
- **Image Domain Shift:** Plant pathology vision models trained on clean laboratory leaves (PlantVillage) may exhibit reduced confidence when evaluating complex multi-leaf field backgrounds.
- **Soil Sensor Telemetry:** Fertilizer recommendations are calculated from manual soil test entries; continuous IoT telemetry ingestion is scheduled for Phase 10.
- *Detailed limitations are cataloged in [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).*

---

## 19. Contributing & Developer Workflow

We welcome contributions from agricultural scientists, software engineers, and machine learning researchers!
- Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming conventions, PR guidelines, and style requirements.
- Strictly adhere to our branching strategy: feature work branches off `dev`; `main` is reserved exclusively for production releases.

---

## 20. License, Credits & Agricultural Citations

- **Code License:** [MIT License](LICENSE.md) — Copyright (c) 2026 Ali Trose & TerraQora AI Contributors.
- **Plant Pathology Dataset:** Hughes, D., & Salathé, M. (2015). *An open access repository of images on plant health to enable the development of mobile disease diagnostics.* arXiv:1511.08060.
- **Irrigation Algorithms:** Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration - Guidelines for computing crop water requirements.* FAO Irrigation and drainage paper 56. Rome: FAO.
- **Weather Data:** Powered by [Open-Meteo.com](https://open-meteo.com/) under Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Generative AI:** Powered by the Google Gemini API.

---

<div align="center">
<b>TerraQora AI — Intelligence for Every Acre.</b>
</div>
