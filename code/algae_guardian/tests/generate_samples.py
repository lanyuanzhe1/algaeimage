"""Generate synthetic test sample images for the algae detection pipeline."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import cv2


def create_sample(save_path, width=640, height=480, algae_list=None,
                  bg_brightness=200, noise_level=5, blur=False, label=""):
    """Create a synthetic algae microscopy image."""
    img = np.ones((height, width, 3), dtype=np.uint8) * bg_brightness

    for algae in (algae_list or []):
        cx, cy = algae.get("pos", (np.random.randint(50, width-50),
                                   np.random.randint(50, height-50)))
        r = algae.get("radius", 12)
        color = algae.get("color", (50, 120, 50))
        thickness = algae.get("thickness", -1)
        cv2.circle(img, (cx, cy), r, color, thickness)

        # Inner detail for realism
        if r > 8:
            inner_color = tuple(min(c+30, 255) for c in color)
            cv2.circle(img, (cx-2, cy-2), r//2, inner_color, 1)

    # Add noise
    if noise_level > 0:
        noise = np.random.randn(*img.shape).astype(np.uint8) * noise_level
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Blur
    if blur:
        img = cv2.GaussianBlur(img, (5, 5), 2)

    cv2.imwrite(save_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return img


def main():
    samples_dir = Path(__file__).parent / "samples"
    samples_dir.mkdir(exist_ok=True)

    # Clear existing
    for f in samples_dir.glob("*.png"):
        f.unlink()

    # ── 1. Normal sample: mix of algae species ──
    create_sample(
        str(samples_dir / "01_normal_mix.png"),
        label="Normal mix",
        algae_list=[
            {"pos": (120, 200), "radius": 18, "color": (40, 100, 30)},   # Spherical brown
            {"pos": (300, 150), "radius": 8, "color": (60, 140, 60)},    # Small green
            {"pos": (500, 250), "radius": 22, "color": (30, 80, 50)},    # Large colony
            {"pos": (200, 350), "radius": 12, "color": (50, 110, 40)},
            {"pos": (400, 380), "radius": 10, "color": (70, 130, 55)},
            {"pos": (550, 100), "radius": 14, "color": (45, 105, 35)},
        ],
        noise_level=3,
    )
    print("  01_normal_mix.png - 正常混合藻类样本")

    # ── 2. Dense bloom: high concentration ──
    algae_dense = []
    for i in range(35):
        algae_dense.append({
            "pos": (np.random.randint(30, 610), np.random.randint(30, 450)),
            "radius": np.random.randint(5, 20),
            "color": (np.random.randint(20, 60), np.random.randint(80, 140),
                      np.random.randint(30, 70)),
        })
    create_sample(
        str(samples_dir / "02_dense_bloom.png"),
        label="Dense bloom",
        algae_list=algae_dense,
        noise_level=4,
    )
    print("  02_dense_bloom.png - 高浓度藻华样本")

    # ── 3. Clear water: near-zero algae ──
    create_sample(
        str(samples_dir / "03_clear_water.png"),
        label="Clear water",
        algae_list=[
            {"pos": (320, 240), "radius": 6, "color": (80, 150, 80)},
        ],
        noise_level=2,
    )
    print("  03_clear_water.png - 清水对照样本")

    # ── 4. Turbid water: high noise + algae ──
    create_sample(
        str(samples_dir / "04_turbid_water.png"),
        label="Turbid water",
        algae_list=[
            {"pos": (150, 180), "radius": 16, "color": (30, 70, 40)},
            {"pos": (350, 300), "radius": 20, "color": (40, 90, 50)},
            {"pos": (500, 150), "radius": 10, "color": (50, 100, 45)},
            {"pos": (250, 400), "radius": 14, "color": (35, 80, 40)},
        ],
        bg_brightness=180,
        noise_level=20,
        blur=True,
    )
    print("  04_turbid_water.png - 浑浊水体样本（高噪声+模糊）")

    # ── 5. Toxic algae: high-risk species ──
    create_sample(
        str(samples_dir / "05_toxic_bloom.png"),
        label="Toxic bloom",
        algae_list=[
            {"pos": (90, 100), "radius": 22, "color": (20, 60, 30), "thickness": 2},
            {"pos": (90, 100), "radius": 18, "color": (25, 70, 35)},
            {"pos": (250, 150), "radius": 25, "color": (15, 50, 25), "thickness": 2},
            {"pos": (250, 150), "radius": 20, "color": (20, 60, 30)},
            {"pos": (400, 200), "radius": 16, "color": (30, 80, 40)},
            {"pos": (180, 350), "radius": 14, "color": (25, 65, 35)},
            {"pos": (520, 350), "radius": 19, "color": (20, 55, 30)},
        ],
        noise_level=3,
    )
    print("  05_toxic_bloom.png - 高风险/毒性藻类样本")

    # ── 6. Simulated DoFP raw polarization frame ──
    h, w = 480, 640
    raw_dofp = np.ones((h, w), dtype=np.uint8) * 180
    # Draw algae circles
    for _ in range(6):
        cx, cy = np.random.randint(50, w-50), np.random.randint(50, h-50)
        r = np.random.randint(10, 25)
        # Vary intensity based on simulated polarization response
        for y in range(max(0, cy-r), min(h, cy+r)):
            for x in range(max(0, cx-r), min(w, cx+r)):
                if (x-cx)**2 + (y-cy)**2 <= r**2:
                    # Simulate DoFP pattern modulation
                    pattern_val = ((x % 2) * 30 + (y % 2) * 20)
                    raw_dofp[y, x] = np.clip(int(raw_dofp[y, x]) + pattern_val, 0, 255).astype(np.uint8)
    noise = np.random.randn(h, w).astype(np.int16) * 5
    raw_dofp = np.clip(raw_dofp.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    cv2.imwrite(str(samples_dir / "06_polarization_raw.png"), raw_dofp)
    print("  06_polarization_raw.png - 模拟偏振原始帧")

    # ── 7. Quality issues: blurry + overexposed ──
    bad_img = np.ones((480, 640, 3), dtype=np.uint8) * 240
    algae_bad = [
        {"pos": (200, 200), "radius": 15, "color": (80, 160, 80)},
        {"pos": (400, 300), "radius": 20, "color": (60, 130, 60)},
    ]
    for a in algae_bad:
        cv2.circle(bad_img, a["pos"], a["radius"], a["color"], -1)
    bad_img = cv2.GaussianBlur(bad_img, (15, 15), 8)
    cv2.imwrite(str(samples_dir / "07_quality_issues.png"),
                cv2.cvtColor(bad_img, cv2.COLOR_RGB2BGR))
    print("  07_quality_issues.png - 质量不合格样本（模糊+过曝）")

    print(f"\n  → 共 7 个样本生成于: {samples_dir}")


if __name__ == "__main__":
    main()
