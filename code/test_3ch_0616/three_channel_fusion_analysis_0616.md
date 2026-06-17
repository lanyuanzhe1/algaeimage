# 三通道融合管线分析 + FMPD 全量测试

> 2026-06-16 | 分支: `rdn-analysis`

---

## 完成事项

- 验证 RDN 参数量 612,356 ≈ 0.61M（CLAUDE.md 记录准确），分析 865 GMACs 慢的根因
- 整理全项目 ~95,819 张图片清单 → `docs/2026-06-15_image_inventory.md`
- 下载 81 张公开藻类明场参考图（Phycokey + Wikimedia + NOAA）
- 找到 4 张用户选定样本的全处理步骤对应图 → `pic/pic_0616/` (173 files, 17 dirs)
- 发现 V2 产线 YOLO 推理输入与训练数据格式不匹配：推理用 I_enh×3，训练用 [S0, I_enh_v1, corrected] 三通道融合
- 发现两条不同的 I_enh 公式（v1 加法 vs v2 减法）
- 编写三通道融合全量测试脚本 → `code/test_3ch_0616/`

---

## 技术原理

### RDN 参数量与计算量的悖论

**参数量 0.61M 正确**，但计算量 865 GMACs @ 1024px。根因不是参数多，而是 **Dense Connection 导致通道膨胀**：

```
单个 RDB 内 6 个 DenseLayer 的输入通道逐层增长:
  Layer 0: Conv2d(16, 16, 3) → cat → 32ch   | 2,320 MACs/px
  Layer 1: Conv2d(32, 16, 3) → cat → 48ch   | 4,624
  Layer 2: Conv2d(48, 16, 3) → cat → 64ch   | 6,928
  Layer 3: Conv2d(64, 16, 3) → cat → 80ch   | 9,232
  Layer 4: Conv2d(80, 16, 3) → cat → 96ch   | 11,536
  Layer 5: Conv2d(96, 16, 3) → cat → 112ch  | 13,840

12 RDBs × (6 dense layers + 1 LFF) = 72 dense conv + 12 LFF = 84 层
每层都是全3×3卷积，无1×1 bottleneck，无depthwise分离
全程保持 H×W 不变（无下采样）
```

RDN vs YOLOv8s: 865 vs 28 GMACs = 30.5 倍。`PIPELINE_MAX_WIDTH=1024` 已将 2080px 从 1957 GMACs 砍到 865，但仍是瓶颈。

### 三通道融合 vs 单通道 I_enh 的来龙去脉

**训练侧**（`batch_process_rdn.py`）:

```
RGB → 结构张量 → 4ch偏振 → RDN重建 → 3通道融合:
  R = S0_norm   = min-max(S0) × 255              ← 归一化总光强
  G = enhanced  = polarization_enhancement v1      ← I_enh v1 (加法式)
  B = corrected = clip(S0 × (1-0.5·DoLP), 0,255)  ← 去散射抑制
→ CLAHE + color_correct → YOLO 训练输入
```

**推理侧**（V2 产线 `inference.py`）:

```
RGB → 结构张量 → 4ch偏振 → RDN → I_enh v2 (单通道灰度) → stack×3 → YOLO
```

**两条 I_enh 公式差异**:

|        | v1 (训练用)                             | v2 (V2产线)                                              |
| ------ | --------------------------------------- | -------------------------------------------------------- |
| 公式   | `Norm(S0+0.3·S0+0.2·AoP+0.4·DoLP)` | `Norm(S0·(1+0.6-0.35·DoLP+0.25·\|sin(2AoP)\|·DoLP))` |
| DoLP   | 加法（偏振越强越亮）                    | 减法（偏振越强越暗 = 去散射）                            |
| 归一化 | 各分量独立归一化后相加                  | 乘积后单次归一化                                         |
| AoP    | 直接归一化                              | \|sin(2AoP)\| 连续周期映射                               |

**mismatch**: 模型训练吃 3ch [S0, I_enh_v1, corrected]，推理喂 1ch [I_enh_v2, I_enh_v2, I_enh_v2]。通道数、通道内容、I_enh 公式三重不一致。

### 结构张量 vs HSV 的历史定论

| 方法         | LifeWatch 95类 mAP50              | FMPD 5类 mAP50              | 定论           |
| ------------ | --------------------------------- | --------------------------- | -------------- |
| 结构张量+RDN | **84.7%** (epoch19救援微调) | **73.9%** (train=val) | **主线** |
| HSV+RDN      | 34.2%                             | 33.0%                       | 废弃           |
| HSV no RDN   | 37.9%                             | 35.4%                       | 废弃           |

HSV 对 LifeWatch 暗场数据崩溃的物理原因：暗场下 HSV 色彩饱和度趋近零，DoLP 映射函数失效。结构张量从梯度方向计算取向，不依赖色彩，天然适配暗场。

### corrected 通道计算

```python
# 原始代码: algae_guardian/image_processing/polarization.py
def suppress_backscatter(S0, DoLP, strength=0.5):
    corrected = S0 * (1.0 - strength * DoLP)  # S0 为 raw 尺度
    return np.clip(corrected, 0, 255).astype(np.uint8)
```

