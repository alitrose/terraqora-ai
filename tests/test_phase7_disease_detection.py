from __future__ import annotations

import io
import json
import os
from pathlib import Path
import secrets
import sys
import uuid

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
import pytest
from sqlalchemy.orm import Session, sessionmaker
import torch

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"

from ai.chatbot.providers import ChatTurn, LLMProvider, LLMResponse  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.session import build_engine, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.modules import DiseaseDetection  # noqa: E402
from app.services import chat_service, disease_service  # noqa: E402
from ml.preprocessing.disease_features import PLANTVILLAGE_CLASSES  # noqa: E402
from ml.preprocessing.disease_model import (  # noqa: E402
    PlantDiseasePredictor,
    build_vision_backbone,
)


def _make_alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture()
def isolated_disease_client(tmp_path: Path):
    db_file = tmp_path / "phase7_disease_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    get_settings.cache_clear()
    disease_service.reset_cache()
    chat_service.set_provider_factory_for_testing(None)
    command.upgrade(_make_alembic_config(db_url), "head")

    engine = build_engine(db_url)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    app = create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, TestingSessionLocal, tmp_path
    disease_service.reset_cache()
    chat_service.set_provider_factory_for_testing(None)


def _register_farmer(client: TestClient, email: str) -> tuple[dict[str, str], str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Disease Test Farmer",
            "email": email,
            "password": "StrongPassword!123",
            "preferred_language": "en",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["id"]


def _make_textured_leaf_png(size: tuple[int, int] = (160, 160)) -> bytes:
    rng = np.random.default_rng(77)
    arr = rng.integers(30, 190, (size[1], size[0], 3), dtype=np.uint8)
    # Give a realistic green central leaf region
    arr[25:-25, 35:-35, 1] = np.clip(arr[25:-25, 35:-35, 1] + 55, 0, 255)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def _write_test_checkpoint(path: Path, *, confident_class_idx: int | None = 29, bias_margin: float = 8.0) -> None:
    model = build_vision_backbone("mobilenet_v3_small", num_classes=len(PLANTVILLAGE_CLASSES), pretrained=False)
    with torch.no_grad():
        for p in model.classifier[-1].parameters():
            p.zero_()
        if confident_class_idx is not None:
            model.classifier[-1].bias[confident_class_idx] = bias_margin
    payload = {
        "architecture": "mobilenet_v3_small",
        "class_names": list(PLANTVILLAGE_CLASSES),
        "temperature": 1.0,
        "image_size": 224,
        "model_version": "test-vision-v1",
        "state_dict": model.state_dict(),
    }
    torch.save(payload, path)


def test_disease_upload_validation_and_missing_corrupt_artifact_503(isolated_disease_client):
    client, _, tmp_path = isolated_disease_client
    headers, _ = _register_farmer(client, "imgval@example.com")

    # Unauthenticated rejected
    assert client.get("/api/v1/disease/history").status_code == 401

    # Unsupported MIME type rejected
    bad_txt = client.post(
        "/api/v1/disease/detect",
        headers=headers,
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert bad_txt.status_code == 415

    # MIME spoofing (PNG bytes sent with image/jpeg Content-Type) rejected
    png_bytes = _make_textured_leaf_png()
    spoof = client.post(
        "/api/v1/disease/detect",
        headers=headers,
        files={"file": ("leaf.jpg", png_bytes, "image/jpeg")},
    )
    assert spoof.status_code == 422

    # Corrupted JPEG bytes rejected cleanly
    corrupt = client.post(
        "/api/v1/disease/detect",
        headers=headers,
        files={"file": ("broken.jpg", b"\xff\xd8\xff\xe0corrupt_data", "image/jpeg")},
    )
    assert corrupt.status_code == 422

    # Tiny <32x32 image rejected cleanly
    tiny_buf = io.BytesIO()
    Image.new("RGB", (16, 16), color=(60, 140, 60)).save(tiny_buf, format="PNG")
    tiny = client.post(
        "/api/v1/disease/detect",
        headers=headers,
        files={"file": ("tiny.png", tiny_buf.getvalue(), "image/png")},
    )
    assert tiny.status_code == 422

    # Oversized (> 5 MB) payload rejected with 413
    oversized = client.post(
        "/api/v1/disease/detect",
        headers=headers,
        files={"file": ("huge.png", b"0" * (5 * 1024 * 1024 + 128), "image/png")},
    )
    assert oversized.status_code == 413

    # Missing .pt checkpoint returns safe 503
    disease_service.set_paths_for_testing(model_path=tmp_path / "missing.pt")
    res_missing = client.post(
        "/api/v1/disease/detect",
        headers=headers,
        files={"file": ("leaf.png", png_bytes, "image/png")},
        data={"crop_hint": "Tomato"},
    )
    assert res_missing.status_code == 503
    assert "unavailable" in res_missing.json()["detail"].lower()

    # Corrupt .pt checkpoint returns safe 503
    corrupt_ckpt = tmp_path / "corrupt.pt"
    corrupt_ckpt.write_bytes(b"corrupt_checkpoint_bytes")
    disease_service.set_paths_for_testing(model_path=corrupt_ckpt)
    res_corrupt_ckpt = client.post(
        "/api/v1/disease/detect",
        headers=headers,
        files={"file": ("leaf.png", png_bytes, "image/png")},
        data={"crop_hint": "Tomato"},
    )
    assert res_corrupt_ckpt.status_code == 503


def test_disease_inference_abstention_farm_linking_and_history(isolated_disease_client):
    client, SessionLocal, tmp_path = isolated_disease_client
    headers_a, user_a_id = _register_farmer(client, "leafa@example.com")
    headers_b, _ = _register_farmer(client, "leafb@example.com")

    ckpt_path = tmp_path / "valid_test_vision.pt"
    # Class 29 = Tomato___Early_blight
    _write_test_checkpoint(ckpt_path, confident_class_idx=29, bias_margin=9.0)
    disease_service.set_paths_for_testing(model_path=ckpt_path)

    farm_a_id = client.post(
        "/api/v1/farms",
        headers=headers_a,
        json={
            "name": "Salem Tomato Block",
            "state": "Tamil Nadu",
            "district": "Salem",
            "area_hectares": 1.5,
            "soil_type": "Red Loamy",
            "soil_ph": 6.5,
            "irrigation_type": "drip",
            "primary_crop": "Tomato",
        },
    ).json()["id"]

    leaf_png = _make_textured_leaf_png()

    # 1. Cross-user farm link rejected with 403
    forbidden = client.post(
        "/api/v1/disease/detect",
        headers=headers_b,
        files={"file": ("leaf.png", leaf_png, "image/png")},
        data={"crop_hint": "Tomato", "farm_id": farm_a_id},
    )
    assert forbidden.status_code == 403

    # 2. Confident valid prediction stored in DB
    ok = client.post(
        "/api/v1/disease/detect",
        headers=headers_a,
        files={"file": ("tomato_leaf.png", leaf_png, "image/png")},
        data={"crop_hint": "Tomato", "farm_id": farm_a_id},
    )
    assert ok.status_code == 200, ok.text
    d_ok = ok.json()
    assert d_ok["predicted_label"] == "Tomato___Early_blight"
    assert d_ok["crop_name"] == "Tomato"
    assert d_ok["is_uncertain"] is False
    assert d_ok["confidence"] > 0.65
    assert len(d_ok["top_predictions"]) == 3
    assert "kg/ha" not in d_ok["treatment_summary"].lower()
    assert "ml/l" not in d_ok["treatment_summary"].lower()

    # 3. Blank uniform frame abstains cleanly even when logits prefer a class
    blank_buf = io.BytesIO()
    Image.new("RGB", (180, 180), color=(246, 246, 246)).save(blank_buf, format="PNG")
    blank_res = client.post(
        "/api/v1/disease/detect",
        headers=headers_a,
        files={"file": ("blank.png", blank_buf.getvalue(), "image/png")},
        data={"crop_hint": "Tomato"},
    )
    assert blank_res.status_code == 200
    assert blank_res.json()["is_uncertain"] is True
    assert "blank" in blank_res.json()["uncertainty_reason"].lower()

    # 4. Unsupported crop (Rice) triggers explicit out-of-scope abstention
    rice_res = client.post(
        "/api/v1/disease/detect",
        headers=headers_a,
        files={"file": ("paddy.png", leaf_png, "image/png")},
        data={"crop_hint": "Rice"},
    )
    assert rice_res.status_code == 200
    assert rice_res.json()["is_uncertain"] is True
    assert rice_res.json()["predicted_label"] == "Uncertain___Out_Of_Scope_Crop"
    assert "outside the trained PlantVillage" in rice_res.json()["uncertainty_reason"]

    # 5. Ambiguous / near-uniform logits (confidence < 0.65) triggers uncertain warning
    ambig_ckpt = tmp_path / "ambig_vision.pt"
    _write_test_checkpoint(ambig_ckpt, confident_class_idx=None)
    disease_service.set_paths_for_testing(model_path=ambig_ckpt)
    ambig_res = client.post(
        "/api/v1/disease/detect",
        headers=headers_a,
        files={"file": ("ambig.png", leaf_png, "image/png")},
        data={"crop_hint": "Tomato"},
    )
    assert ambig_res.status_code == 200
    assert ambig_res.json()["is_uncertain"] is True
    assert ambig_res.json()["confidence"] < 0.65

    # 6. History shows user A scans only
    hist_a = client.get("/api/v1/disease/history", headers=headers_a).json()
    hist_b = client.get("/api/v1/disease/history", headers=headers_b).json()
    assert len(hist_a) == 4
    assert hist_b == []

    with SessionLocal() as db:
        rows = db.query(DiseaseDetection).filter(DiseaseDetection.user_id == uuid.UUID(user_a_id)).all()
        assert len(rows) == 4


def test_genai_assistant_includes_disease_scan_and_respects_uncertainty(isolated_disease_client):
    client, SessionLocal, _ = isolated_disease_client
    captured: list[str] = []

    class CaptureProvider(LLMProvider):
        provider_name = "gemini"
        model_name = "gemini-2.5-flash"

        def generate(
            self,
            *,
            system_prompt: str,
            history: list[ChatTurn],
            user_message: str,
            temperature: float = 0.35,
            max_output_tokens: int = 1024,
        ) -> LLMResponse:
            _ = history, user_message, temperature, max_output_tokens
            captured.append(system_prompt)
            return LLMResponse(
                text="[TerraQora ML] Vision screening is uncertain — retake a clear daylight leaf photo and verify with KVK.",
                provider=self.provider_name,
                model_name=self.model_name,
                latency_ms=19,
            )

    chat_service.set_provider_factory_for_testing(lambda _s: CaptureProvider())
    headers, uid = _register_farmer(client, "genaidis@example.com")

    with SessionLocal() as db:
        db.add(
            DiseaseDetection(
                user_id=uuid.UUID(uid),
                crop_hint="Rice",
                image_filename="paddy_spot.jpg",
                image_mime_type="image/jpeg",
                image_size_bytes=2048,
                image_sha256="a" * 64,
                predicted_label="Uncertain___Out_Of_Scope_Crop",
                confidence=0.41,
                is_uncertain=True,
                top_predictions_json=[],
                treatment_summary="Abstained; consult KVK.",
                prevention_notes="Capture clear daylight photo.",
                model_version="phase7-vision-v1.0.0",
            )
        )
        db.commit()

    sid = client.post("/api/v1/chat/sessions", headers=headers, json={"language": "en"}).json()["id"]
    turn = client.post(
        f"/api/v1/chat/sessions/{sid}/messages",
        headers=headers,
        json={"content": "What should I spray for this leaf scan?", "language": "en"},
    )
    assert turn.status_code == 200
    assert len(captured) == 1
    assert "UNCERTAIN (DO NOT treat as confirmed diagnosis" in captured[0]
    assert "Uncertain___Out_Of_Scope_Crop" in captured[0]


def test_real_trained_disease_pipeline_zero_leakage_and_artifacts_when_present():
    audit_path = ROOT / "ml" / "evaluation" / "disease_audit.json"
    metrics_path = ROOT / "ml" / "evaluation" / "disease_metrics.json"
    model_path = ROOT / "ml" / "saved_models" / "plant_disease_model.pt"

    if not (audit_path.exists() and metrics_path.exists() and model_path.exists()):
        pytest.skip("PlantVillage training artifacts not yet generated on disk.")

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["license"] == "cc0-1.0"
    assert audit["integrity_summary"]["num_classes"] == 38
    assert audit["integrity_summary"]["corrupt_or_unreadable_images"] == 0
    split_sum = audit["deduplicated_split_summary"]
    assert split_sum["train_val_sha256_overlap"] == 0
    assert split_sum["train_test_sha256_overlap"] == 0
    assert split_sum["val_test_sha256_overlap"] == 0
    assert split_sum["train_val_dhash_overlap"] == 0
    assert split_sum["train_test_dhash_overlap"] == 0
    assert split_sum["val_test_dhash_overlap"] == 0

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["zero_leakage_verified"] is True
    assert len(metrics["model_comparison"]) >= 3
    assert metrics["selected_test_metrics"]["accuracy"] >= 0.85
    assert metrics["selected_test_metrics"]["macro_f1"] >= 0.80

    # Verify trained checkpoint reloads with weights_only=True
    predictor = PlantDiseasePredictor.from_checkpoint(model_path)
    assert len(predictor.class_names) == 38
