# 数据集调研报告 — 藻影卫士

> 调研日期：2026-05-07
> 调研目标：寻找可用于"藻影卫士"项目训练的数据集，包含偏振显微藻类图像和普通显微藻类图像

---

## 一、关键结论

**公开数据集中不存在DoFP偏振显微藻类数据集。** 原因：
- DoFP（Division of Focal Plane）偏振相机属于特种设备，尚未在藻类监测领域大规模部署
- 偏振显微成像本身在藻类领域的公开数据极少
- 这反而是本项目技术壁垒的体现

**策略：路线分离**
- **偏振重建网络（RDN/SPDRDN）**：需用自己的偏振相机采集配对数据
- **YOLO藻类检测**：使用公开显微藻类数据集训练，偏振增强作为前置预处理

---

## 二、重点推荐数据集（用于 YOLO 检测训练）

### 1. LifeWatch FlowCam Phytoplankton Dataset v2 ⭐ 首选

| 项目 | 内容 |
|------|------|
| **链接** | [Zenodo v2 (2025)](https://zenodo-rdm.web.cern.ch/records/16679297) |
| **规模** | **337,514张** 图像 |
| **类别** | 95个分类（硅藻、甲藻、纤毛虫等） |
| **标注** | 分类标签，train/val/test = 80/10/10 |
| **成像方式** | FlowCam（流式成像），与本项目的暗场显微成像接近 |
| **许可** | CC BY 4.0 |
| **DOI** | `10.5281/zenodo.16679297` |
| **说明** | 比利时北海数据，含WoRMS分类ID，手工验证标签，是目前最大的开源浮游植物图像数据集 |

### 2. FMPD — Freshwater Microscopy Phytoplankton Dataset

| 项目 | 内容 |
|------|------|
| **链接** | [Zenodo](https://zenodo.org/records/11126643) |
| **规模** | 293张多物种图像 |
| **类别** | 5类（含产毒蓝藻 *Woronichinia naegeliana*、*Anabaena spiroides*） |
| **标注** | **COCO格式bbox标注**，可直接用于YOLO训练 |
| **成像方式** | 10×明场显微镜，2080×1540 px，.tif格式 |
| **DOI** | `10.5281/zenodo.11126643` |

### 3. Mega Microalgae Database（中国海洋二所）

| 项目 | 内容 |
|------|------|
| **来源** | *Marine Pollution Bulletin* 2025 |
| **规模** | **106,606张** / 142类（140种微藻+浮游动物+其他） |
| **特点** | 含28种潜在有害藻华（HAB）物种，使用IFCB成像 |
| **适用** | 最贴合有害藻华检测场景，但需联系作者获取 |

### 4. Chaohu Lake Phytoplankton Dataset

| 项目 | 内容 |
|------|------|
| **来源** | *Algal Research* 2024 |
| **规模** | 26,564张 / 68属 |
| **特点** | 巢湖实地采集，长尾分布，适合测试类别不均衡场景 |

### 5. KAUST 高分辨率彩色偏振图像数据集

| 项目 | 内容 |
|------|------|
| **链接** | [项目主页](https://vccimaging.org/Publications/Simeng2021Demosaic/) |
| **规模** | 40组场景 |
| **特点** | 高分辨率彩色偏振数据，含马赛克强度数据，可用于偏振仿真方法验证 |
| **适用** | 偏振重建网络的仿真训练参考，**非藻类数据** |

---

## 三、其他相关资源

### 学术资源

| 资源 | 说明 |
|------|------|
| [USEPA provisional HABs](https://github.com/USEPA/provisional_habs/) | 美国EPA有害藻华水质监测数据，含叶绿素/藻蓝蛋白 |
| [BloomOptix](https://agdatacommons.nal.usda.gov/articles/model/BloomOptix_Machine_Learning_Model/29042369) | USDA发布的Mask R-CNN模型，检测蓝藻，含训练数据 |
| [phytoClassUCSC](https://huggingface.co/patcdaniel/phytoClassUCSC) | Hugging Face上的浮游植物分类器模型（Xception） |
| [samitizerxu/algae-wirs](https://huggingface.co/datasets/samitizerxu/algae-wirs) | Hugging Face藻类分类数据集，17,035训练 + 6,494测试 |

---

## 四、训练策略建议

```
                     ┌──────────────────────────┐
                     │   LifeWatch 337k 数据集    │
                     │  (普通FlowCam显微图像)     │
                     └──────────┬───────────────┘
                                ▼
                     ┌──────────────────────────┐
                     │  RGB → 偏振模拟模块        │
                     │  (模拟DoFP 0°/45°/90°)     │
                     └──────────┬───────────────┘
                                ▼
                     ┌──────────────────────────┐
                     │  偏振增强 Pipeline         │
                     │  → Stokes → I_enh 公式    │
                     └──────────┬───────────────┘
                                ▼
                     ┌──────────────────────────┐
                     │  YOLO 基础模型训练         │
                     └──────────┬───────────────┘
                                ▼
                     ┌──────────────────────────┐
                     │  真实偏振数据 → 微调       │
                     │  (越用越准)               │
                     └──────────────────────────┘
```

### 优先下载

1. **LifeWatch FlowCam v2**（337k张，CC BY 4.0）— 量大、开源、成像方式接近
2. **FMPD**（293张，COCO标注）— 快速验证YOLO训练流程

---

## 五、LifeWatch 数据集执行记录

> 执行日期：2026-05-10
> 服务器：3bcl6l7ghrg2kl9hunt.funhpc.com:30920 (RTX 5060 Ti 16GB, CUDA 13.0)
> Conda环境：/data/miniconda/envs/ican

### 数据集概览

| 项目 | 值 |
|------|-----|
| 总图像 | 337,541 张 |
| 类别数 | 95 类 |
| Train/Val/Test | 302,972 / 13,037 / 21,532 (80/10/10) |
| 图像尺寸 | 50-300px FlowCam粒子缩略图 |
| 格式 | 分类标签 (每张图一个藻类粒子) |

### 执行管线

```
本地 zip 上传 → 服务器解压 → YOLO格式转换 → 偏振模拟 → RDN重建 → YOLO训练
```

### 核心命令

```bash
# 1. 上传数据集 (本地→服务器, 555MB)
scp Flowcam_images_training_split_metadata.zip root@server:/data/datasets/lifewatch/

# 2. 解压 (嵌套zip: 外层→内层→images)
cd /data/datasets/lifewatch/
unzip Flowcam_images_training_split_metadata.zip      # 外层 → 内层zip + metadata
unzip Flowcam_images_training_split_metadata.zip      # 内层 → images_all/ + dataset_files_equal/
unzip Flowcam_images_training.zip -d images_all/       # 337,541张图片 → 95个类目录

# 3. YOLO格式转换 (解析split文件, 创建labels)
python cloud_training/prepare_lifewatch.py \
    --data-dir /data/datasets/lifewatch \
    --output-dir /data/lifewatch_yolo \
    --splits train,val,test

# 4. 偏振模拟 (RGB → I0/I45/I90/I135 .npz)
python cloud_training/simulate_polarization.py \
    --input-dir /data/lifewatch_yolo/{split}/images \
    --output-dir /data/lifewatch_yolo/{split}/polarized \
    --polarization-strength 1.0

# 5. RDN偏振重建 (.npz → 增强图像)
python cloud_training/rdn_reconstruct.py \
    --input-dir /data/lifewatch_yolo/{split}/polarized \
    --model /data/rdn_training/checkpoint/best.pth \
    --output-dir /data/lifewatch_yolo/{split}/rdn_enhanced \
    --img-size 640 --device cuda

# 6. YOLOv8训练
python cloud_training/train_lifewatch_yolo.py \
    --data /data/lifewatch_yolo/dataset.yaml \
    --model yolov8n.pt \
    --epochs 100 --batch 128 --imgsz 320 \
    --name lifewatch_v8n_100e
```

### 执行统计

| 步骤 | Val (13k) | Test (21.5k) | Train (303k) |
|------|-----------|-------------|-------------|
| YOLO格式转换 | ~2min | ~3min | ~15min |
| 偏振模拟 | ~2min | ~5min | ~50min |
| RDN重建 | ~4min | ~7min | ~90min (预估) |

### 关键决策

- **imgsz=320**: 原图50-300px，用640浪费显存且无效上采样
- **batch=128**: RTX 5060 Ti 16GB 对v8n在320px可撑住
- **full-image bbox**: FlowCam每图单粒子，YOLO标签格式 `class_id 0.5 0.5 1.0 1.0`
- **nohup执行**: 长任务使用nohup防止SSH断开中断
- **原始图训练**: FlowCam图像已干净，偏振+RDK增强对这类粒子图的增益待验证
