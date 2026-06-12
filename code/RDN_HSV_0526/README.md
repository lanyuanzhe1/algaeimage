# RDN_HSV_0526 — HSV 偏振 RDN 训练与管线实验

## 定位

为 FMPD (Freshwater Microscopy Phytoplankton Dataset) 5类明场显微图像训练
**HSV 色彩空间偏振模拟** 管线，作为 `algae_image_v2` 的核心处理引擎候选。

## 背景

V1 (`algae_image_v1`) 采用结构张量梯度法模拟偏振，在 LifeWatch 95类暗场 FlowCam
数据上达到 mAP50 84.7%。但 FMPD 是 **明场显微镜** 成像，与 LifeWatch 的暗场
FlowCam 成像原理不同——需要独立的偏振模拟方案和检测模型。

HSV 法的核心假设 (Yan et al., Photonics 2024):
- H (Hue) → AoP (偏振角)，颜色不同的结构有不同的光学各向异性取向
- S (Saturation) → DoLP (偏振度)，色素密集区偏振响应更强
- V (Value) → S0 (总光强)

## 目录结构

```
RDN_HSV_0526/
├── models.py                    # RDN 网络定义 (4→16→16→4, 12 blocks, 6 layers, ~0.6M)
├── datasets.py                  # H5 格式训练数据集
├── utils.py                     # PSNR 计算、AverageMeter
├── generate_hsv_data.py         # 生成 HSV 偏振训练对 (.mat)
├── prepare_h5.py                # .mat → H5 打包
├── train.py                     # RDN 训练脚本 (CombinedLoss: L1 + AoP)
├── evaluate_pipeline.py         # 完整管线评估 (含分块 RDN)
├── evaluate_pipeline_no_rdn.py  # 管线评估 (无 RDN，直接 HSV→I_enh→YOLO)
├── checkpoint/
│   ├── best.pth                 # 最佳 RDN 权重 (epoch 99, PSNR 22.03 dB)
│   └── epoch_*.pth              # 各 epoch 检查点
├── data/                        # 训练数据 (5000 train + 200 eval)
├── evaluation_report.json       # 含 RDN 管线评估结果
├── evaluation_report_no_rdn.json # 无 RDN 管线评估结果
└── README.md                    # 本文件
```

## 实验历程

### 实验 1: HSV RDN 训练 (2026-05-26)

**目的**: 为 HSV 偏振模拟训练专用的 RDN 去噪网络。

**方法**:
- 从 FMPD 293 张原图随机裁剪 5000 组 64×64 patches
- HSV 法生成含噪(noise=0.05)/纯净偏振通道对
- RDN 网络: 4ch→16feat→12 RDB×6 dense layers→4ch (~0.6M params)
- 损失函数: CombinedLoss (L1 + AoP consistency, 1:0.1)
- 训练: Adam lr=1e-4, batch=32, 100 epochs, RTX 4050 Laptop

**结果**:
- 最佳 PSNR: **22.03 dB** @ epoch 99
- 对比: 结构张量法 RDN = 62.46 dB
- 结论: HSV 颜色→偏振映射缺乏物理一致性，RDN 无法有效学习去噪模式

### 实验 2: 含 RDN 管线评估

**目的**: 测试 HSV 偏振→RDN→I_enh→YOLOv8l 全管线效果。

**方法**: 293张FMPD原图全走管线，与 COCO 标注计算 mAP50。
每张图用 512×512 分块 RDN 处理以适应 6GB 显存。

**结果**:
- **mAP50: 0.330**
- 速度: 4.44s/张
- 各类别: Spiroides 0.588, Woronichinia 0.549, Other-phyto 0.280,
  Non-phyto 0.144, Dinobryon 0.091

### 实验 3: HSV 无 RDN 管线评估

**目的**: 验证 RDN 是否必要——HSV 偏振模拟本身是确定性的颜色空间变换，
输出已平滑，理论上不需要去噪。

**方法**: RGB → HSV偏振(I0/I45/I90/I135) → I_enh v2 → YOLOv8l。
跳过 RDN 步骤。脚本: `evaluate_pipeline_no_rdn.py`

**结果**:
- **mAP50: 0.354** (+7.3% over RDN version!)
- 速度: **0.65s/张** (7× faster)
- 各类别: Woronichinia 0.644, Spiroides 0.594, Other-phyto 0.306,
  Non-phyto 0.136, Dinobryon 0.091

### 实验 3b: 结构张量 无 RDN 管线评估 (对照实验)

**目的**: 验证结构张量法是否也能跳过 RDN。结构张量法会加入模拟
光子噪声——去掉 RDN 意味着噪声直接进入 I_enh 和 YOLO。

**方法**: RGB → 结构张量偏振(含噪声) → I_enh v2 → YOLOv8l。
跳过 RDN 步骤。脚本: `evaluate_pipeline_struct_no_rdn.py`

**结果**:
- **mAP50: 0.069** (崩溃级别)
- 速度: 1.06s/张
- 仅 513 个检测 (GT 3162 个)
- 各类别均 < 0.15，Dinobryon 0.000

**结论**: 结构张量法**必须**配合 RDN 使用——其模拟的偏振噪声需要
RDN 去噪恢复。HSV 法则相反，RDN 反而有害。

## 完整对比

| 实验 | 管线 | mAP50 | 速度 | 脚本 |
|------|------|-------|------|------|
| 参考 | 结构张量 + RDN + YOLOv8l | **0.429** | — | — |
| 实验 2 | HSV + RDN(22dB) + YOLOv8l | 0.330 | 4.44s | `evaluate_pipeline.py` |
| **实验 3** | **HSV (无RDN) + YOLOv8l** | **0.354** | **0.65s** | `evaluate_pipeline_no_rdn.py` |
| 实验 3b | 结构张量 (无RDN) + YOLOv8l | 0.069 | 1.06s | `evaluate_pipeline_struct_no_rdn.py` |

## 结论

1. **结构张量 ↔ RDN 是强绑定**: 结构张量模拟噪声 → RDN 去噪 → 干净通道。
   拆开任一步骤都会崩溃 (mAP50 从 0.429 跌到 0.069)
2. **HSV ↔ 无RDN 是最优轻量方案**: HSV 确定性映射无需去噪，
   RDN 反而引入伪影。HSV 直出是 v2 的最佳选择
3. **HSV 仍不及结构张量+RDN**: mAP50 0.354 vs 0.429，差距 ~17%
4. **类别难度分化明显**: Woronichinia (0.644) / Spiroides (0.594)
   形态特征突出，检测稳定；Non-phyto (0.136) / Dinobryon (0.091)
   是所有方案的难题
5. **RDN PSNR 22dB 不足以恢复有用信号**: HSV 的 RDN 训练效果远
   差于结构张量 (62dB)，反映了颜色映射与物理偏振过程的本质差异

## 下一步

`algae_image_v2` 建议方案:
- 默认管线: **HSV 直出 (无RDN) + I_enh v2 + YOLOv8l**
- 备选管线: 结构张量 + RDN + YOLOv8l (精度更高但更慢)
- 前端支持管线切换
- 针对 Dinobryon / Non-phytoplankton 需补充训练样本

## 运行

```bash
conda activate ican
cd e:/code/codex/code/RDN_HSV_0526

# 实验 3: HSV 无 RDN (推荐用于 v2)
python evaluate_pipeline_no_rdn.py

# 实验 2: HSV 含 RDN (分块处理)
python evaluate_pipeline.py

# 实验 3b: 结构张量 无 RDN (对照)
python evaluate_pipeline_struct_no_rdn.py
```
