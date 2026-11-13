# TerraQora AI — Known Limitations & Scientific Disclosures

**Document Status:** Complete & Verified  
**Principle:** Transparent agronomic disclosures, scientific honesty, and ethical AI deployment.

---

## 1. Machine Learning & Predictive Limitations

### A. Crop Yield Prediction
- **Dataset Scope:** Models were trained on historical Indian agricultural statistics (19,689 records, 1997–2020) spanning 55 major crops across 30 states.
- **Microclimate Unpredictability:** Tabular macro statistics cannot fully predict sudden extreme weather anomalies (unseasonal hail, cloudbursts, severe flash droughts) or localized pest outbreaks occurring within a single week.
- **Zero-Leakage Policy:** While excluding post-harvest `Production` ensures zero target leakage, tabular regressions reflect regional average productivity rather than hyper-localized farm parcel variance.

### B. Crop Suitability Recommendation
- **Feature Envelope:** Evaluates 22 target crops across 7 physical parameters (N, P, K, temperature, humidity, soil pH, rainfall).
- **Out-of-Scope Species:** Minor millets, specialized floriculture, medicinal herbs, and perennial forest species outside the 22-class taxonomy are not modeled.

### C. Fertilizer Formulation & Soil Nutrient Planning
- **Formulation Scope:** Recommends among 7 primary commercial fertilizer formulations (Urea, DAP, 14-35-14, 28-28-0, 17-17-17, 20-20-0, 10-26-26).
- **Zero Fabricated Dosages Policy:** The platform strictly abstains from inventing arbitrary chemical milligram quantities. All outputs emphasize validation against physical, certified Soil Health Cards (SHC) issued by state agricultural departments.

### D. Plant Pathology Computer Vision
- **PlantVillage Bias:** The underlying dataset predominantly features individual leaves photographed against uniform laboratory or clean backgrounds. Performance on messy field photographs with overlapping canopy foliage, heavy shadows, or soil background may be degraded.
- **Abstention Threshold:** To prevent hazardous misdiagnoses, the model automatically abstains when confidence falls below 0.60 or when the observed crop species is not among the 14 supported PlantVillage families.

---

## 2. Telemetry & Meteorological Limitations

### A. Open-Meteo Weather & FAO-56 Evapotranspiration
- **Sensorless Microclimate:** Unless an in-field soil probe or IoT telemetry station is physically linked, soil moisture and daily water depletion are estimated purely from meteorological Penman-Monteith formulas and crop coefficients ($K_c$).
- **Rainfall Variability:** Convective summer thunderstorms may exhibit intense hyper-local variation that differs from the 11 km grid resolution of numerical weather prediction models.

---

## 3. Generative AI Advisory Limitations

### A. Grounded Agricultural RAG
- **Advisory Role Only:** The GenAI Assistant is powered by Google Gemini 2.5 Flash and grounded in curated ICAR, TNAU, and FAO agronomy manuals. However, Generative AI models are probabilistic and must never be treated as certified crop insurance or chemical safety directives.
- **Pesticide & Fungicide Safety:** Farmers must always consult licensed local agronomists and adhere to manufacturer label safety directions (PPE, pre-harvest intervals, environmental toxicity) before applying any chemical treatments.

---

## 4. Hosting & Infrastructure Constraints (Free-Tier Targets)

### A. Render Web Service
- **Cold Starts:** Free-tier services spin down after 15 minutes of inactivity. Resuming can take 45–60 seconds on initial cold requests.
- **512 MB RAM Ceiling:** Memory usage is capped at 512 MB. While the application runs at <140 MB RSS, running multiple concurrent heavy PyTorch image inferences could cause resource pressure under sustained burst traffic.
- **Ephemeral Filesystem:** Uploaded leaf images and generated report PDFs are not permanently preserved across container rebuilds unless backed by persistent object storage (S3/R2).
