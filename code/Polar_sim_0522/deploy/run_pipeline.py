"""Full LifeWatch HSV pipeline with batched RDN inference for GPU throughput.

Usage: PYTHONUNBUFFERED=1 python deploy/run_pipeline.py \
    --image-dir /data/lifewatch_hsv/images \
    --split-dir /data/lifewatch_hsv/splits \
    --rdn-model /data/lifewatch_hsv/rdn_training/rdn_hsv_lifewatch.pth \
    --output /data/lifewatch_hsv/processed --splits train,val,test \
    --batch-size 128
"""

import argparse, os, sys, time
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, "/data/lifewatch_hsv/code")

import numpy as np
import cv2
import torch
from hsv_polarization import hsv_to_polarization
from image_processing.polarization import PolarizationProcessor
from image_processing.enhancement import ImageEnhancer
from ml.reconstructor import RDN

ALPHA, BETA, GAMMA = 0.6, 0.25, 0.35
POL_STRENGTH, NOISE_LEVEL = 1.0, 0.02
OUTPUT_SIZE = 320


def _norm_u8(x):
    x = x.astype(np.float32)
    d = x.max() - x.min()
    return np.zeros_like(x, dtype=np.uint8) if d < 1e-10 else ((x - x.min()) / d * 255).astype(np.uint8)


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


PATCH_SIZE = 128  # fixed input size for batched RDN inference

def pad_to_square(img_hw, target):
    """Fit (C,H,W) array into target×target: resize if needed, then zero-pad.
    Returns (padded_array, new_h, new_w)."""
    c, h, w = img_hw.shape
    if max(h, w) > target:
        scale = target / max(h, w)
        h, w = int(h * scale), int(w * scale)
        img_hw = np.array([cv2.resize(ch, (w, h), interpolation=cv2.INTER_LINEAR) for ch in img_hw])
    out = np.zeros((c, target, target), dtype=img_hw.dtype)
    out[:, :h, :w] = img_hw
    return out, h, w

def prepare_batch(batch_stems, stem_to_path, device):
    """HSV sim on CPU -> batched tensors for RDN at fixed PATCH_SIZE.
    Returns (batch_tensor, orig_sizes_list)."""
    inputs = []
    orig_sizes = []
    for stem in batch_stems:
        img = cv2.imread(str(stem_to_path[stem]))
        if img is None:
            raise ValueError(f"Failed to read: {stem}")
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        sim = hsv_to_polarization(rgb, polarization_strength=POL_STRENGTH,
                                  add_noise=True, noise_level=NOISE_LEVEL)
        ch = np.stack([sim[k].astype(np.float32)/255.0 for k in ['I0','I45','I90','I135']], axis=0)
        ch, nh, nw = pad_to_square(ch, PATCH_SIZE)
        orig_sizes.append((nh, nw))
        inputs.append(ch)

    batch = torch.from_numpy(np.stack(inputs, axis=0)).to(device)
    return batch, orig_sizes


