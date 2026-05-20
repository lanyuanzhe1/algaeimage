"""Prepare train.h5 and eval.h5 from .mat files.

Usage: python prepare_h5.py --data-dir /path/to/data
"""
import argparse
import glob
import os
import h5py
import numpy as np
from scipy.io import loadmat


def prepare(data_dir, patch_size=64, stride=32):
    for h5_name, noise_subdir, truth_subdir in [
        ("train.h5", "noise", "truth"),
        ("eval.h5", "eval_noise", "eval_truth"),
    ]:
        noise_dir = os.path.join(data_dir, noise_subdir)
        truth_dir = os.path.join(data_dir, truth_subdir)

        noise_files = sorted(glob.glob(os.path.join(noise_dir, "*.mat")))
        truth_files = sorted(glob.glob(os.path.join(truth_dir, "*.mat")))

        if not noise_files:
            print(f"  [SKIP] {noise_dir} empty")
            continue

        h5_path = os.path.join(data_dir, h5_name)
        print(f"Creating {h5_path} from {len(noise_files)} pairs...")

        with h5py.File(h5_path, "w") as f:
            lr_group = f.create_group("lr")
            hr_group = f.create_group("hr")
            patch_idx = 0

            for nf, tf in zip(noise_files, truth_files):
                try:
                    lr = loadmat(nf)["Norm_photon"]
                    hr = loadmat(tf)["Norm_photon"]
                except NotImplementedError:
                    with h5py.File(nf, "r") as nfh:
                        lr = np.array(nfh["Norm_photon"]).T
                    with h5py.File(tf, "r") as tfh:
                        hr = np.array(tfh["Norm_photon"]).T

                h, w = lr.shape[:2]
                for x in range(0, h - patch_size + 1, stride):
                    for y in range(0, w - patch_size + 1, stride):
                        lr_group.create_dataset(
                            str(patch_idx), data=lr[x : x + patch_size, y : y + patch_size]
                        )
                        hr_group.create_dataset(
                            str(patch_idx), data=hr[x : x + patch_size, y : y + patch_size]
                        )
                        patch_idx += 1

            print(f"  {h5_name}: {patch_idx} patches")
        print(f"  Size: {os.path.getsize(h5_path) / 1e6:.0f} MB")

    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="/data/rdn_training")
    parser.add_argument("--patch-size", type=int, default=64)
    parser.add_argument("--stride", type=int, default=32)
    args = parser.parse_args()
    prepare(args.data_dir, args.patch_size, args.stride)
