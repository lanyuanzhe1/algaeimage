# Polar_sim_0522 LifeWatch HSV 全流程 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Tesla V100-SXM2-32GB 服务器上，使用 HSV 偏振模拟方法 + RDN 自训练 + YOLOv8l，对 LifeWatch 95 类 302k 样本完成全流程处理与训练。

**Architecture:** 本地准备代码和数据集 → 上传至新服务器 → 服务器端顺序执行：RDN 小样本训练 → 全量 RGB 经 HSV+RDN+I_enh 转为 YOLO 训练图 → YOLOv8l 300 epoch 训练。

**Tech Stack:** Python 3.11, PyTorch 2.10.0, CUDA 12.8, ultralytics, OpenCV, paramiko

**前置条件:** 用户提供新服务器的 IP、端口、root 密码。

**服务器连接:**
```bash
ssh -p 44448 root@tssjfkari2ofchucsnow.deepln.com
# Password: 31N41wYaWf5hsGtZNSYcyRHsTlkP32Dx
```
| 项目 | 值 |
|------|-----|
| Host | tssjfkari2ofchucsnow.deepln.com |
| Port | 44448 |
| User | root |
| GPU | Tesla V100-SXM2-32GB |
| VRAM | 32 GB |
| Python | /data/miniconda/envs/torch/bin/python (3.12, PyTorch 2.10.0+cu128) |
| 工作目录 | /data/lifewatch_hsv/ |
| /data 可用 | 51 GB |

---

### Task 0: 创建目录结构和 `__init__.py`

**Files:**

- Create: `code/Polar_sim_0522/image_processing/__init__.py`
- Create: `code/Polar_sim_0522/ml/__init__.py`
- Create: `code/Polar_sim_0522/ml/models/` (目录)
- Create: `code/Polar_sim_0522/deploy/` (目录)

- [ ] **Step 1: 创建所有目录**

```bash
mkdir -p e:/code/algaeimage/code/Polar_sim_0522/image_processing
mkdir -p e:/code/algaeimage/code/Polar_sim_0522/ml/models
mkdir -p e:/code/algaeimage/code/Polar_sim_0522/deploy
mkdir -p e:/code/algaeimage/code/Polar_sim_0522/docs
```

- [ ] **Step 2: 写出 `__init__.py` 文件**

`image_processing/__init__.py`:

```python
"""Image processing: polarization simulation, enhancement, quality assessment."""
```

`ml/__init__.py`:

```python
"""Machine learning: RDN reconstruction, YOLO detection, tracker."""
```

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/
git commit -m "feat: create Polar_sim_0522 directory structure"
```

---

### Task 1: 复制 `hsv_polarization.py`（HSV 偏振模拟）

**Files:**

- Create: `code/Polar_sim_0522/hsv_polarization.py`
- Source: `code/Polar_sim_0520/hsv_polarization.py` (完整复制)

- [ ] **Step 1: 复制文件**

```bash
cp e:/code/algaeimage/code/Polar_sim_0520/hsv_polarization.py e:/code/algaeimage/code/Polar_sim_0522/hsv_polarization.py
```

- [ ] **Step 2: 验证导入可用**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import sys; sys.path.insert(0, 'e:/code/algaeimage/code/Polar_sim_0522')
from hsv_polarization import hsv_to_polarization, batch_simulate_hsv
print('Import OK: hsv_to_polarization, batch_simulate_hsv')
"
```

预期: `Import OK: hsv_to_polarization, batch_simulate_hsv`

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/hsv_polarization.py
git commit -m "feat: copy hsv_polarization.py from Polar_sim_0520"
```

---

### Task 2: 复制 `image_processing/polarization.py`

**Files:**

- Create: `code/Polar_sim_0522/image_processing/polarization.py`
- Source: `code/Polar_sim_0520/image_processing/polarization.py` (完整复制)

- [ ] **Step 1: 复制文件**

```bash
cp e:/code/algaeimage/code/Polar_sim_0520/image_processing/polarization.py e:/code/algaeimage/code/Polar_sim_0522/image_processing/polarization.py
```

- [ ] **Step 2: 验证导入**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import sys, os; os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
sys.path.insert(0, 'e:/code/algaeimage/code/Polar_sim_0522')
from image_processing.polarization import PolarizationProcessor
pp = PolarizationProcessor()
print('Import OK:', type(pp).__name__)
"
```

预期: `Import OK: PolarizationProcessor`

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/image_processing/polarization.py
git commit -m "feat: copy polarization.py from Polar_sim_0520"
```

---

### Task 3: 复制 `image_processing/enhancement.py`

**Files:**

- Create: `code/Polar_sim_0522/image_processing/enhancement.py`
- Source: `code/Polar_sim_0520/image_processing/enhancement.py` (完整复制)

- [ ] **Step 1: 复制文件**

```bash
cp e:/code/algaeimage/code/Polar_sim_0520/image_processing/enhancement.py e:/code/algaeimage/code/Polar_sim_0522/image_processing/enhancement.py
```

- [ ] **Step 2: 验证导入**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import sys, os; os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
sys.path.insert(0, 'e:/code/algaeimage/code/Polar_sim_0522')
from image_processing.enhancement import ImageEnhancer
ie = ImageEnhancer()
print('Import OK:', type(ie).__name__)
"
```

预期: `Import OK: ImageEnhancer`

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/image_processing/enhancement.py
git commit -m "feat: copy enhancement.py from Polar_sim_0520"
```

---

### Task 4: 复制 `ml/reconstructor.py`

**Files:**

- Create: `code/Polar_sim_0522/ml/reconstructor.py`
- Source: `code/Polar_sim_0520/ml/reconstructor.py`

- [ ] **Step 1: 复制文件**

```bash
cp e:/code/algaeimage/code/Polar_sim_0520/ml/reconstructor.py e:/code/algaeimage/code/Polar_sim_0522/ml/reconstructor.py
```

- [ ] **Step 2: 验证导入**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import sys, os; os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
sys.path.insert(0, 'e:/code/algaeimage/code/Polar_sim_0522')
from ml.reconstructor import RDN, DenseLayer, RDB, PolarizationReconstructor
print('Import OK: RDN, PolarizationReconstructor')
"
```

