"""Cloud training script for RDN polarization reconstruction network.

Wraps SPDRDN training pipeline with our data generation for one-command cloud training.

Usage:
    python train_rdn_cloud.py --data-dir ./data/rdn_training --epochs 100

This is the script that runs on the GPU cloud server.
It does NOT require the full algae_guardian project - just PyTorch + data.
"""
import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Train RDN on cloud GPU")
    parser.add_argument("--data-dir", type=str, default="./data/rdn_training",
                        help="Directory containing noise/ and truth/ with .mat files")
    parser.add_argument("--output-dir", type=str, default="./checkpoint",
                        help="Where to save model checkpoints")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--patch-size", type=int, default=64)
    parser.add_argument("--num-features", type=int, default=32)
    parser.add_argument("--growth-rate", type=int, default=32)
    parser.add_argument("--num-blocks", type=int, default=12)
    parser.add_argument("--num-layers", type=int, default=6)
    parser.add_argument("--l1-weight", type=float, default=1.0)
    parser.add_argument("--aop-weight", type=float, default=0.1,
                        help="AoP loss weight helps polarization quality")
    args = parser.parse_args()

    # ── Step 1: Prepare h5 files ──
    # If SPDRDN prepare.py is available, use it
    sprdn_prepare = Path("prepare.py")
    if sprdn_prepare.exists():
        print("[Step 1] Using SPDRDN prepare.py to create h5 dataset...")
        noise_dir = os.path.join(args.data_dir, "noise")
        truth_dir = os.path.join(args.data_dir, "truth")
        os.system(f"python prepare.py --input-dir {noise_dir} --label-dir {truth_dir} "
                  f"--output-path ./data/train.h5 "
                  f"--patch-size {args.patch_size} --stride {args.patch_size // 2}")
        train_file = "./data/train.h5"
        eval_file = "./data/train.h5"
    else:
        print("[Step 1] SPDRDN prepare.py not found, using built-in preparation...")
        train_file, eval_file = _builtin_prepare(args.data_dir, args.patch_size)

    # ── Step 2: Start training ──
    print(f"\n[Step 2] Starting RDN training for {args.epochs} epochs...")
    print(f"  Model: RDN(features={args.num_features}, growth={args.growth_rate}, "
          f"blocks={args.num_blocks}, layers={args.num_layers})")
    print(f"  Data:  {train_file}")
    print(f"  Loss:  L1_weight={args.l1_weight}, AoP_weight={args.aop_weight}")
    print(f"  Batch: {args.batch_size}, LR={args.lr}")
    print(f"  Output:{args.output_dir}")
    print("=" * 60)

    _train_rdn(
        train_file=train_file,
        eval_file=eval_file,
        output_dir=args.output_dir,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        num_features=args.num_features,
        growth_rate=args.growth_rate,
        num_blocks=args.num_blocks,
        num_layers=args.num_layers,
        l1_weight=args.l1_weight,
        aop_weight=args.aop_weight,
    )


def _builtin_prepare(data_dir: str, patch_size: int):
    """Built-in data preparation if SPDRDN prepare.py not available."""
    import glob
    import h5py
    import numpy as np
    from scipy.io import loadmat

    os.makedirs("./data", exist_ok=True)

    noise_files = sorted(glob.glob(os.path.join(data_dir, "noise", "*.mat")))
    truth_files = sorted(glob.glob(os.path.join(data_dir, "truth", "*.mat")))

    stride = patch_size // 2

    for h5_path, file_pairs in [("data/train.h5", list(zip(noise_files[:-100], truth_files[:-100]))),
                                  ("data/eval.h5", list(zip(noise_files[-100:], truth_files[-100:])))]:
        with h5py.File(h5_path, 'w') as f:
            lr_group = f.create_group('lr')
            hr_group = f.create_group('hr')
            patch_idx = 0

            for noise_path, truth_path in file_pairs:
                try:
                    noise_data = loadmat(noise_path)
                    truth_data = loadmat(truth_path)
                except NotImplementedError:
                    with h5py.File(noise_path, 'r') as nf:
                        noise_data = {'Norm_photon': np.array(nf['Norm_photon']).T}
                    with h5py.File(truth_path, 'r') as tf:
                        truth_data = {'Norm_photon': np.array(tf['Norm_photon']).T}

                lr = noise_data['Norm_photon']
                hr = truth_data['Norm_photon']

                h, w = lr.shape[:2]
                for x in range(0, h - patch_size + 1, stride):
                    for y in range(0, w - patch_size + 1, stride):
                        lr_group.create_dataset(str(patch_idx), data=lr[x:x + patch_size, y:y + patch_size])
                        hr_group.create_dataset(str(patch_idx), data=hr[x:x + patch_size, y:y + patch_size])
                        patch_idx += 1

            print(f"  Created {h5_path} with {patch_idx} patches")

    return "data/train.h5", "data/eval.h5"


