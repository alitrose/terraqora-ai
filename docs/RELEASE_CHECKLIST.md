# TerraQora AI — Release Checklist & Version Gate

**Target Release:** v1.0.0-rc1  
**Target Milestone:** Phase 10 Production Release  
**Branch:** `dev` -> `main`

---

## 1. Release Verification Gates

- [x] **Gate 1: Zero Exposed Secrets** — All `.env`, API keys, and test tokens scrubbed or masked.
- [x] **Gate 2: Preserved Datasets** — Raw historical datasets checksum-verified against Phase 2 baseline.
- [x] **Gate 3: All Automated Tests Green** — 42 backend pytest tests and 14 frontend Vitest tests pass.
- [x] **Gate 4: TypeScript Clean** — `npx tsc --noEmit` exits with code 0.
- [x] **Gate 5: Production Frontend Bundle** — `npm run build` succeeds under 1.2 MB total assets.
- [x] **Gate 6: Offline Database Schema** — Alembic compiles valid PostgreSQL DDL with triggers and UUIDs.
- [x] **Gate 7: Security Headers Configured** — ASGI middleware and Vercel configuration apply security headers.
- [x] **Gate 8: Turnkey IaC Blueprint** — `render.yaml` and `frontend/vercel.json` defined and validated.
- [x] **Gate 9: Complete Documentation** — Comprehensive README, Installation guide, Security audit, and API contracts.
- [ ] **Gate 10: Final Merge Approval** — User review and approval to merge `dev` into `main` and execute Phase 10 deployment.

---

## 2. Release Steps to Merge into `main` (Upon Phase 10 Approval)

```bash
# 1. Ensure dev is clean and all tests pass
git checkout dev
git status

# 2. Checkout main branch
git checkout main

# 3. Fast-forward or merge dev into main
git merge dev --no-ff -m "Release v1.0.0: TerraQora AI Smart Agriculture Platform"

# 4. Tag release version
git tag -a v1.0.0 -m "TerraQora AI v1.0.0 Release"

# 5. Push to GitHub (Only when user explicitly approves Phase 10)
# git push origin main --tags
```
