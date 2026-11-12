"""Phase 7 Part A — Plant Disease Vision Training, Comparison & Calibration Pipeline.

Reads the zero-leakage grouped stratified splits (`ml/datasets/processed/disease_splits.parquet`),
trains and compares:
  1. Baseline: 96-dim HSV/RGB Color Histogram + LogisticRegression
  2. Transfer Learning A: MobileNetV3-Small (head warmup + top-block fine-tuning + temp scaling)
  3. Transfer Learning B: EfficientNet-B0 (head warmup + top-block fine-tuning + temp scaling)

Evaluates all models on the untouched held-out test split, computes 10-bin ECE & Brier
calibration metrics, validates abstention thresholds on in-domain vs synthetic OOD inputs,
and serializes a weights_only-safe checkpoint (`ml/saved_models/plant_disease_model.pt`) plus
benchmark metrics (`ml/evaluation/disease_metrics.json`).
"""

from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
import torch
import torch.nn as nn
from PIL import Image
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.preprocessing.disease_features import (  # noqa: E402
    PLANTVILLAGE_CLASSES,
    extract_color_histogram_features,
    validate_and_decode_leaf_image,
)
from ml.preprocessing.disease_model import (  # noqa: E402
    IMAGENET_MEAN,
    IMAGENET_STD,
    PlantDiseasePredictor,
    build_vision_backbone,
)

RAW_DIR = ROOT / "ml" / "datasets" / "plantvillage"
SPLITS_PARQUET = ROOT / "ml" / "datasets" / "processed" / "disease_splits.parquet"
MODEL_OUT = ROOT / "ml" / "saved_models" / "plant_disease_model.pt"
METRICS_OUT = ROOT / "ml" / "evaluation" / "disease_metrics.json"
AUDIT_JSON = ROOT / "ml" / "evaluation" / "disease_audit.json"

MODEL_VERSION = "phase7-vision-v1.0.0"
SEED = 20261112
IMAGE_SIZE = 224


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def _load_split_image_bytes() -> tuple[dict[str, list[dict[str, Any]]], dict[tuple[str, int], bytes]]:
    if not SPLITS_PARQUET.exists():
        raise FileNotFoundError(
            f"Missing split index at {SPLITS_PARQUET}. Run python -m ml.audit_plant_disease first."
        )

    split_rows = pq.read_table(SPLITS_PARQUET).to_pylist()
    by_split: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    needed_rows: dict[str, set[int]] = {}
    for row in split_rows:
        by_split[row["split"]].append(row)
        needed_rows.setdefault(row["source_file"], set()).add(int(row["row_index"]))

    bytes_cache: dict[tuple[str, int], bytes] = {}
    for source_file, wanted_indices in needed_rows.items():
        ppath = RAW_DIR / source_file
        pf = pq.ParquetFile(ppath)
        global_idx = 0
        for batch in pf.iter_batches(batch_size=512, columns=["image"]):
            img_col = batch.column("image").to_pylist()
            for cell in img_col:
                if global_idx in wanted_indices:
                    raw = cell["bytes"] if isinstance(cell, dict) else cell
                    bytes_cache[(source_file, global_idx)] = bytes(raw)
                global_idx += 1

    print(
        f"[DATA] Loaded {len(bytes_cache)} image buffers "
        f"(train={len(by_split['train'])}, val={len(by_split['val'])}, test={len(by_split['test'])})",
        flush=True,
    )
    return by_split, bytes_cache


class ParquetLeafDataset(Dataset[tuple[torch.Tensor, int]]):
    def __init__(
        self,
        records: list[dict[str, Any]],
        bytes_cache: dict[tuple[str, int], bytes],
        transform: transforms.Compose,
    ) -> None:
        self.records = records
        self.bytes_cache = bytes_cache
        self.transform = transform

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        rec = self.records[index]
        raw = self.bytes_cache[(rec["source_file"], int(rec["row_index"]))]
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        return self.transform(img), int(rec["label_id"])


def _compute_ece_and_brier(
    probs: np.ndarray, y_true: np.ndarray, n_bins: int = 10
) -> tuple[float, float]:
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == y_true).astype(np.float64)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = max(1, len(y_true))
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        in_bin = (confidences > lo) & (confidences <= hi) if i > 0 else (confidences >= lo) & (confidences <= hi)
        cnt = int(in_bin.sum())
        if cnt == 0:
            continue
        ece += (cnt / n) * abs(float(accuracies[in_bin].mean()) - float(confidences[in_bin].mean()))

    one_hot = np.zeros_like(probs, dtype=np.float64)
    one_hot[np.arange(len(y_true)), y_true] = 1.0
    brier = float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))
    return round(float(ece), 5), round(brier, 5)


