# TerraQora AI — Phase 5B Recommendation ML Report (Crop & Fertilizer)

This document summarizes the dataset audits, experimental controls, stratified validation benchmarks, error analysis, agronomic safety guardrails, and production limitations for both Phase 5B recommendation modules:
1. **Part A — Crop Recommendation (22-Class Soil & Climate Suitability Classifier)**
2. **Part B — Fertilizer Recommendation (7-Class Grade Classifier + Conservative ICAR Rules)**

---

## Part A: Crop Recommendation (`Crop_recommendation.csv`)

### 1. Dataset Audit & Quality Summary
- **Source File (Preserved Read-Only):** [Crop_recommendation.csv](../ml/datasets/raw/Crop_recommendation.csv) (`SHA-256: 54a5a6e5408668e668667efc50de2fc867c1b875e0431b4f54dd331b0a109a4e`)
- **Audit Script & Output:** [audit_crop_recommendation.py](../ml/audit_crop_recommendation.py) → [crop_rec_audit.json](../ml/evaluation/crop_rec_audit.json)
- **Dimensions & Class Balance:** `2,200` rows × `8` columns (`N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`, `label`); `22` perfectly balanced crop classes with `100` samples each.
- **Data Integrity:** `0` missing values, `0` exact duplicate rows, `0` feature-only duplicate vectors, `0` conflicting labels, `0` whitespace anomalies in labels, and `0` physical domain violations (`humidity ∈ [14.26, 99.98]%`, `ph ∈ [3.50, 9.94]`, `N, P, K, rainfall >= 0`).
- **Feature Scope Finding:** UI inputs `Season` and `Region / State` do **not** exist in `Crop_recommendation.csv`. Inference computes suitability probabilities strictly from the `7` physical soil and climate inputs (`N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`) and records `season`/`region` purely as agronomic plot context.

### 2. Stratified Split & 7-Model Benchmark Comparison
To prevent validation/preprocessing leakage, `Crop_recommendation.csv` was partitioned **before** fitting any scaler, transformer, or training quartile benchmark ([train_crop_recommendation.py](../ml/training/train_crop_recommendation.py)):
- **Train Split (60%):** `1,320` rows (`60` samples/crop)
- **Validation Split (20%):** `440` rows (`20` samples/crop)
- **5-Fold Stratified CV (Dev = Train+Val):** `1,760` rows
- **Held-Out Test Split (20%):** `440` rows (`20` samples/crop — evaluated once)

| Model Key | Algorithm | Train Acc | Val Acc | 5-Fold CV Acc (Dev) | CV5 Log Loss | Train−Val Gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `dummy_majority` | DummyClassifier (Baseline) | `0.0455` | `0.0455` | `0.0455 ± 0.0000` | `34.4053` | `0.0000` |
| `decision_tree_reg` | Decision Tree (`max_depth=10`, `min_samples_leaf=3`) | `0.9841` | `0.9659` | `0.9653 ± 0.0118` | `0.5179` | `0.0182` |
| `logistic_regression_scaled` | Logistic Regression (`StandardScaler` + Ratios) | `0.9826` | `0.9727` | `0.9744 ± 0.0060` | `0.1293` | `0.0099` |
| `xgboost_classifier` | XGBoost Multiclass (Regularized) | `1.0000` | `0.9909` | `0.9875 ± 0.0043` | `0.0533` | `0.0091` |
| `random_forest_engineered` | Random Forest (`Raw + NPK/Moisture Ratios`) | `1.0000` | `0.9864` | `0.9892 ± 0.0049` | `0.0767` | `0.0136` |
| `random_forest_raw` | Random Forest (`7 Raw Features`) | `1.0000` | `0.9909` | `0.9926 ± 0.0061` | `0.0735` | `0.0091` |
| **`gaussian_nb_raw` (Selected)** | **Gaussian Naive Bayes (`7 Raw Features`)** | **`0.9970`** | **`0.9909`** | **`0.9949 ± 0.0042`** | **`0.0158`** | **`0.0061`** |

