# 偏振重建与伪彩图生成公式

## 管线流程 (不可变更顺序)

```
RGB原图 → 偏振模拟(I0/I45/I90/I135) → RDN偏振重建 → I_enh增强 → 堆叠伪彩RGB → CLAHE+色彩校正 → YOLO输入
```

## Step 1: 偏振模拟 — simulate_polarization_channels()

基于结构张量的梯度偏振模拟，Malus 定律：

```
I(θ) = I_base × (1 + P × cos²(θ - θ_local))
```

其中：
- `I_base = gray / 255` — 灰度归一化强度
- `P = anisotropy × edge_norm × strength` — 偏振调制因子
- `θ ∈ {0°, 45°, 90°, 135°}` — 四个偏振方向
- `θ_local = 0.5 × arctan2(2·Jxy, Jxx - Jyy) mod π` — 局部主方向

藻类区域增强 (`green_ratio > 0.33 & gray < 200`)：
```
I0  *= (1 + 0.15)    # algae_factor = 0.3 × strength
I45 *= (1 + 0.30)    # 45° 响应最强
I90 *= (1 + 0.09)
I135 *= (1 + 0.18)
```

## Step 2: Stokes 重建 — reconstruct_stokes()

```
S0 = I0 + I90                        # 总强度
S1 = I0 - I90                        # 0°/90° 差
S2 = I45 - I135                      # 45°/135° 差
DoLP = √(S1² + S2²) / (S0 + ε)      # 线偏振度, clip [0,1]
AoP = 0.5 × arctan2(S2, S1)         # 偏振角, 弧度 [-π/2, π/2]
```

## Step 3a: I_enh 偏振增强 — polarization_enhancement() 【v1 当前公式】

每个分量**独立** min-max 归一化到 [0,1]：

```
S0_norm  = (S0 - min(S0)) / (max(S0) - min(S0))
DoLP_norm = (DoLP - min(DoLP)) / (max(DoLP) - min(DoLP))
AoP_norm  = (AoP - min(AoP)) / (max(AoP) - min(AoP))
```

加权求和后**再次** min-max 归一化：

```
I_enh = Norm( S0_norm + λ1·S0_norm + λ2·AoP_norm + λ3·DoLP_norm )
      = Norm( 1.3·S0_norm + 0.2·AoP_norm + 0.4·DoLP_norm )
```

默认 λ: `λ1=0.3, λ2=0.2, λ3=0.4`

**v1 已知问题：**
1. DoLP 未 clip 到 [0,1]——RDN 输出的 S0 包含零值像素，除以 ε=1e-10 导致 DoLP 爆炸到 10^12 量级。`corrected = S0*(1-0.5*DoLP)` 产生大量负值，clip 后 B 通道数值尺度崩坏，是不同图像 B/R 在 0.27~1.69 剧烈波动的根因
2. DoLP 被**加**入公式——高散射区域反而变亮，与"去散射"目标相反
3. AoP 是圆周期量 (0 和 π 等价)，min-max 归一化在周期断层处产生伪影
4. 三个分量独立归一化后再混合，破坏相对权重关系；二次归一化后 S0 主导

## Step 3b: 背向散射抑制 — suppress_backscatter()

```
backscatter = DoLP × strength          # strength = 0.5
corrected = S0 × (1.0 - backscatter)
          = S0 × (1.0 - 0.5 × DoLP)
```

方向正确（DoLP 高的区域被压低），但直接作用于原始 S0 数值，未归一化。

## Step 3c: 三通道伪彩堆叠

```
S0_norm = uint8( (S0 - min(S0)) / (max(S0) - min(S0)) × 255 )

pseudo_RGB = stack([
    R: S0_norm,        # 总强度 → 红通道
    G: I_enh,          # 偏振增强 → 绿通道
    B: corrected,      # 散射抑制 → 蓝通道
])

final = CLAHE(pseudo_RGB) + ColorCorrect(pseudo_RGB)
```

**本质：** 三个物理含义不同的灰度图强行塞入 RGB 三通道。通道间差异完全由公式权重决定，非自然色。

---

## v2 改进方案 (待实施)

### I_enh v2 公式

核心改动：
1. **DoLP 改为减法** — 高散射区域变暗（实际去散射）
2. **AoP 用 |sin(2·AoP)| 映射** — 连续无周期断层，峰值在 45°/135°（偏振对比度最强方向）
3. **所有分量作用在 S0 上** — 只做一次最终归一化，保留物理关系
4. **AoP × DoLP 交互** — 只在偏振强的区域做结构增强

```
AoP_mod = |sin(2 × AoP)|           # 连续映射到 [0,1]

I_enh = Norm( S0_norm × (1.0 + α - γ × DoLP + β × AoP_mod × DoLP) )
```

其中：
- `α` — S0 基础增强 (建议 0.6)
- `β` — 偏振结构增强系数 (建议 0.25)
- `γ` — 去散射强度系数 (建议 0.35)

### 背向散射 v2

```
corrected_raw = S0 × (1.0 - 0.5 × DoLP)
corrected = uint8( normalize(corrected_raw) × 255 )   # 与 S0_norm 相同归一化
```

v1 直接 clip 到 [0,255] 不归一化，导致 B 通道数值尺度与 R/G 通道不一致，是造成
不同图像 B/R 比值在 0.27~1.69 剧烈波动的主因。

### 伪彩堆叠 v2

```
pseudo_RGB = stack([
    R: S0_norm,         # 归一化总强度
    G: I_enh_v2,        # v2 偏振增强
    B: corrected_norm,  # 归一化散射抑制 (v2 已修正)
])
final = CLAHE(pseudo_RGB) + ColorCorrect(pseudo_RGB)
```

三通道均采用 min-max 归一化到 [0,255]，保持各通道纹理差异但统一亮度分布。
