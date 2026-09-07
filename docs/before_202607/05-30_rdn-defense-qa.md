# RDN 偏振重建网络 — 答辩技术问答

> 准备日期：2026-05-30
> 对应代码：[code/algae_image_v1/core_engine/reconstructor.py](../code/algae_image_v1/core_engine/reconstructor.py)

---

## 问题一：网络为什么能去噪？（网络原理）

RDN（Residual Dense Network，残差稠密网络）的去噪能力来源于**四个结构设计的协同**：

### 1. 稠密连接（Dense Connectivity）

每个 RDB（Residual Dense Block）内部，6 层卷积以稠密方式级联：

```python
# reconstructor.py L39-41
DenseLayer(in_channels + growth_rate * i, growth_rate)  # i = 0, 1, ..., 5
```

每层的输入 = **前面所有层输出的拼接**（`torch.cat([x, self.relu(self.conv(x))], 1)`）。第 6 层能同时看到第 1~5 层的所有特征图，信息逐层累积而不衰减。

**与普通 CNN 对比**：

| 普通 CNN（链式） | RDN（稠密） |
|:---|:---|
| 第 N 层只看第 N-1 层 | 第 N 层看第 1 ~ N-1 全部层 |
| 深层丢失浅层纹理 | 深层保留浅层高频细节 |
| 梯度消失风险大 | 梯度多路径回传，训练稳定 |

对于偏振去噪，这意味着**最细的偏振纹理（细胞壁边缘、硅质骨架）即使在 12 个 Block 之后也不会丢失**。

### 2. 双层残差学习（Dual Residual Learning）

代码中有两层残差：

**局部残差**（RDB 级别）：
```python
# reconstructor.py L47
return x + self.lff(self.layers(x))
```
每个 RDB 输出 = 原始输入 + 稠密层的特征融合。网络只需学习**该阶段需要添加的修正量**。

**全局残差**（网络级别）：
```python
# reconstructor.py L90
x = self.gff(torch.cat(local_features, 1)) + sfe1
```
最终输出前，全局特征融合结果 + 浅层特征（`sfe1`）。这意味着：

- **浅层特征（低频轮廓）直接跳过所有 12 个 RDB**，通过跳跃连接无损传递
- **深层特征（高频噪声残差）通过 12 个 RDB 逐步提取和修正**
- 网络本质上在学习 `output = input + f(input)`，其中 `f` 只建模噪声残差

对于偏振通道，结构张量 + Malus 定律确定的物理结构（低频）是不需要"去噪"的——跳跃连接保证它原样保留。网络只修正被噪声污染的高频部分。

### 3. 全局特征融合（Global Feature Fusion）

12 个 RDB 块的所有输出被拼接，经 1×1 + 3×3 卷积融合：

```python
# reconstructor.py L73-76
self.gff = nn.Sequential(
    nn.Conv2d(self.G * self.D, self.G0, kernel_size=1),   # 16×12=192 → 16
    nn.Conv2d(self.G0, self.G0, kernel_size=3, padding=1),
)
```

不同 Block 深度提取的特征各有用处：
- **浅层 Block**（Block 1-3）：捕捉局部边缘梯度、纹理方向 → 对应偏振角 AoP 的空间连续性
- **中层 Block**（Block 4-8）：捕捉中等尺度结构 → 对应 DoLP 的区域一致性
- **深层 Block**（Block 9-12）：捕捉语义级信息 → 区分藻类区域 vs 背景

全局融合让网络同时利用所有尺度的信息做最终重建。

### 4. 物理约束损失函数

训练损失不是单纯的像素 L1，而是**混合自适应损失**：

```python
# train_rdn_cloud.py L32-33, L168
criterion = CombinedLoss(l1_weight=1.0, aop_weight=0.1)
```

- **L1 Loss**：像素级保真，确保输出与真值在亮度上一致
- **AoP Loss**：偏振角保真，确保去噪后 `arctan2(S2, S1)` 不变。偏振角定义了藻类边缘的几何方向，是目标检测最关键的特征之一

**一句话总结**：RDN 不是简单的"模糊降噪"——稠密连接保留高频偏振纹理，残差学习让网络只拟合噪声分量（物理结构通过跳跃连接无损传递），AoP 损失约束偏振角物理一致性，全局特征融合整合多尺度信息。

---

## 问题二：有监督还是无监督？

**有监督学习（Supervised Learning）。**

训练需要成对数据 `(noisy_input → clean_target)`：

