# TerraQora AI — Machine Learning & Computer Vision (`ml/`)

Houses verified datasets (`datasets/`), leak-free preprocessing (`preprocessing/`), model training scripts (`training/`), evaluation benchmarks (`evaluation/`), and serialized production artifacts (`saved_models/`).

See [DATASETS.md](datasets/DATASETS.md) for dataset provenance & SHA-256 verification and [CROP_YIELD_ML.md](../docs/CROP_YIELD_ML.md) for the complete Phase 5 Crop Yield ML audit, benchmarks, and model limitations.

---

## Structure

```text
ml/
├── audit_crop_yield.py                 # Stage 1 read-only dataset & leakage audit
├── datasets/
│   ├── DATASETS.md
│   └── raw/                            # Original CSVs (preserved read-only)
├── evaluation/
│   ├── crop_yield_audit.json           # Verified empirical dataset audit output
│   └── crop_yield_metrics.json         # Chronological 7-model benchmark + error analysis
├── preprocessing/
│   ├── crop_yield_features.py          # Canonical validation + scale-invariant feature engineering
│   └── crop_yield_model.py             # SegmentedYieldPredictor + exact TreeSHAP drivers
├── saved_models/
│   └── crop_yield_model.joblib         # Generated locally (~0.47 MB; gitignored *.joblib)
└── training/
    └── train_crop_yield.py             # Chronological training, benchmarking & serialization
```

## Reproducing Crop Yield Model Locally

Because compiled binary model artifacts (`*.joblib`, `*.pkl`) are excluded by `.gitignore`, regenerate `ml/saved_models/crop_yield_model.joblib` after cloning using the workspace `.venv`:

```powershell
.\.venv\Scripts\python.exe -m ml.audit_crop_yield
.\.venv\Scripts\python.exe -m ml.training.train_crop_yield
```
