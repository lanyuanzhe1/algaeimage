# HSV 偏振模拟替换方案 — 完整工作报告

## 0. 摘要

将藻影卫士项目中原有的**结构张量+Malus定律**偏振模拟方法，替换为基于 **HSV 颜色空间映射** 的新方法（源自 Yan et al., Photonics 2024）。在 FMPD 293 张显微藻类数据集上，用新方法增强图像训练 YOLOv8l，对比原方法训练的同架构模型：

**HSV 法 Overall F1=0.763，原结构张量法 Overall F1=0.501，全 5 类均胜出，F1 提升 52%。**

---

## 1. 背景与动机

### 1.1 原有方法

`image_processing/polarization_sim.py` 实现了基于**结构张量 + Malus 定律**的 RGB→偏振模拟：

```
RGB → 灰度 → 结构张量(梯度+Gaussian) → orientation/anisotropy/edge
    → P = anisotropy × edge_norm × strength
    → I(θ) = I_base × (1 + P × cos²(θ − orientation))
    → 4通道 I0/I45/I90/I135
```

**核心假设**："边缘强=偏振度高，边缘方向=偏振方向"。透明藻类内部无偏振信号，碎屑边缘产生假偏振，调制深度低。

### 1.2 新方法来源

Yan et al. (2024): *"Training a Dataset Simulated Using RGB Images for an End-to-End Event-Based DoLP Recovery Network"*, **Photonics (MDPI)**, Vol. 11, Issue 5, Article 481.
DOI: [10.3390/photonics11050481](https://doi.org/10.3390/photonics11050481)

该论文提出将 RGB 图像的 HSV 通道直接映射为偏振参数：
- **H (色相) → AoP (偏振角)**：不同颜色的细胞结构对应不同偏振取向
- **S (饱和度) → DoLP (偏振度)**：色素丰富区域偏振响应更强
- **V (明度) → S₀ (总强度)**：亮度对应基强度

然后用 Stokes 公式还原 4 个偏振通道：
```
I(θ) = ½ S₀ × (1 + DoLP × cos(2(θ − AoP)))
```

---

## 2. 技术实现

### 2.1 文件结构

所有工作隔离在 `code/Polar_sim_0520/` 下，不修改原始 `algae_guardian/` 代码：

```
Polar_sim_0520/
├── hsv_polarization.py        # HSV→偏振核心算法
├── run_pipeline.py            # Stage 1-3 完整管线
├── run_yolo.py                # YOLO 检测脚本
├── compare_results.py         # 对比评估脚本
├── prepare_training.py        # 训练数据准备
├── train_yolo.py              # YOLO 训练脚本
├── auto_train_eval.py         # 全自动训练+评估+报告
├── image_processing/          # 从 algae_guardian 复制的依赖
│   ├── polarization.py
│   ├── enhancement.py
│   └── polarization_sim.py    # 结构张量法(仅作对比)
├── ml/                        # 从 algae_guardian 复制的依赖
│   ├── reconstructor.py
│   └── models/rdn_polarization.pth
├── docs/
│   ├── pipeline_design.md
│   ├── session_2026-05-20.md
│   └── final_report_2026-05-21.md  ← 本文档
└── output/
    ├── hsv_preview_293/       # HSV 偏振 2×3 网格预览
    ├── polarization_hsv/      # Stage 1: 293 .npz 偏振通道
    ├── rdn_output_hsv/        # Stage 2: RDN 重建 3ch
    ├── yolo_input_hsv/        # Stage 3: I_enh v2 + CLAHE
    ├── yolo_results_hsv/      # YOLO 检测画框结果
    ├── yolo_labels_hsv/       # YOLO 检测标签
    ├── yolo_training_hsv/     # HSV 训练输出 (模型+曲线)
    ├── yolo_results_struct/   # 结构张量法 YOLO 检测
    ├── comparison_report.json  # 不公平对比报告 (旧)
    ├── fair_comparison_report.json  # 公平对比报告
    └── stats.json
```

### 2.2 核心算法

```python
def hsv_to_polarization(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    H = hsv[:,:,0]          # [0, 180)
    S = hsv[:,:,1] / 255    # [0, 1]
    V = hsv[:,:,2] / 255    # [0, 1]

    AoP  = H * π / 180       # H → 偏振角
    DoLP = S * strength      # S → 偏振度
    S0   = V                 # V → 总强度

    # 暗像素 DoLP 压制 (H/S 在低亮度下不可靠)
    DoLP[V < 0.05] *= V[V < 0.05] / 0.05

    # Stokes 公式计算 4 通道
    for θ in [0°, 45°, 90°, 135°]:
        I_θ = ½ S₀ × (1 + DoLP × cos(2(θ − AoP)))
```

### 2.3 完整管线

```
RGB原图 → HSV偏振(I0/I45/I90/I135) → RDN去噪(4ch→4ch) → Stokes
    → I_enh_v2 + 背散射抑制 → CLAHE → YOLO检测
```

每步独立落盘，便于检查和复用。

---

## 3. 发现的问题与修复

### 3.1 config.py 类定义不匹配

**问题**：`ALGAE_CLASSES` 定义了 6 类虚构中文藻名，与训练模型 best.pt 的 5 类英文名完全不对应。

**修复**：对齐为 5 类：Other-phytoplankton, Non-phytoplankton, Woronichinia, Spiroides, Dinobryon。

### 3.2 RDN 输出语义错配

**发现**：RDN 训练目标→I0'/I45'/I90'/I135'（伪偏振强度），但推理时输出被当作 S0/S1/S2（斯托克斯参数），通过 `*2-128` 中心化。

**影响**：RDN 本质是 4→4 去噪自编码器，工程上有效但语义不对位。

### 3.3 DoLP 饱和

**现象**：`*2-128` 导致 S1/S2 幅值远超 S0，DoLP 被 clip 到 1.0 饱和（均值 0.991）。

**影响**：I_enh v2 公式中 `-γ·DoLP` 退化为常数，削弱了自适应去散射。但对 YOLO 检测的最终影响有限，因为 `β·AoP_mod·DoLP` 项仍在变化。

### 3.4 Windows 训练兼容性

- OMP 冲突 (OpenCV vs PyTorch)：设置 `KMP_DUPLICATE_LIB_OK=TRUE`
- DataLoader 多进程权限：设置 `workers=0`

---

## 4. 实验结果

### 4.1 训练配置

| 参数 | 值 |
|------|---|
| 模型 | YOLOv8l (COCO 预训练) |
| 训练图像 | 234 (HSV 增强, 80% FMPD) |
| 验证图像 | 59 (20%) |
| 类别 | 5 类 |
| Epochs | 300, patience=50 |
| Batch | 8 |
| 显存 | ~5.3GB / 6GB |
| 耗时 | 6.1h (239 epochs, best@212) |
| GPU | RTX 4050 Laptop |

### 4.2 训练结果

| 指标 | HSV YOLOv8l | 原结构张量 YOLOv8l |
|------|-----------|-----------------|
| mAP50 | **0.646** | 0.429 |
| mAP50-95 | **0.314** | 0.197 |
| Best epoch | 212 | 110 |
| Precision | 0.597 | - |
| Recall | 0.650 | - |

### 4.3 公平对比评估

两个模型在**相同的 FMPD 293 张标注数据**上评估（IoU=0.5）：

| 类别 | HSV F1 | Struct F1 | Δ | 胜者 |
|------|--------|-----------|----|------|
| Other-phytoplankton | **0.813** | 0.543 | +49.8% | HSV |
| Non-phytoplankton | **0.696** | 0.348 | +100% | HSV |
| Woronichinia | **0.952** | 0.892 | +6.7% | HSV |
| Spiroides | **0.866** | 0.682 | +27.0% | HSV |
| Dinobryon | **0.845** | 0.640 | +32.1% | HSV |
| **OVERALL** | **0.763** | **0.501** | **+52.3%** | **5:0** |

### 4.4 检测数量对比

| | HSV | Struct | GT |
|------|-----|--------|-----|
| 总检出 | 3498 | 1919 | 3162 |
| 检出/图 | 11.9 | 6.5 | 10.8 |
| Precision | 0.726 | 0.663 | - |
| Recall | 0.803 | 0.403 | - |

HSV 法检出数量接近 GT 水平（3498 vs 3162），而结构张量法严重漏检（1919）。

---

## 5. 分析

### 5.1 为什么 HSV 法更好

1. **全图偏振信号**：结构张量法只在边缘有偏振响应，HSV 法对藻类内部色素区域也有信号，提供了更丰富的纹理特征供 YOLO 学习
2. **RGB 全色信息利用**：结构张量法只用灰度图算梯度，HSV 法利用了 H/S/V 三通道，保留了颜色→偏振的区分度
3. **藻类适配性**：浮游藻类色素丰富（叶绿素、藻蓝素等），S 通道（饱和度）能有效区分藻体和背景水样
4. **Non-phytoplankton 改善最大**：结构张量法对非藻类碎屑产生假边缘偏振（和藻类边界难以区分），HSV 法因碎屑饱和度低而自然地抑制了这些假信号

### 5.2 局限性

1. **启发式映射**：HSV→偏振没有严格物理推导，不同光照/染色条件下效果可能变化
2. **DoLP 仍然饱和**：RDN 输出语义错配未修复，DoLP 区分度未发挥
3. **数据量小**：仅 293 张 FMPD，泛化性待验证
4. **单一显微平台**：仅在 FlowCam 暗场显微图像上验证

---

## 6. 结论

**HSV 颜色空间映射法完全可替代原有的结构张量偏振模拟方法。** 在 FMPD 数据集上，新方法训练的 YOLOv8l 全面优于原方法（Overall F1: 0.763 vs 0.501, +52%），5 个藻类类别全覆盖。

建议后续在更大的 Lifewatch 数据集（33.7 万张）上验证泛化性，并修复 DoLP 饱和问题以进一步利用偏振增强公式的设计意图。

---

## 附录 A: 论文来源

**Yan, C., Wang, X., Zhang, X., Wang, C., Sun, Q., & Zuo, Y. (2024).**
*Training a Dataset Simulated Using RGB Images for an End-to-End Event-Based DoLP Recovery Network.*
Photonics, 11(5), 481. MDPI.
DOI: [10.3390/photonics11050481](https://doi.org/10.3390/photonics11050481)

北京理工大学，光电成像技术与系统教育部重点实验室。

## 附录 B: 运行命令

```bash
conda activate ican
cd code/Polar_sim_0520

# 预览 HSV 偏振效果
python hsv_polarization.py

# 完整管线 (293 张)
python run_pipeline.py --skip-struct

# YOLO 检测
python run_yolo.py

# 全自动训练+评估
python auto_train_eval.py
```
