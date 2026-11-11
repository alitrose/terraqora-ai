# TerraQora AI — Machine Learning & Computer Vision (`ml/`)

Houses verified datasets (`datasets/`), leak-free preprocessing (`preprocessing/`), model training scripts (`training/`), evaluation benchmarks (`evaluation/`), and serialized production artifacts (`saved_models/`).

See [DATASETS.md](datasets/DATASETS.md) for dataset provenance & SHA-256 verification, [CROP_YIELD_ML.md](../docs/CROP_YIELD_ML.md) for Phase 5 Crop Yield ML benchmarks, and [RECOMMENDATION_ML.md](../docs/RECOMMENDATION_ML.md) for Phase 5B Crop & Fertilizer Recommendation audits, benchmarks, and safety rules.

---

## Structure

```text
ml/
├── audit_crop_yield.py                 # Phase 5: crop_yield.csv dataset & leakage audit
├── audit_crop_recommendation.py        # Phase 5B: Crop_recommendation.csv audit
├── audit_fertilizer.py                 # Phase 5B: Fertilizer_Prediction.csv + alternative audit
├── datasets/
│   ├── DATASETS.md
│   └── raw/                            # Original CSVs (preserved read-only)
├── evaluation/
│   ├── crop_yield_audit.json           # Phase 5 empirical dataset audit
│   ├── crop_yield_metrics.json         # Chronological 7-model yield benchmark
│   ├── crop_rec_audit.json             # Phase 5B crop dataset audit (2,200 rows)
│   ├── crop_rec_metrics.json           # Stratified 7-model crop classification benchmark
│   ├── fertilizer_audit.json           # Phase 5B fertilizer audit + MI + rejected dataset log
│   └── fertilizer_metrics.json         # Stratified 8-model ablation & confusion matrix
├── preprocessing/
│   ├── crop_yield_features.py          # Phase 5 canonical validation + scale-invariant engineering
│   ├── crop_yield_model.py             # SegmentedYieldPredictor + exact TreeSHAP drivers
│   ├── crop_rec_features.py            # Phase 5B crop recommendation validation & ratios
│   ├── crop_rec_model.py               # GaussianNB/multiclass wrapper + quartile fit reasons
│   ├── fertilizer_features.py          # Phase 5B fertilizer normalization + ICAR soil rules
│   └── fertilizer_model.py             # FertilizerClassifierModel grade predictor wrapper
├── saved_models/
│   ├── crop_yield_model.joblib         # Generated locally (~0.47 MB; gitignored *.joblib)
│   ├── crop_recommendation_model.joblib # Generated locally (~5.6 KB; gitignored *.joblib)
│   └── fertilizer_model.joblib         # Generated locally (~1.6 KB; gitignored *.joblib)
└── training/
    ├── train_crop_yield.py             # Phase 5 chronological training & serialization
    ├── train_crop_recommendation.py    # Phase 5B stratified crop classification training
    └── train_fertilizer.py             # Phase 5B stratified fertilizer ablation & training
```

## Reproducing Trained Models Locally

Because compiled binary model artifacts (`*.joblib`, `*.pkl`) are excluded by `.gitignore`, regenerate all Phase 5 & 5B `.joblib` artifacts locally using the workspace `.venv`:

```powershell
# Phase 5: Crop Yield Prediction
.\.venv\Scripts\python.exe -m ml.audit_crop_yield
.\.venv\Scripts\python.exe -m ml.training.train_crop_yield

# Phase 5B Part A: Crop Recommendation
.\.venv\Scripts\python.exe -m ml.audit_crop_recommendation
.\.venv\Scripts\python.exe -m ml.training.train_crop_recommendation

# Phase 5B Part B: Fertilizer Recommendation
.\.venv\Scripts\python.exe -m ml.audit_fertilizer
.\.venv\Scripts\python.exe -m ml.training.train_fertilizer
```
