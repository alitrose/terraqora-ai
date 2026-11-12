"""PyTorch CPU-safe Plant Disease Vision architecture and temperature-calibrated predictor.

All checkpoints store strictly tensor state dicts and primitive metadata so production
servers can load artifacts safely with `torch.load(..., map_location="cpu", weights_only=True)`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from ml.preprocessing.disease_features import (
    PLANTVILLAGE_CLASSES,
    SUPPORTED_SPECIES_CANONICAL,
    ValidatedLeafImage,
    get_disease_guidance,
    parse_plantvillage_label,
    resolve_crop_hint_support,
)

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def build_vision_backbone(
    architecture: str,
    *,
    num_classes: int = len(PLANTVILLAGE_CLASSES),
    pretrained: bool = False,
) -> Any:
    """Construct MobileNetV3-Small or EfficientNet-B0 classifier without hidden hub calls when pretrained=False."""
    import torch.nn as nn
    from torchvision import models

    if architecture == "mobilenet_v3_small":
        weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        model = models.mobilenet_v3_small(weights=weights)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, num_classes)
        return model

    if architecture == "efficientnet_b0":
        weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        model = models.efficientnet_b0(weights=weights)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, num_classes)
        return model

    raise ValueError(f"Unsupported vision architecture '{architecture}'.")


def preprocess_pil_for_vision(image: Image.Image, image_size: int = 224) -> Any:
    """Deterministic RGB Resize -> CenterCrop -> Normalize tensor of shape (1, 3, H, W)."""
    import torch

    resize_dim = int(round(image_size * 256 / 224))
    rgb = image.convert("RGB")
    w, h = rgb.size
    if w < h:
        new_w = resize_dim
        new_h = max(resize_dim, int(round(h * (resize_dim / max(1, w)))))
    else:
        new_h = resize_dim
        new_w = max(resize_dim, int(round(w * (resize_dim / max(1, h)))))
    resized = rgb.resize((new_w, new_h), Image.Resampling.BILINEAR)

    left = (new_w - image_size) // 2
    top = (new_h - image_size) // 2
    cropped = resized.crop((left, top, left + image_size, top + image_size))

    arr = np.asarray(cropped, dtype=np.float32) / 255.0
    mean = np.array(IMAGENET_MEAN, dtype=np.float32)
    std = np.array(IMAGENET_STD, dtype=np.float32)
    norm = (arr - mean) / std
    chw = np.transpose(norm, (2, 0, 1))
    return torch.from_numpy(np.ascontiguousarray(chw)).unsqueeze(0)


@dataclass
class DiseasePredictionOutput:
    predicted_label: str
    crop_name: str
    disease_name: str
    is_healthy: bool
    confidence: float
    top2_margin: float
    is_uncertain: bool
    uncertainty_reason: str | None
    top_predictions: list[dict[str, Any]]
    treatment_summary: str
    prevention_notes: str
    next_steps: list[str]
    limitations: list[str]
    supported_scope_note: str
    model_version: str


class PlantDiseasePredictor:
    """Inference wrapper with calibrated temperature scaling and abstention guardrails."""

    def __init__(
        self,
        *,
        model: Any,
        architecture: str,
        class_names: list[str],
        temperature: float,
        image_size: int,
        model_version: str,
    ) -> None:
        self.model = model
        self.model.eval()
        self.architecture = architecture
        self.class_names = list(class_names)
        self.temperature = max(0.05, float(temperature))
        self.image_size = int(image_size)
        self.model_version = model_version

    @classmethod
    def from_checkpoint(cls, checkpoint_path: Path) -> "PlantDiseasePredictor":
        import torch

        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        if not isinstance(payload, dict) or "state_dict" not in payload or "architecture" not in payload:
            raise ValueError("Invalid plant disease checkpoint schema.")

        architecture = str(payload["architecture"])
        class_names = [str(c) for c in payload.get("class_names", PLANTVILLAGE_CLASSES)]
        temperature = float(payload.get("temperature", 1.0))
        image_size = int(payload.get("image_size", 224))
        model_version = str(payload.get("model_version", "phase7-vision-v1.0.0"))

        model = build_vision_backbone(
            architecture,
            num_classes=len(class_names),
            pretrained=False,
        )
        model.load_state_dict(payload["state_dict"], strict=True)
        model.eval()
        return cls(
            model=model,
            architecture=architecture,
            class_names=class_names,
            temperature=temperature,
            image_size=image_size,
            model_version=model_version,
        )

    def predict(
        self,
        validated: ValidatedLeafImage,
        *,
        crop_hint: str | None = None,
        confidence_threshold: float = 0.65,
        min_margin: float = 0.15,
    ) -> DiseasePredictionOutput:
        import torch

        tensor = preprocess_pil_for_vision(validated.rgb_image, self.image_size)
        with torch.inference_mode():
            logits = self.model(tensor).squeeze(0).float()
            probs_tensor = torch.softmax(logits / self.temperature, dim=0)
            probs = probs_tensor.cpu().numpy()

        top_indices = np.argsort(-probs)[:3]
        top_predictions = [
            {
                "label": self.class_names[int(idx)],
                "confidence": round(float(probs[int(idx)]), 4),
            }
            for idx in top_indices
        ]

        top1_label = top_predictions[0]["label"]
        top1_conf = float(top_predictions[0]["confidence"])
        top2_conf = float(top_predictions[1]["confidence"]) if len(top_predictions) > 1 else 0.0
        margin = round(top1_conf - top2_conf, 4)

        crop_name, disease_name, is_healthy = parse_plantvillage_label(top1_label)
        is_supported_hint, canonical_prefix = resolve_crop_hint_support(crop_hint)

        uncertainty_reasons: list[str] = []
        if not is_supported_hint:
            uncertainty_reasons.append(
                f"Expected crop '{crop_hint}' is outside the trained PlantVillage 14-species catalog "
                f"(supported crops: {', '.join(SUPPORTED_SPECIES_CANONICAL)})."
            )
        if validated.is_low_detail_or_blank and validated.low_detail_reason:
            uncertainty_reasons.append(validated.low_detail_reason)
        if top1_conf < confidence_threshold:
            uncertainty_reasons.append(
                f"Calibrated top-1 probability ({top1_conf * 100:.1f}%) is below the "
                f"{confidence_threshold * 100:.0f}% screening certainty threshold."
            )
        elif margin < min_margin:
            uncertainty_reasons.append(
                f"Top two disease candidates differ by only {margin * 100:.1f}% "
                f"(below {min_margin * 100:.0f}% separation margin), indicating visual ambiguity."
            )

        if (
            is_supported_hint
            and canonical_prefix is not None
            and not top1_label.startswith(canonical_prefix)
        ):
            uncertainty_reasons.append(
                f"Selected crop context ('{crop_hint}') does not match the top visual species match "
                f"('{crop_name}'); inspect leaf framing or confirm crop species."
            )

        is_uncertain = len(uncertainty_reasons) > 0
        if is_uncertain:
            predicted_label_out = (
                "Uncertain___Out_Of_Scope_Crop" if not is_supported_hint else f"Uncertain___Review_Required ({top1_label})"
            )[:120]
            display_crop = crop_hint.strip() if crop_hint and crop_hint.strip() else crop_name
            display_disease = (
                "Uncertain / Unsupported Crop"
                if not is_supported_hint
                else f"Uncertain Screening (Closest match: {crop_name} — {disease_name})"
            )
            display_healthy = False
            guidance = get_disease_guidance(top1_label, is_uncertain=True)
        else:
            predicted_label_out = top1_label[:120]
            display_crop = crop_name
            display_disease = disease_name
            display_healthy = is_healthy
            guidance = get_disease_guidance(top1_label, is_uncertain=False)

        scope_note = (
            "Trained on 38 PlantVillage classes across 14 crop species (Apple, Blueberry, Cherry, "
            "Corn/Maize, Grape, Citrus Orange, Peach, Bell Pepper, Potato, Raspberry, Soybean, "
            "Squash, Strawberry, Tomato). Major field crops like Rice, Wheat, Cotton, Sugarcane, "
            "and Coconut are not supported by this vision model."
        )
        limitations = [
            "Screening aid trained primarily on single-leaf PlantVillage laboratory backgrounds; field lighting or cluttered canopies reduce certainty.",
            "Visual leaf spots cannot definitively distinguish fungal/bacterial infection from nutrient stress without physical inspection or KVK lab testing.",
            "No chemical spray dosages or concentrations are prescribed automatically; verify approved local products with KVK.",
        ]

        return DiseasePredictionOutput(
            predicted_label=predicted_label_out,
            crop_name=display_crop,
            disease_name=display_disease,
            is_healthy=display_healthy,
            confidence=round(top1_conf, 4),
            top2_margin=margin,
            is_uncertain=is_uncertain,
            uncertainty_reason=" ".join(uncertainty_reasons) if uncertainty_reasons else None,
            top_predictions=top_predictions,
            treatment_summary=guidance["treatment_summary"],
            prevention_notes=guidance["prevention_notes"],
            next_steps=guidance["next_steps"],
            limitations=limitations,
            supported_scope_note=scope_note,
            model_version=self.model_version,
        )
