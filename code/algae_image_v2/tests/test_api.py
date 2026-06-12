"""API tests for /detect/visualize endpoint.

Tests the HTTP contract — status codes, response structure, validation,
error propagation — with a mocked pipeline to avoid depending on cv2/torch.

TDD cycle: RED → GREEN → REFACTOR, one test at a time.
"""
import base64
import io
import os
import sys
from contextlib import asynccontextmanager, contextmanager

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ═══════════════════════════════════════════════════════════════════════════════
# Mock heavy native deps (cv2, numpy) BEFORE importing the app.
# routes.py does `import cv2` and `import numpy as np` at module level.
# ═══════════════════════════════════════════════════════════════════════════════
try:
    import cv2  # noqa: F401
except ImportError:
    import unittest.mock as _mock

    _fake_cv2 = _mock.MagicMock()
    _fake_cv2.IMREAD_COLOR = 1
    _fake_cv2.COLOR_BGR2RGB = 4
    _fake_cv2.imdecode.return_value = None
    _fake_cv2.cvtColor.return_value = None
    _fake_cv2.imwrite.return_value = True
    sys.modules["cv2"] = _fake_cv2

try:
    import numpy as np  # noqa: F401
except ImportError:
    import unittest.mock as _mock

    _fake_np = _mock.MagicMock()
    _fake_np.uint8 = int
    _fake_np.frombuffer.return_value = b""
    sys.modules["numpy"] = _fake_np


# ── Mini PNG (1×1 white pixel) for test uploads ──────────────────────────────
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)
_B64_IMG = f"data:image/png;base64,{base64.b64encode(_TINY_PNG).decode()}"

# ── Synthetic pipeline visualization result ───────────────────────────────────
_FAKE_STEPS = [
    {"title": "1. RGB原图", "image": _B64_IMG, "description": "明场显微图像 (64×64)"},
    {"title": "2. 偏振模拟", "image": _B64_IMG, "description": "HSV色彩空间法 → I0/I45/I90/I135 四通道"},
    {"title": "3. Stokes参数", "image": _B64_IMG, "description": "DoLP偏振度 + AoP偏振角 伪彩色图"},
    {"title": "4. I_enh v2增强", "image": _B64_IMG, "description": "去散射增强"},
    {"title": "5. 检测结果", "image": _B64_IMG, "description": "YOLOv8l 5类FMPD检测"},
]

_FAKE_DETECTIONS = [
    {
        "class_id": 0, "class_name": "Woronichinia", "class_name_zh": "沃氏藻",
        "confidence": 0.85, "bbox": [10.0, 20.0, 50.0, 60.0], "risk_level": "high",
    },
    {
        "class_id": 3, "class_name": "Other-phytoplankton", "class_name_zh": "其他浮游植物",
        "confidence": 0.62, "bbox": [80.0, 30.0, 120.0, 90.0], "risk_level": "medium",
    },
]

_FAKE_PIPELINE_RESULT = {
    "steps": _FAKE_STEPS,
    "detections": _FAKE_DETECTIONS,
    "q_score": 0.78,
    "processing_time_ms": 152.3,
}


class FakePipelineRunner:
    """Returns pre-canned visualization results without cv2/torch."""

    def run_with_visualization(self, filepath: str) -> dict:
        return _FAKE_PIPELINE_RESULT


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

_ENDPOINT = "/api/v1/detect/visualize"


def _upload_image(client, filename="algae.png", content_type="image/png"):
    """POST a valid tiny PNG to the visualize endpoint.  Returns the httpx Response."""
    return client.post(
        _ENDPOINT,
        files={"file": (filename, io.BytesIO(_TINY_PNG), content_type)},
    )


def _upload_non_image(client, filename="readme.txt", data=b"hello world",
                      content_type="text/plain"):
    """POST a non-image file to the visualize endpoint."""
    return client.post(
        _ENDPOINT,
        files={"file": (filename, io.BytesIO(data), content_type)},
    )


@contextmanager
def _with_pipeline_override(app, factory):
    """Temporarily override the get_pipeline dependency on *app*.

    Usage::
        with _with_pipeline_override(app, lambda: MyFake()):
            resp = client.post(...)
    """
    from backend.app.routes import get_pipeline

    original = app.dependency_overrides.get(get_pipeline)
    app.dependency_overrides[get_pipeline] = factory
    try:
        yield
    finally:
        if original is not None:
            app.dependency_overrides[get_pipeline] = original
        else:
            app.dependency_overrides.pop(get_pipeline, None)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixture
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def client(tmp_path):
    """TestClient with overridden lifespan, pipeline, and database.

    Skips model loading (no torch/cv2).  Uses a temp-dir SQLite so tests
    don't pollute the real history database.
    """
    from backend.app.main import app
    from backend.app.routes import get_pipeline, get_db

    # --- Override lifespan: skip torch / YOLO loading ---
    @asynccontextmanager
    async def _test_lifespan(app_):
        from backend.app.database import init_db

        _redirect_config_paths(tmp_path)
        await init_db()
        yield

    app.router.lifespan_context = _test_lifespan

    # --- Override pipeline dependency ---
    app.dependency_overrides[get_pipeline] = lambda: FakePipelineRunner()

    # --- Override DB dependency: use isolated temp SQLite ---
    import backend.app.config as _cfg

    async def _test_get_db():
        import aiosqlite

        db = await aiosqlite.connect(_cfg.DB_PATH)
        db.row_factory = aiosqlite.Row
        return db

    app.dependency_overrides[get_db] = _test_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