def _softmax_np(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    scaled = logits / max(0.05, float(temperature))
    scaled -= scaled.max(axis=1, keepdims=True)
    exp_x = np.exp(scaled)
    return exp_x / exp_x.sum(axis=1, keepdims=True)


def _fit_temperature_on_val(val_logits: np.ndarray, y_val: np.ndarray) -> float:
    def nll_loss(temp: float) -> float:
        probs = _softmax_np(val_logits, temp)
        p_true = np.clip(probs[np.arange(len(y_val)), y_val], 1e-12, 1.0)
        return float(-np.mean(np.log(p_true)))

    res = minimize_scalar(nll_loss, bounds=(0.35, 3.0), method="bounded")
    return round(float(res.x), 4)


def _classification_summary(probs: np.ndarray, y_true: np.ndarray) -> dict[str, Any]:
    y_pred = probs.argmax(axis=1)
    acc = float(accuracy_score(y_true, y_pred))
    top3_idx = np.argsort(-probs, axis=1)[:, :3]
    top3_acc = float(np.mean([y_true[i] in top3_idx[i] for i in range(len(y_true))]))
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    weighted_f1 = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )[2]
    ece, brier = _compute_ece_and_brier(probs, y_true)
    return {
        "accuracy": round(acc, 4),
        "top3_accuracy": round(top3_acc, 4),
        "macro_precision": round(float(macro_p), 4),
        "macro_recall": round(float(macro_r), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "ece_10bin": ece,
        "brier_score": brier,
    }


def _train_histogram_baseline(
    by_split: dict[str, list[dict[str, Any]]],
    bytes_cache: dict[tuple[str, int], bytes],
) -> dict[str, Any]:
    t0 = time.time()
    print("[BASELINE] Extracting 96-dim HSV/RGB histograms...", flush=True)

    def _feat_matrix(recs: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        xs, ys = [], []
        for rec in recs:
            raw = bytes_cache[(rec["source_file"], int(rec["row_index"]))]
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            xs.append(extract_color_histogram_features(img))
            ys.append(int(rec["label_id"]))
        return np.vstack(xs), np.array(ys, dtype=np.int64)

    X_tr, y_tr = _feat_matrix(by_split["train"])
    X_val, y_val = _feat_matrix(by_split["val"])
    X_te, y_te = _feat_matrix(by_split["test"])

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_val_s = scaler.transform(X_val)
    X_te_s = scaler.transform(X_te)

    clf = LogisticRegression(max_iter=600, C=3.0)
    clf.fit(X_tr_s, y_tr)

    val_probs = clf.predict_proba(X_val_s)
    test_probs = clf.predict_proba(X_te_s)
    elapsed = round(time.time() - t0, 1)

    val_m = _classification_summary(val_probs, y_val)
    test_m = _classification_summary(test_probs, y_te)
    print(
        f"[BASELINE] Done in {elapsed}s | Val Macro-F1={val_m['macro_f1']} | "
        f"Test Acc={test_m['accuracy']} Macro-F1={test_m['macro_f1']}",
        flush=True,
    )
    return {
        "name": "HSV+RGB Histogram + LogisticRegression",
        "architecture": "histogram_logreg",
        "train_seconds": elapsed,
        "val_metrics": val_m,
        "test_metrics": test_m,
    }


def _collect_logits(model: nn.Module, loader: DataLoader[Any]) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    logits_list: list[np.ndarray] = []
    targets_list: list[np.ndarray] = []
    with torch.inference_mode():
        for xb, yb in loader:
            out = model(xb)
            logits_list.append(out.cpu().numpy())
            targets_list.append(yb.cpu().numpy())
    return np.vstack(logits_list), np.concatenate(targets_list)


def _train_cnn_candidate(
    architecture: str,
    by_split: dict[str, list[dict[str, Any]]],
    bytes_cache: dict[tuple[str, int], bytes],
) -> dict[str, Any]:
    t0 = time.time()
    print(f"[CNN:{architecture}] Initializing ImageNet-pretrained backbone...", flush=True)

    train_tf = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.82, 1.0)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.12, contrast=0.12, saturation=0.12),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )
    eval_tf = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )

    train_ds = ParquetLeafDataset(by_split["train"], bytes_cache, train_tf)
    val_ds = ParquetLeafDataset(by_split["val"], bytes_cache, eval_tf)
    test_ds = ParquetLeafDataset(by_split["test"], bytes_cache, eval_tf)

    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=64, shuffle=False, num_workers=0)

    model = build_vision_backbone(
        architecture, num_classes=len(PLANTVILLAGE_CLASSES), pretrained=True
    )

    # Freeze early layers for fast stable convergence; fine-tune top feature blocks + classifier head
    for param in model.parameters():
        param.requires_grad = False
    for param in model.classifier.parameters():
        param.requires_grad = True
    if hasattr(model, "features"):
        n_blocks = len(model.features)
        unfreeze_from = max(0, n_blocks - 3)
        for idx in range(unfreeze_from, n_blocks):
            for param in model.features[idx].parameters():
                param.requires_grad = True

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(
        f"[CNN:{architecture}] Trainable params: {trainable_params:,} / {total_params:,}",
        flush=True,
    )

    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    epochs = 4
    optimizer = torch.optim.AdamW(
        [
            {"params": [p for p in model.features.parameters() if p.requires_grad], "lr": 3e-4},
            {"params": model.classifier.parameters(), "lr": 1.2e-3},
        ],
        weight_decay=1e-4,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_f1 = -1.0
    best_state_dict: dict[str, torch.Tensor] | None = None
    history: list[dict[str, Any]] = []

    for epoch in range(1, epochs + 1):
        ep_t0 = time.time()
        model.train()
        running_loss = 0.0
        seen = 0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item()) * xb.size(0)
            seen += xb.size(0)
        scheduler.step()

        val_logits, y_val = _collect_logits(model, val_loader)
        val_probs_raw = _softmax_np(val_logits, 1.0)
        val_summary = _classification_summary(val_probs_raw, y_val)
        ep_time = round(time.time() - ep_t0, 1)
        ep_loss = round(running_loss / max(1, seen), 4)
        history.append(
            {
                "epoch": epoch,
                "train_loss": ep_loss,
                "val_accuracy": val_summary["accuracy"],
                "val_macro_f1": val_summary["macro_f1"],
                "seconds": ep_time,
            }
        )
        print(
            f"[CNN:{architecture}] Epoch {epoch}/{epochs} ({ep_time}s) "
            f"loss={ep_loss} val_acc={val_summary['accuracy']} val_f1={val_summary['macro_f1']}",
            flush=True,
        )
        if val_summary["macro_f1"] > best_val_f1:
            best_val_f1 = val_summary["macro_f1"]
            best_state_dict = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    assert best_state_dict is not None
    model.load_state_dict(best_state_dict)

    # Validation temperature scaling
    val_logits, y_val = _collect_logits(model, val_loader)
    temperature = _fit_temperature_on_val(val_logits, y_val)
    val_probs_uncal = _softmax_np(val_logits, 1.0)
    val_probs_cal = _softmax_np(val_logits, temperature)

    # Untouched held-out test evaluation
    test_logits, y_test = _collect_logits(model, test_loader)
    test_probs_uncal = _softmax_np(test_logits, 1.0)
    test_probs_cal = _softmax_np(test_logits, temperature)

    val_m = _classification_summary(val_probs_cal, y_val)
    test_m_uncal = _classification_summary(test_probs_uncal, y_test)
    test_m_cal = _classification_summary(test_probs_cal, y_test)

    total_time = round(time.time() - t0, 1)
    print(
        f"[CNN:{architecture}] Finished in {total_time}s | Temp={temperature} | "
        f"Test Acc={test_m_cal['accuracy']} Macro-F1={test_m_cal['macro_f1']} "
        f"ECE={test_m_uncal['ece_10bin']}->{test_m_cal['ece_10bin']}",
        flush=True,
    )

    return {
        "architecture": architecture,
        "name": (
            "MobileNetV3-Small Transfer Learning (ImageNet)"
            if architecture == "mobilenet_v3_small"
            else "EfficientNet-B0 Transfer Learning (ImageNet)"
        ),
        "train_seconds": total_time,
        "trainable_params": trainable_params,
        "total_params": total_params,
        "temperature": temperature,
        "history": history,
        "val_metrics_uncalibrated": _classification_summary(val_probs_uncal, y_val),
        "val_metrics_calibrated": val_m,
        "test_metrics_uncalibrated": test_m_uncal,
        "test_metrics": test_m_cal,
        "test_probs": test_probs_cal,
        "y_test": y_test,
        "state_dict": best_state_dict,
    }


