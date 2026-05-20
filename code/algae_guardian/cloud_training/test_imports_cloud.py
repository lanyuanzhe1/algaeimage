"""Test imports on cloud server. Run this directly on the cloud."""
import sys
sys.path.insert(0, '/data/algae_guardian')

try:
    from ml.reconstructor import RDN, PolarizationReconstructor
    print("OK: ml.reconstructor")
except Exception as e:
    print(f"FAIL: ml.reconstructor - {e}")

try:
    from image_processing.polarization_sim import simulate_polarization_channels
    print("OK: polarization_sim")
except Exception as e:
    print(f"FAIL: polarization_sim - {e}")

try:
    from image_processing.enhancement import ImageEnhancer
    print("OK: enhancement")
except Exception as e:
    print(f"FAIL: enhancement - {e}")

try:
    from image_processing.polarization import PolarizationProcessor
    print("OK: polarization")
except Exception as e:
    print(f"FAIL: polarization - {e}")

# Test RDN model loading
try:
    recon = PolarizationReconstructor(
        model_path='/data/rdn_training/checkpoint/best.pth',
        device='cpu'
    )
    ok = recon.load_model()
    print(f"OK: RDN model loaded={ok}")
except Exception as e:
    print(f"FAIL: RDN model load - {e}")

print("\nAll checks done.")
