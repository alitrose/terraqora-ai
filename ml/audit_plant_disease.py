"""Phase 7 Part A — PlantVillage Dataset Download, Integrity & Leakage Audit, and Leak-Free Split Builder.

Downloads the public-domain (CC0-1.0) PlantVillage parquet distribution from HuggingFace
with HTTP Range resume, decodes and validates every image, detects exact SHA-256 and
64-bit perceptual dHash duplicate clusters across all files, documents class imbalance
and scope limitations, and generates a strictly zero-leakage grouped stratified
Train / Validation / Test index (`ml/datasets/processed/disease_splits.parquet`).
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.preprocessing.disease_features import (  # noqa: E402
    PLANTVILLAGE_CLASSES,
    SUPPORTED_SPECIES_CANONICAL,
    UNSUPPORTED_COMMON_CROPS,
    compute_dhash_hex,
)

DATASET_REPO = "BrandonFors/Plant-Diseases-PlantVillage-Dataset"
DATASET_LICENSE = "cc0-1.0"
DATASET_CITATIONS = (
    "Hughes & Salathe (2015), 'An open access repository of images on plant health to enable the "
    "development of mobile disease diagnostics', arXiv:1511.08060; distributed via HuggingFace "
    f"dataset '{DATASET_REPO}' ({DATASET_LICENSE})."
)

PARQUET_FILES: tuple[tuple[str, str], ...] = (
    ("test", "data/test-00000-of-00001.parquet"),
    ("train", "data/train-00000-of-00002.parquet"),
    ("train", "data/train-00001-of-00002.parquet"),
)

RAW_DIR = ROOT / "ml" / "datasets" / "plantvillage"
PROCESSED_SPLITS = ROOT / "ml" / "datasets" / "processed" / "disease_splits.parquet"
AUDIT_OUT = ROOT / "ml" / "evaluation" / "disease_audit.json"

MAX_GROUPS_PER_CLASS_TRAIN = 120
MAX_GROUPS_PER_CLASS_VAL = 30
MAX_GROUPS_PER_CLASS_TEST = 45
SPLIT_SEED = 20261112


def _fetch_remote_sizes() -> dict[str, int]:
    url = f"https://huggingface.co/api/datasets/{DATASET_REPO}/tree/main/data"
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        items = resp.json()
    return {str(item["path"]): int(item["size"]) for item in items}


def download_parquet_files(force: bool = False) -> list[tuple[str, Path]]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    remote_sizes = _fetch_remote_sizes()
    local_paths: list[tuple[str, Path]] = []

    for split_tag, rel_path in PARQUET_FILES:
        expected_size = remote_sizes[rel_path]
        filename = Path(rel_path).name
        final_path = RAW_DIR / filename
        part_path = RAW_DIR / f"{filename}.part"

        if not force and final_path.exists() and final_path.stat().st_size == expected_size:
            print(f"[SKIP] {filename} already verified ({expected_size / 1048576:.1f} MB)", flush=True)
            local_paths.append((split_tag, final_path))
            continue

        url = f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/main/{rel_path}"
        max_attempts = 40
        for attempt in range(1, max_attempts + 1):
            downloaded = part_path.stat().st_size if part_path.exists() else 0
            if downloaded >= expected_size:
                if downloaded == expected_size:
                    part_path.replace(final_path)
                    break
                part_path.unlink(missing_ok=True)
                downloaded = 0

            headers = {"Range": f"bytes={downloaded}-"} if downloaded > 0 else {}
            print(
                f"[DL] {filename} attempt {attempt}/{max_attempts} resuming from "
                f"{downloaded / 1048576:.1f}/{expected_size / 1048576:.1f} MB",
                flush=True,
            )
            try:
                timeout = httpx.Timeout(connect=20.0, read=60.0, write=30.0, pool=20.0)
                with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                    with client.stream("GET", url, headers=headers) as resp:
                        if resp.status_code == 200 and downloaded > 0:
                            # Server ignored Range; restart clean
                            downloaded = 0
                            mode = "wb"
                        elif resp.status_code in (200, 206):
                            mode = "ab" if downloaded > 0 else "wb"
                        else:
                            resp.raise_for_status()
                            mode = "wb"

                        last_log_bytes = downloaded
                        with part_path.open(mode) as f:
                            for chunk in resp.iter_bytes(chunk_size=131072):
                                if not chunk:
                                    continue
                                f.write(chunk)
                                downloaded += len(chunk)
                                if downloaded - last_log_bytes >= 15 * 1048576:
                                    pct = 100.0 * downloaded / expected_size
                                    print(
                                        f"     {filename}: {downloaded / 1048576:.1f} / "
                                        f"{expected_size / 1048576:.1f} MB ({pct:.1f}%)",
                                        flush=True,
                                    )
                                    last_log_bytes = downloaded

                if part_path.exists() and part_path.stat().st_size == expected_size:
                    part_path.replace(final_path)
                    print(f"[DONE] {filename} verified ({expected_size / 1048576:.1f} MB)", flush=True)
                    break
            except Exception as exc:
                print(f"[RETRY] {filename} attempt {attempt} interrupted: {exc}", flush=True)
                time.sleep(min(10, attempt * 1.5))
        else:
            raise RuntimeError(f"Failed to download {filename} after {max_attempts} attempts.")

        local_paths.append((split_tag, final_path))

    return local_paths


def _extract_image_bytes(cell: Any) -> bytes:
    if isinstance(cell, dict):
        raw = cell.get("bytes")
        if isinstance(raw, (bytes, bytearray, memoryview)):
            return bytes(raw)
    if isinstance(cell, (bytes, bytearray, memoryview)):
        return bytes(cell)
    raise ValueError("Missing image byte buffer in parquet cell.")


def run_audit(force_download: bool = False) -> dict[str, Any]:
    local_files = download_parquet_files(force=force_download)

    records: list[dict[str, Any]] = []
    corrupt_count = 0
    widths: list[int] = []
    heights: list[int] = []
    modes: Counter[str] = Counter()
    formats: Counter[str] = Counter()
    upstream_sha_by_split: dict[str, set[str]] = defaultdict(set)
    upstream_dhash_by_split: dict[str, set[str]] = defaultdict(set)
    sha_to_labels: dict[str, set[int]] = defaultdict(set)
    dhash_to_labels: dict[str, set[int]] = defaultdict(set)

    start_ts = time.time()
    for split_tag, ppath in local_files:
        pf = pq.ParquetFile(ppath)
        rel_file = ppath.name
        global_row = 0
        print(f"[AUDIT] Scanning {rel_file} ({pf.metadata.num_rows} rows)...", flush=True)

        for batch in pf.iter_batches(batch_size=512, columns=["image", "label"]):
            img_col = batch.column("image").to_pylist()
            lbl_col = batch.column("label").to_pylist()
            for img_cell, label_idx in zip(img_col, lbl_col):
                try:
                    raw_bytes = _extract_image_bytes(img_cell)
                    sha256 = hashlib.sha256(raw_bytes).hexdigest()
                    with Image.open(io.BytesIO(raw_bytes)) as img:
                        img_fmt = str(img.format or "UNKNOWN")
                        img_mode = str(img.mode)
                        w, h = img.size
                        rgb = img.convert("RGB")
                        dhash_hex = compute_dhash_hex(rgb)
                except (UnidentifiedImageError, OSError, ValueError):
                    corrupt_count += 1
                    global_row += 1
                    continue

                label_id = int(label_idx)
                label_name = PLANTVILLAGE_CLASSES[label_id]
                widths.append(w)
                heights.append(h)
                modes[img_mode] += 1
                formats[img_fmt] += 1
                upstream_sha_by_split[split_tag].add(sha256)
                upstream_dhash_by_split[split_tag].add(dhash_hex)
                sha_to_labels[sha256].add(label_id)
                dhash_to_labels[dhash_hex].add(label_id)

                records.append(
                    {
                        "source_file": rel_file,
                        "upstream_split": split_tag,
                        "row_index": global_row,
                        "label_id": label_id,
                        "label_name": label_name,
                        "sha256": sha256,
                        "dhash_hex": dhash_hex,
                        "width": w,
                        "height": h,
                    }
                )
                global_row += 1

        print(f"        Scanned {rel_file} in {time.time() - start_ts:.1f}s total.", flush=True)

    total_valid = len(records)
    sha_counts = Counter(r["sha256"] for r in records)
    dhash_counts = Counter(r["dhash_hex"] for r in records)

    exact_duplicate_rows = sum(c - 1 for c in sha_counts.values() if c > 1)
    near_duplicate_rows = sum(c - 1 for c in dhash_counts.values() if c > 1)
    cross_split_exact_overlap = len(upstream_sha_by_split["train"] & upstream_sha_by_split["test"])
    cross_split_dhash_overlap = len(upstream_dhash_by_split["train"] & upstream_dhash_by_split["test"])
    cross_class_exact_collisions = sum(1 for lbls in sha_to_labels.values() if len(lbls) > 1)
    cross_class_dhash_collisions = sum(1 for lbls in dhash_to_labels.values() if len(lbls) > 1)

    class_counts_raw = Counter(r["label_name"] for r in records)
    sorted_class_counts = {lbl: int(class_counts_raw.get(lbl, 0)) for lbl in PLANTVILLAGE_CLASSES}

    # Build deduplicated representative pool keyed by (label_id, dhash_hex) -> 1 clean canonical sample
    # while linking every row to group_id = f"{label_id}:{dhash_hex}" (ensuring conflicting cross-label hashes are also isolated).
    # First exclude any hash colliding across distinct classes from entering modeling splits to keep evaluation clean.
    conflicting_dhashes = {dh for dh, lbls in dhash_to_labels.items() if len(lbls) > 1}
    rng = np.random.default_rng(SPLIT_SEED)

    # Group non-conflicting unique dhash groups per label_id
    by_label_dhash: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for rec in records:
        dh = rec["dhash_hex"]
        if dh in conflicting_dhashes:
            continue
        lid = rec["label_id"]
        if dh not in by_label_dhash[lid]:
            by_label_dhash[lid][dh] = rec

    # Assign each unique dhash globally to train / val / test BEFORE capping per-class so ZERO dhash overlap
    # can ever happen even across classes or unused pool
    all_unique_dhashes = sorted({dh for m in by_label_dhash.values() for dh in m.keys()})
    rng.shuffle(all_unique_dhashes)

    # Map each class's unique dhash groups strictly proportionally: 65% train / 15% val / 20% test
    assigned_splits: list[dict[str, Any]] = []
    split_class_counts: dict[str, Counter[str]] = {
        "train": Counter(),
        "val": Counter(),
        "test": Counter(),
    }
    pool_class_counts: Counter[str] = Counter()

    for lid, label_name in enumerate(PLANTVILLAGE_CLASSES):
        dhash_map = by_label_dhash[lid]
        unique_keys = sorted(dhash_map.keys())
        pool_class_counts[label_name] = len(unique_keys)
        idx = np.arange(len(unique_keys))
        rng.shuffle(idx)

        n_total = len(unique_keys)
        n_test = max(12, int(round(0.20 * n_total)))
        n_val = max(10, int(round(0.15 * n_total)))
        if n_test + n_val >= n_total - 20:
            n_test = max(5, int(0.20 * n_total))
            n_val = max(5, int(0.15 * n_total))
        n_train = n_total - n_test - n_val

        train_keys = [unique_keys[i] for i in idx[:n_train]]
        val_keys = [unique_keys[i] for i in idx[n_train : n_train + n_val]]
        test_keys = [unique_keys[i] for i in idx[n_train + n_val :]]

        # Cap balanced per-class counts cleanly on train/val/test to prevent Orange/Soybean domination
        # while retaining every split leakage guarantee
        selected_train = train_keys[:MAX_GROUPS_PER_CLASS_TRAIN]
        selected_val = val_keys[:MAX_GROUPS_PER_CLASS_VAL]
        selected_test = test_keys[:MAX_GROUPS_PER_CLASS_TEST]

        for split_name, key_list in (
            ("train", selected_train),
            ("val", selected_val),
            ("test", selected_test),
        ):
            for dh in key_list:
                rec = dhash_map[dh]
                assigned_splits.append(
                    {
                        "source_file": rec["source_file"],
                        "row_index": rec["row_index"],
                        "label_id": rec["label_id"],
                        "label_name": rec["label_name"],
                        "sha256": rec["sha256"],
                        "dhash_hex": rec["dhash_hex"],
                        "split": split_name,
                    }
                )
                split_class_counts[split_name][label_name] += 1

    # Verify strict zero-leakage invariant across splits
    split_shas: dict[str, set[str]] = defaultdict(set)
    split_dhashes: dict[str, set[str]] = defaultdict(set)
    for item in assigned_splits:
        split_shas[item["split"]].add(item["sha256"])
        split_dhashes[item["split"]].add(item["dhash_hex"])

    assert not (split_shas["train"] & split_shas["val"]), "SHA leakage train/val!"
    assert not (split_shas["train"] & split_shas["test"]), "SHA leakage train/test!"
    assert not (split_shas["val"] & split_shas["test"]), "SHA leakage val/test!"
    assert not (split_dhashes["train"] & split_dhashes["val"]), "dHash leakage train/val!"
    assert not (split_dhashes["train"] & split_dhashes["test"]), "dHash leakage train/test!"
    assert not (split_dhashes["val"] & split_dhashes["test"]), "dHash leakage val/test!"

    PROCESSED_SPLITS.parent.mkdir(parents=True, exist_ok=True)
    split_table = pa.Table.from_pylist(assigned_splits)
    pq.write_table(split_table, PROCESSED_SPLITS)

    min_raw = min(sorted_class_counts.values())
    max_raw = max(sorted_class_counts.values())

    audit_report = {
        "dataset_repo": DATASET_REPO,
        "license": DATASET_LICENSE,
        "citation": DATASET_CITATIONS,
        "parquet_files": [
            {
                "upstream_split": split_tag,
                "filename": ppath.name,
                "size_bytes": ppath.stat().st_size,
                "size_mb": round(ppath.stat().st_size / 1048576, 2),
            }
            for split_tag, ppath in local_files
        ],
        "integrity_summary": {
            "total_decoded_valid_images": total_valid,
            "corrupt_or_unreadable_images": corrupt_count,
            "num_classes": len(PLANTVILLAGE_CLASSES),
            "num_supported_crop_species": len(SUPPORTED_SPECIES_CANONICAL),
            "supported_crop_species": list(SUPPORTED_SPECIES_CANONICAL),
            "unsupported_major_crops_examples": list(UNSUPPORTED_COMMON_CROPS),
            "image_formats": dict(formats),
            "image_modes": dict(modes),
            "width_px": {
                "min": int(min(widths)),
                "median": int(np.median(widths)),
                "max": int(max(widths)),
            },
            "height_px": {
                "min": int(min(heights)),
                "median": int(np.median(heights)),
                "max": int(max(heights)),
            },
        },
        "duplicate_and_leakage_audit": {
            "unique_sha256_count": len(sha_counts),
            "exact_sha256_duplicate_images": int(exact_duplicate_rows),
            "unique_dhash_count": len(dhash_counts),
            "near_duplicate_dhash_images": int(near_duplicate_rows),
            "upstream_train_vs_test_sha256_overlap": int(cross_split_exact_overlap),
            "upstream_train_vs_test_dhash_overlap": int(cross_split_dhash_overlap),
            "cross_class_sha256_collisions": int(cross_class_exact_collisions),
            "cross_class_dhash_collisions": int(cross_class_dhash_collisions),
            "mitigation_applied": (
                "Excluded cross-class hash collisions, collapsed near-duplicate perceptual dHash groups, "
                "and rebuilt grouped stratified train/val/test splits with 0% SHA-256 and 0% dHash overlap."
            ),
        },
        "class_distribution_raw": {
            "min_images_per_class": int(min_raw),
            "max_images_per_class": int(max_raw),
            "imbalance_ratio": round(float(max_raw / max(1, min_raw)), 2),
            "counts": sorted_class_counts,
        },
        "deduplicated_split_summary": {
            "splits_manifest_path": str(PROCESSED_SPLITS.relative_to(ROOT)).replace("\\", "/"),
            "split_seed": SPLIT_SEED,
            "total_curated_images": len(assigned_splits),
            "train_count": int(sum(split_class_counts["train"].values())),
            "val_count": int(sum(split_class_counts["val"].values())),
            "test_count": int(sum(split_class_counts["test"].values())),
            "train_val_sha256_overlap": 0,
            "train_test_sha256_overlap": 0,
            "val_test_sha256_overlap": 0,
            "train_val_dhash_overlap": 0,
            "train_test_dhash_overlap": 0,
            "val_test_dhash_overlap": 0,
            "per_class_pool_unique_dhash_counts": dict(pool_class_counts),
            "per_class_split_counts": {
                lbl: {
                    "train": int(split_class_counts["train"][lbl]),
                    "val": int(split_class_counts["val"][lbl]),
                    "test": int(split_class_counts["test"][lbl]),
                }
                for lbl in PLANTVILLAGE_CLASSES
            },
        },
        "documented_limitations": [
            "PlantVillage covers 38 classes across 14 temperate/horticultural species only; major field crops such as Rice, Wheat, Cotton, Sugarcane, Coconut, and Banana are NOT represented.",
            "Original PlantVillage images were captured mainly on uniform grey/dark laboratory backgrounds (segmented leaves), creating a domain gap when users upload cluttered live field canopy photos.",
            "Visual leaf spots cannot definitively prove nutrient deficiency vs abiotic stress vs fungal/viral infection without KVK or lab verification.",
            "Upstream split contained exact/near-duplicate leaves; evaluation strictly uses our deduplicated grouped splits to prevent inflated accuracy.",
        ],
    }

    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_OUT.write_text(json.dumps(audit_report, indent=2), encoding="utf-8")
    print(f"[AUDIT COMPLETE] Report written to {AUDIT_OUT}")
    print(
        f"Summary: total={total_valid}, corrupt={corrupt_count}, "
        f"exact_dups={exact_duplicate_rows}, near_dups={near_duplicate_rows}, "
        f"upstream_leak(sha/dhash)={cross_split_exact_overlap}/{cross_split_dhash_overlap}, "
        f"curated_splits={len(assigned_splits)} "
        f"(train={audit_report['deduplicated_split_summary']['train_count']}, "
        f"val={audit_report['deduplicated_split_summary']['val_count']}, "
        f"test={audit_report['deduplicated_split_summary']['test_count']})"
    )
    return audit_report


if __name__ == "__main__":
    run_audit()
