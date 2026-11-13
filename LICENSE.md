# TerraQora AI — License & Intellectual Property Terms

**Project:** TerraQora AI  
**Tagline:** Intelligence for Every Acre.  
**Copyright (c) 2026 Ali Trose & TerraQora AI Contributors.**

---

## 1. Software License (MIT License)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 2. Agricultural & Decision Support Disclaimer

> [!CAUTION]
> **TERRAQORA AI IS AN AGRO-DECISION SUPPORT AND EDUCATIONAL SYSTEM. IT DOES NOT CONSTITUTE A CERTIFIED AGRONOMIC, CHEMICAL, OR FINANCIAL GUARANTEE.**

1. **Crop Yield Predictions:** Predictions are statistical estimations derived from historical regional records, seasonal patterns, and environmental features. Real-world yields depend on microclimates, pest pressures, seed germination rates, soil microbiology, and unforeseen catastrophic meteorological occurrences.
2. **Fertilizer & Nutrient Recommendations:** N-P-K nutrient recommendations are calculated based on general soil chemical classifications and target crop demands. Prior to bulk chemical application, farmers must perform certified lab soil testing and adhere to local agricultural extension and environmental regulations.
3. **Plant Pathology & Disease Diagnosis:** Computer vision inferences represent probabilistic classifications trained on standard benchmark imagery (PlantVillage). Field symptoms may exhibit co-infections, physiological nutrient deficiencies, or abiotic disorders that mimic fungal or bacterial pathogens. Chemical fungicide or bactericide sprays must be validated with a local agronomist.
4. **Irrigation & Meteorological Data:** Evapotranspiration calculations follow the FAO-56 Penman-Monteith method with standard crop coefficients. In-field soil moisture sensors, drainage profiles, and root depths should inform critical irrigation scheduling.

---

## 3. Dataset Provenance & Licenses

The Machine Learning and Computer Vision models incorporated in TerraQora AI rely on public and open-access benchmark agricultural datasets:

| Dataset | Modality | Primary Source / Provenance | License / Permitted Use |
| :--- | :--- | :--- | :--- |
| **PlantVillage** | Computer Vision (54,306 images, 38 crop disease classes) | Hughes, D. & Salathé, M. (2015), Penn State / EPFL | Creative Commons Zero (CC0 1.0) Public Domain Dedication |
| **Crop Recommendation** | Tabular Soil & Climate Data (2,200 samples, 22 crops) | Open Agricultural Research Benchmark via Kaggle / data.world | Open Database License (ODbL) / Public Domain |
| **Crop Yield Statistics** | Tabular Agronomic Data (19,689 records, India 1997–2020) | Ministry of Agriculture & Farmers Welfare, Directorate of Economics and Statistics | Open Government Data (OGD) Platform / Educational & Research Use |
| **Fertilizer Recommendation** | Tabular Soil & Crop Data (99 agricultural records) | Agricultural University Extension Benchmark | Creative Commons Attribution (CC BY 4.0) |

Original raw datasets are archived in `ml/datasets/` and are preserved under their respective original licenses.

---

## 4. Third-Party Service Attributions

TerraQora AI interfaces with external telemetry and generative intelligence APIs:

### A. Open-Meteo Weather API
- **License / Terms:** Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Attribution Statement:** Weather forecast data, historical agro-meteorological reanalysis, and reference evapotranspiration are powered by [Open-Meteo.com](https://open-meteo.com/) under the CC BY 4.0 license.
- **Provider Role:** Primary meteorological data source. Does not require proprietary commercial API keys for non-commercial standard usage.

### B. Google Gemini API
- **Provider:** Google LLC.
- **Terms:** Governed by Google Cloud Platform Terms of Service and Gemini API Terms of Use.
- **Role:** Grounds the multilingual GenAI Farming Assistant via server-side Gemini 2.5 Flash endpoints. API credentials remain strictly server-side.

### C. OpenWeatherMap API
- **Provider:** OpenWeather Ltd.
- **Terms:** Governed by OpenWeather Terms of Service.
- **Role:** Secondary fallback meteorological provider configurable via `WEATHER_PROVIDER=openweathermap`.

---

## 5. Trademark Notice

"TerraQora", "TerraQora AI", and the TerraQora leaf-shield brand emblem are trademarks of Ali Trose. Use of these names for derivative commercial platforms without prior written authorization is prohibited.
