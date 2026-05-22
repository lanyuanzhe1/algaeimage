# LifeWatch 全流程重跑方案：HSV偏振 + RDN自训练 + YOLOv8l 95类

## 1. 变更摘要

| 维度 | 旧管线 (FMPD) | Polar_sim_0520 | **本方案 Polar_sim_0522** |
|------|-------------|---------------|--------------------------|
| 偏振模拟 | 结构张量+Malus | HSV (Yan 2024) | **HSV (Yan 2024)** |
| RDN 训练数据 | FMPD 293张 | FMPD 293张 | **LifeWatch ~3000张小样本** |
| RDN 输入分布 | 结构张量4ch | 结构张量4ch | **HSV 4ch** (同分布训练) |
| 数据集 | FMPD 293/5类 | FMPD 293/5类 | **LifeWatch 337k/95类** |
| YOLO 基模型 | yolov8l.pt | yolov8l.pt | **yolov8l.pt** |
| 训练规模 | 234/59 | 234/59 | **302,972 / ~13,000 / ~21,500** |

**核心变更：RDN 不再复用旧权重，而是在 LifeWatch HSV 数据上重新训练。** Polar_sim_0520 的旧 RDN 对 HSV 输入有效，但因为旧 RDN 训练数据（结构张量 4ch）和新数据（HSV 4ch）分布不同，自训练 RDN 能获得更好的重建质量。

## 2. 服务器

- **GPU**: RTX 4090 24GB (funhpc 容器)
- **基环境**: PyTorch 2.10.0, CUDA 12.8
- **需安装**: `ultralytics`, `opencv-python-headless`, `scipy`, `h5py`
- **磁盘**: ≥60GB
  - 原图 zip 537MB + 解压 ~1GB
  - YOLO 训练图 (320×320 JPEG) ~15GB
  - RDN 训练数据 (~3000 .npz) ~200MB
  - 模型权重 ~50MB

## 3. 管线总览

```
阶段0: 环境配置 (服务器)
    conda create + pip install

阶段1: 数据部署 (本地上传)
    Flowcam_images_training.zip + split文件 + 代码 + RDN训练脚本

阶段2: RDN 小样本训练 (~2h)
    3000张RGB → HSV 4ch → 加噪 → RDN训练(4→4去噪) → rdn_hsv_lifewatch.pth

阶段3: 全量管线处理 (~3-5h)
    337k RGB → HSV 4ch → 新RDN → I_enh v2 → YOLO训练图

阶段4: YOLOv8l 95类训练 (~25-35h)
    yolov8l.pt → 300 epochs → best.pt
```

## 4. 各阶段详细设计

### 4.1 阶段 0：服务器环境配置

```bash
# 基环境已有 PyTorch 2.10.0 + CUDA 12.8
# 额外安装
pip install ultralytics opencv-python-headless scipy h5py paramiko
```

验证：`python -c "import torch; print(torch.cuda.is_available()); from ultralytics import YOLO"`

### 4.2 阶段 1：数据部署

从本地上传：
1. `Flowcam_images_training.zip` (537MB) → 服务器 `/data/lifewatch_hsv/`
2. `train.txt`, `val.txt`, `test.txt` (split 文件) → `/data/lifewatch_hsv/splits/`
3. `classes.txt` (95 类名) → `/data/lifewatch_hsv/splits/`
4. Pipeline 代码 (hsv_polarization.py, reconstructor.py, enhancement.py, polarization.py)
5. RDN 训练脚本 + 全管线脚本

服务器端解压 zip → `/data/lifewatch_hsv/images/`（按 class 目录结构）

### 4.3 阶段 2：RDN 小样本训练

**目的**：让 RDN 学习 HSV 生成的 4 通道偏振数据的去噪/增强模式。

**训练数据构造**：
```
从 train split 随机抽取 3000 张 RGB 图
for each RGB:
    1. resize 到固定尺寸 (96×96, 填0 padding 保持比例)
    2. hsv_to_polarization(rgb, noise=True, noise_level=0.02)
       → I0, I45, I90, I135 (float32 [0, 1])
    3. input = 加噪版本 (noise_level=0.02 Gaussian)
       target = 无噪版本 (add_noise=False)
    4. 保存配对 → .h5 文件
```

**RDN 架构** (与当前一致)：
```python
RDN(num_channels=4, num_features=16, growth_rate=16,
    num_blocks=12, num_layers=6)
```

**训练配置**：
```yaml
optimizer: Adam
lr: 1e-4
batch_size: 32
epochs: 100
loss: L1Loss (MAE)
train/val split: 2800 / 200
input_size: 96×96 (固定尺寸, padding 保持比例)
scheduler: StepLR(step=80, gamma=0.1)
```

**输出**：`rdn_hsv_lifewatch.pth` (约 2.4MB)

**预估时间**：RTX 4090 上 ~1-2 小时

