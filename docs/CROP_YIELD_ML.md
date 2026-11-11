# TerraQora AI — Crop Yield Prediction ML Pipeline (Phase 5)

**Module Status:** Live (Phase 5 Trained & Integrated)  
**Selected Model:** `random_forest_segmented` — **Segmented Random Forest Regressor (Non-Coconut `tonnes/ha` + Coconut `nuts/ha`, Scale-Invariant Features)**  
**Artifact Path:** [`ml/saved_models/crop_yield_model.joblib`](../ml/saved_models/crop_yield_model.joblib) (`7.66 MB`, `< 15 MB` budget; gitignored binary reproducible deterministically via CLI)  
**Audit & Benchmark Artifacts:** [`ml/evaluation/crop_yield_audit.json`](../ml/evaluation/crop_yield_audit.json) and [`ml/evaluation/crop_yield_metrics.json`](../ml/evaluation/crop_yield_metrics.json)

---

## 1. Dataset Audit & Data Quality (`crop_yield.csv`)

Audited via read-only script [`ml/audit_crop_yield.py`](../ml/audit_crop_yield.py) on [`ml/datasets/raw/crop_yield.csv`](../ml/datasets/raw/crop_yield.csv):

- **Checksum (Preserved Untouched):** `ab9bc356b1f8107d490376cec24450a0e2906322ad25788ab22fb32537ab1f8f`
- **Source Provenance:** Indian Ministry of Agriculture & Farmers Welfare historical state-season-year crop yield statistics (`1997–2020`, CC0 / Public Domain educational & research dataset).
- **Dimensions:** `19,689` rows × `10` columns (`Crop`, `Crop_Year`, `Season`, `State`, `Area`, `Production`, `Annual_Rainfall`, `Fertilizer`, `Pesticide`, `Yield`).
- **Missing Values:** `0` missing (`NaN`/null) values across all 10 columns.
- **Duplicates:** `0` exact duplicates; `0` duplicates across composite key `(Crop, Crop_Year, Season, State)` after trimming whitespace.
- **Whitespace Anomalies Found & Cleaned:**
  - All `19,689` rows contained trailing whitespace in `Season` (e.g., `'Kharif     '`).
  - All `172` `'Coconut '` rows contained a trailing space.
  - `'Other  Rabi pulses'` retains double internal space in the raw CSV; backend canonicalization accepts both `'Other  Rabi pulses'` and single-spaced `'Other Rabi pulses'`.
- **Cardinality (Cleaned):** `55` Crops, `30` States/UTs, `6` Seasons (`Autumn`, `Kharif`, `Rabi`, `Summer`, `Whole Year`, `Winter`), `24` years (`1997–2020`; note `2020` contains only `37` rows, all in `Uttarakhand`).
- **Zero / Outlier Checks:**
  - `0` rows have `Area <= 0`, `Annual_Rainfall <= 0`, `Yield < 0`, `Fertilizer == 0`, or `Pesticide == 0`.
  - `112` rows report `Yield == 0.0` (`108` with `Production == 0`, `4` with positive tiny production rounded to `0.0` in source records).
  - Extreme horticultural / smallholder reporting spikes exist in raw statistics (e.g., `Maize 1997 Autumn Maharashtra: Yield=989.87`, `Onion 2018 Kharif Andhra Pradesh: Yield=247.57`, `Banana 2018 Whole Year Andhra Pradesh: Yield=126.39`).

---

## 2. Target Leakage & Covariate-Shift Investigation

### A. Post-Harvest Target Leakage (`Production` Exclusion)
An integrity audit quantified the relationship between `Production`, `Area`, and `Yield`:

