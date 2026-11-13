# Contributing to TerraQora AI

Thank you for your interest in contributing to **TerraQora AI — Intelligence for Every Acre.**

We welcome contributions from software developers, agronomists, data scientists, ML engineers, and agricultural domain researchers.

---

## 1. Development Principles & Code Standards

1. **Zero Target Leakage in ML:** Never introduce post-harvest or collinear features (e.g. `Production`) into pre-harvest crop yield prediction models.
2. **Zero Fabricated Chemical Dosages:** Never generate arbitrary chemical fertilizer or pesticide quantities without validation against accredited soil testing standards (e.g. ICAR / TNAU Soil Health Cards).
3. **Multi-Tenant Row-Level Isolation:** Every user query must be strictly scoped to `current_user.id`. Farm plot ownership must be verified before executing read or write operations.
4. **Zero Hardcoded Secrets:** Never commit `.env` files, API keys, passwords, or tokens. Always use `.env.example` as a template and load configuration via `pydantic-settings`.
5. **Strict Typing & Linting:** 
   - Backend Python code must adhere to PEP 8, SQLAlchemy 2.0 type annotations, and Pydantic v2 schemas.
   - Frontend TypeScript code must compile cleanly with `npx tsc --noEmit` under strict null checks.

---

## 2. Git Workflow

- All feature development and bug fixes take place on feature branches branching off `dev`:
  ```bash
  git checkout dev
  git checkout -b feature/your-feature-name
  ```
- Write targeted unit and integration tests under `tests/` or `frontend/src/test/`.
- Ensure all existing tests pass before submitting a pull request:
  ```bash
  # Backend
  pytest -v
  
  # Frontend
  cd frontend
  npm test -- --run
  npx tsc --noEmit
  npm run build
  ```
- Pull requests are opened against `dev`. Direct pushes to `main` are strictly prohibited.

---

## 3. Reporting Issues & Vulnerabilities

- **Bug Reports:** Open an issue with full reproduction steps, expected behavior, observed logs, and system environment details.
- **Security Disclosures:** If you discover a potential security vulnerability or credential exposure, please do not file a public issue. Contact the repository maintainers directly.
