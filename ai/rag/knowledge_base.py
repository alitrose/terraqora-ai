from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RagChunk:
    chunk_id: str
    source_title: str
    section: str
    keywords: tuple[str, ...]
    content: str


_AGRONOMY_CORPUS: tuple[RagChunk, ...] = (
    RagChunk(
        chunk_id="soil_ph_management",
        source_title="ICAR Soil Health & Acidity Management Principles",
        section="Soil pH Buffering & Nutrient Availability",
        keywords=(
            "ph",
            "acidic",
            "alkaline",
            "lime",
            "gypsum",
            "soil",
            "red",
            "loamy",
            "laterite",
            "மண்",
            "മണ്ണ്",
            "मिट्टी",
            "నేల",
        ),
        content=(
            "Most field crops achieve optimal macronutrient availability near soil pH 6.0-7.5. "
            "Strongly acidic soils (pH < 5.5) reduce phosphorus availability and can cause aluminum "
            "toxicity; agricultural lime needs depend on soil texture and buffer pH, so exact "
            "amendment quantities must be determined by a Soil Health Card laboratory test before "
            "sowing. Strongly alkaline soils (pH > 8.0) benefit from organic compost incorporation, "
            "adequate drainage, and KVK-verified gypsum or micronutrient programs."
        ),
    ),
    RagChunk(
        chunk_id="npk_fertilizer_stewardship",
        source_title="TerraQora Balanced Nutrient Stewardship Guide",
        section="NPK Split Application & Guardrails",
        keywords=(
            "npk",
            "nitrogen",
            "phosphorus",
            "potassium",
            "urea",
            "dap",
            "mop",
            "fertilizer",
            "nutrient",
            "dose",
            "dosage",
            "split",
            "உரம்",
            "വളം",
            "खाद",
            "उर्वरक",
            "ఎరువు",
        ),
        content=(
            "Balanced nutrient management prioritizes soil testing before purchasing chemical inputs. "
            "Nitrogen is mobile in soil and is most effective when split across basal sowing/transplanting "
            "and active vegetative/panicle growth stages rather than applied in a single heavy broadcast. "
            "Phosphorus supports root establishment early in the season, while potassium strengthens "
            "water regulation and stress tolerance. When Soil Health Card values already show sufficient "
            "N, P, and K, avoid blanket mineral application and focus on organic matter maintenance. "
            "Never guess exact per-hectare dosages; verify site-specific schedules with a local KVK agronomist."
        ),
    ),
    RagChunk(
        chunk_id="kharif_rice_paddy",
        source_title="ICAR Rice Cultivation Reference",
        section="Kharif Paddy Nutrient & Water Management",
        keywords=(
            "rice",
            "paddy",
            "kharif",
            "transplanting",
            "panicle",
            "yellowing",
            "tillering",
            "leaf",
            "color",
            "chart",
            "நெல்",
            "നെല്ല്",
            "धान",
            "चावल",
            "వరి",
        ),
        content=(
            "In Kharif paddy, synchronize nitrogen top-dressing with active tillering and panicle "
            "initiation using Leaf Color Chart (LCC) checks to minimize volatilization and leaching losses. "
            "Maintain shallow standing water during critical rooting and flowering phases while avoiding "
            "continuous deep stagnation that encourages root rot or sheath blight. Drain excess rainwater "
            "promptly during intense monsoon spells to preserve root oxygenation."
        ),
    ),
    RagChunk(
        chunk_id="disease_non_diagnosis",
        source_title="Integrated Pest & Disease Stewardship Guide",
        section="Preventive Hygiene & Non-Diagnosis Boundary",
        keywords=(
            "disease",
            "blight",
            "rust",
            "spot",
            "fungus",
            "fungal",
            "pest",
            "yellow",
            "leaf",
            "tomato",
            "banana",
            "infected",
            "spray",
            "fungicide",
            "நோய்",
            "രോഗം",
            "रोग",
            "बीमारी",
            "తెగులు",
        ),
        content=(
            "Visual symptoms described only in text—such as spots, yellowing, or wilting—can overlap "
            "across fungal, bacterial, viral, and nutrient-deficiency causes, so text alone cannot provide "
            "a reliable diagnosis. Recommended immediate low-risk actions include scouting affected plants, "
            "removing heavily damaged lower debris from the field, avoiding late-evening overhead irrigation "
            "that keeps foliage wet overnight, and maintaining spacing for airflow. For accurate screening, "
            "inspect a sharp daylight leaf photo in TerraQora's Plant Disease Vision module or consult a local "
            "KVK plant pathologist before choosing any crop-labeled treatment."
        ),
    ),
    RagChunk(
        chunk_id="irrigation_weather_et0",
        source_title="Agro-Meteorology & Irrigation Scheduling Guide",
        section="Rain-Aware Scheduling & ET0 Estimation",
        keywords=(
            "irrigation",
            "water",
            "drip",
            "rain",
            "rainfall",
            "weather",
            "forecast",
            "et0",
            "drought",
            "moisture",
            "heat",
            "பாசனம்",
            "தண்ணீர்",
            "ജലസേചനം",
            "വെള്ളം",
            "सिंचाई",
            "पानी",
            "నీటిపారుదల",
            "నీరు",
        ),
        content=(
            "Effective irrigation scheduling compares crop evapotranspiration demand (ET0 multiplied by "
            "crop growth-stage coefficient) against effective upcoming rainfall. If meaningful rainfall "
            "is forecast within the next 48-72 hours, delaying supplemental irrigation conserves water "
            "and prevents nutrient leaching and waterlogging. Note that meteorological ET0 advisories are "
            "weather-based estimates rather than direct in-field soil moisture probe readings; always check "
            "topsoil moisture by hand before turning pumps on."
        ),
    ),
    RagChunk(
        chunk_id="crop_selection_rotation",
        source_title="Sustainable Cropping Systems & Diversification Guide",
        section="Agro-Climatic Fit & Legume Rotation",
        keywords=(
            "crop",
            "yield",
            "recommend",
            "suitable",
            "sowing",
            "season",
            "rabi",
            "rotation",
            "pulse",
            "coconut",
            "maize",
            "cotton",
            "பயிர்",
            "വിള",
            "फसल",
            "పంట",
        ),
        content=(
            "Selecting well-adapted crops requires evaluating soil NPK levels, soil pH, seasonal rainfall, "
            "temperature, humidity, and historical regional performance together. Rotating cereals such as "
            "rice, wheat, or maize with nitrogen-fixing pulses (moong, urad, chickpea, pigeonpea) helps "
            "break pest cycles and enrich organic nitrogen reserves. Use TerraQora's Crop Suitability and "
            "Crop Yield ML modules alongside local mandi/water availability planning before finalizing acreage."
        ),
    ),
)

