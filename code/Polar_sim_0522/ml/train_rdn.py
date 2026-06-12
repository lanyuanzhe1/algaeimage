"""Train RDN (4->4) on LifeWatch HSV polarization data.

Usage (on server):
    /data/miniconda/envs/torch/bin/python ml/train_rdn.py \
        --image-dir /data/lifewatch_hsv/images \
        --split-file /data/lifewatch_hsv/splits/train.txt \
        --output /data/lifewatch_hsv/rdn_training/rdn_hsv_lifewatch.pth \
        --num-samples 3000 --epochs 100 --batch 32 --lr 1e-4
"""

import argparse, os, sys, time, random
import numpy as np
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from ml.reconstructor import RDN


class HSVPolarizationDataset(Dataset):
    """On-the-fly HSV polarization 4-channel training pairs."""

    def __init__(self, image_dir, split_file, num_samples, patch_size=96, noise_level=0.02):
        from hsv_polarization import hsv_to_polarization
        self.hsv_func = hsv_to_polarization
        self.image_dir = Path(image_dir)
        self.patch_size = patch_size
        self.noise_level = noise_level

        all_imgs = list(self.image_dir.rglob("*.jpg"))
        if not all_imgs:
            raise FileNotFoundError(f"No .jpg found in {image_dir}")

        stems = set()
        if split_file and Path(split_file).exists():
            with open(split_file) as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    parts = line.rsplit(" ", 1)
                    if len(parts) == 2:
                        basename = parts[0].replace("\\", "/").split("/")[-1]
                        stems.add(basename.rsplit(".", 1)[0])

        if stems:
            all_imgs = [p for p in all_imgs if p.stem in stems]

        if len(all_imgs) < num_samples:
            num_samples = len(all_imgs)

        self.images = random.sample(all_imgs, num_samples)
        print(f"RDN dataset: {len(self.images)} images")

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        import cv2
        rgb = cv2.cvtColor(cv2.imread(str(self.images[idx])), cv2.COLOR_BGR2RGB)

        clean = self.hsv_func(rgb, polarization_strength=1.0, add_noise=False)
        clean_arr = np.stack([clean["I0"], clean["I45"], clean["I90"], clean["I135"]],
                             axis=0).astype(np.float32) / 255.0

        noisy = self.hsv_func(rgb, polarization_strength=1.0,
                              add_noise=True, noise_level=self.noise_level)
        noisy_arr = np.stack([noisy["I0"], noisy["I45"], noisy["I90"], noisy["I135"]],
                             axis=0).astype(np.float32) / 255.0

        c, h, w = clean_arr.shape
        scale = self.patch_size / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)
        clean_arr = np.array([cv2.resize(ch, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                              for ch in clean_arr])
        noisy_arr = np.array([cv2.resize(ch, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                              for ch in noisy_arr])

        padded_clean = np.zeros((c, self.patch_size, self.patch_size), dtype=np.float32)
        padded_noisy = np.zeros((c, self.patch_size, self.patch_size), dtype=np.float32)
        padded_clean[:, :new_h, :new_w] = clean_arr
        padded_noisy[:, :new_h, :new_w] = noisy_arr

        return torch.from_numpy(padded_noisy), torch.from_numpy(padded_clean)


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    dataset = HSVPolarizationDataset(
        image_dir=args.image_dir, split_file=args.split_file,
        num_samples=args.num_samples, patch_size=args.patch_size,
        noise_level=args.noise_level,
    )

    n_train = int(len(dataset) * 0.8)
    n_val = len(dataset) - n_train
    train_ds, val_ds = torch.utils.data.random_split(
        dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(42))

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch, shuffle=False, num_workers=0)

    model = RDN(num_channels=4, num_features=16, growth_rate=16,
                num_blocks=12, num_layers=6).to(device)
    print(f"RDN params: {sum(p.numel() for p in model.parameters()):,}")

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=80, gamma=0.1)
    criterion = nn.L1Loss()

    best_loss = float("inf")
    t0 = time.time()

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        for noisy, clean in train_loader:
            noisy, clean = noisy.to(device), clean.to(device)
            optimizer.zero_grad()
            loss = criterion(model(noisy), clean)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * noisy.size(0)
        train_loss /= len(train_ds)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for noisy, clean in val_loader:
                noisy, clean = noisy.to(device), clean.to(device)
                val_loss += criterion(model(noisy), clean).item() * noisy.size(0)
        val_loss /= len(val_ds)

        scheduler.step()

        if epoch % 10 == 0 or epoch == 1:
            elapsed = time.time() - t0
            print(f"Epoch {epoch:3d}/{args.epochs} | train_loss={train_loss:.6f} "
                  f"val_loss={val_loss:.6f} | lr={scheduler.get_last_lr()[0]:.2e} | {elapsed:.0f}s")

        if val_loss < best_loss:
            best_loss = val_loss
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), args.output)
            print(f"  -> saved best (val_loss={best_loss:.6f})")

    elapsed = time.time() - t0
    print(f"\nDone: {elapsed:.0f}s ({elapsed/60:.1f}m), best_val_loss={best_loss:.6f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", required=True)
    parser.add_argument("--split-file", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--num-samples", type=int, default=3000)
    parser.add_argument("--patch-size", type=int, default=96)
    parser.add_argument("--noise-level", type=float, default=0.02)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    train(parser.parse_args())
