# HSV 偏振模拟方案 — 本地运行设计

## 背景

现有方案 (`image_processing/polarization_sim.py`) 用**结构张量 + Malus 定律**从 RGB 模拟偏振，核心假设是"边缘=偏振"。

Yan et al. (Photonics, 2024) 提出了一种更简洁的替代方案：**RGB → HSV → AoP/DoLP/S₀ 直接映射**。本实验对比两种方案对下游增强图像的影响。

## 两种偏振模拟方法对比

### 方法 A：结构张量法（现有）

```
RGB → 灰度图 → 结构张量(梯度+Gaussian) → orientation/anisotropy/edge
    → P = anisotropy × edge_norm × strength
    → I(θ) = I_base × (1 + P × cos²(θ − orientation))
    → 4通道 I0/I45/I90/I135
```

- **核心假设**：边缘强的地方偏振度高，边缘方向即偏振方向
- **优点**：物理直觉合理（藻类细胞壁/硅藻纹路确实在边缘处偏振最强）
- **缺点**：透明内部无偏振信号，碎屑边缘产生假偏振，调制深度低（max 2×）

### 方法 B：HSV 映射法（新增）

```
RGB → HSV颜色空间
    → H (色相)  → AoP  = H × π / 180        [0, π)
    → S (饱和度) → DoLP = S / 255 × strength  [0, 1]
    → V (明度)  → S₀   = V / 255             [0, 1]
    → I(θ) = ½ S₀ × (1 + DoLP × cos(2(θ − AoP)))
    → 4通道 I0/I45/I90/I135
```

- **核心假设**：色素丰富的区域偏振度高（饱和度高），不同颜色结构对应不同偏振角
- **优点**：全图都有偏振信号（不限于边缘），利用了 RGB 全色信息，代码简洁
- **缺点**：HSV 和偏振之间没有严格物理对应，同样是启发式
- **特殊处理**：暗像素 (V<0.05) 处 DoLP 被压制，避免噪声放大

### 关键差异

| 维度 | 结构张量法 | HSV 映射法 |
|------|-----------|-----------|
| 偏振来源 | 梯度（边缘检测） | 颜色饱和度 |
| 信号密度 | 仅边缘区域有 | 全图均匀 |
| 对透明藻内部的响应 | 无 | 有（如果色素丰富） |
| 对背景碎屑 | 强边缘→强假偏振 | 低饱和→弱偏振 |
| 物理依据 | Malus + 结构张量 | 纯启发式映射 |
| 论文支撑 | IEEE SPL 2024 伪偏振方法 | Yan et al. Photonics 2024 |

## v2 管线流程

两种方法共享同一条下游管线：

```
                     ┌─────────────────────┐
RGB原图 ─────────────┤ 方法A: 结构张量+Malus │
                     │ 方法B: HSV 映射      │
                     └──────┬──────────────┘
                            ↓
                    4通道偏振图像
                   I0 / I45 / I90 / I135
                            ↓
              ┌─ Stokes 重建 ─────────────────┐
              │ S0 = I0+I90, S1 = I0-I90      │
              │ S2 = I45-I135, DoLP, AoP      │
              └──────────────┬────────────────┘
                             ↓
              ┌─ RDN 重建 (4ch → 3ch) ────────┐
              │ 输入: I0,I45,I90,I135         │
              │ 输出: S0', S1', S2'           │
              │ 模型: rdn_polarization.pth    │
              │ epoch 97, PSNR 62.46dB        │
              └──────────────┬────────────────┘
                             ↓
              ┌─ RDN不加载时: analytical fallback ─┐
              │ 直接使用 raw Stokes 的S0/S1/S2    │
              └──────────────┬────────────────┘
                             ↓
              ┌─ I_enh v2 公式 ───────────────┐
              │ AoP_mod = |sin(2·AoP)|         │
              │ I_enh = S0×(1+α-γ·DoLP        │
              │          +β·AoP_mod·DoLP)      │
              │ α=0.6, β=0.25, γ=0.35         │
              └──────────────┬────────────────┘
                             ↓
              ┌─ 三通道合成 ──────────────────┐
              │ Ch0: S0_norm (归一化强度)      │
              │ Ch1: I_enh (偏振增强)          │
              │ Ch2: corrected (散射抑制)      │
              │ corrected = S0×(1−0.5·DoLP)   │
              └──────────────┬────────────────┘
                             ↓
              ┌─ CLAHE + 颜色校正 ────────────┐
              │ 自适应直方图均衡 + 水下色彩校正│
              └──────────────┬────────────────┘
                             ↓
                    最终 3 通道增强图像
                    (用于 YOLO 检测)
```

## 重要提醒：RDN 领域偏移

当前 `rdn_polarization.pth` 是用**结构张量法**模拟的偏振数据训练的（`generate_rdn_data.py` 用 `simulate_polarization_channels` 生成 noise/truth 对）。

HSV 偏振模拟的输出分布与结构张量法**不同**（全图偏振 vs. 仅边缘偏振），直接喂给用结构张量数据训练的 RDN 存在**领域偏移**。

因此，对比实验应该做**两个维度**的 ablation：

| 配置 | 偏振模拟 | RDN | 说明 |
|------|---------|-----|------|
| HSV-RDN | HSV映射 | ON | 有领域偏移，但值得看实际效果 |
| HSV-ana | HSV映射 | OFF (analytical) | HSV纯方法，无RDN干扰 |
| Struct-RDN | 结构张量 | ON | 现有baseline |
| Struct-ana | 结构张量 | OFF | 结构张量纯方法 |

## 文件结构

```
Polar_sim_0520/
├── hsv_polarization.py    # HSV→偏振核心算法
├── run_pipeline.py        # 对比管线（支持 --skip-rdn 等参数）
├── docs/
│   └── pipeline_design.md # 本文档
└── output/
    ├── comparisons/       # 并排对比图
    ├── hsv_final/         # HSV管线最终输出 (293张)
    ├── struct_final/      # 结构张量管线最终输出
    └── stats.json         # 统计汇总
```

## 运行命令

```bash
conda activate ican
cd code/Polar_sim_0520

# 测试 5 张样本（快速验证）
python run_pipeline.py --num-samples 5

# 测试 5 张，跳过 RDN（纯 analytical）
python run_pipeline.py --num-samples 5 --skip-rdn

# 跑全部 293 张
python run_pipeline.py --all

# 调整偏振强度
python run_pipeline.py --num-samples 5 --pol-strength 0.5
python run_pipeline.py --num-samples 5 --pol-strength 1.5
```

## 评估策略

1. **视觉对比**：并排对比图直观判断两方法对藻类结构可见度的影响
2. **DoLP 统计**：比较两方法生成的 DoLP 均值/分布，评估偏振信号丰富度
3. **I_enh 统计**：比较增强通道的平均亮度，评估对比度增强效果
4. **下游验证（后续）**：将两方法的输出分别送入 YOLO，对比检测 mAP