_NON_WORD_RE = re.compile(r"[^\w\u0900-\u097F\u0B80-\u0BFF\u0C00-\u0C7F\u0D00-\u0D7F]+")


def _tokenize(text: str) -> set[str]:
    return {tok for tok in _NON_WORD_RE.split(text.lower()) if len(tok) >= 2}


def retrieve_agronomy_context(
    query: str,
    *,
    farm_crop: str | None = None,
    farm_soil_type: str | None = None,
    top_k: int = 3,
) -> list[RagChunk]:
    """Deterministically retrieve top grounded agronomy passages for RAG."""
    combined_query = " ".join(
        part for part in (query, farm_crop or "", farm_soil_type or "") if part
    )
    query_tokens = _tokenize(combined_query)
    lower_query = combined_query.lower()

    scored: list[tuple[int, int, RagChunk]] = []
    for idx, chunk in enumerate(_AGRONOMY_CORPUS):
        score = 0
        for kw in chunk.keywords:
            if kw in query_tokens:
                score += 4
            elif kw in lower_query:
                score += 2

        chunk_tokens = _tokenize(f"{chunk.section} {chunk.content}")
        overlap = query_tokens.intersection(chunk_tokens)
        score += len(overlap)
        scored.append((score, -idx, chunk))

    scored.sort(reverse=True)
    positive = [chunk for score, _, chunk in scored if score > 0][:top_k]
    if positive:
        return positive
    # Safe grounded fallback when query uses very general phrasing
    return [_AGRONOMY_CORPUS[1], _AGRONOMY_CORPUS[5]][:top_k]


def format_rag_context(chunks: list[RagChunk]) -> str:
    if not chunks:
        return ""
    blocks = []
    for chunk in chunks:
        blocks.append(
            f"- Source: {chunk.source_title} | Section: {chunk.section}\n"
            f"  Guidance: {chunk.content}"
        )
    return "\n".join(blocks)
