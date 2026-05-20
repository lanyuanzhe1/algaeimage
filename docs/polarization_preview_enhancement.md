# 偏振预览图增强方案

> 日期：2026-05-08

## 背景

偏振模拟生成的 I0/I45/I90/I135 四通道数据，在计算 Stokes 参数并可视化时存在对比度不足的问题：

- **S1/I0-I90 和 S2/I45-I135** 是差分信号，数值量级远小于 S0，直接线性映射到灰度几乎不可见
- **DoLP** 大部分像素集中在低值区（0~0.3），线性显示时细节淹没
- **AoP** 的角度信息依赖 DoLP 决定饱和度，低 DoLP 区域颜色完全丢失

## 增强方法

### 1. S0|S1|S2 三面板并排图

对每个面板独立处理：

| 面板 | 处理流程 |
|------|---------|
| S0 (总光强) | Min-Max 归一化 → CLAHE(clip=2.0, grid=8) |
| S1 (0°/90° 差分) | 对称归一化 (0→gray128) → CLAHE |
| S2 (45°/135° 差分) | 对称归一化 (0→gray128) → CLAHE |

CLAHE（ Contrast Limited Adaptive Histogram Equalization）将原本集中在狭窄范围的灰度值拉伸至 0-255 全动态范围，使微弱偏振差异变得肉眼可见。使用 clip=2.0 限制噪声放大。

### 2. AoP 偏振角伪彩图

- **Hue** = AoP 角度值，[-π/2, π/2] 映射到 [0, 180]
- **Saturation** = `max(DoLP × 255, 100)`，保证饱和度不低于 ~0.4，使角度颜色在低 DoLP 区域仍然可见
- **Value** = S0 归一化 → CLAHE，保留结构细节

### 3. DoLP 线偏振度灰度图

- 线性映射到 [0, 255]
- CLAHE 拉伸局部对比度
- Gamma 校正 (γ=0.7) 提亮中低值区域

## 实现

脚本位置：`cloud_training/enhance_polarization_preview.py`

输入：`polarization/*.npz`（含 I0/I45/I90/I135）
输出：`enhanced_preview/*_stokes.jpg`、`*_aop.jpg`、`*_dolp.jpg`

## 与原始预览的对比

原始预览 (`preview/`) 使用线性归一化，适合数据验证；增强预览 (`enhanced_preview/`) 使用 CLAHE 等自适应方法，适合肉眼观察结构差异。两者互不替代。
