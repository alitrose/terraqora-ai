# TerraQora AI — Phase 7 Plant Disease Vision ML Report

**Module:** Leaf Disease Computer Vision Screening (`ml/audit_plant_disease.py`, `ml/preprocessing/disease_features.py`, `ml/preprocessing/disease_model.py`, `ml/training/train_plant_disease.py`, `backend/app/services/disease_service.py`)  
**Runtime Stack:** PyTorch CPU (`weights_only=True` safe checkpoint) + Pillow + OpenCV + scikit-learn  
**Role Statement:** Screening aid only — calibrated uncertainty gates abstain on ambiguous, low-detail, out-of-scope crops, or conflicting crop context instead of returning false confidence.

---

## 1. Dataset Selection, License & Provenance
- **Dataset:** PlantVillage Leaf Disease Repository — Hughes & Salathé (2015), *arXiv:1511.08060*
- **Verified Public-Domain Source:** `BrandonFors/Plant-Diseases-PlantVillage-Dataset` (HuggingFace Parquet distribution, `3` shards totaling `812.61 MB`: `test-00000-of-00001.parquet` `161.95 MB`, `train-00000-of-00002.parquet` `305.77 MB`, `train-00001-of-00002.parquet` `344.89 MB`)
- **License:** `CC0 1.0` (Public Domain Dedication)
- **Audit Script & Report:** [audit_plant_disease.py](../ml/audit_plant_disease.py) → [disease_audit.json](../ml/evaluation/disease_audit.json)

### Supported Scope vs. Explicit Exclusions
- **38 Classes across 14 Crop Species (`SUPPORTED_SPECIES_CANONICAL`):** Apple, Blueberry, Cherry, Corn (Maize), Grape, Orange (Citrus), Peach, Pepper (Bell), Potato, Raspberry, Soybean, Squash, Strawberry, and Tomato.
- **Major Crops Explicitly Excluded (Unsupported):** Rice, Wheat, Cotton, Sugarcane, Coconut, Banana, Groundnut, Chickpea, Mustard, Onion, and Mango. Providing one of these in `crop_hint` triggers immediate out-of-scope abstention (`Uncertain___Out_Of_Scope_Crop`).

---

## 2. Dataset Integrity, Class Balance & Leakage Audit
Audited across all `54,305` rows of the raw repository:
- **Valid Decoded Images:** `54,305 / 54,305` RGB `JPEG` images (`256×256` px), `0` corrupt/unreadable files.
- **Raw Class Imbalance (`36.23×`):** Ranges from `152` images (`Potato___healthy`) up to `5,507` images (`Orange___Haunglongbing_(Citrus_greening)`) and `5,090` (`Soybean___healthy`).
- **Duplicate & Upstream Cross-Split Leakage Detected:**
  - `21` exact SHA-256 duplicates (`54,284` unique SHA-256 digests).
  - `31` perceptual 64-bit dHash near-duplicates (`54,274` unique dHash signatures).
  - `7` exact SHA-256 images and `8` perceptual dHash clusters leaked across the upstream HuggingFace `train` and `test` shards, plus `1` cross-class dHash collision.
- **Leakage Mitigation & Balanced Split Index ([disease_splits.parquet](../ml/datasets/processed/disease_splits.parquet)):**
  - Excluded cross-class collision groups, collapsed near-duplicate dHash clusters to canonical representatives, and rebuilt grouped-stratified splits (`seed = 20261112`) capped at `120 / 30 / 45` per class (`Potato___healthy`: `99 / 23 / 30`):
    - **Train:** `4,539` images
    - **Validation:** `1,133` images
    - **Held-Out Test:** `1,695` images
    - **Total Curated Images:** `7,367`
  - Verified **`0` SHA-256 overlap** and **`0` dHash overlap** across every pair among `train`, `val`, and `test`.

---

## 3. Model Comparison & Calibration Benchmarks
All three candidate architectures were trained strictly on the deduplicated `4,539`-image train split, tuned/calibrated on the `1,133`-image validation split, and evaluated once on the untouched `1,695`-image held-out test split ([train_plant_disease.py](../ml/training/train_plant_disease.py) → [disease_metrics.json](../ml/evaluation/disease_metrics.json)):

| Model | Params (Trainable / Total) | Train Time | Val Macro-F1 | Test Acc | Test Top-3 Acc | Test Macro-P / R / F1 | ECE (Uncal → Cal) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **HSV+RGB Histogram (96-dim) + LogReg Baseline** | `N/A` | `28.7 s` | `0.7580` | `0.7546` | `0.9027` | `0.7552 / 0.7558 / 0.7531` | `0.0630` (raw) |
| **MobileNetV3-Small** (ImageNet TL) | `1.27M / 1.56M` | `648.6 s` | `0.9299` | `0.9386` | `0.9894` | `0.9441 / 0.9392 / 0.9384` | `0.1192 → 0.0088` |
| **`EfficientNet-B0` (Selected)** | **`3.20M / 4.06M`** | `5871.2 s` | **`0.9684`** | **`0.9593`** | **`0.9959`** | **`0.9603 / 0.9596 / 0.9592`** | **`0.0943 → 0.0117`** |

