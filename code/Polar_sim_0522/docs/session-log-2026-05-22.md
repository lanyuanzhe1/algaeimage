# Polar_sim_0522 运行日志

## 服务器

| 项目 | 值 |
|------|-----|
| 连接 | `ssh -p 44448 root@tssjfkari2ofchucsnow.deepln.com` |
| GPU | Tesla V100-SXM2-32GB (32 GB VRAM) |
| 环境 | Python 3.12, PyTorch 2.10.0+cu128, CUDA 12.8 |
| 工作目录 | `/data/lifewatch_hsv/` |

## 数据集

| 项目 | 值 |
|------|-----|
| 来源 | LifeWatch FlowCam (Flowcam_images_training.zip 537MB) |
| 总图片 | 337,541 张 (95 类) |
| train | 302,972 |
| val | 13,037 |
| test | 21,532 |
| 图片尺寸 | 中位数 74×66, 均值 90×79 |

---

## Stage 1: RDN 小样本训练

**时间:** 2026-05-22 11:02 - 12:00 (UTC+8)

**配置:**
- 架构: RDN(num_channels=4, num_features=16, growth_rate=16, num_blocks=12, num_layers=6)
- 参数: 612,356
- 训练样本: 3,000 张 (从 train split 随机选取)
- 80/20 分割: 2,400 train / 600 val
- patch_size=96, batch=48, lr=1e-4, epochs=100
- 优化器: Adam, scheduler=StepLR(step=80, gamma=0.1)
- 损失函数: L1Loss
- 输入: HSV 加噪 4 通道 (noise_level=0.02)
- 目标: HSV 干净 4 通道

**结果:**
| 指标 | 值 |
|------|-----|
| 总耗时 | 59.6 分钟 |
| Best val_loss | **0.002350** |
| Epoch 1: train/val | 0.0533 / 0.0182 |
| Epoch 100: train/val | 0.0024 / 0.0024 |
| 模型大小 | 2.5 MB |
| 输出路径 | `/data/lifewatch_hsv/rdn_training/rdn_hsv_lifewatch.pth` |

**收敛曲线:**
```
Epoch  1:  train=0.0533  val=0.0182
Epoch 10:  train=0.0048  val=0.0047
Epoch 20:  train=0.0038  val=0.0041
Epoch 30:  train=0.0035  val=0.0032
Epoch 40:  train=0.0032  val=0.0032
Epoch 50:  train=0.0031  val=0.0028
Epoch 60:  train=0.0028  val=0.0029
Epoch 70:  train=0.0027  val=0.0027
Epoch 80:  train=0.0026  val=0.0026
Epoch 90:  train=0.0024  val=0.0024
Epoch 100: train=0.0024  val=0.0024
Best val_loss: 0.002350
```

### RDN 新旧对比

**方法:** 200 张 LifeWatch HSV val 图片，比较 RDN 原始 float32 输出与干净目标的 L1。

| 方法 | L1 Loss | 降噪 |
|------|---------|------|
| 不加 RDN (原始噪声) | 0.0160 | baseline |
| 旧 RDN (FMPD 结构张量) | 0.1133 | -607% |
| **新 RDN (LifeWatch HSV)** | **0.0043** | **+72.8%** |

**结论:** 
- 新旧 RDN 架构完全相同 (178/178 keys 匹配)
- 旧 RDN 输入域不匹配（结构张量 vs HSV），像素级重建差
- 新 RDN 降噪 72.8%，通过 Stage 1，进入 Stage 2
- 注: L1 仅为像素级指标；旧 RDN 在 Polar_sim_0520 实验中配合 I_enh 后 YOLO F1=0.763 仍然有效，说明 RDN 的像素误差不直接等于下游检测性能

---

## Stage 2: 全量管线处理

(待执行)

## Stage 3: YOLOv8l 95 类训练

(待执行)
