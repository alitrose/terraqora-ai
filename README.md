# TerraQora AI

**Intelligence for Every Acre.**

TerraQora AI is an AI-powered smart agriculture platform combining leak-free Machine Learning, Deep Learning plant pathology vision, real-time meteorological irrigation advisory, agricultural analytics, and grounded multilingual Generative AI.

> **Current Build Phase:** Phase 2 — Architecture, Brand Identity, Repository Structure & PostgreSQL Schema Design (`dev` branch).

## Architecture Overview
- **Frontend:** React + TypeScript + Tailwind CSS + Recharts (deployed to Vercel)
- **Backend:** Python + FastAPI + SQLAlchemy 2.0 + Alembic + ReportLab (deployed to Render)
- **Database:** Managed PostgreSQL (`database/schema.sql`)
- **ML / CV:** Scikit-learn, XGBoost, TensorFlow/Keras, OpenCV (`ml/`)
- **GenAI:** Google Gemini (`google-genai`) behind a provider abstraction + agricultural RAG (`ai/`)

## Documentation Index
- [System Architecture](docs/ARCHITECTURE.md)
- [Brand Guidelines](docs/BRAND_GUIDELINES.md)
- [Database Schema](database/schema.sql) & [ER Diagram](database/ER_DIAGRAM.md)
- [Dataset Provenance](ml/datasets/DATASETS.md)
- [Git Workflow](docs/GIT_WORKFLOW.md)
- [Implementation Roadmap](docs/ROADMAP.md)
- [Deployment Plan](docs/DEPLOYMENT_PLAN.md)
