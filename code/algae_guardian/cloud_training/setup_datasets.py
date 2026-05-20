"""Extract and organize downloaded datasets for training.

Usage:
    python setup_datasets.py

Expects:
    ./Flowcam_images_training_split_metadata.zip  (LifeWatch)
    ./FMPD_dataset.zip                            (FMPD)

Creates:
    ./datasets/
        lifewatch/
            images/train/  (class subdirectories or flat)
            images/val/
            images/test/
        fmpd/
            images/  (all + annotation JSON)
"""
import zipfile
import shutil
from pathlib import Path
import argparse


def extract_lifewatch(zip_path: str, out_dir: str):
    """Extract LifeWatch FlowCam dataset."""
    out = Path(out_dir) / "lifewatch"
    out.mkdir(parents=True, exist_ok=True)

    print(f"[LifeWatch] Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(str(out))
    print(f"[LifeWatch] Extracted to {out}/")

    # Show structure
    items = list(out.rglob("*"))[:20]
    for item in items:
        print(f"  {item.relative_to(out)}")
    if len(list(out.rglob("*"))) > 20:
        print(f"  ... and {len(list(out.rglob('*'))) - 20} more files")

    # Find image directories
    img_dirs = list(out.rglob("images")) + list(out.rglob("train"))
    if img_dirs:
        print(f"\n  Images found in: {img_dirs[0]}")
        train_imgs = list(Path(img_dirs[0]).rglob("*.png"))
        print(f"  Sample images: {len(train_imgs)} PNG files")


def extract_fmpd(zip_path: str, out_dir: str):
    """Extract FMPD dataset."""
    out = Path(out_dir) / "fmpd"
    out.mkdir(parents=True, exist_ok=True)

    print(f"\n[FMPD] Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(str(out))
    print(f"[FMPD] Extracted to {out}/")

    # Show structure
    items = list(out.rglob("*"))[:20]
    for item in items:
        print(f"  {item.relative_to(out)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lifewatch-zip", type=str,
                        default="./Flowcam_images_training_split_metadata.zip")
    parser.add_argument("--fmpd-zip", type=str,
                        default="./FMPD_dataset.zip")
    parser.add_argument("--output-dir", type=str, default="./datasets")
    args = parser.parse_args()

    print("=" * 50)
    print("  Dataset Setup")
    print("=" * 50)

    # Check files exist and are complete
    for name, path in [("LifeWatch", args.lifewatch_zip), ("FMPD", args.fmpd_zip)]:
        p = Path(path)
        if not p.exists():
            print(f"[{name}] {path} not found, skipping")
            continue
        size_mb = p.stat().st_size / (1024 * 1024)
        print(f"[{name}] {path}: {size_mb:.0f} MB")

    # Extract if files exist
    lifewatch_zip = Path(args.lifewatch_zip)
    fmpd_zip = Path(args.fmpd_zip)

    if lifewatch_zip.exists() and lifewatch_zip.stat().st_size > 500_000_000:
        extract_lifewatch(str(lifewatch_zip), args.output_dir)
    else:
        print(f"\n[LifeWatch] Zip incomplete ({lifewatch_zip.stat().st_size / 1e6:.0f} MB / ~582 MB), waiting for download...")

    if fmpd_zip.exists() and fmpd_zip.stat().st_size > 100_000_000:
        extract_fmpd(str(fmpd_zip), args.output_dir)
    else:
        print(f"\n[FMPD] Zip incomplete ({fmpd_zip.stat().st_size / 1e6:.0f} MB), waiting for download...")

    print("\nDone. Run again when downloads complete.")


if __name__ == "__main__":
    main()