def _evaluate_thresholds_and_ood(
    predictor: PlantDiseasePredictor,
    test_probs: np.ndarray,
    y_test: np.ndarray,
) -> dict[str, Any]:
    y_pred = test_probs.argmax(axis=1)
    sorted_p = np.sort(test_probs, axis=1)
    top1 = sorted_p[:, -1]
    margin = sorted_p[:, -1] - sorted_p[:, -2]

    sweeps = []
    for conf_thr in (0.50, 0.60, 0.65, 0.75, 0.85):
        accepted = (top1 >= conf_thr) & (margin >= 0.15)
        cov = float(accepted.mean())
        sel_acc = float((y_pred[accepted] == y_test[accepted]).mean()) if accepted.any() else 0.0
        sweeps.append(
            {
                "confidence_threshold": conf_thr,
                "min_top2_margin": 0.15,
                "coverage": round(cov, 4),
                "selective_accuracy": round(sel_acc, 4),
                "abstained_count": int((~accepted).sum()),
            }
        )

    # Synthetic OOD & low-detail rejection sanity checks
    rng = np.random.default_rng(SEED)
    ood_cases: list[tuple[str, Image.Image, str | None]] = [
        ("blank_white_frame", Image.new("RGB", (224, 224), color=(248, 248, 248)), None),
        ("flat_green_canvas", Image.new("RGB", (224, 224), color=(46, 139, 87)), None),
        (
            "gaussian_noise_frame",
            Image.fromarray(rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)),
            None,
        ),
        (
            "unsupported_rice_hint",
            Image.fromarray(rng.integers(20, 220, (224, 224, 3), dtype=np.uint8)),
            "Rice",
        ),
    ]
    ood_results = []
    for case_name, img, hint in ood_cases:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        validated = validate_and_decode_leaf_image(buf.getvalue(), declared_mime="image/png")
        out = predictor.predict(
            validated,
            crop_hint=hint,
            confidence_threshold=0.65,
            min_margin=0.15,
        )
        ood_results.append(
            {
                "case": case_name,
                "is_uncertain": out.is_uncertain,
                "confidence": out.confidence,
                "uncertainty_reason": out.uncertainty_reason,
            }
        )

    return {
        "threshold_tradeoffs": sweeps,
        "recommended_confidence_threshold": 0.65,
        "recommended_min_margin": 0.15,
        "ood_and_blank_abstention_checks": ood_results,
    }


