# 云服务器 RDN 偏振重建网络训练指南

## 整体流程

```
本地                         云服务器 (GPU)
 │                              │
 ├─ 下载 LifeWatch/FMPD 数据     │
 ├─ generate_rdn_data.py         │
 │   → noise/*.mat               │
 │   → truth/*.mat               │
 │         │                     │
 │         └── data.zip ──────→  │
 │                    scp/rsync  │
 │                              ├─ unzip data
 │                              ├─ prepare.py → train.h5 + eval.h5
 │                              ├─ train.py    ← RDN 训练
 │                              └─ best.pth / epoch_*.pth
 │                                    │
 │                         └── 权重 ←─┘ 下载回本地
 │                              scp/rsync
 │
 ├─ 加载到 PolarizationReconstructor
 │   → reconstruct_deep() 使用真实权重
 └─ 完整 YOLO 检测训练
```

## 步骤 1：本地生成训练数据

```bash
# 确保 LifeWatch 数据已解压
cd algae_guardian

# 生成 RDN 训练对
python cloud_training/generate_rdn_data.py \
    --input-dir ./datasets/lifewatch/images/train \
    --output-dir ./data/rdn_training \
    --num-pairs 5000 \
    --patch-size 64
```

自动生成：
- `data/rdn_training/noise/` ← 模拟偏振输入（含噪声的 I0/I45/I90/I135）
- `data/rdn_training/truth/` ← 干净目标（原始图转换的4通道）

## 步骤 2：上传到云服务器

```bash
# 打包
tar -czf rdn_training_data.tar.gz data/rdn_training/

# 上传（替换为你的服务器地址）
scp rdn_training_data.tar.gz user@your-server:/path/to/SPDRDN/code/
```

## 步骤 3：云服务器上执行

```bash
# 解压
cd /path/to/SPDRDN/code/
tar -xzf rdn_training_data.tar.gz
mv data/rdn_training ../../data/noise  # 使用新数据替换原SPDRDN的noise和truth目录
# 实际上需要更细致的处理...

# 准备 h5 训练文件
python AOP-branch/prepare.py \
    --input-dir ../../data/noise \
    --label-dir ../../data/truth \
    --output-path ./data/train.h5 \
    --patch-size 64 --stride 32

# 或者直接使用我们提供的简化脚本
python cloud_training/train_rdn_cloud.py \
    --data-dir ./data/rdn_training \
    --epochs 100 \
    --batch-size 32 \
    --lr 1e-4
```

## 步骤 4：下载训练好的权重

```bash
# 从云服务器下载
scp user@your-server:/path/to/SPDRDN/code/checkpoint/best.pth \
    ./ml/models/rdn_polarization.pth
```

## 步骤 5：本地使用

训练好的 `rdn_polarization.pth` 会自动被 `ml/reconstructor.py` 加载：

```python
from ml.reconstructor import PolarizationReconstructor
reconstructor = PolarizationReconstructor(model_path="ml/models/rdn_polarization.pth")
reconstructor.load_model()
# 现在 reconstruct() 会使用训练好的 RDN 权重而非 fallback
```

## 环境依赖（云服务器）

```bash
# SPDRDN 需要：
pip install torch torchvision h5py scipy opencv-python tqdm numpy
# 推荐用 Conda：
conda env create -f SPDRDN/code/work_agent/cloud_server/environment_ican.yml
```