### Why `EfficientNet-B0` Was Selected
- `EfficientNet-B0` improved held-out Macro-F1 by **`+20.61` percentage points** over the color-histogram baseline and **`+2.08` percentage points** over `MobileNetV3-Small` (`0.9592` vs `0.9384`), achieving `99.59%` Top-3 held-out accuracy across 38 classes.
- Post-hoc **temperature scaling** (`T = 0.5341` fitted on validation NLL) improved confidence calibration dramatically on the held-out test split:
  - **10-bin Expected Calibration Error (ECE):** dropped from `0.09426` → **`0.01167`** (`87.6%` reduction in calibration error).
  - **Brier Score:** dropped from `0.07804` → **`0.05817`**.
- **Saved Production Artifact:** `ml/saved_models/plant_disease_model.pt` (`16,508,567 bytes` / **`15.74 MB`**), containing only primitive metadata + tensor `state_dict` so production loads cleanly via `torch.load(..., map_location="cpu", weights_only=True)`.

---

## 4. Abstention Thresholds & OOD Safety Evaluation
To convert calibrated probabilities into safe agricultural screening behavior, production applies dual abstention thresholds (`DISEASE_CONFIDENCE_THRESHOLD=0.65`, `DISEASE_MIN_MARGIN=0.15`):

| Confidence Cutoff | Min Top-2 Margin | Held-Out Coverage | Selective Accuracy | Abstained Samples (`/ 1,695`) |
| ---: | ---: | ---: | ---: | ---: |
| `0.50` | `0.15` | `98.58%` | `96.89%` | `24` |
| `0.60` | `0.15` | `97.40%` | `97.58%` | `44` |
| **`0.65` (Selected)** | **`0.15`** | **`96.40%`** | **`97.80%`** | **`61`** |
| `0.75` | `0.15` | `94.22%` | `98.37%` | `98` |
| `0.85` | `0.15` | `92.21%` | `98.72%` | `132` |

### Verified Abstention & OOD Gate Checks
1. **Blank White Frame (`224×224`):** `confidence = 0.0438`, `is_uncertain = true` (low-detail variance gate + confidence gate).
2. **Flat Green Canvas (`224×224`):** `confidence = 0.0444`, `is_uncertain = true` (low-detail variance gate + confidence gate).
3. **Gaussian Noise Frame (`224×224`):** `confidence = 0.2674`, `is_uncertain = true` (below `0.65` calibrated confidence cutoff).
4. **Unsupported Crop Hint (`Rice`):** `is_uncertain = true`, `predicted_label = "Uncertain___Out_Of_Scope_Crop"`.
5. **Species Mismatch Guardrail:** If the farmer specifies a supported `crop_hint` (e.g., `Potato`) whose prefix disagrees with the visual top-1 crop species, the predictor abstains and requests clear single-leaf confirmation.

---

## 5. Error Analysis (Held-Out Test Set: `69` Errors / `1,695` Samples)
Seven classes achieved `F1 = 1.0000` (`Apple___Black_rot`, `Apple___Cedar_apple_rust`, `Cherry_(including_sour)___Powdery_mildew`, `Cherry_(including_sour)___healthy`, `Orange___Haunglongbing_(Citrus_greening)`, `Soybean___healthy`, and `Squash___Powdery_mildew`). Lowest F1 classes and dominant error modes align closely with biological lesion similarity:

- **Hardest Classes (n = 45 each):**
  - `Tomato___Early_blight`: `F1 = 0.8193` (`P = 0.8947`, `R = 0.7556`)
  - `Tomato___Late_blight`: `F1 = 0.8261` (`P = 0.8085`, `R = 0.8444`)
  - `Tomato___Target_Spot`: `F1 = 0.8571` (`P = 0.9231`, `R = 0.8000`)
  - `Corn_(maize)___Northern_Leaf_Blight`: `F1 = 0.8791` (`P = 0.8696`, `R = 0.8889`)
  - `Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot`: `F1 = 0.9011` (`P = 0.8913`, `R = 0.9111`)
  - `Pepper,_bell___Bacterial_spot`: `F1 = 0.9011` (`P = 0.8913`, `R = 0.9111`)
- **Dominant Off-Diagonal Confusions:**
  - `Tomato___Early_blight ↔ Tomato___Late_blight` (`7` + `3` = `10` images) and `Tomato___Late_blight → Potato___Late_blight` (`3` images — same oomycete pathogen *Phytophthora infestans* across Solanaceae foliage).
  - `Corn___Northern_Leaf_Blight ↔ Corn___Cercospora_Gray_leaf_spot` (`5` + `4` = `9` images — overlapping necrotic leaf streaking).
  - Mild/early lesions confused with healthy leaves (`Pepper___Bacterial_spot → healthy`: `4`; `Apple___Apple_scab → healthy`: `3`).

---

## 6. Documented Scientific & Deployment Limitations
1. **Laboratory Background Domain Gap:** PlantVillage leaves are isolated against clean neutral grey/black laboratory backgrounds; sunlit field canopy photos with soil/sky/shadows degrade confidence. Farmers are guided via UI framing tips and uncertainty notices.
2. **Symptom vs. Etiology Ambiguity:** Visual foliar spots alone cannot distinguish nutrient toxicity/deficiency, herbicide scorch, or abiotic drought stress from pathogen infection; KVK agronomist confirmation is advised.
3. **No Fabricated Chemical Dosages:** IPM guidance inside [disease_features.py](../ml/preprocessing/disease_features.py) gives sanitary/cultural practices and qualitative class guidance only — never `kg/ha` or `ml/L` pesticide doses.
4. **GenAI Non-Override Coupling:** When `chat_service.py` injects recent disease scans into Gemini, uncertain predictions carry an explicit `UNCERTAIN` directive forbidding the LLM from overriding the abstention flag or inventing a confirmed diagnosis.