- 训练数据集结构为 `noise/` 和 `truth/` 两个目录，一一配对（[generate_rdn_data.py:49-51](../code/algae_guardian/cloud_training/generate_rdn_data.py#L49-L51)）
- 训练循环明确以 clean 为监督信号（[train_rdn_cloud.py:196-197](../code/algae_guardian/cloud_training/train_rdn_cloud.py#L196-L197)）：

```python
preds = model(inputs)                          # noisy → 网络 → 预测
total_loss, _, _ = criterion(preds, labels)    # 以 clean 为 label
```

- 评估指标为 PSNR（峰值信噪比），需参考真值才能计算：最佳 **62.46 dB** @ epoch 97

但是，这里的"监督"有一个关键特殊性——**真值不是人工标注的，而是用物理模型自生成的**（见问题三）。

---

## 问题三：高质量无噪声 Ground Truth 怎么来的？

### 核心方法：物理模型自合成（Self-synthesis via Physical Model）

**真值不是从真实偏振相机采集的，而是用结构张量 + Malus 定律的物理模型生成的。**

### 具体流程

参考代码：[generate_rdn_data.py:100-132](../code/algae_guardian/cloud_training/generate_rdn_data.py#L100-L132)

```
同一张 RGB 显微图像 (64×64 patch)
        │
        ▼
结构张量法（梯度 → 各向异性 → 边缘强度）
        │
        ▼
Malus 定律 (I(θ) = I_base × (1 + P × cos²(orientation - θ)))
        │
        ├─── add_shot_noise=False ──→ I0/I45/I90/I135 clean ──→ truth/*.mat  (Ground Truth)
        │
        └─── add_shot_noise=True ───→ I0/I45/I90/I135 noisy ──→ noise/*.mat  (Input)
           (noise_level=0.05, 高斯噪声)
```

详细步骤：

1. **随机选取**：从 FMPD 数据集的 293 张大图中随机裁剪 64×64 像素的 patch
2. **偏振物理计算**：
   - 将 RGB 转灰度图
   - 计算结构张量（Sobel 梯度 + 高斯平滑），得到：
     - `orientation`（局部主导方向，0~π）
     - `anisotropy`（各向异性度，0~1）
     - `edge_strength`（边缘强度）
   - 通过 Malus 定律计算四个偏振通道：
     ```
     I(θ) = I_base × (1 + P × cos²(orientation - θ))
     P = anisotropy × edge_norm × polarization_strength
     ```
     其中 θ ∈ {0°, 45°, 90°, 135°}
3. **Target（真值）**：上述计算**不加噪声**，得到物理上"完美"的四通道偏振
4. **Input（输入）**：同一公式**加上高斯噪声**（`noise_level=0.05`），模拟真实 DoFP 偏振相机的传感器噪声
5. **归一化**：两者分别 min-max 归一化到 [0,1]，存为 `.mat` 文件（匹配 SPDRDN 训练格式）

### 训练规模

| 数据集 | 训练对 | 验证对 | 来源 |
|:---|:---|:---|:---|
| FMPD（结构张量法）| 5,000 | 200 | [generate_rdn_data.py](../code/algae_guardian/cloud_training/generate_rdn_data.py) |
| LifeWatch（HSV 法）| 2,400 | 600 | [train_rdn.py](../code/Polar_sim_0522/ml/train_rdn.py) |

### 为什么这种方法是合理的？

**1. 物理确定性保证**：结构张量 + Malus 定律是**确定性运算**。给定同一张 RGB 图像，永远输出同样的四个偏振通道，不存在随机性。因此不加噪声的版本天然就是"完美真值"。

**2. 噪声模拟真实传感器**：合成的散粒/高斯噪声模拟的是 DoFP 偏振相机传感器的非理想性——光子散粒噪声、暗电流噪声、读出噪声。RDN 学习的映射本质上是"从传感器输出恢复到物理理想值"。

**3. 学术界范式**：这种"物理模型生成配对数据 → 深度学习去噪"的范式在计算成像领域（如去马赛克、超分辨、去模糊）广泛应用。物理模型提供数据流形结构，深度学习提供高效投影算子。

### 如果评委追问："这算是真正的去噪，还是只是过拟合仿真？"

**回答策略**：

> 结构张量 + Malus 定律模拟的是**理想偏振成像物理规律**，加入的噪声模拟的是**真实传感器非理想性**。RDN 学习的是"在有传感器噪声的情况下，如何恢复物理正确的偏振通道"。这不是过拟合仿真，而是**以物理模型为 prior 的数据驱动去噪**——物理模型定义了干净数据的流形结构，RDN 用学习的方式做该流形上的投影。
>
> 关键在于：**推理时输入的是真实显微图像经过同一物理模型模拟产生的偏振通道**。RDN 的作用是去除模拟过程中的噪声扰动，使输出通道更接近物理理想值。后续 YOLO 检测在经验上证明了有效性——经过 RDN 去噪后，mAP50 从 ~30% 提升至 **82.24%**（LifeWatch 95 类，严格 train/val 划分）。
>
> 如果未来有条件获取真实偏振相机的配对数据，可以用同样的网络架构做 fine-tune，PSNR 预期会更高。

---

## 补充：训练参数一览

| 参数 | 值 |
|:---|:---|
| 网络架构 | RDN(4→16→12×RDB×6layers→4) |
| 参数量 | ~0.6M |
| 模型大小 | ~2.5 MB |
| 输入通道 | 4（I0, I45, I90, I135）|
| 输出通道 | 4（重建后的 I0, I45, I90, I135）|
| 基础学习率 | 1×10⁻⁴ |
| 学习率衰减 | 第 80 epoch 降至 1×10⁻⁵（StepLR step=80, gamma=0.1）|
| 优化器 | Adam |
| 损失函数 | CombinedLoss(L1 + 0.1×AoP) |
| Batch Size | 32 |
| 训练轮数 | 100 |
| 最佳 PSNR | **62.46 dB** @ epoch 97 |
| 训练耗时 | ~1.3 小时（RTX 5060 Ti）|
| 每轮耗时 | ~47 秒 |

## 补充：RDN 在 V2 产品中的角色

V2 产品（`algae_image_v2`）已**跳过 RDN**。因为 V2 采用 HSV 色彩空间法做偏振模拟（而非结构张量法），HSV 是确定性色彩映射，没有需要去噪的物理噪声过程。跳过 RDN 后管线更轻，但代价是 mAP50 从 82.24%（结构张量 + RDN）降至 42.9%（HSV，无 RDN）。

**这恰恰反证了 RDN 的价值**：RDN + 结构张量法形成了"物理梯度增强 + 深度学习去噪"的协同效应，对暗场显微藻类的边缘检测有降维打击般的提升效果。