def _redirect_config_paths(tmp_path):
    """Point UPLOAD_DIR / RESULT_DIR / DB_PATH into *tmp_path* for isolation."""
    import backend.app.config as cfg
    import backend.app.routes as routes_mod

    data = tmp_path / "data"
    uploads = data / "uploads"
    results = data / "results"
    uploads.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)

    cfg.UPLOAD_DIR = routes_mod.UPLOAD_DIR = str(uploads)
    cfg.RESULT_DIR = routes_mod.RESULT_DIR = str(results)
    cfg.DATA_DIR = str(data)
    cfg.DB_PATH = str(data / "history.db")


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Happy path
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectVisualizeHappyPath:
    """Valid upload → 200 with complete VizDetectResponse."""

    def test_returns_200_with_all_top_level_fields(self, client):
        """Upload a tiny PNG and verify the response envelope is correct."""
        resp = _upload_image(client)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()

        for field in ("id", "filename", "steps", "detections",
                      "q_score", "risk_level", "processing_time_ms"):
            assert field in body, f"Response missing '{field}'"

        assert isinstance(body["steps"], list)
        assert isinstance(body["detections"], list)
        assert isinstance(body["q_score"], float)
        assert body["risk_level"] in ("high", "medium", "low", None)
        assert isinstance(body["processing_time_ms"], float)

    def test_steps_have_correct_format_and_data_uris(self, client):
        """Each pipeline step must carry title, image (data URI), description."""
        body = _upload_image(client).json()
        steps = body["steps"]

        assert len(steps) == 5, f"Expected 5 steps, got {len(steps)}"

        for i, step in enumerate(steps):
            for key in ("title", "image", "description"):
                assert key in step, f"Step {i} missing '{key}'"
            assert isinstance(step["title"], str) and len(step["title"]) > 0
            assert isinstance(step["description"], str) and len(step["description"]) > 0

            # Image must be a valid data URI: data:image/png;base64,<payload>
            img = step["image"]
            assert img.startswith("data:image/"), f"Step {i}: not a data URI"
            assert ";base64," in img, f"Step {i}: not base64-encoded"
            payload = img.split(";base64,", 1)[1]
            try:
                decoded = base64.b64decode(payload)
                assert len(decoded) > 0, f"Step {i}: empty image payload"
            except Exception as exc:
                pytest.fail(f"Step {i}: invalid base64 — {exc}")

    def test_detections_have_required_fields(self, client):
        """Every detection item must carry class_id, class_name, confidence, bbox, risk_level."""
        detections = _upload_image(client).json()["detections"]

        assert len(detections) > 0, "Expected at least one detection"
        for i, det in enumerate(detections):
            for key in ("class_id", "class_name", "class_name_zh",
                        "confidence", "bbox", "risk_level"):
                assert key in det, f"Detection {i} missing '{key}'"
            assert isinstance(det["confidence"], (int, float))
            assert 0.0 <= det["confidence"] <= 1.0
            assert len(det["bbox"]) == 4
            assert det["risk_level"] in ("high", "medium", "low")


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Error handling
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectVisualizeErrors:
    """Input validation, dependency errors, and pipeline failures."""

    def test_non_image_file_returns_400(self, client):
        """Uploading a text file (not an image) must yield 400."""
        resp = _upload_non_image(client)
        assert resp.status_code == 400
        assert "image" in resp.json()["detail"].lower()

    def test_no_content_type_returns_400(self, client):
        """Uploading a file without content_type is treated as non-image."""
        resp = client.post(
            _ENDPOINT,
            files={"file": ("data.bin", io.BytesIO(b"\x00\x01\x02"))},
        )
        assert resp.status_code == 400

    def test_pipeline_not_loaded_returns_503(self, client):
        """When get_pipeline raises 503, the endpoint must propagate it."""
        from backend.app.main import app

        def _fail_with_503():
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Models not loaded yet")

        with _with_pipeline_override(app, _fail_with_503):
            resp = _upload_image(client)
        assert resp.status_code == 503
        assert "not loaded" in resp.json()["detail"].lower()

    def test_pipeline_exception_returns_500(self, client):
        """When the pipeline raises an unexpected error, the endpoint returns 500."""
        from backend.app.main import app

        class _CrashingPipeline:
            def run_with_visualization(self, filepath: str) -> dict:
                raise RuntimeError("Simulated GPU OOM")

        with _with_pipeline_override(app, lambda: _CrashingPipeline()):
            resp = _upload_image(client)
        assert resp.status_code == 500
        assert "pipeline" in resp.json()["detail"].lower()