def _train_rdn(train_file, eval_file, output_dir, num_epochs, batch_size, lr,
               num_features, growth_rate, num_blocks, num_layers,
               l1_weight, aop_weight):
    """Core RDN training loop."""
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.backends.cudnn as cudnn
    from torch.utils.data import DataLoader
    import copy
    import math

    # Add SPDRDN code to path for model/dataset imports
    _spdrn_added = False
    for sprdn_path in [".", "../SPDRDN/code/AOP-branch", "SPDRDN/code/AOP-branch",
                       os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "../../SPDRDN/code/AOP-branch")]:
        candidate = os.path.abspath(sprdn_path)
        if os.path.exists(os.path.join(candidate, "models.py")):
            sys.path.insert(0, candidate)
            _spdrn_added = True
            break

    if not _spdrn_added:
        print("[WARN] SPDRDN not found in common locations, trying current directory")
        # Fallback: assume SPDRDN files are already in path

    from datasets import TrainDataset, EvalDataset
    from utils import AverageMeter, calc_psnr
    from models import RDN, CombinedLoss

    os.makedirs(output_dir, exist_ok=True)
    cudnn.benchmark = True
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device}")
    if device.type == "cpu":
        print("[WARN] No GPU detected! Training on CPU will be very slow.")

    model = RDN(num_channels=4,
                num_features=num_features,
                growth_rate=growth_rate,
                num_blocks=num_blocks,
                num_layers=num_layers).to(device)

    criterion = CombinedLoss(l1_weight=l1_weight, aop_weight=aop_weight)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    train_dataset = TrainDataset(train_file)
    train_loader = DataLoader(train_dataset, batch_size=batch_size,
                               shuffle=True, num_workers=4, pin_memory=True)
    eval_dataset = EvalDataset(eval_file)
    eval_loader = DataLoader(eval_dataset, batch_size=1)

    best_weights = copy.deepcopy(model.state_dict())
    best_epoch = 0
    best_psnr = 0.0

    from tqdm import tqdm

    for epoch in range(num_epochs):
        for param_group in optimizer.param_groups:
            param_group['lr'] = lr * (0.1 ** (epoch // int(num_epochs * 0.8)))

        # ── Train ──
        model.train()
        epoch_losses = AverageMeter()

        with tqdm(total=len(train_loader) * batch_size, ncols=100) as pbar:
            pbar.set_description(f"Epoch {epoch}/{num_epochs - 1}")
            for inputs, labels in train_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                preds = model(inputs)
                total_loss, _, _ = criterion(preds, labels)
                epoch_losses.update(total_loss.item(), len(inputs))

                optimizer.zero_grad()
                total_loss.backward()
                optimizer.step()
                pbar.set_postfix(loss=f"{epoch_losses.avg:.6f}")
                pbar.update(len(inputs))

        # ── Save checkpoint ──
        if (epoch + 1) % 10 == 0:
            torch.save(model.state_dict(),
                       os.path.join(output_dir, f"epoch_{epoch}.pth"))

        # ── Evaluate ──
        model.eval()
        epoch_psnr = AverageMeter()
        for inputs, labels in eval_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            with torch.no_grad():
                preds = model(inputs)
            epoch_psnr.update(calc_psnr(preds, labels), len(inputs))

        print(f"  Eval PSNR: {epoch_psnr.avg:.2f} dB")

        if epoch_psnr.avg > best_psnr:
            best_epoch = epoch
            best_psnr = epoch_psnr.avg
            best_weights = copy.deepcopy(model.state_dict())

    print(f"\n[INFO] Best epoch: {best_epoch}, PSNR: {best_psnr:.2f} dB")
    torch.save(best_weights, os.path.join(output_dir, "best.pth"))
    print(f"[INFO] Best weights saved to {os.path.join(output_dir, 'best.pth')}")


if __name__ == "__main__":
    main()
