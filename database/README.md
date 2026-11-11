# Database Layer (`database/`)

This directory holds the PostgreSQL schema specification and entity-relationship documentation for **TerraQora AI**.

- [schema.sql](schema.sql): Canonical PostgreSQL 15+ DDL defining all core tables (`users`, `farmer_profiles`, `farms`, `crop_predictions`, `disease_detections`, `fertilizer_recommendations`, `irrigation_recommendations`, `crop_recommendations`, `chat_sessions`, `chat_messages`, `generated_reports`), indexes, constraints, and triggers.
- [ER_DIAGRAM.md](ER_DIAGRAM.md): Mermaid ER diagram and authorization policies.

In **Phase 4**, SQLAlchemy 2.0 ORM models and Alembic migrations inside `backend/app/db/` will match this schema cleanly.
