# TerraQora AI — Git Branching & Backup Strategy

## 1. Repository & Branch Topology
- **Remote Target (to be created once Phase 8 tests pass):** `alitrose/terraqora-ai`
- **Untouched Legacy Remote:** `alitrose/SMART-FRAMING-APP` remains completely untouched.
- **Production Branch:** `main` — stable, tested, deployable snapshots only.
- **Development Branch:** `dev` — primary integration branch across Phases 2–9.
- **Feature Branches:** `feature/<phase-or-module>` (branched from and merged into `dev`).

## 2. Local Legacy Backup
All original notebooks, Flask stub, pickled model, and raw CSV datasets were archived without deleting or modifying any original files:
- **Backup Archive:** `C:\Users\alitr\Backups\TerraQora_Legacy_Backup_20261111.zip`
- **Untouched Original Sources:**
  - `C:\Users\alitr\OneDrive\Desktop\2026IN\`
  - `C:\Users\alitr\Downloads\Crop_recommendation.csv`
- **Security Hygiene:** Legacy notebooks containing exposed API keys are **excluded from Git history** so secrets never enter commits or remote branches.