- **Empirical Leakage Proof:**
  - Pearson correlation between `Production / Area` and `Yield` across all `19,689` rows is **`r = 0.9965`**.
  - Median absolute difference `|Yield - Production / Area|` = **`0.0559`**.
  - `4,038` rows match `Production / Area` within `<= 1%` (the dataset's raw `Yield` column is directly derived from district-aggregated `Production / Area`).
- **Engineering Enforcement:**
  1. `Production` is dropped immediately prior to feature transformation and rejected inside [`clean_crop_yield_dataframe`](../ml/preprocessing/crop_yield_features.py) if passed in any DataFrame (`ValueError: Target leakage error`).
  2. FastAPI schema [`CropYieldRequest`](../backend/app/schemas/predictions.py) uses `ConfigDict(extra="forbid")` so any API request sending `production`, `Production`, or `yield` fails validation cleanly with HTTP **`422 Unprocessable Entity`**.

### B. Extensive Macro-Area Covariate Shift Discovery & Resolution
In state-level historical census rows, `Area` (`10^4–10^6 ha`), total `Fertilizer`, and total `Pesticide` are macro aggregates (`Corr(Area, Fertilizer) = 0.9733`, `Corr(Area, Pesticide) = 0.9735`, median nutrient dose `144.49 kg/ha`). Notice why raw extensive totals cause severe real-world failure on individual farmer plots (`1–10 ha`):
- Across `Coconut` (`172` rows), the 7 rare low-area entries (`15–100 ha`) occur only in non-coastal states (`Mizoram = 2.60`, `Chhattisgarh = 0.00`), while coastal producers (`Kerala`, `Tamil Nadu`, `Karnataka`) have `20,000–925,000 ha`. Including raw `Area`, `Fertilizer`, or `Pesticide` totals caused tree models to mispredict small `3.5 ha` Kerala Coconut plots as `~5 nuts/ha` instead of `~6,731 nuts/ha` and small `1 ha` UP Sugarcane plots as `11.7 t/ha` instead of `64.9 t/ha`.
- Removing extensive macro columns from model inputs and training strictly on **scale-invariant agronomic intensities** (`fertilizer_per_ha = Fertilizer / Area`, `pesticide_per_ha = Pesticide / Area`, and log/rainfall interactions):
  1. Guaranteed exact smallholder-to-macro scale invariance (`1 ha`, `5 ha`, and `50,000 ha` yield identical per-hectare estimates at equal input intensity).
  2. **Simultaneously improved** held-out chronological Test generalization across Non-Coconut crops (`RMSE 7.36 -> 6.47 t/ha`, `R² 0.689 -> 0.760`).

---

## 3. Unit Divergence & Engineered Features

### A. Target Unit Segmentation (`SegmentedYieldPredictor`)
- **`Coconut` (`172` rows):** Measured in **nuts/hectare** (`min 0.0`, `median 8,466.3`, `mean 8,652.0`, `p95 13,767.2`, `max 21,105.0`, `std 3,772.5`).
- **Remaining `54` Crops (`19,517` rows):** Measured in **tonnes/hectare** (`min 0.0`, `median 1.02`, `mean 4.41`, `p95 18.36`, `max 989.87`, `std 14.59`).

As confirmed in ablation (`ridge_unified` Test `R² = -12.6759`; `xgboost_unified` Test `R² = 0.2849`), training a single unsegmented model corrupts Non-Coconut predictions due to Coconut's ~`8,652` scale dominating squared-error splits. [`SegmentedYieldPredictor`](../ml/preprocessing/crop_yield_model.py) isolates two estimators cleanly by unit (`Coconut` vs `Non-Coconut`).

### B. Strictly Scale-Invariant Model Features
[`YieldFeatureEngineer`](../ml/preprocessing/crop_yield_features.py) computes these pre-harvest features:

| Feature Name | Formula / Definition | Purpose |
| --- | --- | --- |
| `Crop`, `Season`, `State` | Trimmed & canonicalized categoricals (`OneHotEncoder(handle_unknown="ignore")`) | Regional agro-climatic & phenological baselines |
| `Crop_Year` | Integer calendar year | Historical temporal context |
| `Annual_Rainfall`, `log_rainfall` | `Annual_Rainfall`, `log1p(Annual_Rainfall)` | Monsoon / precipitation exposure |
| `fertilizer_per_ha`, `pesticide_per_ha` | `Fertilizer / max(Area, 1e-6)`, `Pesticide / max(Area, 1e-6)` | Scale-invariant input intensity (`kg/ha`) |
| `log_fertilizer_per_ha`, `log_pesticide_per_ha` | `log1p(fertilizer_per_ha)`, `log1p(pesticide_per_ha)` | Diminishing agronomic returns transform |
| `rain_x_fert_per_ha` | `log_rainfall * log_fertilizer_per_ha` | Rainfall × nutrient synergy |

`Area` (`area_hectares > 0`) is strictly validated and used to compute per-hectare nutrient/pesticide intensities as well as `estimated_total_production = predicted_yield * area_hectares`.

---

## 4. Chronological Train / Validation / Test Split

To eliminate future data leakage and match real-world forecasting deployment, [`ml/training/train_crop_yield.py`](../ml/training/train_crop_yield.py) enforces a strict **chronological time split**:

| Split | Years | Total Rows | Non-Coconut Rows | Coconut Rows | Notes |
| --- | --- | --- | --- | --- | --- |
| **Train** | `1997–2015` | `15,404` | `15,265` | `139` | Historical baseline training |
| **Validation** | `2016–2017` | `2,106` | `2,090` | `16` | Model selection on Non-Coconut RMSE |
| **Held-Out Test** | `2018–2020` | `2,179` | `2,162` | `17` | Final unbiased out-of-time evaluation |

*Cold-Start Crop Note:* `'Other Summer Pulses'` (`10` total rows) only begins appearing in `2016`, serving as a natural unseen-crop test in Validation/Test (`OneHotEncoder(handle_unknown="ignore")`). After locking hyperparameters and recording all chronological benchmarks, the production artifact (`crop_yield_model.joblib`) is refitted with identical hyperparameters across all `19,689` cleaned rows (`1997–2020`) so all 55 crops work in production. **All reported accuracy metrics below remain strictly locked from the `1997–2015` train -> `2018–2020` out-of-time test evaluation.**

---

## 5. Model Comparison & Empirical Benchmark Results

All 7 candidate pipelines evaluated identically on Validation (`2016–2017`) and Held-Out Test (`2018–2020`):

| Model Candidate | Val Non-Coco MAE (`t/ha`) | Val Non-Coco RMSE (`t/ha`) | Val Non-Coco `R²` | Test Non-Coco MAE (`t/ha`) | Test Non-Coco RMSE (`t/ha`) | Test Non-Coco `R²` | Test Coconut `R²` | Artifact Size | Latency (`ms/row`) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dummy_median_segmented` (baseline) | `3.9470` | `14.6281` | `-0.0651` | `4.0318` | `13.7050` | `-0.0787` | `-0.0421` | `0.002 MB` | `6.74` |
| `ridge_unified` (unsegmented ablation) | `27.8321` | `47.6770` | `-10.3139` | `29.7845` | `48.7977` | `-12.6759` | `-0.0152` | `0.003 MB` | `7.03` |
| `ridge_segmented` | `2.9747` | `10.2739` | `0.4746` | `2.9943` | `8.5135` | `0.5837` | `0.5761` | `0.004 MB` | `7.17` |
| **`random_forest_segmented` (Selected)** | **`1.2974`** | **`8.6013`** | **`0.6318`** | **`1.4076`** | **`6.4679`** | **`0.7597`** | **`0.7065`** | **`6.416 MB`** | **`80.33`** |
| `xgboost_unified` (unsegmented ablation) | `3.9305` | `26.3516` | `-2.4563` | `2.2700` | `11.1582` | `0.2849` | `0.7756` | `0.415 MB` | `13.18` |
| `xgboost_segmented_native` | `1.4469` | `8.6602` | `0.6267` | `1.5540` | `6.6129` | `0.7488` | `0.6885` | `0.433 MB` | `13.23` |
| `xgboost_segmented_log1p` | `1.3160` | `8.7784` | `0.6164` | `1.5097` | `6.9247` | `0.7246` | `0.5467` | `0.413 MB` | `20.23` |

*(Full refit `crop_yield_model.joblib` size on disk = `7.66 MB`.)*

> [!NOTE]
> **Combined-Unit Metric Transparency:** Combined overall Test `R²` across mixed units (`tonnes/ha` + `nuts/ha`, `n = 2,179`) is `0.9523` (`RMSE = 185.4233`), even for the naive `dummy_median_segmented` baseline (`R² = 0.8305`), solely because bimodal `Coconut` (`~8,652`) vs `Non-Coconut` (`~4.4`) dominates cross-group variance. TerraQora AI **always evaluates and reports unit-segmented metrics** (`Non-Coconut R² = 0.7597` and `Coconut R² = 0.7065`) rather than quoting inflated mixed-unit `R²`.

### Held-Out Test 95% Bootstrap Confidence Intervals (`random_forest_segmented`, Non-Coconut `n = 2,162`, 1,000 resamples)
- **MAE:** `1.4076 t/ha` (`95% CI: [1.1882, 1.7156]`)
- **RMSE:** `6.4679 t/ha` (`95% CI: [3.2177, 9.9488]`)
- **R²:** `0.7597` (`95% CI: [0.5584, 0.9268]`)
- **Coconut Segment (`n = 17`):** `MAE = 1,589.87 nuts/ha`, `RMSE = 2,098.00 nuts/ha`, `R² = 0.7065`.

### Why `random_forest_segmented` Won Selection
1. Achieved the **lowest Validation Non-Coconut RMSE (`8.6013 t/ha`), lowest Validation MAE (`1.2974 t/ha`), and highest Held-Out Test Non-Coconut `R²` (`0.7597`) + Test Coconut `R²` (`0.7065`)** across all unit-segmented models.
2. Fits cleanly under the `15 MB` deployment size ceiling (`7.66 MB`) and executes deterministic local **Saabas decision-path attributions** per request (implemented alongside TreeSHAP support in [`compute_feature_drivers`](../ml/preprocessing/crop_yield_model.py)).

---

## 6. Error Analysis & Known Model Limitations

### Slice Performance on Held-Out Test Set (`2018–2020`, `random_forest_segmented`)
- **By Year (`Non-Coconut`):**
  - `2018` (`n=1,055`): `MAE = 1.5977 t/ha`, `RMSE = 8.6992`, `R² = 0.6377`
  - `2019` (`n=1,070`): `MAE = 1.2290 t/ha`, `RMSE = 3.0568`, `R² = 0.9332`
  - `2020` (`n=37`): `MAE = 1.1562 t/ha`, `RMSE = 4.0537`, `R² = 0.9061`
- **By Season (`Non-Coconut`):**
  - `Autumn` (`n=46`): `MAE = 0.5125 t/ha`, `RMSE = 0.9341`, `R² = 0.0738`
  - `Winter` (`n=44`): `MAE = 0.7879 t/ha`, `RMSE = 1.4047`, `R² = 0.9860`
  - `Summer` (`n=163`): `MAE = 0.7944 t/ha`, `RMSE = 1.4038`, `R² = 0.9503`
  - `Rabi` (`n=701`): `MAE = 0.8347 t/ha`, `RMSE = 2.8658`, `R² = 0.6953`
  - `Kharif` (`n=928`): `MAE = 1.2822 t/ha`, `RMSE = 8.2473`, `R² = 0.5927`
  - `Whole Year` (`n=280`): `MAE = 3.8591 t/ha`, `RMSE = 8.6847`, `R² = 0.8640`
- **Highest-MAE Crops:** `Banana` (`MAE 12.12 t/ha`, mean `38.93`), `Onion` (`MAE 8.97 t/ha`, driven by extreme `Andhra Pradesh 2018 Kharif Onion = 247.57 t/ha` reporting spike with residual `233.70 t/ha`), `Sugarcane` (`MAE 8.68 t/ha`, mean `59.84`).
- **Zero-Yield Test Rows (`n=15`):** `MAE = 1.6229 t/ha` (model naturally predicts positive historical regional baselines on unrecorded crop-failure rows).
- **Cold-Start Unseen Crop (`Other Summer Pulses`, `n=5`):** `MAE = 0.2580 t/ha` via `OneHotEncoder(handle_unknown="ignore")` seasonal/state priors during evaluation, and directly learned in full refit.

### Documented Limitations (Must Be Disclosed to Users)
1. **Macro State-Annual Granularity:** Inputs represent state-level annual rainfall and state-level aggregate chemical rates rather than plot-level daily weather, irrigation schedule, cultivar genetics, pest outbreaks, or soil NPK/pH chemistry.
2. **Temporal Clamping Beyond 2020:** Tree ensembles cannot extrapolate linear upward yield trends beyond their training year range (`1997–2020`); target years `> 2020` evaluate against the late-2010s temporal baseline.
3. **Small Coconut Sample Size:** Only `172` historical observations exist for Coconut (`17` test rows across coastal states); Coconut variance (`±2,098 nuts/ha` RMSE) reflects palm age and plantation management factors not present in tabular census columns.
4. **Source Reporting Outliers:** Raw historical census data contains occasional extreme reporting spikes (e.g., `247.57 t/ha` Onion, `126.39 t/ha` Banana) that dominate squared-error tails.

---

## 7. Reproducing Training & Calling the Inference Endpoint

### Re-run Audit & Training Locally
```powershell
.\.venv\Scripts\python.exe -m ml.audit_crop_yield
.\.venv\Scripts\python.exe -m ml.training.train_crop_yield
```

### Live FastAPI Endpoints (Phase 5)
- `POST /api/v1/predictions/yield` (Authenticated Bearer JWT, rate-limited `20/minute`):
  - Enforces strict Pydantic validation (`extra="forbid"`, rejects `"production"`/`"Production"`/`"yield"` with `422`), canonicalizes crop/state/season names, computes exact per-row decision-path `feature_drivers[]`, returns `source_mode: "live_api"`, and persists records to SQLAlchemy `crop_predictions`.
  - Returns HTTP `503 Service Unavailable` cleanly (without stack traces) if `crop_yield_model.joblib` is missing or unreadable.
- `GET /api/v1/predictions/yield/history?limit=10` (Authenticated Bearer JWT):
  - Returns the signed-in farmer's persisted predictions ordered newest first.