### 3. Held-Out Test Evaluation (`440` Rows) & Error Analysis
- **Held-Out Accuracy:** `0.9955` (1,000-bootstrap 95% CI: `[0.9886, 1.0000]`)
- **Held-Out Macro Precision / Recall / F1:** `0.9959` / `0.9955` / `0.9954` (F1 95% CI: `[0.9882, 1.0000]`)
- **Top-3 Accuracy:** `1.0000` (`440 / 440` ground-truth crops ranked inside Top-3)
- **Log Loss:** `0.0156` (`Dev − Test` accuracy gap: `-0.0006`, zero overfitting)
- **Serialized Artifact:** `ml/saved_models/crop_recommendation_model.joblib` (`5,693 bytes` / `5.6 KB`, `phase5b-crop-v1.0.0`), storing training-fold per-crop quartile bands inside [`CropRecommendationModel`](../ml/preprocessing/crop_rec_model.py) for human-readable `fit_reason` explanations.
- **Misclassification Inspection (`2 / 440` errors):** Only `2` `rice` samples were misclassified as `jute` (with `rice` ranked #2 in both cases):
  1. `(N=83, P=60, K=36, 25.6°C, 80.15% RH, pH 6.9, rainfall=200.83 mm)` → predicted `jute (0.7400)`, actual `rice (0.2600)`
  2. `(N=67, P=43, K=39, 26.04°C, 84.97% RH, pH 6.0, rainfall=186.75 mm)` → predicted `jute (0.8354)`, actual `rice (0.1646)`
- **Limitations:** Synthetic benchmark clustering produces near-Gaussian envelopes across `22` crops (`jute` mean rainfall `174.79 mm` overlaps lower-tail `rice` samples around `185–201 mm`); lacks regional water-table constraints, soil texture, and farm economic factors.

---

## Part B: Fertilizer Recommendation (`Fertilizer_Prediction.csv` + ICAR Rules)

### 1. Public Dataset Selection & Audit
Four candidate public fertilizer datasets were audited before selecting training data:
1. **`gdabhishek` / `FarmApp` `Fertilizer Prediction.csv` — SELECTED** ([Fertilizer_Prediction.csv](../ml/datasets/raw/Fertilizer_Prediction.csv), `SHA-256: dfd69cee9d3d7a4403aab5647d5749050ae406ad42dc9ce3f508aa3442955e41`): `99` rows × `9` columns, `0` missing values, `0` duplicates, clean separation across `7` commercial fertilizer formulations (`Urea: 22`, `DAP: 18`, `28-28: 17`, `14-35-14: 14`, `20-20: 14`, `17-17-17: 7`, `10-26-26: 7`). Raw CSV typos (`'Temparature'`, `'Humidity '`, `'Phosphorous'`) are normalized non-destructively in [fertilizer_features.py](../ml/preprocessing/fertilizer_features.py).
2. **`irakozekelly/fertilizer-prediction` (`100,000` rows, Kaggle) — REJECTED:** Empirical audit showed mutual information `≤ 0.014` across every feature and `5`-fold Random Forest CV accuracy of `14.43%` (worse than `14.71%` majority guess) — pure uniform random label synthesis.
3. **`Tejasgolhar/Fertilizer_Recommendation_System f2.csv` (`552` rows) — REJECTED:** `414 / 552` (`75.0%`) exact duplicate rows causing severe split leakage, singleton target class (`1` sample), inconsistent labels, and no license metadata.
4. **AgriNet Mendeley Dataset (`doi:10.17632/c7tr9j78td.1`, `257` rows, CC BY 4.0) — REJECTED FOR TRAINING:** Authentic KVK IVRI Bareilly alluvial soil lab chemistry (`pH`, `EC`, `OC`), but the distributed CSV omits fertilizer target label columns.

### 2. Crucial Domain Finding & Feature Ablation
Inspection of [fertilizer_audit.json](../ml/evaluation/fertilizer_audit.json) revealed two essential domain truths:
- **Mutual Information:** `Phosphorus (1.5882)`, `Nitrogen (1.2209)`, and `Potassium (0.8275)` explain `100%` of grade separation, whereas `Soil Type (0.0067)`, `Crop Type (0.0000)`, `Temperature (0.0783)`, `Humidity (0.0285)`, and `Moisture (0.0484)` carry effectively zero predictive signal.
- **Formulation Signature Semantics:** In `Fertilizer_Prediction.csv`, class rows encode **target nutrient formulation profiles** (e.g., `Urea`: `N=35–42, P=0, K=0`; `DAP`: `N=10–15, P=35–42, K=0`; `10-26-26`: `N=4–13, P=15–21, K=16–19`), **not** raw excess soil test readings. Directly feeding a farmer's soil reading (`N=85`, `P=50`) into a raw unguarded model would falsely output `Urea`.
- **Missing Clinical Variables:** Soil `pH` (`pH` column absent), organic carbon, crop trial yield response, straight MOP (`0-0-60`), and exact `kg/ha` dosage rates do **not** exist anywhere in the dataset.

### 3. Stratified Benchmark (`60` Train / `19` Val / `20` Test + `5`-Fold CV on `79` Dev)
Feature ablation in [train_fertilizer.py](../ml/training/train_fertilizer.py) compared `all 8 features`, `5 UI-collectable features`, and parsimonious `3 NPK grade features`:

| Model Key | Feature Scope | Train Acc | Val Acc | 5-Fold CV Acc | CV5 Macro-F1 | CV5 Log Loss |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `dummy_majority` | `npk_only_3` | `0.2167` | `0.2105` | `0.2158` | `0.0505` | `28.2642` |
| `decision_tree_all8` | `all_8_features` | `1.0000` | `1.0000` | `0.9367` | `0.8657` | `2.2828` |
| `logistic_regression_all8` | `all_8_features` | `1.0000` | `0.9474` | `0.9367` | `0.8714` | `0.3733` |
| `random_forest_all8` | `all_8_features` | `1.0000` | `0.9474` | `0.9492` | `0.9257` | `0.6515` |
| `random_forest_collectable5` | `collectable_5_features` | `1.0000` | `1.0000` | `0.9742` | `0.9467` | `0.4974` |
| `xgboost_npk3` | `npk_only_3` | `1.0000` | `0.9474` | `0.9742` | `0.9276` | `0.1822` |
| `random_forest_npk3` | `npk_only_3` | `1.0000` | `1.0000` | `0.9875` | `0.9810` | `0.1072` |
| **`logistic_regression_npk3` (Selected)** | **`npk_only_3`** | **`1.0000`** | **`1.0000`** | **`1.0000 ± 0.0000`** | **`1.0000`** | **`0.1417`** |

- **Held-Out Test (`20` rows):** Accuracy `1.0000`, Macro Precision/Recall/F1 `1.0000`, Log Loss `0.1389`.
- **Serialized Artifact:** `ml/saved_models/fertilizer_model.joblib` (`1,665 bytes` / `1.6 KB`, `phase5b-fert-v1.0.0`).

### 4. Separation of Dataset ML vs. Agronomic Safety Rules
In [fertilizer_service.py](../backend/app/services/fertilizer_service.py), every fertilizer assessment cleanly distinguishes empirical ML predictions from qualitative ICAR rules:
1. **ICAR Soil Sufficiency Screening (`assess_soil_balance`):** Evaluates soil test readings against baseline bands (`N: 40–95`, `P: 30–65`, `K: 30–75`) and soil `pH` (`< 5.8` acidic / `> 7.8` alkaline qualitative KVK guidance).
2. **Sufficiency Guardrail Override (`agronomic_sufficiency_guardrail`):** When `has_any_deficit == False` (all N, P, K optimal/high), the service blocks chemical grade escalation, sets `ml_predicted_grade = null`, and advises organic maintenance only.
3. **Deficit Signature Projection → ML Grade (`ml_grade_with_agronomic_guardrails`):** When one or more nutrients are low, proportional shortfall weights are projected cleanly onto the trained classifier's `(N, P, K)` demand space — calibrated across pure-N (`Urea`), pure-P (`DAP`), moderate/severe N+P (`20-20` / `28-28`), balanced NPK (`17-17-17`), K+P dominant (`10-26-26`), and P-heavy N+K (`14-35-14`). Pure Potassium-only deficits explicitly disclose that straight Potash (`MOP 0-0-60`) is absent from the 7 dataset labels.
4. **Domain Harmonization Disclosure & Zero Fabricated Dosages:** Crops/soils outside the `11` dataset crop groups and `5` soil textures trigger transparent disclosures inside `dataset_coverage_note`, and **no numeric application rates (`kg/ha`, `g/plant`, or lime tonnage) are ever fabricated**.