### 4.4 阶段 3：全量管线处理

```
for each split in [train, val, test]:
    for each RGB image:
        1. hsv_to_polarization(rgb, strength=1.0, noise=0.02)
           → I0, I45, I90, I135  (4通道 uint8)
        2. RDN.reconstruct_4ch(I0, I45, I90, I135)
           → recon_I0, recon_I45, recon_I90, recon_I135
        3. 从 recon 4通道计算 Stokes:
           S0 = I0 + I90
           S1 = I0 - I90
           S2 = I45 - I135
           DoLP = sqrt(S1²+S2²) / (S0+1e-10), clip [0,1]
           AoP = 0.5 * arctan2(S2, S1)
        4. I_enh v2:
           enhanced = S0_norm * (1 + 0.6 - 0.35*DoLP + 0.25*|sin(2*AoP)|*DoLP)
        5. Backscatter suppression:
           corrected = S0 * (1 - 0.5*DoLP) → normalize → uint8
        6. Stack 3ch [S0_norm, enhanced, corrected] → CLAHE → 保存为YOLO输入图
        7. 从 split 文件生成对应 YOLO label
```

**关键参数**：
- `polarization_strength=1.0`
- I_enh: `α=0.6, β=0.25, γ=0.35`
- `noise_level=0.02`
- YOLO 输出尺寸: `imgsz=320`（内部 resize，不改变原图比例）

### 4.5 阶段 4：YOLOv8l 95 类训练

```yaml
model: yolov8l.pt
epochs: 300
imgsz: 320
batch: 64
lr0: 0.001
lrf: 0.0001
optimizer: AdamW
patience: 50
device: cuda
seed: 0
deterministic: True
classes: 95
# 数据增强
hsv_s: 0.0           # 关键! 禁用 YOLO HSV 增强
hsv_v: 0.0           # 保持偏振通道物理含义
fliplr: 0.5
mosaic: 1.0
mixup: 0.1
erasing: 0.4
auto_augment: randaugment
close_mosaic: 10
warmup_epochs: 5
weight_decay: 0.0005
```

**预估时间**：RTX 4090 上 300 epochs × ~5min/epoch ≈ 25 小时（早停可能 15-20h）

## 5. 文件结构

### 5.1 本仓库 `code/Polar_sim_0522/`

```
Polar_sim_0522/
  hsv_polarization.py         ← 从 Polar_sim_0520 复制
  image_processing/
    __init__.py
    polarization.py           ← Stokes计算 + I_enh v1/v2
    enhancement.py            ← CLAHE + 色彩校正
  ml/
    __init__.py
    reconstructor.py          ← RDN 模型定义 + 推理 (4→4)
    train_rdn.py              ← [新增] RDN 训练脚本 (LifeWatch小样本)
  deploy/
    setup_env.py              ← [新增] 服务器环境配置
    upload_all.py             ← [新增] 上传数据+代码 到服务器
    run_pipeline.py           ← [新增] 服务器端全管线 (阶段3)
    train_yolo.py             ← [新增] 服务器端 YOLO 训练启动
  docs/
    design.md                 ← 本文件
```

### 5.2 服务器端

```
/data/lifewatch_hsv/
  images/                     ← 解压后的 337k RGB 原图 (按 class 目录)
  splits/
    train.txt, val.txt, test.txt, classes.txt
  rdn_training/               ← RDN 小样本训练数据 (临时)
    samples.h5
    rdn_hsv_lifewatch.pth     ← 训练产出
  processed/
    train/                    ← YOLO 训练图 (~303k 张 3ch JPEG)
    val/                      ← ~13k 张
    test/                     ← ~21.5k 张
  dataset.yaml                ← YOLO 数据集配置
  yolo_results/
    v8l_hsv_95/               ← 训练输出
      weights/best.pt
      results.csv
      args.yaml
```

## 6. 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| 95 类严重不均衡 (类别样本数从几十到几万) | 高 | per_class_weights 自动计算; 监控尾部类 recall |
| RDN 小样本训练 3000 张不够 | 低 | RDN 是 4→4 去噪, 任务简单; 不够则加到 5000 |
| 4090 24GB batch=64 OOM | 低 | 降 batch=48 或 imgsz=256 |
| 300 epochs 不够 (95类复杂) | 中 | patience=50 早停; 若未收敛则改 epochs=500 |
| hsv_s=0 必须禁用 YOLO HSV增强 | 高 | 训练前检查 args.yaml 确认 |
| 全管线 337k 处理耗时长 | 低 | 74×66 原图, HSV+RDN+I_enh < 10ms/张, 总计<1h |

## 7. 成功标准

- RDN 训练: val L1 loss < 0.01 (4→4 重建)
- YOLOv8l 95类: mAP50 ≥ 0.35 (LifeWatch 95类为复杂细粒度分类)
- 管线可复现: 所有步骤固定 seed