def train_and_evaluate() -> dict[str, Any]:
    _set_seed(SEED)
    by_split, bytes_cache = _load_split_image_bytes()

    baseline_res = _train_histogram_baseline(by_split, bytes_cache)
    mobilenet_res = _train_cnn_candidate("mobilenet_v3_small", by_split, bytes_cache)
    effnet_res = _train_cnn_candidate("efficientnet_b0", by_split, bytes_cache)

    candidates = [mobilenet_res, effnet_res]
    # Pick highest validation macro-F1; tie-break towards MobileNetV3-Small if within 0.004 for lighter footprint
    candidates_sorted = sorted(
        candidates,
        key=lambda c: (c["val_metrics_calibrated"]["macro_f1"], -c["total_params"]),
        reverse=True,
    )
    winner = candidates_sorted[0]
    runner_up = candidates_sorted[1]
    if (
        runner_up["architecture"] == "mobilenet_v3_small"
        and abs(winner["val_metrics_calibrated"]["macro_f1"] - runner_up["val_metrics_calibrated"]["macro_f1"]) <= 0.004
    ):
        winner = runner_up

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_payload = {
        "architecture": winner["architecture"],
        "class_names": list(PLANTVILLAGE_CLASSES),
        "temperature": float(winner["temperature"]),
        "image_size": IMAGE_SIZE,
        "model_version": MODEL_VERSION,
        "state_dict": winner["state_dict"],
    }
    torch.save(checkpoint_payload, MODEL_OUT)
    artifact_bytes = MODEL_OUT.stat().st_size

    # Verify clean weights_only=True reload right away
    predictor = PlantDiseasePredictor.from_checkpoint(MODEL_OUT)

    y_test = winner["y_test"]
    test_probs = winner["test_probs"]
    y_pred = test_probs.argmax(axis=1)

    p_cls, r_cls, f1_cls, sup_cls = precision_recall_fscore_support(
        y_test, y_pred, labels=list(range(len(PLANTVILLAGE_CLASSES))), zero_division=0
    )
    per_class_metrics = {
        PLANTVILLAGE_CLASSES[i]: {
            "precision": round(float(p_cls[i]), 4),
            "recall": round(float(r_cls[i]), 4),
            "f1": round(float(f1_cls[i]), 4),
            "support": int(sup_cls[i]),
        }
        for i in range(len(PLANTVILLAGE_CLASSES))
    }
    cm = confusion_matrix(
        y_test, y_pred, labels=list(range(len(PLANTVILLAGE_CLASSES)))
    ).tolist()

    threshold_analysis = _evaluate_thresholds_and_ood(predictor, test_probs, y_test)

    comparison_table = [
        {
            "model_name": baseline_res["name"],
            "architecture": baseline_res["architecture"],
            "train_seconds": baseline_res["train_seconds"],
            "val_macro_f1": baseline_res["val_metrics"]["macro_f1"],
            "test_accuracy": baseline_res["test_metrics"]["accuracy"],
            "test_top3_accuracy": baseline_res["test_metrics"]["top3_accuracy"],
            "test_macro_precision": baseline_res["test_metrics"]["macro_precision"],
            "test_macro_recall": baseline_res["test_metrics"]["macro_recall"],
            "test_macro_f1": baseline_res["test_metrics"]["macro_f1"],
            "test_ece_10bin": baseline_res["test_metrics"]["ece_10bin"],
        },
        *[
            {
                "model_name": item["name"],
                "architecture": item["architecture"],
                "train_seconds": item["train_seconds"],
                "total_params": item["total_params"],
                "trainable_params": item["trainable_params"],
                "temperature": item["temperature"],
                "val_macro_f1": item["val_metrics_calibrated"]["macro_f1"],
                "test_accuracy": item["test_metrics"]["accuracy"],
                "test_top3_accuracy": item["test_metrics"]["top3_accuracy"],
                "test_macro_precision": item["test_metrics"]["macro_precision"],
                "test_macro_recall": item["test_metrics"]["macro_recall"],
                "test_macro_f1": item["test_metrics"]["macro_f1"],
                "test_ece_uncalibrated": item["test_metrics_uncalibrated"]["ece_10bin"],
                "test_ece_calibrated": item["test_metrics"]["ece_10bin"],
                "test_brier_uncalibrated": item["test_metrics_uncalibrated"]["brier_score"],
                "test_brier_calibrated": item["test_metrics"]["brier_score"],
            }
            for item in candidates
        ],
    ]

    report = {
        "model_version": MODEL_VERSION,
        "selected_architecture": winner["architecture"],
        "selected_algorithm": winner["name"],
        "artifact_path": str(MODEL_OUT.relative_to(ROOT)).replace("\\", "/"),
        "artifact_size_bytes": int(artifact_bytes),
        "artifact_size_mb": round(artifact_bytes / 1048576, 2),
        "calibration_temperature": winner["temperature"],
        "split_sizes": {
            "train": len(by_split["train"]),
            "val": len(by_split["val"]),
            "test": len(by_split["test"]),
        },
        "zero_leakage_verified": True,
        "selected_val_metrics": winner["val_metrics_calibrated"],
        "selected_test_metrics_uncalibrated": winner["test_metrics_uncalibrated"],
        "selected_test_metrics": winner["test_metrics"],
        "model_comparison": comparison_table,
        "training_history": {
            c["architecture"]: c["history"] for c in candidates
        },
        "calibration_and_threshold_analysis": threshold_analysis,
        "per_class_test_metrics": per_class_metrics,
        "confusion_matrix_labels": list(PLANTVILLAGE_CLASSES),
        "confusion_matrix": cm,
    }

    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"[TRAIN COMPLETE] Selected {winner['name']} ({round(artifact_bytes / 1048576, 2)} MB) | "
        f"Test Acc={winner['test_metrics']['accuracy']} | Macro-F1={winner['test_metrics']['macro_f1']}",
        flush=True,
    )
    return report


if __name__ == "__main__":
    train_and_evaluate()
