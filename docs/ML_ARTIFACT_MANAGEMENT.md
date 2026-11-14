# TerraQora AI — Machine Learning Artifact Management & Packaging Strategy

**Document Status:** Complete & Verified  
**Branch:** `dev`  
**Author:** ML Engineering & DevSecOps  
**Scope:** Model Serialization, Checksums, Reproducibility & Deployment Strategy

---

## 1. Verified Model Artifacts Manifest

All 4 machine learning and computer vision models are serialized, versioned, and stored locally in `ml/saved_models/`:

| Model Identifier | Architecture / Algorithm | File Name | Size (MB) | SHA-256 Checksum | Runtime Framework |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Crop Yield Prediction** | Segmented Random Forest Regressor (Non-Coconut + Coconut) | `crop_yield_model.joblib` | **7.660 MB** | `0c1a619a2dc01dc6f2957947b8cb418744e68d46434bc3e4a4b7b323ad5d09e0` | `scikit-learn>=1.5.0`, `joblib` |
| **Crop Recommendation** | Gaussian Naive Bayes Classifier | `crop_recommendation_model.joblib` | **0.005 MB** | `11c950bbaedef1f2916a3728962fdb856c931a65ca24e258e1cabb01bdb5117a` | `scikit-learn>=1.5.0`, `joblib` |
| **Fertilizer Recommendation**| Logistic Regression (3 NPK Features) + Zero Dosages | `fertilizer_model.joblib` | **0.002 MB** | `4be5fd9c06401acd9041e52c724235a8c43f5da27ba10670b7609e0f7bfbc2e7` | `scikit-learn>=1.5.0`, `joblib` |
| **Plant Pathology CV** | EfficientNet-B0 Transfer Learning (38 Classes) | `plant_disease_model.pt` | **15.744 MB** | `c1fc22bf1bee57067f64504af52e35d4ae9163a55a61fbe854180ae8f0eb1597` | `torch>=2.4.0`, `torchvision>=0.19.0` |

**Total Combined Model Footprint:** **~23.41 MB**  
This lightweight footprint easily satisfies Render's 512 MB free-tier RAM limit and avoids out-of-memory (OOM) fatal crashes.

---

## 2. Training Pipelines & Deterministic Reproducibility

Every model can be deterministically re-trained and re-evaluated from source datasets using the dedicated training scripts in `ml/training/`:

```
ml/
├── audit_crop_recommendation.py     # EDA and data quality audit for Crop Recommendation
├── audit_fertilizer.py              # EDA and data quality audit for Fertilizer
├── audit_crop_yield.py               # Leakage audit for Crop Yield (Production exclusion)
├── training/
│   ├── train_crop_yield.py          # Trains Yield models (Ridge, DT, RF, XGBoost)
│   ├── train_crop_recommendation.py # Trains 22-class Crop Recommendation classifier
│   ├── train_fertilizer.py          # Trains 7-formulation Fertilizer classifier
│   └── train_plant_disease.py       # Fine-tunes EfficientNet-B0 on 38 PlantVillage classes
└── preprocessing/
    ├── pipeline.py                  # Crop yield feature pipelines
    ├── recommendation_features.py   # Crop & Fertilizer transformers
    └── disease_features.py          # Image decoding, validation & perceptual dHash
```

### Reproducibility Commands
```bash
# 1. Train Crop Yield Model (7.66 MB output)
python ml/training/train_crop_yield.py

# 2. Train Crop Recommendation Model (5 KB output)
python ml/training/train_crop_recommendation.py

# 3. Train Fertilizer Model (2 KB output)
python ml/training/train_fertilizer.py

# 4. Train Plant Disease Vision Model (15.74 MB output)
python ml/training/train_plant_disease.py
```

---

## 3. Git Tracking & Storage Strategy

### Git Ignore Policy
All model weights (`*.joblib`, `*.pt`, `*.pth`, `*.pkl`, `*.onnx`) and heavy parquet files are strictly excluded via `.gitignore`:
```gitignore
*.pkl
*.joblib
*.h5
*.keras
*.tflite
*.onnx
*.pt
*.pth
*.parquet
ml/saved_models/*.joblib
ml/saved_models/*.pt
```

### Production Deployment Artifact Storage Approaches

1. **Option A: Container Build Phase (Current / Recommended for Render)**
   - Because all 4 models total only **23.4 MB**, model weights can be downloaded or bundled during Docker/Render container build using a verified SHA-256 pre-flight script.
2. **Option B: Cloud Object Storage (S3 / Cloudflare R2 / GCS)**
   - For enterprise scale, model weights are uploaded to an S3/R2 bucket with public/presigned read access.
   - On ASGI server startup, if `ml/saved_models/<model>` is missing, the application automatically downloads the artifact and validates its SHA-256 hash before initialization.

---

## 4. Missing Model Behavior & Fault Tolerance

If an artifact is deleted or unavailable:
- The backend does **not** crash on startup.
- Calling the affected endpoint returns `HTTP 503 Service Unavailable`:
  `detail="Crop yield model is not available on this server. Contact system administrator."`
- Admin dashboard marks the affected module as `Unavailable` in the Model Registry.
- This behavior is tested in `tests/test_phase5_crop_yield.py` and `tests/test_phase7_disease_detection.py`.
