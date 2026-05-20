# 藻影卫士 — 云服务器训练记录与操作指南

> 日期：2026-05-07
> 服务器：funhpc 容器云

---

## 一、服务器连接

```bash
ssh -p 30647 root@wv9jj98fgbb9ua7hunt.funhpc.com
```

密码：`cKMu9GtKi6wxYQotLQLfPE6RYKmsKKba`

### 环境激活
```bash
export PATH=/data/miniconda/bin:$PATH
source /data/miniconda/etc/profile.d/conda.sh
conda activate ican
```

### 环境规格
| 项目 | 内容 |
|------|------|
| GPU | NVIDIA GeForce RTX 5060 Ti (16GB VRAM) |
| CUDA Driver | 13.0 |
| Python | 3.11.15 (conda env: ican) |
| PyTorch | 2.11.0+cu128 |
| OpenCV | 4.13.0 |
| 系统盘 | 30GB (15GB 空余) |
| 数据盘 | `/data` 60GB (35GB 空余) |

---

## 二、RDN 训练记录

### 2.1 训练数据

训练数据由本地 `generate_rdn_data.py` 生成，方法为**梯度法偏振模拟**（方法一）：

```
RGB藻类图像 → 结构张量分析 → 模拟I0/I45/I90/I135 → 加噪 → 配对.mat
```

数据规模：
- 训练对：5000 patches（64×64×4）
- 评估对：200 patches
- 总大小：~350MB → H5格式后 629MB

### 2.2 训练参数

| 参数 | 值 |
|------|-----|
| 模型 | RDN (Residual Dense Network) |
| 输入通道 | 4 (I0, I45, I90, I135) |
| 输出通道 | 4 |
| num_features | 16 |
| growth_rate | 16 |
| num_blocks | 12 |
| num_layers | 6 |
| batch_size | 32 |
| 学习率 | 1e-4 (epoch 80 → 1e-5) |
| 优化器 | Adam |
| 损失函数 | CombinedLoss (L1 + AoP) |
| 训练轮数 | 100 |

> 注意：SPDRDN 的 `train.py` 中模型初始化**硬编码**了 `num_features=16, growth_rate=16`，
> 不受命令行参数 `--num-features --growth-rate` 影响。若需修改架构需直接改源码。

### 2.3 训练结果

| 指标 | 值 |
|------|-----|
| 最佳 PSNR | **62.46 dB** @ epoch 97 |
| 初始 Loss | 0.445 |
| 最终 Loss | 0.119 |
| 训练速度 | 初期 3.38 it/s → 后期 145 it/s |
| 每 epoch 耗时 | ~47 秒 |
| 总耗时 | ~1.3 小时 |

### 2.4 训练产出

**服务器路径：** `/data/rdn_training/`

```
/data/rdn_training/
├── checkpoint/
│   ├── epoch_9.pth  ~  epoch_99.pth   (每10 epoch保存)
│   └── best.pth                          (最佳权重，2.4MB)
├── train.h5          (5000 patches, 629MB)
├── eval.h5           (200 patches, 26MB)
├── training.log      (完整训练日志)
├── code/             (训练代码)
├── noise/            (输入.mat)
├── truth/            (目标.mat)
├── eval_noise/       (评估输入)
├── eval_truth/       (评估目标)
└── run_train.sh      (启动脚本)
```

### 2.5 监控命令

```bash
# 查看训练日志
tail -f /data/rdn_training/training.log

# 查看GPU状态
watch -n 2 nvidia-smi

# 查看进程
ps aux | grep train.py

# 查看权重
ls -lh /data/rdn_training/checkpoint/

# 磁盘空间
df -h
```

---

## 三、本地权重集成

### 3.1 下载 best.pth

```bash
# 从服务器下载到本地
scp -P 30647 root@wv9jj98fgbb9ua7hunt.funhpc.com:/data/rdn_training/checkpoint/best.pth \
    ./ml/models/rdn_polarization.pth
```

### 3.2 加载方式

```python
from ml.reconstructor import PolarizationReconstructor

reconstructor = PolarizationReconstructor(model_path="ml/models/rdn_polarization.pth")
reconstructor.load_model()  # 返回 True 表示加载成功

# 深度重建（4通道输入 → 3通道输出）
result = reconstructor.reconstruct(I0, I45, I90, I135, use_deep=True)
```

有 `.pth` 时自动用 RDN，没有则 fallback 到解析重建。

---

## 四、完整 Pipeline 顺序

```
RGB 藻类图像
  │
  ├─ Step 1: 模拟偏振采集
  │    simulate_polarization_channels()
  │    → I0, I45, I90, I135 (4通道)
  │
  ├─ Step 2: RDN 偏振重建
  │    PolarizationReconstructor.reconstruct()
  │    → 3通道重建图 (PSNR 62.46)
  │
  ├─ Step 3: 图像增强与去散射
  │    I_enh公式 + 后向散射抑制 + CLAHE
  │
  ├─ Step 4: 质量评分筛选
  │    Q = w_c·C + w_s·S + w_f·F - w_o·O - w_b·B
  │
  ├─ Step 5: YOLO 检测
  │
  ├─ Step 6: 时间序列跟踪
  │    C_k_bar(t) 滑动窗平均 + G_k(t) 增长速率
  │
  └─ Step 7: 融合预警
       R_k = α·f(C) + β·f(G) + γ·E + δ·H
       → 绿/黄/橙/红 四级预警
```

---

## 五、待办事项

- [ ] 下载 LifeWatch FlowCam 数据集（~555MB，Zenodo可直连）
- [ ] 下载 FMPD 数据集（前两次下载均损坏，需重试）
- [ ] 批量运行 RDN pipeline 生成 YOLO 训练集
- [ ] YOLO 模型训练（需安装 ultralytics）
- [ ] 真实偏振相机数据采集 → RDN fine-tune

---

## 六、注意事项

1. **代码在 `ican` conda 环境中运行**，本地路径：`A:\Anaconda_envs\envs\ican\python.exe`
2. RDN 模型架构必须与训练时一致（4通道入/出，features=16）
3. 运行需 PyTorch 和 torchvision，`ultralytics` 为可选项（仅YOLO训练时需）
4. test_pipeline.py 跳过 YOLO 步骤是正常的（无 ultralytics 时自动跳过）
5. 训练好的 `best.pth` 也可从服务器 `/data/rdn_training/checkpoint/` 重新下载
