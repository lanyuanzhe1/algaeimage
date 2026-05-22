"""Master orchestrator — run on server after upload.

Usage:
    export PYTHONPATH=/data/lifewatch_hsv/code
    /data/miniconda/envs/torch/bin/python deploy/run_all.py

Stages:
    1. RDN small-sample training (~1-2h)
    2. Full pipeline: HSV -> RDN -> I_enh -> YOLO dataset (~3-5h)
    3. YOLOv8l 95-class training (~40-60h on V100)
"""

import subprocess, sys, os
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PYTHONPATH"] = "/data/lifewatch_hsv/code"

BASE = Path("/data/lifewatch_hsv")
CODE = BASE / "code"
PYTHON = "/data/miniconda/envs/torch/bin/python"

STAGES = [
    {
        "name": "RDN Training (3k samples, 100 epochs)",
        "cmd": (
            f"{PYTHON} {CODE}/ml/train_rdn.py "
            f"--image-dir {BASE}/images "
            f"--split-file {BASE}/splits/train.txt "
            f"--output {BASE}/rdn_training/rdn_hsv_lifewatch.pth "
            f"--num-samples 3000 --epochs 100 --batch 32 --lr 1e-4"
        ),
        "check": f"{BASE}/rdn_training/rdn_hsv_lifewatch.pth",
    },
    {
        "name": "Full Pipeline (HSV -> RDN -> I_enh -> 337k images)",
        "cmd": (
            f"{PYTHON} {CODE}/deploy/run_pipeline.py "
            f"--image-dir {BASE}/images "
            f"--split-dir {BASE}/splits "
            f"--rdn-model {BASE}/rdn_training/rdn_hsv_lifewatch.pth "
            f"--output {BASE}/processed "
            f"--splits train,val,test"
        ),
        "check": f"{BASE}/processed/dataset.yaml",
    },
    {
        "name": "YOLOv8l 95-class Training (300 epochs)",
        "cmd": (
            f"{PYTHON} {CODE}/deploy/train_yolo.py "
            f"--data {BASE}/processed/dataset.yaml "
            f"--output {BASE}/yolo_results/v8l_hsv_95 "
            f"--epochs 300 --batch 128 --imgsz 320"
        ),
        "check": f"{BASE}/yolo_results/v8l_hsv_95/weights/best.pt",
    },
]


def main():
    print("=" * 70)
    print("  LifeWatch HSV Full Pipeline")
    print(f"  GPU: Tesla V100-SXM2-32GB | 95 classes | 302,972 train")
    print("=" * 70)

    for i, stage in enumerate(STAGES, 1):
        name, cmd, check = stage["name"], stage["cmd"], stage["check"]

        print(f"\n{'='*70}")
        print(f"  Stage {i}/{len(STAGES)}: {name}")
        print(f"{'='*70}")
        print(f"  CMD: {cmd}")

        if Path(check).exists():
            print(f"  SKIP (already done: {check})")
            continue

        sys.stdout.flush()
        result = subprocess.run(cmd, shell=True, cwd=str(CODE))
        if result.returncode != 0:
            print(f"\n  FAILED with exit code {result.returncode}")
            sys.exit(1)

        if not Path(check).exists():
            print(f"\n  FAILED: output not found: {check}")
            sys.exit(1)

        print(f"\n  Stage {i}: {name} -- DONE")

    print(f"\n{'='*70}")
    print("  ALL STAGES COMPLETE")
    print(f"{'='*70}")
    print(f"  RDN:    {BASE}/rdn_training/rdn_hsv_lifewatch.pth")
    print(f"  Dataset: {BASE}/processed/dataset.yaml")
    print(f"  YOLO:   {BASE}/yolo_results/v8l_hsv_95/weights/best.pt")


if __name__ == "__main__":
    main()
