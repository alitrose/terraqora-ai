import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_structure_exists():
    expected_paths = [
        ROOT / "README.md",
        ROOT / ".gitignore",
        ROOT / ".env.example",
        ROOT / "requirements.txt",
        ROOT / "frontend" / "design-tokens.json",
        ROOT / "frontend" / "public" / "terraqora-logo.svg",
        ROOT / "frontend" / "public" / "terraqora-mark.svg",
        ROOT / "frontend" / "public" / "favicon.svg",
        ROOT / "database" / "schema.sql",
        ROOT / "database" / "ER_DIAGRAM.md",
        ROOT / "docs" / "ARCHITECTURE.md",
        ROOT / "docs" / "BRAND_GUIDELINES.md",
        ROOT / "docs" / "GIT_WORKFLOW.md",
        ROOT / "docs" / "ROADMAP.md",
        ROOT / "docs" / "DEPLOYMENT_PLAN.md",
        ROOT / "ml" / "datasets" / "DATASETS.md",
        ROOT / "ml" / "datasets" / "raw" / "crop_yield.csv",
        ROOT / "ml" / "datasets" / "raw" / "Crop_recommendation.csv",
    ]
    for path in expected_paths:
        assert path.exists(), f"Missing expected Phase 2 path: {path}"


def test_no_exposed_secrets_in_repository():
    secret_patterns = [
        re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),
        re.compile(r"AQ\.Ab8[0-9A-Za-z\-_]{15,}"),
        re.compile(r"sk-[0-9A-Za-z]{20,}"),
        re.compile(r"3Ehbl3[0-9A-Za-z_]{15,}"),
    ]
    import os

    skip_dirs = {".git", "node_modules", "dist", ".venv", "__pycache__", ".pytest_cache"}
    skip_suffixes = {
        ".csv",
        ".parquet",
        ".part",
        ".pt",
        ".pth",
        ".joblib",
        ".pkl",
        ".keras",
        ".h5",
        ".tflite",
        ".onnx",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".pdf",
    }
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            file_path = Path(dirpath) / fname
            if file_path.suffix.lower() in skip_suffixes:
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for pat in secret_patterns:
                assert not pat.search(text), f"Potential secret found in {file_path}"


def test_env_example_and_gitignore():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in [".env", "*.pkl", "*.keras", "node_modules/"]:
        assert pattern in gitignore

    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in [
        "DATABASE_URL=",
        "JWT_SECRET_KEY=",
        "GEMINI_API_KEY=",
        "CORS_ORIGINS=",
        "VITE_API_BASE_URL=",
    ]:
        assert key in env_example


def test_preserved_datasets_checksums():
    def sha256(p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    crop_yield = ROOT / "ml" / "datasets" / "raw" / "crop_yield.csv"
    crop_rec = ROOT / "ml" / "datasets" / "raw" / "Crop_recommendation.csv"
    assert sha256(crop_yield) == "ab9bc356b1f8107d490376cec24450a0e2906322ad25788ab22fb32537ab1f8f"
    assert sha256(crop_rec) == "54a5a6e5408668e668667efc50de2fc867c1b875e0431b4f54dd331b0a109a4e"


def test_brand_assets_and_tokens_valid():
    tokens = json.loads((ROOT / "frontend" / "design-tokens.json").read_text(encoding="utf-8"))
    assert tokens["brand"]["name"] == "TerraQora AI"
    assert tokens["brand"]["tagline"] == "Intelligence for Every Acre."
    assert tokens["colors"]["forestDeep"] == "#123524"
    assert tokens["colors"]["harvestGold"] == "#C9972C"

    for svg_name in ["terraqora-logo.svg", "terraqora-mark.svg", "favicon.svg"]:
        svg_path = ROOT / "frontend" / "public" / svg_name
        tree = ET.parse(svg_path)
        assert tree.getroot().tag.endswith("svg")


def test_database_schema_contains_all_tables_and_constraints():
    ddl = (ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
    required_tables = [
        "users",
        "farmer_profiles",
        "farms",
        "crop_predictions",
        "disease_detections",
        "fertilizer_recommendations",
        "irrigation_recommendations",
        "crop_recommendations",
        "chat_sessions",
        "chat_messages",
        "generated_reports",
    ]
    for tbl in required_tables:
        assert f"CREATE TABLE IF NOT EXISTS {tbl}" in ddl, f"Missing table {tbl}"
    assert "REFERENCES users(id) ON DELETE CASCADE" in ddl
    assert "is_sensor_backed BOOLEAN NOT NULL DEFAULT FALSE" in ddl
    assert "CREATE INDEX" in ddl
