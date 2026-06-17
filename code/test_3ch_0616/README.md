# test_3ch_0616 — 三通道融合管线测试

> 2026-06-16 | 测试三通道融合 [S0_norm, I_enh_v2, corrected] vs 单通道 I_enh×3
> 对应输出: `pic/pic_0616/11_三通道融合_0616测试/`

---

## 技术路线

### 全量管线

```
原始 TIFF (2080×1540)
  ↓
① 结构张量偏振模拟 (core_engine/polarization_sim.py)
  结构张量梯度法 + Malus 定律 → I0/I45/I90/I135 (4ch, float32, [0,1])
  ↓
② RDN 残差稠密网络去噪 (core_engine/reconstructor.py)
  4→16→12×RDB(6 dense layers)→4, 0.61M params, PSNR 62.46dB
  ↓
③ Stokes 参数解算 (core_engine/enhancement.py → compute_stokes)
  S0 = I0+I90, S1 = I0-I90, S2 = I45-I135
  DoLP = √(S1²+S2²)/S0, AoP = 0.5·arctan2(S2,S1)
  ↓
④ 三通道重建
  ┌─────────────────────────────────────────────┐
  │ R: S0_norm  = min-max(S0) × 255             │  总光强 → 保留形态
  │ G: I_enh_v2 = Norm(S0·(1+α-γ·DoLP+β·|sin(2AoP)|·DoLP)) │  偏振增强 → 突出纹理
  │ B: corrected = clip(S0_norm·(1-0.5·DoLP), 0, 255)     │  去散射 → 压低背景
  └─────────────────────────────────────────────┘
  → 三通道融合 [S0_norm, I_enh_v2, corrected] (H, W, 3) uint8
  ↓
⑤ YOLOv8s 检测 (core_engine/inference.py)
  对比: 1ch I_enh×3 (当前V2) vs 3ch fusion (本测试)
```

### I_enh v2 公式

```
I_enh = Norm( S0_norm × (1.0 + α - γ·DoLP + β × |sin(2·AoP)| × DoLP) )
α=0.6  基础 S0 增强
β=0.25 AoP 结构增强 (峰值 @45°/135°)
γ=0.35 DoLP 去散射抑制 (减法项)
```

### corrected 公式

```
corrected = clip( S0_norm × (1.0 - 0.5 × DoLP), 0, 255 )
```

与 S0_norm 同一尺度（min-max 归一化后），不做独立归一化。
对应原始代码: `image_processing/polarization.py → suppress_backscatter()`

### 三通道含义

| 通道 | 变量 | 物理含义 | 视觉作用 |
|------|------|----------|----------|
| R | S0_norm | 归一化总光强 | 保留藻体基本形态 |
| G | I_enh_v2 | 偏振增强灰度 | 突出边界、纹理、颗粒 |
| B | corrected | 去散射抑制 | 压低背景噪声、增强信噪比 |

---

## 对比项

| | 1ch I_enh×3 (当前V2) | 3ch fusion (本测试) |
|---|---|---|
| YOLO 输入 | [I_enh, I_enh, I_enh] — 单通道×3 | [S0, I_enh, corrected] — 三通道不同信息 |
| 训练数据匹配 | ❌ YOLO权重训练时用的是3ch | ✅ 与训练数据格式一致 |
| 信息量 | 1 通道有效信息 | 3 通道互补信息 |

---

## 运行

```bash
cd e:/code/codex/code/test_3ch_0616
A:/Anaconda_envs/envs/ican/python.exe run.py
```

输出目录: `../../pic/pic_0616/11_三通道融合_0616测试/`