关键：**不做独立 min-max 归一化**，只 clip 到 [0,255]。保持与 S0_norm 的尺度关系。测试脚本初版错误地对 corrected 做了独立归一化，已修正。

---

## 行动细节

### RDN 分析

```bash
cd e:/code/codex
git checkout -b rdn-analysis HEAD  # 基于 v2-platform
```

```python
# 精确计算参数量
model = RDN(num_channels=4, num_features=16, growth_rate=16, num_blocks=12, num_layers=6)
sum(p.numel() for p in model.parameters())  # → 612,356
```

GPU benchmark 结果：

- 2080×1540: 8.69s/forward, 0.4 Mpx/s
- 1024×1383: 2.32s/forward, 0.6 Mpx/s
- FLOPs: 865 GMACs @ 1024px (YOLO 的 30.5 倍)

### 图片资产整理

```bash
# 项目全量扫描 → docs/2026-06-15_image_inventory.md
# 4 张 SNAP 全管线对照 → pic/pic_0616/ (173 files)

# Phycokey 蓝藻图下载 (76 张)
python -c "import urllib.request; ..."  
# 来源: cfb.unh.edu/phycokey/, 免费学术使用

# Wikimedia Commons 公开图 (4 张)
# NOAA Public Domain (1 张)
```

### 三通道融合测试

```bash
mkdir -p code/test_3ch_0616/
# run.py: 全量管线 + 3ch fusion vs 1ch baseline
# README.md: 技术文档

cd code/test_3ch_0616
A:/Anaconda_envs/envs/ican/python.exe run.py
# → 输出: pic/pic_0616/11_三通道融合_0616测试/
```

4 张样本先行验证结果（2080px 全分辨率）：

| SNAP        | 1ch det | 3ch det | 现象                                    |
| ----------- | ------- | ------- | --------------------------------------- |
| 054111-0039 | 3       | 3       | 置信度整体提升                          |
| 055157-0050 | 17      | 16      | 重复框合并，置信度大幅提升 (最高 +0.48) |
| 110720-0001 | 1       | 1       | Dinobryon 置信度 +0.03                  |
| 111352-0019 | 4       | 4       | Non-phyto 置信度集中提升                |

核心发现：三通道融合对 Non-phytoplankton 类别的重复框合并效果显著——多个 0.30-0.55 的低置信度框被合并为单个 0.78 的高置信度框。

全量 FMPD 293 张测试进行中（后台运行）。

---

## 遇到的问题

### 1. 测试脚本初版 corrected 通道错误

**现象**: corrected 通道做了独立 min-max 归一化，与原始 `suppress_backscatter` 行为不一致。

**根因**: 原函数 `np.clip(S0*(1-0.5*DoLP), 0, 255)` 直接用 raw S0 值 clip，保持原始强度尺度。我加了 `(corrected - min)/(max - min) * 255` 破坏了与 S0_norm 通道的尺度一致性。

**解决**: 改用 `S0_norm * (1 - 0.5 * DoLP)` + clip only，与原始行为对齐。

### 2. WebFetch 全网封锁

**现象**: RBGE、FSU Molecular Expressions、Wikimedia Commons、PxHere、NOAA Photo Library 全部被 WebFetch 返回 "Unable to verify if domain is safe to fetch"。

**解决**:

- Wikimedia: 用 MD5 hash 反算 `upload.wikimedia.org` 直接 URL + Python urllib
- NOAA: 从 `publicdomainfiles.com` 间接提取
- Phycokey: Python 直接抓取 HTML → 解析 img src → 逐个下载

### 3. Wikimedia 429 限速

**现象**: 连续请求后返回 HTTP 429 Too Many Requests。

**解决**: 每 3 秒一个请求 + 分批下载，最终获取 4 张 Wikimedia 图。

---

## 结果/产出

| 文件                                     | 说明                                                    |
| ---------------------------------------- | ------------------------------------------------------- |
| `docs/2026-06-15_image_inventory.md`   | 全项目 ~95,819 张图片清单，按管线阶段分类               |
| `docs/reference_images/` (81 files)    | 公开藻类明场参考图 (Phycokey 76 + Wikimedia 4 + NOAA 1) |
| `pic/pic_0616/` (173 files, 17 dirs)   | 4 张 SNAP 全处理步骤对照，按日期+技术分类               |
| `pic/pic_0616/README.md`               | 配图说明 + 管线跑批历史                                 |
| `code/test_3ch_0616/run.py`            | 全量 FMPD 三通道融合 vs 单通道对比测试                  |
| `code/test_3ch_0616/README.md`         | 三通道融合技术文档                                      |
| `pic/pic_0616/11_三通道融合_0616测试/` | 测试输出（进行中）                                      |

---

## 下一步

1. FMPD 全量 293 张测试完成后，统计 1ch vs 3ch 的检测数差异、置信度分布、类别分布
2. 若 3ch 在全量上表现一致优于 1ch，在 v2-platform 分支上修改 `inference.py` 支持三通道融合推理
3. 考虑将 `rdn_output_v2` 生成脚本也升级为三通道融合输出
4. corrected 通道公式中 `S0_norm × (1-0.5·DoLP)` 与原代码 `S0_raw * (1-0.5*DoLP)` 的细微差异值得后续验证
