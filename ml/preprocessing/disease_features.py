"""Canonical PlantVillage labels, image validation, perceptual hashing, and IPM guidance.

Zero model training logic or backend imports live here so both training scripts
and production FastAPI services share identical label definitions, image checks,
hashing rules, and safe non-dosage management notes.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
from typing import Any
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

PLANTVILLAGE_CLASSES: tuple[str, ...] = (
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
)

SUPPORTED_SPECIES_CANONICAL: tuple[str, ...] = (
    "Apple",
    "Blueberry",
    "Cherry",
    "Corn (Maize)",
    "Grape",
    "Orange (Citrus)",
    "Peach",
    "Pepper (Bell)",
    "Potato",
    "Raspberry",
    "Soybean",
    "Squash",
    "Strawberry",
    "Tomato",
)

_CROP_HINT_ALIASES: dict[str, str] = {
    "apple": "Apple",
    "blueberry": "Blueberry",
    "cherry": "Cherry_(including_sour)",
    "corn": "Corn_(maize)",
    "maize": "Corn_(maize)",
    "corn / maize": "Corn_(maize)",
    "corn (maize)": "Corn_(maize)",
    "grape": "Grape",
    "orange": "Orange",
    "citrus": "Orange",
    "orange (citrus)": "Orange",
    "peach": "Peach",
    "pepper": "Pepper,_bell",
    "bell pepper": "Pepper,_bell",
    "pepper (bell)": "Pepper,_bell",
    "pepper, bell": "Pepper,_bell",
    "capsicum": "Pepper,_bell",
    "potato": "Potato",
    "raspberry": "Raspberry",
    "soybean": "Soybean",
    "soya": "Soybean",
    "squash": "Squash",
    "strawberry": "Strawberry",
    "tomato": "Tomato",
}

UNSUPPORTED_COMMON_CROPS: tuple[str, ...] = (
    "Rice",
    "Wheat",
    "Cotton",
    "Sugarcane",
    "Coconut",
    "Banana",
    "Groundnut",
    "Chickpea",
    "Mustard",
    "Onion",
    "Mango",
)

ALLOWED_IMAGE_MIME_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/jpg", "image/png", "image/webp"}
)
PIL_FORMAT_TO_MIME: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}

MIN_IMAGE_SIDE_PX = 32
DEFAULT_MAX_IMAGE_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class ValidatedLeafImage:
    rgb_image: Image.Image
    width: int
    height: int
    detected_format: str
    detected_mime: str
    size_bytes: int
    sha256: str
    dhash_hex: str
    luma_std: float
    mean_rgb: tuple[float, float, float]
    is_low_detail_or_blank: bool
    low_detail_reason: str | None


def compute_bytes_sha256(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def compute_dhash_hex(image: Image.Image, hash_size: int = 8) -> str:
    """Compute a 64-bit difference hash (dHash) over normalized grayscale pixels."""
    gray = ImageOps.exif_transpose(image).convert("L").resize(
        (hash_size + 1, hash_size), Image.Resampling.BILINEAR
    )
    arr = np.asarray(gray, dtype=np.uint8)
    diff = arr[:, 1:] > arr[:, :-1]
    bits = diff.flatten().astype(np.uint8)
    val = 0
    for b in bits:
        val = (val << 1) | int(b)
    return f"{val:016x}"


def validate_and_decode_leaf_image(
    raw_bytes: bytes,
    *,
    declared_mime: str | None = None,
    max_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
) -> ValidatedLeafImage:
    """Validate byte size, declared MIME, true encoded image signature, and visual content."""
    if not raw_bytes:
        raise ValueError("Uploaded file is empty.")
    if len(raw_bytes) > max_bytes:
        raise ValueError(
            f"Image exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB."
        )

    if declared_mime is not None:
        cleaned_mime = declared_mime.split(";")[0].strip().lower()
        if cleaned_mime and cleaned_mime not in ALLOWED_IMAGE_MIME_TYPES:
            raise ValueError(
                f"Unsupported media type '{cleaned_mime}'. Accepted types: JPEG, PNG, WebP."
            )

    try:
        probe = Image.open(io.BytesIO(raw_bytes))
        detected_format = (probe.format or "").upper()
        probe.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ValueError("Uploaded file is not a valid or intact JPEG, PNG, or WebP image.") from exc

    if detected_format not in PIL_FORMAT_TO_MIME:
        raise ValueError(
            f"Unsupported image format '{detected_format or 'unknown'}'. Only JPEG, PNG, and WebP are accepted."
        )

    detected_mime = PIL_FORMAT_TO_MIME[detected_format]
    if declared_mime is not None:
        cleaned_mime = declared_mime.split(";")[0].strip().lower()
        # Allow image/jpg synonym for JPEG
        normalized_declared = "image/jpeg" if cleaned_mime == "image/jpg" else cleaned_mime
        if normalized_declared and normalized_declared != detected_mime:
            raise ValueError(
                f"File signature ({detected_mime}) does not match declared Content-Type ({cleaned_mime})."
            )

    # Full decode after verify()
    try:
        decoded = Image.open(io.BytesIO(raw_bytes))
        decoded = ImageOps.exif_transpose(decoded).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("Failed to decode leaf image pixel data.") from exc

    width, height = decoded.size
    if width < MIN_IMAGE_SIDE_PX or height < MIN_IMAGE_SIDE_PX:
        raise ValueError(
            f"Image resolution ({width}x{height}) is too small; minimum supported size is {MIN_IMAGE_SIDE_PX}x{MIN_IMAGE_SIDE_PX} px."
        )

    arr = np.asarray(decoded.resize((128, 128), Image.Resampling.BILINEAR), dtype=np.float32)
    luma = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    luma_std = float(np.std(luma))
    mean_rgb = tuple(float(x) for x in arr.mean(axis=(0, 1)))

    # Edge strength check helps distinguish solid / nearly uniform images from real leaves
    gx = np.abs(np.diff(luma, axis=1)).mean()
    gy = np.abs(np.diff(luma, axis=0)).mean()
    edge_mean = float(0.5 * (gx + gy))

    is_low_detail = luma_std < 8.0 or edge_mean < 1.2
    low_detail_reason = None
    if is_low_detail:
        low_detail_reason = (
            "Uploaded frame lacks visible leaf texture or contrast (nearly blank or uniform image). "
            "Capture a sharp daylight close-up of a single leaf."
        )

    return ValidatedLeafImage(
        rgb_image=decoded,
        width=width,
        height=height,
        detected_format=detected_format,
        detected_mime=detected_mime,
        size_bytes=len(raw_bytes),
        sha256=compute_bytes_sha256(raw_bytes),
        dhash_hex=compute_dhash_hex(decoded),
        luma_std=round(luma_std, 3),
        mean_rgb=tuple(round(v, 2) for v in mean_rgb),
        is_low_detail_or_blank=is_low_detail,
        low_detail_reason=low_detail_reason,
    )


def extract_color_histogram_features(image: Image.Image) -> np.ndarray:
    """Extract deterministic 96-dim HSV + RGB spatial color/texture feature vector."""
    resized = image.resize((96, 96), Image.Resampling.BILINEAR)
    rgb = np.asarray(resized, dtype=np.float32) / 255.0
    hsv = np.asarray(resized.convert("HSV"), dtype=np.float32) / 255.0

    feats: list[np.ndarray] = []
    for ch in range(3):
        hist_rgb, _ = np.histogram(rgb[:, :, ch], bins=16, range=(0.0, 1.0))
        feats.append(hist_rgb.astype(np.float32) / max(1, hist_rgb.sum()))
    for ch in range(3):
        hist_hsv, _ = np.histogram(hsv[:, :, ch], bins=16, range=(0.0, 1.0))
        feats.append(hist_hsv.astype(np.float32) / max(1, hist_hsv.sum()))

    return np.concatenate(feats, axis=0)


def parse_plantvillage_label(raw_label: str) -> tuple[str, str, bool]:
    """Split PlantVillage class name into (crop_name, disease_name, is_healthy)."""
    if "___" in raw_label:
        crop_part, disease_part = raw_label.split("___", 1)
    else:
        crop_part, disease_part = raw_label, "Unknown Condition"

    crop_clean = (
        crop_part.replace("_(including_sour)", "")
        .replace(",_bell", " (Bell)")
        .replace("_(maize)", " (Maize)")
        .replace("_", " ")
        .strip()
    )
    disease_clean = disease_part.replace("_", " ").strip()
    is_healthy = disease_clean.lower() == "healthy"
    if is_healthy:
        disease_clean = "Healthy Foliage"
    return crop_clean, disease_clean, is_healthy


def resolve_crop_hint_support(crop_hint: str | None) -> tuple[bool, str | None]:
    """Return (is_supported, canonical_plantvillage_prefix_or_none)."""
    if crop_hint is None:
        return True, None
    cleaned = crop_hint.strip().lower()
    if not cleaned or cleaned in {"auto", "auto-detect", "unknown", "other"}:
        return True, None
    if cleaned in _CROP_HINT_ALIASES:
        return True, _CROP_HINT_ALIASES[cleaned]
    for alias, prefix in _CROP_HINT_ALIASES.items():
        if alias in cleaned:
            return True, prefix
    return False, None


def get_disease_guidance(raw_label: str, *, is_uncertain: bool) -> dict[str, Any]:
    """Return strictly non-dosage IPM management, prevention, and next steps."""
    crop_name, disease_name, is_healthy = parse_plantvillage_label(raw_label)

    if is_uncertain:
        return {
            "treatment_summary": (
                "Automated vision screening confidence is insufficient for a reliable diagnosis. "
                "Isolate visibly damaged leaves only where practical, avoid applying unverified chemical sprays, "
                "and consult your local Krishi Vigyan Kendra (KVK) or plant pathology officer with fresh leaf samples."
            ),
            "prevention_notes": (
                "Ensure clear natural daylight framing of a single leaf against a clean neutral background, "
                "avoid overhead irrigation late in the day, and maintain field sanitation until specialist verification."
            ),
            "next_steps": [
                "Retake 2-3 close-up photos of both upper and lower leaf surfaces in diffused daylight.",
                "Verify that the selected crop species is covered by the PlantVillage 14-crop vision catalog.",
                "Share clear photos or physical leaf cuttings with your local KVK / extension agronomist before chemical intervention.",
            ],
        }

    if is_healthy:
        return {
            "treatment_summary": (
                f"Foliage matches healthy {crop_name} reference patterns in PlantVillage screening. "
                "No curative disease intervention is indicated from this image alone."
            ),
            "prevention_notes": (
                "Continue routine weekly scouting of lower and inner canopy leaves, maintain balanced NPK nutrition, "
                "and keep furrow/drip scheduling aligned with crop stage and forecast rainfall."
            ),
            "next_steps": [
                "Inspect undersides of older leaves during routine scouting for early pest eggs or lesions.",
                "Maintain field sanitation and clean pruning tools between plots.",
            ],
        }

    lower = disease_name.lower()
    if "virus" in lower or "haunglongbing" in lower or "citrus greening" in lower:
        treatment = (
            f"Visual patterns resemble {disease_name} on {crop_name}. Plant viruses and systemic vascular diseases "
            "cannot be cured by foliar fungicide sprays. Confirm with KVK/lab indexing, remove severely infected rogue "
            "plants carefully to limit spread, and manage insect vectors (whiteflies, aphids, psyllids) using approved IPM."
        )
        prevention = (
            "Use certified disease-free nursery stock/seedlings, install yellow sticky traps or insect-proof netting "
            "in nurseries, control alternate weed hosts, and sanitize hands/tools after handling symptomatic plants."
        )
        steps = [
            "Confirm systemic/viral symptoms with KVK or state agricultural extension lab before uprooting.",
            "Scout nearby healthy plants for insect vectors (whiteflies, aphids, psyllids).",
            "Follow local extension guidance for approved vector IPM rather than repeating fungicide applications.",
        ]
    elif "bacterial" in lower:
        treatment = (
            f"Visual lesions align with {disease_name} on {crop_name}. Avoid working in the field when foliage is wet "
            "to curb bacterial ooze spread, remove heavily necrotic lower leaves into sealed bags, and ask your local "
            "agronomist whether approved copper/bio-control bactericide programs suit your growth stage."
        )
        prevention = (
            "Plant treated/pathogen-free seed, practice a 2-3 year non-host crop rotation, switch from overhead sprinklers "
            "to drip irrigation, and avoid mechanical leaf injury."
        )
        steps = [
            "Avoid pruning or harvesting while dew or rain leaves foliage wet.",
            "Confirm recommended bactericide compatibility and pre-harvest interval with KVK.",
            "Sanitize stakes, crates, and shears before entering clean blocks.",
        ]
    elif "spider mites" in lower:
        treatment = (
            f"Stippling/bronzing matches {disease_name} indicators on {crop_name}. Check leaf undersides with a 10x hand lens "
            "for webbing and motile mites, conserve natural predatory mites, and consult KVK for targeted miticide/bio-control options."
        )
        prevention = (
            "Avoid water stress during hot dry spells, limit dusty field borders, and avoid broad-spectrum pyrethroid "
            "sprays that flare spider mite outbreaks by eliminating beneficial predators."
        )
        steps = [
            "Inspect leaf undersides with a hand lens to verify active mites before treatment.",
            "Irrigate adequately to reduce drought-induced heat stress on foliage.",
            "Ask your local agronomist for selective mite management compatible with beneficials.",
        ]
    elif "late blight" in lower or "early blight" in lower or "scab" in lower or "rot" in lower or "mildew" in lower or "rust" in lower or "spot" in lower:
        treatment = (
            f"Leaf symptoms align with fungal/oomycete {disease_name} on {crop_name}. Promptly rogue or bag heavily blighted "
            "foliage if infection is localized, widen airflow between rows, and consult your local KVK or input dealer "
            "for label-verified active ingredients and safe spray timing (no generic dosage assumed)."
        )
        prevention = (
            "Adopt wider plant spacing and mulching to prevent soil splash, irrigate at soil level early in the morning, "
            "remove post-harvest crop debris, and rotate crops away from susceptible hosts."
        )
        steps = [
            "Inspect neighboring plants and lower canopy humidity pockets over the next 24-48 hours.",
            "Avoid evening overhead watering that leaves foliage wet overnight.",
            "Confirm locally registered fungicide mode-of-action and label rates with KVK before spraying.",
        ]
    else:
        treatment = (
            f"Screening matched {disease_name} on {crop_name}. Verify lesions physically in the field and seek "
            "confirmation from a local extension agronomist before chemical treatment."
        )
        prevention = (
            "Maintain balanced nutrition, clean field margins, and crop rotation with non-host species."
        )
        steps = [
            "Inspect at least 5-10 plants across different parts of the plot to gauge spread.",
            "Consult local KVK with leaf samples for targeted diagnosis and label-compliant management.",
        ]

    return {
        "treatment_summary": treatment,
        "prevention_notes": prevention,
        "next_steps": steps,
    }
