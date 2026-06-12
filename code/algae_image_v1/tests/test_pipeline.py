"""Integration tests for the full detection pipeline."""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPolarizationSim:
    def test_output_shape(self):
        from core_engine.polarization_sim import simulate_polarization
        img = np.random.randint(0, 255, (128, 256, 3), dtype=np.uint8)
        result = simulate_polarization(img)
        assert result.shape == (4, 128, 256)
        assert result.dtype == np.float32

    def test_value_range(self):
        from core_engine.polarization_sim import simulate_polarization
        img = np.ones((64, 64, 3), dtype=np.uint8) * 128
        result = simulate_polarization(img)
        assert result.min() >= 0.0


class TestEnhancement:
    def test_stokes_output(self):
        from core_engine.enhancement import compute_stokes
        I = np.abs(np.random.randn(4, 64, 64).astype(np.float32)) * 0.5 + 0.5
        s = compute_stokes(I)
        for k in ['S0', 'S1', 'S2', 'DoLP', 'AoP']:
            assert k in s

    def test_enhance_shape_and_range(self):
        from core_engine.enhancement import enhance
        I = np.abs(np.random.randn(4, 64, 64).astype(np.float32)) * 0.5 + 0.5
        result = enhance(I)
        assert result.shape == (64, 64)
        assert result.min() >= 0 and result.max() <= 1.0


class TestInference:
    def test_load_model(self, yolo_model):
        from ultralytics import YOLO
        assert isinstance(yolo_model, YOLO)

    def test_detect_random_noise(self, yolo_model):
        from core_engine.inference import detect
        img = np.random.randint(0, 255, (320, 320), dtype=np.uint8)
        results = detect(yolo_model, img, conf=0.9)
        assert isinstance(results, list)

    def test_detection_structure(self, yolo_model):
        from core_engine.inference import detect
        img = np.random.randint(0, 255, (320, 320), dtype=np.uint8)
        results = detect(yolo_model, img, conf=0.9)
        for d in results:
            assert 'class_id' in d
            assert 'class_name' in d
            assert 'confidence' in d
            assert 'bbox' in d
            assert 'risk_level' in d
            assert len(d['bbox']) == 4


class TestQuality:
    def test_score_range(self):
        from core_engine.quality import compute_q_score
        I = np.abs(np.random.randn(4, 64, 64).astype(np.float32)) * 0.3 + 0.5
        q = compute_q_score(I)
        assert 0.0 <= q <= 1.0

    def test_quality_label(self):
        from core_engine.quality import quality_label
        assert quality_label(0.8) == "Good"
        assert quality_label(0.5) == "Fair"
        assert quality_label(0.2) == "Poor"


class TestConfig:
    def test_class_count(self):
        from core_engine.config import LIFEWATCH_95_CLASSES
        assert len(LIFEWATCH_95_CLASSES) == 95

    def test_risk_mapping(self):
        from core_engine.config import get_risk_level
        assert get_risk_level("Microcystis") == "high"
        assert get_risk_level("Unknown_X") == "low"

    def test_class_name_lookup(self):
        from core_engine.config import get_class_name
        assert get_class_name(38) == "Microcystis"
        assert get_class_name(999).startswith("Unknown")


class TestRDNReconstruction:
    def test_load_rdn(self, rdn_model):
        import torch.nn as nn
        assert isinstance(rdn_model, nn.Module)

    def test_reconstruct_shape(self, rdn_model):
        from core_engine.reconstructor import reconstruct
        I_noisy = np.abs(np.random.randn(4, 64, 64).astype(np.float32)) * 0.1 + 0.5
        I_clean = reconstruct(rdn_model, I_noisy, device="cpu")
        assert I_clean.shape == (4, 64, 64)
        assert I_clean.dtype == np.float32
