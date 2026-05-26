"""Shared test fixtures."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def rdn_model():
    from core_engine.reconstructor import load_rdn_model
    weights = os.path.join(os.path.dirname(__file__), "..", "weights", "rdn_polarization.pth")
    return load_rdn_model(weights, device="cpu")


@pytest.fixture(scope="session")
def yolo_model():
    from core_engine.inference import load_yolo
    weights = os.path.join(os.path.dirname(__file__), "..", "weights", "best.pt")
    return load_yolo(weights, device="cpu")
