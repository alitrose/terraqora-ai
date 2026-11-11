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

## 2. Public Datasets Planned for Acquisition (Phases 5 & 7)

### Fertilizer Recommendation Dataset (Module 4 — Phase 5)
- **Planned Source:** Standard public Agricultural Fertilizer Prediction dataset (`Temperature, Humidity, Moisture, Soil Type, Crop Type, Nitrogen, Potassium, Phosphorous, Fertilizer Name`) paired with ICAR soil-test NPK threshold ranges (`N, P, K, pH, Soil Type, Crop Type`).
- **Validation Gate:** Verify zero missing labels, valid pH/NPK bounds, deduplication, and stratified cross-validation before model serialization. Never fabricate chemical dosages.

### PlantVillage Leaf Disease Dataset (Module 2 — Phase 7)
- **Planned Source:** PlantVillage Dataset (Hughes & Salathé, 2015 — CC0 / Public Domain via TensorFlow Datasets `plant_village` or verified Kaggle/GitHub mirror).
- **Validation Gate:** Verify class counts, image readability via OpenCV, strict train/validation/test split before augmentation, and record exact confusion matrix + calibration thresholds (`confidence < 0.65` → Uncertain warning).
