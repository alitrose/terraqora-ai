# TerraQora AI — Dataset Inventory, Provenance & Validation Rules

All original datasets remain preserved untouched at their source locations. Copies inside `ml/datasets/raw/` are verified by SHA-256 checksums.

## 1. Existing Preserved Datasets

### `crop_yield.csv` (Modules 1 & 7)
- **Original Path:** `C:\Users\alitr\OneDrive\Desktop\2026IN\crop_yield.csv`
- **Local Copy:** `ml/datasets/raw/crop_yield.csv`
- **SHA-256:** `ab9bc356b1f8107d490376cec24450a0e2906322ad25788ab22fb32537ab1f8f`
- **Attribution & License:** Agricultural Crop Yield in Indian States Dataset (Kaggle / Public Indian Ministry of Agriculture & Farmers Welfare historical records, 1997–2020; CC0 / Public Domain educational & research dataset).
- **Shape:** `19,689` rows × `10` columns (`Crop`, `Crop_Year`, `Season`, `State`, `Area`, `Production`, `Annual_Rainfall`, `Fertilizer`, `Pesticide`, `Yield`).
- **Audit Findings (Handled in Phase 5 Preprocessing):**
  - Trailing whitespace in `Season` (all `19,689` rows) and `Crop` (`172` rows of `'Coconut '`).
  - Target leakage: `Production / Area` correlates `r = 0.9965` with `Yield`. `Production` **must never be used as an input feature** for yield prediction.
  - Unit divergence: `Coconut` is measured in nuts/hectare (median `8,466.3`, max `21,105.0`), whereas the other 54 crops are in tonnes/hectare (median `1.03`).
  - Year `2020` has only `37` samples vs `410–1,079` in `1997–2019`; `112` rows have `Yield == 0` / `Production == 0`.

### `Crop_recommendation.csv` (Module 6)
- **Original Path:** `C:\Users\alitr\Downloads\Crop_recommendation.csv`
- **Local Copy:** `ml/datasets/raw/Crop_recommendation.csv`
- **SHA-256:** `54a5a6e5408668e668667efc50de2fc867c1b875e0431b4f54dd331b0a109a4e`
- **Attribution & License:** Crop Recommendation Dataset (Atharva Ingle, Kaggle — compiled from Indian soil/climate benchmark ranges; CC0: Public Domain).
- **Shape:** `2,200` rows × `8` columns (`N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`, `label`).
- **Validation Status:** `22` balanced crops (`100` rows each), `0` missing values, `0` duplicates.

---

## 2. Acquired & Planned Public Datasets (Phases 5b & 7)

### `Fertilizer_Prediction.csv` (Module 4 — **Acquired & Audited in Phase 5b**)
- **Source Provenance:** Public Fertilizer Prediction dataset (`gdabhishek/fertilizer-prediction` / `FarmApp` mirror of standard Kaggle agricultural formulation dataset; public research/educational dataset).
- **Local Copy:** `ml/datasets/raw/Fertilizer_Prediction.csv` (`3,829 bytes`)
- **SHA-256:** `dfd69cee9d3d7a4403aab5647d5749050ae406ad42dc9ce3f508aa3442955e41`
- **Shape & Targets:** `99` rows × `9` columns (`Temparature`, `Humidity `, `Moisture`, `Soil Type`, `Crop Type`, `Nitrogen`, `Potassium`, `Phosphorous`, `Fertilizer Name`), `0` missing values, `0` duplicates, `7` commercial grades (`Urea`, `DAP`, `28-28`, `14-35-14`, `20-20`, `17-17-17`, `10-26-26`).
- **Audit Findings & Guardrails:**
  - Raw column typos (`Temparature`, trailing space `Humidity `, `Phosphorous`) normalized cleanly inside [fertilizer_features.py](../preprocessing/fertilizer_features.py).
  - Does **not** contain soil `pH`, straight MOP (`0-0-60`), or numeric application dosages (`kg/ha`); production inference strictly combines 3-NPK grade classification with ICAR soil sufficiency & pH guardrails and refuses to invent chemical application weights.
- **Candidate Datasets Audited & Rejected:** `irakozekelly/fertilizer-prediction` (`100k` rows — uniform random noise, MI ≤ `0.014`, 5-fold CV `14.43%`), `Tejasgolhar f2.csv` (`75%` duplicated rows / singleton class), and `AgriNet` (`doi:10.17632/c7tr9j78td.1` — genuine soil lab chemistry without fertilizer labels). See [RECOMMENDATION_ML.md](../../docs/RECOMMENDATION_ML.md).

### PlantVillage Leaf Disease Dataset (Module 2 — **Acquired & Audited in Phase 7**)
- **Source Provenance:** Hughes & Salathé (2015), *arXiv:1511.08060*, distributed via verified public-domain HuggingFace dataset `BrandonFors/Plant-Diseases-PlantVillage-Dataset` (`3` Parquet shards totaling `812.61 MB`).
- **License:** `CC0 1.0` (Public Domain Dedication — zero attribution/royalty restriction).
- **Local Uncommitted Storage:** `ml/datasets/plantvillage/*.parquet` and leak-free split manifest `ml/datasets/processed/disease_splits.parquet` (explicitly gitignored).
- **Audit Script & Report:** [audit_plant_disease.py](../audit_plant_disease.py) → [disease_audit.json](../evaluation/disease_audit.json)
- **Integrity & Class Balance Findings:**
  - `54,305` valid RGB `JPEG` images (`256×256` px), `0` corrupt/unreadable files, across `38` disease/healthy classes (`14` crop species).
  - Severe raw class imbalance (`36.23×`): `Potato___healthy` (`152` images) vs `Orange___Haunglongbing_(Citrus_greening)` (`5,507` images) and `Soybean___healthy` (`5,090` images).
- **Duplicate & Cross-Split Leakage Audit:**
  - Identified `21` exact SHA-256 duplicates, `31` perceptual 64-bit dHash near-duplicates, `1` cross-class dHash collision, and `7` SHA-256 / `8` dHash images overlapping between upstream `train` and `test` shards.
  - **Mitigation Applied:** Excluded cross-class collision groups, collapsed near-duplicate dHash clusters, and rebuilt strictly isolated grouped-stratified splits totaling `7,367` deduplicated images (`train=4,539`, `val=1,133`, `test=1,695`; capped at `120/30/45` per class, `99/23/30` for `Potato___healthy`) with verified `0` SHA-256 and `0` dHash overlap across splits.
- **Documented Crop & Domain Exclusions:**
  - Covers `14` temperate/horticultural species only (`Apple`, `Blueberry`, `Cherry`, `Corn/Maize`, `Grape`, `Orange/Citrus`, `Peach`, `Bell Pepper`, `Potato`, `Raspberry`, `Soybean`, `Squash`, `Strawberry`, `Tomato`).
  - Does **not** cover major staple field crops such as **Rice, Wheat, Cotton, Sugarcane, Coconut, Banana, Groundnut, Chickpea, Mustard, Onion, or Mango** — the API/UI strictly abstains on these crops.
  - See [DISEASE_DETECTION_ML.md](../../docs/DISEASE_DETECTION_ML.md) for benchmark comparisons, calibration (ECE/Brier), and abstention threshold evaluation.
