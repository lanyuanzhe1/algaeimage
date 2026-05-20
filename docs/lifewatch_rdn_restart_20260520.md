# LifeWatch RDN 重建重启报告

**日期**: 2026-05-20  
**服务器**: RTX 5060 Ti 16GB
```
SSH: ssh -p 30906 root@xnvsn4npo7blo10hunt.funhpc.com
密码: 1NtsRxTIlXBCeRLOSX3nVvkLeXXE8SaI
环境: /data/miniconda/envs/ican/
```

## 背景

LifeWatch FlowCam 浮游植物数据集：95 类，~337k 张粒子图像（train 302,972 / val 13,037 / test 21,532）。偏振模拟已在之前完成（302,972 个 .npz），但 RDN 重建中断在 71,766/302,972（23.7%）。上次 YOLO 训练直接使用原始 RGB 图像，未走偏振增强管线。

## 关键修复

### 1. Stokes 计算错误修复（严重 Bug）

**问题**：RDN 输出 4 通道偏振强度 (I0_rec, I45_rec, I90_rec, I135_rec)，但代码将其前 3 通道直接当作 Stokes 参数使用：

```python
# 错误
S0 = recon_3ch[:, :, 0]           # 实际是 I0_rec，不是总强度
S1 = recon_3ch[:, :, 1] * 2 - 128 # 实际是 I45_rec，不是 S1
S2 = recon_3ch[:, :, 2] * 2 - 128 # 实际是 I90_rec，不是 S2
```

**修复**：取 RDN 全部 4 通道输出，按 Stokes 公式计算：

```python
# 正确
I0_rec, I45_rec, I90_rec, I135_rec = recon_4ch[:,:,0], ..., recon_4ch[:,:,3]
S0 = I0_rec + I90_rec
S1 = I0_rec - I90_rec
S2 = I45_rec - I135_rec
DoLP = sqrt(S1² + S2²) / S0
AoP = 0.5 * arctan2(S2, S1)
```

涉及文件：`ml/reconstructor.py`（RDN 输出改为 4 通道）、`cloud_training/prepare_lifewatch.py`

### 2. I_enh v1 → v2

增强公式从 v1（DoLP 加法）切换到 v2（DoLP 减法去散射）：

```
v2: I_enh = Norm(S0 * (1 + α - γ·DoLP + β·|sin(2·AoP)|·DoLP))
```

默认参数：α=0.6, β=0.25, γ=0.35

### 3. 新增功能

- **YOLO 输入预览**：每个 split 的 `rdn_enhanced/YOLO_input_preview_{date}/` 保存训练输入图像的抽样副本（硬链接，不占额外空间）
- **断点续跑**：RDN 重建自动跳过已存在的输出文件

## 服务器清理

| 操作 | 释放空间 |
|------|----------|
| 删除 `/data/coding/` (旧代码) | 2.6 GB |
| 删除 `/data/fmpd_rdn_output/` (旧 FMPD) | 0.5 GB |
| 删除 `/data/FMPD.zip` | - |
| 删除 `/data/data/`, `/data/tests/`, `/data/backend/` | - |
| 删除 `/data/yolov8n.pt` | - |
| 删除 train/polarized/ (RDN 完成后) | 13 GB |
| 删除 train/images/ (原始副本，改用 rdn_enhanced) | ~2 GB |
| 删除旧 YOLO 训练结果、日志 | - |

**磁盘**: 90G 总量 → 从 100% 降至 51%，45GB 空闲

## 当前运行

完整管线从偏振模拟重新开始（`prepare_lifewatch.py --splits train`）：

```
原始 RGB → 偏振模拟 (I0/I45/I90/I135 .npz) → RDN 重建 → I_enh v2 增强
```

- 阶段 1: 图像复制 (302,972 文件) — ~86 files/s
- 阶段 2: 偏振模拟 — CPU 密集
- 阶段 3: RDN 重建 — GPU，~60 it/s，预计 1.4 小时

## pipeline 配置

```yaml
# dataset.yaml
path: /data/lifewatch_yolo
train: train/rdn_enhanced/images
val: val/rdn_enhanced/images
test: test/rdn_enhanced/images
nc: 95
```

## 文件变更

| 文件 | 变更 |
|------|------|
| `ml/reconstructor.py` | reconstruct_deep 返回 4 通道 |
| `cloud_training/prepare_lifewatch.py` | Stokes 计算修复 + I_enh v2 + 预览 + 断点续跑 |
| `cloud_training/cloud_ssh.py` | 更新服务器地址和密码 |

## 后续

- 等待 train 管线完成
- 启动 YOLO 训练（用偏振增强后的图像）
- 建议：v8n 或 v8s 起步，imgsz=320, batch=128, epochs=100
