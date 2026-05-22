"""Full LifeWatch HSV pipeline: RGB -> HSV 4ch -> RDN -> I_enh v2 -> YOLO dataset.

Usage (on server):
    /data/miniconda/envs/torch/bin/python deploy/run_pipeline.py \
        --image-dir /data/lifewatch_hsv/images \
        --split-dir /data/lifewatch_hsv/splits \
        --rdn-model /data/lifewatch_hsv/rdn_training/rdn_hsv_lifewatch.pth \
        --output /data/lifewatch_hsv/processed \
        --splits train,val,test
"""

import argparse, os, sys, time
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, "/data/lifewatch_hsv/code")

import numpy as np
import cv2
from hsv_polarization import hsv_to_polarization
from image_processing.polarization import PolarizationProcessor
from image_processing.enhancement import ImageEnhancer
from ml.reconstructor import PolarizationReconstructor

ALPHA, BETA, GAMMA = 0.6, 0.25, 0.35
POL_STRENGTH, NOISE_LEVEL = 1.0, 0.02
OUTPUT_SIZE = 320


def _norm_u8(x):
    x = x.astype(np.float32)
    d = x.max() - x.min()
    return np.zeros_like(x, dtype=np.uint8) if d < 1e-10 else ((x - x.min()) / d * 255).astype(np.uint8)


def letterbox(img, target):
    h, w = img.shape[:2]
    s = target / max(h, w)
    nh, nw = int(h * s), int(w * s)
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    padded = np.zeros((target, target, img.shape[2]) if img.ndim == 3 else (target, target), dtype=img.dtype)
    padded[:nh, :nw] = resized
    return padded


def load_split(path):
    mapping = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.rsplit(" ", 1)
            if len(parts) != 2: continue
            stem = parts[0].replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
            mapping[stem] = int(parts[1])
    return mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", required=True)
    parser.add_argument("--split-dir", required=True)
    parser.add_argument("--rdn-model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--splits", default="train,val,test")
    args = parser.parse_args()

    IMAGE_DIR = Path(args.image_dir)
    SPLIT_DIR = Path(args.split_dir)
    OUTPUT = Path(args.output)
    SPLITS = [s.strip() for s in args.splits.split(",")]

    print(f"Loading RDN: {args.rdn_model}")
    recon = PolarizationReconstructor(model_path=args.rdn_model)
    use_rdn = recon.load_model()
    print(f"  RDN loaded: {use_rdn}")

    pp = PolarizationProcessor()
    enhancer = ImageEnhancer()

    for split_name in SPLITS:
        sf = SPLIT_DIR / f"{split_name}.txt"
        if not sf.exists():
            print(f"  SKIP {split_name}: not found")
            continue

        print(f"\n{'='*60}\nProcessing: {split_name}\n{'='*60}")
        stem_to_cls = load_split(str(sf))
        out_img = OUTPUT / split_name / "images"
        out_lbl = OUTPUT / split_name / "labels"
        out_img.mkdir(parents=True, exist_ok=True)
        out_lbl.mkdir(parents=True, exist_ok=True)

        done, miss = 0, 0
        t0 = time.time()

        for stem, cls_id in stem_to_cls.items():
            matches = list(IMAGE_DIR.rglob(f"{stem}.jpg"))
            if not matches:
                miss += 1
                if miss <= 3: print(f"  NOT FOUND: {stem}")
                continue

            try:
                rgb = cv2.cvtColor(cv2.imread(str(matches[0])), cv2.COLOR_BGR2RGB)
                if rgb is None:
                    miss += 1; continue

                sim = hsv_to_polarization(rgb, polarization_strength=POL_STRENGTH,
                                          add_noise=True, noise_level=NOISE_LEVEL)
                I0 = sim["I0"].astype(np.float32)
                I45 = sim["I45"].astype(np.float32)
                I90 = sim["I90"].astype(np.float32)
                I135 = sim["I135"].astype(np.float32)

                if use_rdn:
                    rdn_out = recon.reconstruct(I0, I45, I90, I135, use_deep=True)
                    I0_r = rdn_out[:, :, 0].astype(np.float32)
                    I45_r = rdn_out[:, :, 1].astype(np.float32)
                    I90_r = rdn_out[:, :, 2].astype(np.float32)
                    I135_r = rdn_out[:, :, 3].astype(np.float32)
                else:
                    I0_r, I45_r, I90_r, I135_r = I0, I45, I90, I135

                S0 = I0_r + I90_r
                S1 = I0_r - I90_r
                S2 = I45_r - I135_r
                DoLP = np.clip(np.sqrt(S1**2 + S2**2) / (S0 + 1e-10), 0, 1)
                AoP = 0.5 * np.arctan2(S2, S1)

                S0_ch = letterbox(_norm_u8(S0), OUTPUT_SIZE)
                enh_ch = letterbox(pp.polarization_enhancement_v2(S0, DoLP, AoP, alpha=ALPHA, beta=BETA, gamma=GAMMA), OUTPUT_SIZE)
                corrected_raw = S0 * (1.0 - 0.5 * DoLP.astype(np.float32))
                cor_ch = letterbox(_norm_u8(corrected_raw), OUTPUT_SIZE)

                stacked = np.stack([S0_ch, enh_ch, cor_ch], axis=-1)
                final = enhancer.enhance(stacked, color_correct=True, clahe=True, dehaze=False)
                cv2.imwrite(str(out_img / f"{stem}.jpg"),
                            cv2.cvtColor(final, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])

                with open(out_lbl / f"{stem}.txt", "w") as f:
                    f.write(f"{cls_id} 0.5 0.5 1.0 1.0\n")

                done += 1

                if done % 5000 == 0:
                    e = time.time() - t0
                    rate = done / max(e, 1)
                    eta = (len(stem_to_cls) - done) / max(rate, 0.01)
                    print(f"  [{split_name}] {done}/{len(stem_to_cls)} "
                          f"({100*done/len(stem_to_cls):.1f}%) {rate:.0f}/s ETA {eta/60:.0f}m")

            except Exception as ex:
                miss += 1
                if miss <= 3: print(f"  ERROR {stem}: {ex}")

        e = time.time() - t0
        print(f"  [{split_name}] DONE: {done} ok, {miss} miss, {e:.0f}s ({e/60:.1f}m)")

    # dataset.yaml
    cf = SPLIT_DIR / "classes.txt"
    class_names = []
    if cf.exists():
        with open(cf) as f:
            class_names = [l.strip() for l in f if l.strip()]

    yaml = f"""path: {args.output}
train: train/images
val: val/images
test: test/images
nc: {len(class_names)}
names: {class_names}
"""
    (OUTPUT / "dataset.yaml").write_text(yaml)
    print(f"\nDataset config: {OUTPUT / 'dataset.yaml'}")
    print("Pipeline complete!")


if __name__ == "__main__":
    main()