预期: `Import OK: RDN, PolarizationReconstructor`

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/ml/reconstructor.py
git commit -m "feat: copy reconstructor.py from Polar_sim_0520"
```

---

### Task 5: 创建服务器连接模块 `deploy/cloud_server.py`

**Files:**

- Create: `code/Polar_sim_0522/deploy/cloud_server.py`

此模块封装 paramiko SSH 连接，支持 `run()`, `upload()`, `download()`, `upload_text()`。

- [ ] **Step 1: 写出文件**

```python
"""SSH helper for new LifeWatch HSV cloud server.

Usage:
    from deploy.cloud_server import CloudServer

    with CloudServer(host, port, user, password) as server:
        server.run("nvidia-smi")
        server.upload("local_file", "remote_path")
"""

import io
import os
import paramiko
from pathlib import Path
from typing import Optional


class SSHResult:
    def __init__(self, stdout: str, stderr: str, exit_code: int):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

    def ok(self) -> bool:
        return self.exit_code == 0


class CloudServer:
    """Context manager for cloud server SSH + SFTP connection."""

    def __init__(self, host: str, port: int, user: str, password: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp = None

    def __enter__(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            timeout=15,
        )
        self.client.get_transport().use_compression(True)
        self.sftp = self.client.open_sftp()
        print(f"[SSH] Connected to {self.user}@{self.host}:{self.port}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()
        print("[SSH] Disconnected")

    def run(self, command: str, timeout: int = 600) -> SSHResult:
        """Run a shell command and return result."""
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return SSHResult(
            stdout=stdout.read().decode("utf-8", errors="replace").strip(),
            stderr=stderr.read().decode("utf-8", errors="replace").strip(),
            exit_code=exit_code,
        )

    def upload(self, local_path: str, remote_path: str):
        """Upload a file or directory to the server."""
        local = Path(local_path)
        if local.is_file():
            remote_dir = str(Path(remote_path).parent)
            self.run(f"mkdir -p '{remote_dir}'")
            self.sftp.put(str(local), remote_path)
            size_mb = local.stat().st_size / (1024 * 1024)
            print(f"[Upload] {local.name} -> {remote_path} ({size_mb:.1f} MB)")
        elif local.is_dir():
            self.run(f"mkdir -p '{remote_path}'")
            for f in local.rglob("*"):
                if f.is_file() and "__pycache__" not in str(f):
                    rel = f.relative_to(local)
                    remote_file = str(Path(remote_path) / rel)
                    self.run(f"mkdir -p '{str(Path(remote_file).parent)}'")
                    self.sftp.put(str(f), remote_file)
            print(f"[Upload] Directory {local.name}/ -> {remote_path}/")

    def download(self, remote_path: str, local_path: str):
        """Download a file from the server."""
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        self.sftp.get(remote_path, str(local))
        size_mb = local.stat().st_size / (1024 * 1024)
        print(f"[Download] {remote_path} -> {local.name} ({size_mb:.1f} MB)")

    def upload_text(self, content: str, remote_path: str):
        """Upload text content as a file."""
        f = io.BytesIO(content.encode("utf-8"))
        remote_dir = str(Path(remote_path).parent)
        self.run(f"mkdir -p '{remote_dir}'")
        self.sftp.putfo(f, remote_path)
        print(f"[Upload] text -> {remote_path}")

    def file_exists(self, remote_path: str) -> bool:
        result = self.run(f"test -f '{remote_path}' && echo EXISTS || echo NF")
        return "EXISTS" in result.stdout

    def dir_exists(self, remote_path: str) -> bool:
        result = self.run(f"test -d '{remote_path}' && echo EXISTS || echo NF")
        return "EXISTS" in result.stdout
```

- [ ] **Step 2: 验证语法**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import sys; sys.path.insert(0, 'e:/code/algaeimage/code/Polar_sim_0522')
from deploy.cloud_server import CloudServer, SSHResult
print('Import OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/deploy/cloud_server.py
git commit -m "feat: add CloudServer SSH helper for new server"
```

---

### Task 6: 创建服务器环境配置脚本 `deploy/setup_env.py`

**Files:**

- Create: `code/Polar_sim_0522/deploy/setup_env.py`

此脚本连接新服务器，检查 GPU/磁盘/Python 环境，并安装缺失的依赖。

- [ ] **Step 1: 写出文件**

```python
"""Configure the new RTX 4090 server environment for LifeWatch HSV pipeline.

Run locally to set up the remote server before data upload.
Update SERVER_* variables before running.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.cloud_server import CloudServer

# ═══════════════════════════════════════════════════════
# CONFIGURE THESE
# ═══════════════════════════════════════════════════════
SERVER_HOST = "CHANGE_ME.funhpc.com"
SERVER_PORT = 30000
SERVER_USER = "root"
SERVER_PASSWORD = "CHANGE_ME"

BASE_DIR = "/data/lifewatch_hsv"


def main():
    with CloudServer(SERVER_HOST, SERVER_PORT, SERVER_USER, SERVER_PASSWORD) as s:
        # ── 1. System info ──
        print("=" * 60)
        print("1. System Info")
        print("=" * 60)

        gpu = s.run("nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader")
        print(f"GPU: {gpu.stdout}")

        disk = s.run("df -h /data | tail -1")
        print(f"/data disk: {disk.stdout}")

        py = s.run("python --version 2>&1")
        print(f"Python: {py.stdout}")

        torch = s.run("python -c 'import torch; print(f\"PyTorch {torch.__version__}, CUDA {torch.version.cuda}\")'")
        print(f"PyTorch: {torch.stdout}")

        # ── 2. Install dependencies ──
        print()
        print("=" * 60)
        print("2. Installing Python packages")
        print("=" * 60)

        deps = "ultralytics opencv-python-headless scipy h5py"
        result = s.run(f"pip install {deps} -q 2>&1 | tail -5", timeout=300)
        print(result.stdout)

        # ── 3. Verify installs ──
        print()
        print("=" * 60)
        print("3. Verify imports")
        print("=" * 60)

        verify = """python -c \"
import torch; from ultralytics import YOLO; import cv2; import numpy; import scipy;
print(f'OK: torch={torch.__version__}, ultralytics={YOLO.__module__}, '
      f'cv2={cv2.__version__}')
\""""
        v = s.run(verify)
        print(v.stdout)

        # ── 4. Create directories ──
        print()
        print("=" * 60)
        print("4. Creating directory structure")
        print("=" * 60)

        for d in [BASE_DIR,
                  f"{BASE_DIR}/images",
                  f"{BASE_DIR}/splits",
                  f"{BASE_DIR}/rdn_training",
                  f"{BASE_DIR}/processed/train",
                  f"{BASE_DIR}/processed/val",
                  f"{BASE_DIR}/processed/test",
                  f"{BASE_DIR}/code"]:
            result = s.run(f"mkdir -p {d}")
            print(f"  {d} {'OK' if result.ok() else 'FAIL'}")

        print()
        print("=" * 60)
        print("Setup complete!")
        print("=" * 60)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证语法**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import sys; sys.path.insert(0, 'e:/code/algaeimage/code/Polar_sim_0522')
import ast; ast.parse(open('e:/code/algaeimage/code/Polar_sim_0522/deploy/setup_env.py').read())
print('Syntax OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/deploy/setup_env.py
git commit -m "feat: add server environment setup script"
```

---

### Task 7: 创建数据上传脚本 `deploy/upload_all.py`

**Files:**

- Create: `code/Polar_sim_0522/deploy/upload_all.py`

此脚本将 LifeWatch 数据集 (zip + split 文件) + 项目代码 + RDN 训练脚本上传到新服务器。

- [ ] **Step 1: 写出文件**

```python
"""Upload all data and code to the LifeWatch HSV cloud server.

Upload order:
  1. LifeWatch dataset (Flowcam_images_training.zip + split files)
  2. Project code (hsv_polarization, image_processing, ml, deploy)
  3. RDN training samples (generated locally or on server)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.cloud_server import CloudServer

# ═══════════════════════════════════════════════════════
# CONFIGURE THESE
# ═══════════════════════════════════════════════════════
SERVER_HOST = "CHANGE_ME.funhpc.com"
SERVER_PORT = 30000
SERVER_USER = "root"
SERVER_PASSWORD = "CHANGE_ME"

LOCAL_DATA_DIR = Path("E:/code/algaeimage/code/algae_guardian/data/Flowcam_images_training_split_metadata"
                      "/Flowcam_images_training_split_metadata")
LOCAL_PROJECT = Path(__file__).resolve().parent.parent
BASE_DIR = "/data/lifewatch_hsv"


def main():
    with CloudServer(SERVER_HOST, SERVER_PORT, SERVER_USER, SERVER_PASSWORD) as s:
        # ── 1. Upload LifeWatch images zip ──
        print("=" * 60)
        print("1. Uploading LifeWatch images zip (537 MB)")
        print("=" * 60)

        zip_path = LOCAL_DATA_DIR / "Flowcam_images_training.zip"
        if zip_path.exists():
            s.upload(str(zip_path), f"{BASE_DIR}/images/Flowcam_images_training.zip")
            print("  Extracting on server...")
            r = s.run(
                f"cd {BASE_DIR}/images && unzip -q Flowcam_images_training.zip && "
                f"echo 'Extracted OK'",
                timeout=300
            )
            print(f"  {r.stdout}")
        else:
            print(f"  ERROR: {zip_path} not found!")
            return

        # ── 2. Upload split files ──
        print()
        print("=" * 60)
        print("2. Uploading split files")
        print("=" * 60)

        split_dir = LOCAL_DATA_DIR / "dataset_files_equal"
        for fname in ["train.txt", "val.txt", "test.txt", "classes.txt"]:
            fp = split_dir / fname
            if fp.exists():
                s.upload(str(fp), f"{BASE_DIR}/splits/{fname}")
            else:
                print(f"  WARNING: {fname} not found")

        # ── 3. Upload project code ──
        print()
        print("=" * 60)
        print("3. Uploading project code")
        print("=" * 60)

        for subdir in ["image_processing", "ml", "deploy"]:
            local_dir = LOCAL_PROJECT / subdir
            if local_dir.is_dir():
                s.upload(str(local_dir), f"{BASE_DIR}/code/{subdir}")

        for fname in ["hsv_polarization.py"]:
            fp = LOCAL_PROJECT / fname
            if fp.exists():
                s.upload(str(fp), f"{BASE_DIR}/code/{fname}")

        print()
        print("=" * 60)
        print("Upload complete!")
        print("=" * 60)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证语法**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import ast; ast.parse(open('e:/code/algaeimage/code/Polar_sim_0522/deploy/upload_all.py').read())
print('Syntax OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/deploy/upload_all.py
git commit -m "feat: add data+code upload script"
```

---

### Task 8: 创建 RDN 训练脚本 `ml/train_rdn.py`

**Files:**

- Create: `code/Polar_sim_0522/ml/train_rdn.py`

此脚本在服务器端运行，从 LifeWatch 小样本（3000 张）生成 HSV 4 通道训练数据，训练 RDN 去噪网络。

- [ ] **Step 1: 写出文件**

```python
"""Train RDN for polarization reconstruction on LifeWatch HSV data.

Usage (on server):
    python ml/train_rdn.py \
        --image-dir /data/lifewatch_hsv/images \
        --output /data/lifewatch_hsv/rdn_training/rdn_hsv_lifewatch.pth \
        --num-samples 3000 --epochs 100 --batch 32 --lr 1e-4

Architecture: RDN(4→4), num_features=16, growth_rate=16, blocks=12, layers=6
Input:  HSV-generated noisy 4-channel (I0,I45,I90,I135)
Target: Clean 4-channel (noise-free HSV simulation)
Loss: L1Loss
"""

import argparse
import os
import sys
import time
import numpy as np
from pathlib import Path
import random

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from ml.reconstructor import RDN


# ═══════════════════════════════════════════════
# Dataset: HSV 4-channel pairs
# ═══════════════════════════════════════════════

class HSVPolarizationDataset(Dataset):
    """Generate HSV polarization 4-channel training pairs on-the-fly.

    For each RGB image:
      - target = hsv_to_polarization(noise=False) → clean 4ch
      - input  = hsv_to_polarization(noise=True, noise_level=0.02) → noisy 4ch
    All resized/padded to fixed `patch_size`.
    """

    def __init__(self, image_dir: str, split_file: str, num_samples: int,
                 patch_size: int = 96, noise_level: float = 0.02):
        from hsv_polarization import hsv_to_polarization

        self.hsv_func = hsv_to_polarization
        self.image_dir = Path(image_dir)
        self.patch_size = patch_size
        self.noise_level = noise_level

        # Find all RGB images
        all_imgs = list(self.image_dir.rglob("*.jpg")) + list(self.image_dir.rglob("*.jpeg"))
        if not all_imgs:
            raise FileNotFoundError(f"No .jpg found in {image_dir}")

        # If split_file provided, restrict to those stems
        stems = set()
        if split_file and Path(split_file).exists():
            with open(split_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # Format: path\to\image.jpg class
                    parts = line.rsplit(" ", 1)
                    if len(parts) == 2:
                        basename = parts[0].replace("\\", "/").split("/")[-1]
                        stems.add(basename.rsplit(".", 1)[0])

        if stems:
            all_imgs = [p for p in all_imgs if p.stem in stems]

        if len(all_imgs) < num_samples:
            print(f"Warning: only {len(all_imgs)} images available, using all")
            num_samples = len(all_imgs)

        self.images = random.sample(all_imgs, num_samples)
        print(f"RDN dataset: {len(self.images)} images selected")

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        import cv2
        img_path = self.images[idx]
        rgb = cv2.cvtColor(cv2.imread(str(img_path)), cv2.COLOR_BGR2RGB)

        # Generate clean target (no noise)
        clean = self.hsv_func(rgb, polarization_strength=1.0, add_noise=False)
        clean_arr = np.stack([clean["I0"], clean["I45"], clean["I90"], clean["I135"]],
                             axis=0).astype(np.float32) / 255.0

        # Generate noisy input
        noisy = self.hsv_func(rgb, polarization_strength=1.0,
                              add_noise=True, noise_level=self.noise_level)
        noisy_arr = np.stack([noisy["I0"], noisy["I45"], noisy["I90"], noisy["I135"]],
                             axis=0).astype(np.float32) / 255.0

        # Resize/pad to patch_size with aspect ratio preserved
        c, h, w = clean_arr.shape
        scale = self.patch_size / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)
        clean_arr = np.array([_resize_channel(ch, new_h, new_w) for ch in clean_arr])
        noisy_arr = np.array([_resize_channel(ch, new_h, new_w) for ch in noisy_arr])

        # Pad to exact patch_size
        padded_clean = np.zeros((c, self.patch_size, self.patch_size), dtype=np.float32)
        padded_noisy = np.zeros((c, self.patch_size, self.patch_size), dtype=np.float32)
        padded_clean[:, :new_h, :new_w] = clean_arr
        padded_noisy[:, :new_h, :new_w] = noisy_arr

        return torch.from_numpy(padded_noisy), torch.from_numpy(padded_clean)


def _resize_channel(ch: np.ndarray, h: int, w: int) -> np.ndarray:
    """Resize a single channel with bilinear interpolation (simple)."""
    import cv2
    return cv2.resize(ch, (w, h), interpolation=cv2.INTER_LINEAR)


# ═══════════════════════════════════════════════
# Training loop
# ═══════════════════════════════════════════════

def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Dataset
    dataset = HSVPolarizationDataset(
        image_dir=args.image_dir,
        split_file=args.split_file,
        num_samples=args.num_samples,
        patch_size=args.patch_size,
        noise_level=args.noise_level,
    )

    # 80/20 split
    n_train = int(len(dataset) * 0.8)
    n_val = len(dataset) - n_train
    train_ds, val_ds = torch.utils.data.random_split(dataset, [n_train, n_val],
                                                      generator=torch.Generator().manual_seed(42))

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch, shuffle=False, num_workers=0)

    # Model
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
            output = model(noisy)
            loss = criterion(output, clean)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * noisy.size(0)

        train_loss /= len(train_ds)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for noisy, clean in val_loader:
                noisy, clean = noisy.to(device), clean.to(device)
                output = model(noisy)
                val_loss += criterion(output, clean).item() * noisy.size(0)
        val_loss /= len(val_ds)

        scheduler.step()

        if epoch % 10 == 0 or epoch == 1:
            elapsed = time.time() - t0
            print(f"Epoch {epoch:3d}/{args.epochs} | "
                  f"train_loss={train_loss:.6f} | val_loss={val_loss:.6f} | "
                  f"lr={scheduler.get_last_lr()[0]:.2e} | {elapsed:.0f}s")

        if val_loss < best_loss:
            best_loss = val_loss
            save_dir = Path(args.output).parent
            save_dir.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), args.output)
            print(f"  Saved best model (val_loss={best_loss:.6f})")

    elapsed = time.time() - t0
    print(f"\nTraining complete: {elapsed:.0f}s ({elapsed/60:.1f}m), best_val_loss={best_loss:.6f}")
    print(f"Model saved to {args.output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RDN on LifeWatch HSV data")
    parser.add_argument("--image-dir", required=True,
                        help="Root directory of LifeWatch RGB images (class subdirs)")
    parser.add_argument("--split-file", default="",
                        help="train.txt for filtering images (optional)")
    parser.add_argument("--output", required=True,
                        help="Output .pth path")
    parser.add_argument("--num-samples", type=int, default=3000)
    parser.add_argument("--patch-size", type=int, default=96)
    parser.add_argument("--noise-level", type=float, default=0.02)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()
    train(args)
```

- [ ] **Step 2: 验证语法和导入**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import ast; print('Syntax OK' if ast.parse(open('e:/code/algaeimage/code/Polar_sim_0522/ml/train_rdn.py').read()) else '')
"
```

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/ml/train_rdn.py
git commit -m "feat: add RDN training script for LifeWatch HSV data"
```

---

### Task 9: 创建全量管线脚本 `deploy/run_pipeline.py`

**Files:**

- Create: `code/Polar_sim_0522/deploy/run_pipeline.py`

此脚本在服务器端执行阶段 3：遍历所有 LifeWatch RGB 图像 → HSV 4ch → RDN 重建 → I_enh v2 → YOLO 训练图 + Label。

- [ ] **Step 1: 写出文件**

```python
"""Full LifeWatch HSV pipeline: RGB → HSV → RDN → I_enh → YOLO dataset.

Usage (on server):
    python deploy/run_pipeline.py \
        --image-dir /data/lifewatch_hsv/images \
        --split-dir /data/lifewatch_hsv/splits \
        --rdn-model /data/lifewatch_hsv/rdn_training/rdn_hsv_lifewatch.pth \
        --output /data/lifewatch_hsv/processed \
        --split train,val,test
"""

import argparse
import os
import sys
import time
import json
from pathlib import Path
from collections import defaultdict

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import numpy as np
import cv2

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from hsv_polarization import hsv_to_polarization
from image_processing.polarization import PolarizationProcessor
from image_processing.enhancement import ImageEnhancer
from ml.reconstructor import PolarizationReconstructor

# ═══════════════════════════════════════════════════════
# Parameters
# ═══════════════════════════════════════════════════════
ALPHA = 0.6
BETA = 0.25
GAMMA = 0.35
POL_STRENGTH = 1.0
NOISE_LEVEL = 0.02
YOLO_IMG_SIZE = 320  # output resized square for YOLO


def load_split(split_file: str) -> dict:
    """Parse split file → {image_stem: class_id}."""
    mapping = {}
    with open(split_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                continue
            path_part, cls = parts
            stem = path_part.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
            mapping[stem] = int(cls)
    return mapping


def letterbox(img: np.ndarray, target_size: int) -> np.ndarray:
    """Resize image to target_size × target_size, preserving aspect ratio with 0-padding."""
    h, w = img.shape[:2]
    scale = target_size / max(h, w)
    new_h, new_w = int(h * scale), int(w * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    if len(img.shape) == 3:
        padded = np.zeros((target_size, target_size, img.shape[2]), dtype=img.dtype)
    else:
        padded = np.zeros((target_size, target_size), dtype=img.dtype)
    padded[:new_h, :new_w] = resized
    return padded


def process_single_image(rgb: np.ndarray, pp: PolarizationProcessor,
                         reconstructor: PolarizationReconstructor,
                         enhancer: ImageEnhancer,
                         use_rdn: bool) -> np.ndarray:
    """Process one RGB image through the full enhancement pipeline.

    Returns:
        3-channel YOLO input image (uint8, 320×320)
    """
    # 1. HSV polarization simulation
    sim = hsv_to_polarization(rgb, polarization_strength=POL_STRENGTH,
                              add_noise=True, noise_level=NOISE_LEVEL)
    I0 = sim["I0"].astype(np.float32)
    I45 = sim["I45"].astype(np.float32)
    I90 = sim["I90"].astype(np.float32)
    I135 = sim["I135"].astype(np.float32)

    # 2. RDN reconstruction (4→4) or analytical fallback
    if use_rdn and reconstructor.is_available():
        recon = reconstructor.reconstruct(I0, I45, I90, I135, use_deep=True)
        # Recon output shape: (H, W, 4) for 4-ch mode
        # Actually reconstruct() returns 4ch, let's use it directly
        I0_r = recon[:, :, 0].astype(np.float32)
        I45_r = recon[:, :, 1].astype(np.float32)
        I90_r = recon[:, :, 2].astype(np.float32)
        I135_r = recon[:, :, 3].astype(np.float32)
    else:
        I0_r, I45_r, I90_r, I135_r = I0, I45, I90, I135

    # 3. Rebuild Stokes from reconstructed 4 channels
    S0 = I0_r + I90_r
    S1 = I0_r - I90_r
    S2 = I45_r - I135_r
    DoLP = np.sqrt(S1 ** 2 + S2 ** 2) / (S0 + 1e-10)
    DoLP = np.clip(DoLP, 0, 1)
    AoP = 0.5 * np.arctan2(S2, S1)

    # 4. I_enh v2
    S0_norm = _norm_to_uint8(S0)
    I_enh = pp.polarization_enhancement_v2(S0, DoLP, AoP,
                                           alpha=ALPHA, beta=BETA, gamma=GAMMA)
    I_enh = letterbox(I_enh, YOLO_IMG_SIZE)

    # 5. Backscatter suppression (corrected channel)
    corrected_raw = S0 * (1.0 - 0.5 * DoLP.astype(np.float32))
    corrected = letterbox(_norm_to_uint8(corrected_raw), YOLO_IMG_SIZE)

    S0_norm_lb = letterbox(S0_norm, YOLO_IMG_SIZE)

    # 6. Stack 3ch + CLAHE
    stacked = np.stack([S0_norm_lb, I_enh, corrected], axis=-1)
    final = enhancer.enhance(stacked, color_correct=True, clahe=True, dehaze=False)
    return final


def _norm_to_uint8(x: np.ndarray) -> np.ndarray:
    x_min, x_max = x.min(), x.max()
    if x_max - x_min < 1e-10:
        return np.zeros_like(x, dtype=np.uint8)
    return ((x.astype(np.float32) - x_min) / (x_max - x_min) * 255).astype(np.uint8)


def main():
    parser = argparse.ArgumentParser(description="LifeWatch HSV full pipeline")
    parser.add_argument("--image-dir", required=True)
    parser.add_argument("--split-dir", required=True)
    parser.add_argument("--rdn-model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--splits", default="train,val,test")
    args = parser.parse_args()

    IMAGE_DIR = Path(args.image_dir)
    SPLIT_DIR = Path(args.split_dir)
    OUTPUT = Path(args.output)
    RDN_MODEL = args.rdn_model
    SPLITS = [s.strip() for s in args.splits.split(",")]

    # ── Load RDN model ──
    print(f"Loading RDN model: {RDN_MODEL}")
    reconstructor = PolarizationReconstructor(model_path=RDN_MODEL)
    use_rdn = reconstructor.load_model()
    if use_rdn:
        print(f"  RDN loaded: {RDN_MODEL}")
    else:
        print("  RDN not available, using analytical fallback")

    pp = PolarizationProcessor()
    enhancer = ImageEnhancer()

    # ── Process each split ──
    for split_name in SPLITS:
        split_file = SPLIT_DIR / f"{split_name}.txt"
        if not split_file.exists():
            print(f"  SKIP {split_name}: {split_file} not found")
            continue

        print(f"\n{'=' * 60}")
        print(f"Processing split: {split_name}")
        print(f"  Split file: {split_file}")
        print(f"  Image dir: {IMAGE_DIR}")
        print(f"{'=' * 60}")

        stem_to_cls = load_split(str(split_file))
        out_img_dir = OUTPUT / split_name / "images"
        out_lbl_dir = OUTPUT / split_name / "labels"
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)

        processed = 0
        missing = 0
        t0 = time.time()

        for stem, cls_id in stem_to_cls.items():
            # Find image file
            img_path = None
            for ext in [".jpg", ".jpeg", ".png"]:
                # Search in all class subdirs
                matches = list(IMAGE_DIR.rglob(f"*/{stem}{ext}"))
                if matches:
                    img_path = matches[0]
                    break

            if img_path is None:
                missing += 1
                if missing <= 5:
                    print(f"  NOT FOUND: {stem}")
                continue

            try:
                rgb = cv2.cvtColor(cv2.imread(str(img_path)), cv2.COLOR_BGR2RGB)
                if rgb is None:
                    missing += 1
                    continue

                final = process_single_image(rgb, pp, reconstructor, enhancer, use_rdn)
                out_img = cv2.cvtColor(final, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(out_img_dir / f"{stem}.jpg"), out_img, [cv2.IMWRITE_JPEG_QUALITY, 92])

                # YOLO label: resize doesn't change relative bbox coords for full-frame
                # Write label with class_id and full-frame bbox (0,0,1,1)
                with open(out_lbl_dir / f"{stem}.txt", "w") as f:
                    f.write(f"{cls_id} 0.5 0.5 1.0 1.0\n")

                processed += 1

            except Exception as e:
                missing += 1
                if missing <= 5:
                    print(f"  ERROR processing {stem}: {e}")

            if processed % 5000 == 0:
                elapsed = time.time() - t0
                rate = processed / max(elapsed, 1)
                eta = (len(stem_to_cls) - processed) / max(rate, 0.01)
                print(f"  [{split_name}] {processed}/{len(stem_to_cls)} "
                      f"({100*processed/len(stem_to_cls):.1f}%) "
                      f"{rate:.0f} img/s, ETA {eta/60:.0f}m")

        elapsed = time.time() - t0
        print(f"  [{split_name}] DONE: {processed} processed, {missing} missing "
              f"in {elapsed:.0f}s ({elapsed/60:.1f}m)")

    # ── Generate dataset.yaml ──
    classes_file = SPLIT_DIR / "classes.txt"
    class_names = []
    if classes_file.exists():
        with open(classes_file) as f:
            class_names = [line.strip() for line in f if line.strip()]

    dataset_yaml = f"""# LifeWatch HSV Polarization YOLO Dataset
path: {args.output}
train: train/images
val: val/images
test: test/images
nc: {len(class_names)}
names: {class_names}
"""

    yaml_path = OUTPUT / "dataset.yaml"
    yaml_path.write_text(dataset_yaml)
    print(f"\nDataset config: {yaml_path}")
    print("Pipeline complete!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证语法**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import ast; ast.parse(open('e:/code/algaeimage/code/Polar_sim_0522/deploy/run_pipeline.py').read())
print('Syntax OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/deploy/run_pipeline.py
git commit -m "feat: add full LifeWatch HSV pipeline script"
```

---

### Task 10: 创建 YOLOv8l 训练脚本 `deploy/train_yolo.py`

**Files:**

- Create: `code/Polar_sim_0522/deploy/train_yolo.py`

此脚本在服务器端启动 YOLOv8l 95 类训练。

- [ ] **Step 1: 写出文件**

```python
"""Train YOLOv8l on LifeWatch HSV polarization dataset (95 classes).

Usage (on server):
    python deploy/train_yolo.py \
        --data /data/lifewatch_hsv/processed/dataset.yaml \
        --output /data/lifewatch_hsv/yolo_results/v8l_hsv_95
"""

import argparse
import json
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="dataset.yaml path")
    parser.add_argument("--output", default="/data/lifewatch_hsv/yolo_results/v8l_hsv_95")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--lr0", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=50)
    args = parser.parse_args()

    from ultralytics import YOLO
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
        torch.cuda.empty_cache()

    print(f"\n{'=' * 60}")
    print(f"YOLOv8l Training: LifeWatch 95-class HSV")
    print(f"  Data: {args.data}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch: {args.batch}")
    print(f"  Image size: {args.imgsz}")
    print(f"  Device: {device}")
    print(f"{'=' * 60}\n")

    model = YOLO("yolov8l.pt")
    t0 = time.time()

    results = model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        lr0=args.lr0,
        lrf=1e-4,
        optimizer="AdamW",
        patience=args.patience,
        device=device,
        project=str(Path(args.output).parent),
        name=Path(args.output).name,
        exist_ok=True,
        pretrained=True,
        seed=0,
        deterministic=True,
        amp=True,
        close_mosaic=10,
        warmup_epochs=5,
        warmup_momentum=0.8,
        weight_decay=5e-4,
        workers=0,
        cache=False,
        plots=True,
        save=True,
        val=True,
        # CRITICAL: disable YOLO HSV augmentation
        hsv_s=0.0,
        hsv_v=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
        erasing=0.4,
        auto_augment="randaugment",
    )

    elapsed = time.time() - t0
    print(f"\nTraining complete: {elapsed:.0f}s ({elapsed/3600:.1f}h)")
    print(f"Best epoch: {getattr(results, 'best_epoch', '?')}")
    print(f"Best fitness: {getattr(results, 'best_fitness', '?')}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证语法**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import ast; ast.parse(open('e:/code/algaeimage/code/Polar_sim_0522/deploy/train_yolo.py').read())
print('Syntax OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/deploy/train_yolo.py
git commit -m "feat: add YOLOv8l 95-class training script"
```

---

### Task 11: 创建总控脚本 `deploy/run_all.py`

**Files:**

- Create: `code/Polar_sim_0522/deploy/run_all.py`

一键执行全流程的总控脚本，在所有代码和数据已上传后，在服务器端一键运行。

- [ ] **Step 1: 写出文件**

```python
"""Master orchestrator for LifeWatch HSV full pipeline.

Run on SERVER after upload completes:
    python deploy/run_all.py

Stages:
    1. RDN small-sample training (~1-2h)
    2. Full pipeline: HSV → RDN → I_enh → YOLO dataset (~3-5h)
    3. YOLOv8l 95-class training (~25-35h)
"""

import subprocess
import sys
from pathlib import Path

BASE = Path("/data/lifewatch_hsv")
CODE = BASE / "code"

STAGES = [
    {
        "name": "RDN Training",
        "cmd": (
            f"python {CODE}/ml/train_rdn.py "
            f"--image-dir {BASE}/images "
            f"--split-file {BASE}/splits/train.txt "
            f"--output {BASE}/rdn_training/rdn_hsv_lifewatch.pth "
            f"--num-samples 3000 --epochs 100 --batch 32 --lr 1e-4"
        ),
        "check": f"{BASE}/rdn_training/rdn_hsv_lifewatch.pth",
    },
    {
        "name": "Full Pipeline",
        "cmd": (
            f"python {CODE}/deploy/run_pipeline.py "
            f"--image-dir {BASE}/images "
            f"--split-dir {BASE}/splits "
            f"--rdn-model {BASE}/rdn_training/rdn_hsv_lifewatch.pth "
            f"--output {BASE}/processed "
            f"--splits train,val,test"
        ),
        "check": f"{BASE}/processed/dataset.yaml",
    },
    {
        "name": "YOLOv8l Training",
        "cmd": (
            f"python {CODE}/deploy/train_yolo.py "
            f"--data {BASE}/processed/dataset.yaml "
            f"--output {BASE}/yolo_results/v8l_hsv_95 "
            f"--epochs 300 --batch 64 --imgsz 320"
        ),
        "check": f"{BASE}/yolo_results/v8l_hsv_95/weights/best.pt",
    },
]


def main():
    print("=" * 70)
    print("  LifeWatch HSV Full Pipeline — Master Orchestrator")
    print("=" * 70)

    import os
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    for i, stage in enumerate(STAGES, 1):
        name = stage["name"]
        check_path = stage["check"]
        cmd = stage["cmd"]

        print(f"\n{'=' * 70}")
        print(f"  Stage {i}/{len(STAGES)}: {name}")
        print(f"{'=' * 70}")
        print(f"  Command: {cmd}")
        print()

        # Check if already done
        if Path(check_path).exists():
            print(f"  SKIP (output already exists: {check_path})")
            continue

        # Run
        sys.stdout.flush()
        result = subprocess.run(cmd, shell=True, cwd=str(CODE))
        if result.returncode != 0:
            print(f"\n  ERROR: Stage {i} ({name}) failed with exit code {result.returncode}")
            print(f"  Check log above for details.")
            sys.exit(1)

        # Verify output
        if not Path(check_path).exists():
            print(f"\n  ERROR: Stage {i} ({name}) completed but output NOT FOUND: {check_path}")
            sys.exit(1)

        print(f"\n  Stage {i}/{len(STAGES)}: {name} — DONE ✓")

    print(f"\n{'=' * 70}")
    print("  ALL STAGES COMPLETE")
    print(f"{'=' * 70}")
    print(f"\n  RDN model:     {BASE}/rdn_training/rdn_hsv_lifewatch.pth")
    print(f"  YOLO dataset:  {BASE}/processed/dataset.yaml")
    print(f"  YOLO model:    {BASE}/yolo_results/v8l_hsv_95/weights/best.pt")
    print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证语法**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import ast; ast.parse(open('e:/code/algaeimage/code/Polar_sim_0522/deploy/run_all.py').read())
print('Syntax OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add code/Polar_sim_0522/deploy/run_all.py
git commit -m "feat: add master orchestrator for full pipeline"
```

---

### Task 12: 本地集成测试（小样本验证）

**目标**: 在本地用 50 张 LifeWatch 图片验证全管线能跑通，确认无导入/运行时错误，然后提交。

- [ ] **Step 1: 本地测试 RDN 训练（50 张，10 epoch）**

```bash
cd e:/code/algaeimage/code/Polar_sim_0522 && \
A:/Anaconda_envs/envs/ican/python ml/train_rdn.py \
    --image-dir "E:/code/algaeimage/code/algae_guardian/data/Flowcam_images_training_split_metadata/Flowcam_images_training_split_metadata/Flowcam_images_training" \
    --output e:/code/algaeimage/code/Polar_sim_0522/ml/models/rdn_test.pth \
    --num-samples 50 --epochs 10 --batch 8 --lr 1e-4
```

预期: 正常完成 10 epoch 训练，输出 `rdn_test.pth` 文件。

- [ ] **Step 2: 本地测试管线（10 张）**

```bash
A:/Anaconda_envs/envs/ican/python -c "
import sys, os; os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
sys.path.insert(0, 'e:/code/algaeimage/code/Polar_sim_0522')
import numpy as np, cv2
from pathlib import Path
from hsv_polarization import hsv_to_polarization
from image_processing.polarization import PolarizationProcessor
from image_processing.enhancement import ImageEnhancer
from ml.reconstructor import PolarizationReconstructor

# Load 10 test images
img_dir = Path('E:/code/algaeimage/code/algae_guardian/data/Flowcam_images_training_split_metadata'
               '/Flowcam_images_training_split_metadata/Flowcam_images_training')
imgs = list(img_dir.rglob('*.jpg'))[:10]

pp = PolarizationProcessor()
enhancer = ImageEnhancer()

# No RDN (analytical fallback)
recon = PolarizationReconstructor(model_path=None)

for p in imgs:
    rgb = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
    sim = hsv_to_polarization(rgb, add_noise=False)
    I0, I45 = sim['I0'].astype(np.float32), sim['I45'].astype(np.float32)
    I90, I135 = sim['I90'].astype(np.float32), sim['I135'].astype(np.float32)
    # Analytical reconstruction
    out = recon.reconstruct(I0, I45, I90, I135, use_deep=False)
    S0_f = I0 + I90
    S1_f = I0 - I90
    S2_f = I45 - I135
    DoLP_f = np.clip(np.sqrt(S1_f**2+S2_f**2)/(S0_f+1e-10), 0, 1)
    AoP_f = 0.5 * np.arctan2(S2_f, S1_f)
    enhanced = pp.polarization_enhancement_v2(S0_f, DoLP_f, AoP_f)
    corrected = S0_f * (1.0 - 0.5 * DoLP_f.astype(np.float32))
    S0_norm = ((S0_f - S0_f.min()) / (S0_f.max() - S0_f.min() + 1e-10) * 255).astype(np.uint8)
    stacked = np.stack([S0_norm, enhanced, _norm_to_uint8(corrected)], axis=-1)
    final = enhancer.enhance(stacked, color_correct=True, clahe=True, dehaze=False)
    print(f'  {p.stem}: input {rgb.shape} → output {final.shape}')

print('Pipeline OK for 10 images')

def _norm_to_uint8(x):
    x = x.astype(np.float32)
    x_min, x_max = x.min(), x.max()
    if x_max - x_min < 1e-10:
        return np.zeros_like(x, dtype=np.uint8)
    return ((x - x_min) / (x_max - x_min) * 255).astype(np.uint8)
"
```

预期: 10 张全部输出 `Pipeline OK for 10 images`，无异常。

- [ ] **Step 3: 清理测试产物**

```bash
rm -f e:/code/algaeimage/code/Polar_sim_0522/ml/models/rdn_test.pth
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: local integration test passed"
```

---

## 附录 A：服务器操作流程

```
# === 步骤 1: 本地配置服务器地址 ===
# 编辑 deploy/setup_env.py、deploy/upload_all.py
# 修改 SERVER_HOST, SERVER_PORT, SERVER_PASSWORD

# === 步骤 2: 配置服务器环境 ===
cd e:/code/algaeimage/code/Polar_sim_0522
python deploy/setup_env.py

# === 步骤 3: 上传数据+代码 ===
python deploy/upload_all.py

# === 步骤 4: SSH 登录服务器运行全流程 ===
ssh root@<host> -p <port>
cd /data/lifewatch_hsv/code
python deploy/run_all.py

# === 步骤 5: 下载结果 ===
# 训练完成后
python deploy/download_results.py   # 下载 best.pt + metrics
```

## 附录 B：`reconstruct.py` 输出通道修正

`ml/reconstructor.py:178-185` 中的 `reconstruct_deep` 方法返回 `(H, W, 4)` 的 joint-normalized uint8 数组。在 `run_pipeline.py` 中，4 个通道分别作为 I0', I45', I90', I135' 使用，然后重新计算 Stokes。

**物理正确性**: 4 个重建通道是增强版偏振强度通道（非 S0/S1/S2），必须用 `S0 = I0' + I90'` 的标准 Stokes 重建公式重新计算。这是 Polar_sim_0520 管线中已验证的设计。