def process_batch_outputs(batch_tensor, orig_sizes, pp, enhancer):
    """RDN output -> crop to orig size -> I_enh v2 -> letterbox -> CLAHE on CPU."""
    outs = []
    batch_np = batch_tensor.cpu().numpy()
    for i in range(batch_np.shape[0]):
        oh, ow = orig_sizes[i]
        rdn_out = batch_np[i, :, :oh, :ow]  # crop padded region

        I0 = rdn_out[0]
        I45 = rdn_out[1]
        I90 = rdn_out[2]
        I135 = rdn_out[3]

        S0 = I0 + I90
        S1 = I0 - I90
        S2 = I45 - I135
        DoLP = np.clip(np.sqrt(S1**2+S2**2)/(S0+1e-10), 0, 1)
        AoP = 0.5 * np.arctan2(S2, S1)

        S0_ch = _norm_u8(S0)
        enh_ch = pp.polarization_enhancement_v2(S0, DoLP, AoP, alpha=ALPHA, beta=BETA, gamma=GAMMA)
        corrected_raw = S0 * (1.0 - 0.5 * DoLP.astype(np.float32))
        cor_ch = _norm_u8(corrected_raw)

        # Letterbox to OUTPUT_SIZE
        h, w = S0_ch.shape[:2]
        s = OUTPUT_SIZE / max(h, w)
        nh, nw = int(h*s), int(w*s)
        S0_lb = np.zeros((OUTPUT_SIZE, OUTPUT_SIZE), dtype=np.uint8)
        enh_lb = np.zeros((OUTPUT_SIZE, OUTPUT_SIZE), dtype=np.uint8)
        cor_lb = np.zeros((OUTPUT_SIZE, OUTPUT_SIZE), dtype=np.uint8)
        S0_lb[:nh,:nw] = cv2.resize(S0_ch, (nw,nh), interpolation=cv2.INTER_LINEAR)
        enh_lb[:nh,:nw] = cv2.resize(enh_ch, (nw,nh), interpolation=cv2.INTER_LINEAR)
        cor_lb[:nh,:nw] = cv2.resize(cor_ch, (nw,nh), interpolation=cv2.INTER_LINEAR)

        stacked = np.stack([S0_lb, enh_lb, cor_lb], axis=-1)
        final = enhancer.enhance(stacked, color_correct=True, clahe=True, dehaze=False)
        outs.append(final)
    return outs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", required=True)
    parser.add_argument("--split-dir", required=True)
    parser.add_argument("--rdn-model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--splits", default="train,val,test")
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    IMAGE_DIR = Path(args.image_dir)
    OUTPUT = Path(args.output)
    SPLITS = [s.strip() for s in args.splits.split(",")]
    B = args.batch_size
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {DEVICE}, Batch size: {B}")

    # Load RDN directly (raw float output, no joint-norm)
    model = RDN(num_channels=4, num_features=16, growth_rate=16,
                num_blocks=12, num_layers=6).to(DEVICE)
    sd = torch.load(args.rdn_model, map_location=DEVICE, weights_only=True)
    model.load_state_dict({k:v for k,v in sd.items() if k in model.state_dict().keys()}, strict=False)
    model.eval()
    print(f"RDN loaded: {args.rdn_model}")

    pp = PolarizationProcessor()
    enhancer = ImageEnhancer()

    for split_name in SPLITS:
        sf = Path(args.split_dir) / f"{split_name}.txt"
        if not sf.exists():
            print(f"  SKIP {split_name}: not found")
            continue

        print(f"\n{'='*60}\nProcessing: {split_name}\n{'='*60}")
        stem_to_cls = load_split(str(sf))
        out_img = OUTPUT / split_name / "images"
        out_lbl = OUTPUT / split_name / "labels"
        out_img.mkdir(parents=True, exist_ok=True)
        out_lbl.mkdir(parents=True, exist_ok=True)

        # Pre-build stem->path index
        print("  Building file index...")
        stem_to_path = {}
        for img_path in IMAGE_DIR.rglob("*.jpg"):
            stem_to_path[img_path.stem] = img_path
        print(f"  Indexed {len(stem_to_path)} images")

        stems = list(stem_to_cls.keys())
        done, miss, t0 = 0, 0, time.time()

        # Process in batches
        for start in range(0, len(stems), B):
            batch_stems = [s for s in stems[start:start+B] if s in stem_to_path]
            if not batch_stems:
                continue

            # 1. HSV simulation (CPU) -> padded batched tensors
            try:
                batch_in, orig_sizes = prepare_batch(batch_stems, stem_to_path, DEVICE)
            except Exception as e:
                print(f"  ERROR prepare_batch: {e}")
                miss += len(batch_stems)
                continue

            # 2. RDN inference (GPU batched)
            with torch.no_grad():
                batch_out = model(batch_in)

            # 3. Crop back + I_enh + CLAHE (CPU)
            try:
                finals = process_batch_outputs(batch_out, orig_sizes, pp, enhancer)
            except Exception as e:
                print(f"  ERROR in post-process: {e}")
                for s in batch_stems:
                    miss += 1
                continue

            # 4. Save
            for stem, final in zip(batch_stems, finals):
                cls_id = stem_to_cls[stem]
                cv2.imwrite(str(out_img / f"{stem}.jpg"),
                            cv2.cvtColor(final, cv2.COLOR_RGB2BGR),
                            [cv2.IMWRITE_JPEG_QUALITY, 92])
                with open(out_lbl / f"{stem}.txt", "w") as f:
                    f.write(f"{cls_id} 0.5 0.5 1.0 1.0\n")
                done += 1

            if done % (B * 5) == 0 or done == len(batch_stems):
                e = time.time() - t0
                rate = done / max(e, 1)
                eta = (len(stems) - done) / max(rate, 0.01)
                print(f"  [{split_name}] {done}/{len(stems)} "
                      f"({100*done/len(stems):.1f}%) {rate:.0f}/s ETA {eta/60:.0f}m")

        e = time.time() - t0
        print(f"  [{split_name}] DONE: {done} ok, {miss} miss, {e:.0f}s ({e/60:.1f}m)")

    # dataset.yaml
    cf = Path(args.split_dir) / "classes.txt"
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
