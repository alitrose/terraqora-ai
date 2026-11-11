# TerraQora AI — Brand Guidelines

**Product Name:** TerraQora AI  
**Tagline:** *Intelligence for Every Acre.*  
**Positioning:** Precision agritech SaaS combining leak-free yield forecasting, plant pathology computer vision, meteorological irrigation intelligence, and grounded multilingual Generative AI.

---

## 1. Visual Identity & Assets
- [terraqora-logo.svg](../frontend/public/terraqora-logo.svg): Primary horizontal lockup for navbar, landing header, and report cover headers.
- [terraqora-mark.svg](../frontend/public/terraqora-mark.svg): Square precision-acre emblem for collapsed sidebar, auth screens, and compact cards.
- [favicon.svg](../frontend/public/favicon.svg): 32×32 high-contrast Deep Forest Green & Harvest Gold browser icon.
- [design-tokens.json](../frontend/design-tokens.json): Canonical JSON design tokens consumed by Tailwind CSS and Recharts.

## 2. Color Palette

| Token | Hex | Role |
| --- | --- | --- |
| `forestDeep` | `#123524` | Primary brand anchor, navigation chrome, primary CTA buttons |
| `leafEmerald` | `#2D6A4F` | Interactive focus states, healthy status indicators, chart primary |
| `sproutGreen` | `#52B788` | Positive growth deltas, secondary accents |
| `warmWhite` | `#FAF9F5` | Primary page canvas (warm parchment white for outdoor/long-session legibility) |
| `surfaceWhite` | `#FFFFFF` | Elevated cards, form panels, analytics containers |
| `harvestGold` | `#C9972C` | Intelligence highlights, forecast markers, key KPI accents |
| `soilCharcoal` | `#1B241E` | High-contrast body text |
| `slateMuted` | `#5A665E` | Secondary metadata, axis ticks, captions |

## 3. Typography
- **Display & Headings:** `Plus Jakarta Sans` (weights 600, 700, `-0.02em` tracking)
- **Body & Controls:** `Inter` (weights 400, 500, 600)
- **Telemetry & Metrics:** `JetBrains Mono` (`tabular-nums` for yield predictions, NPK levels, confidence %, and coordinates)

## 4. UI & UX Principles
1. **No generic AI templates:** Avoid purple neon gradients, pulsing blobs, or clutter. Maintain generous whitespace, crisp `1px` borders (`#E4E8E1`), and calm earth-toned contrast.
2. **Honesty & Uncertainty States:** Every ML/CV/Weather/GenAI output includes model version, confidence/uncertainty flags (`< 65%` warning on leaf disease), and explicit separation between estimated weather-derived irrigation vs. soil moisture sensor data.
3. **Full State Coverage:** Every page implements loading skeletons, informative empty states, actionable error recovery, and responsive mobile/tablet/desktop layouts.
