# Handoff: v8s_baseline Batch Prediction

> 2026-06-18 | 分支: `v2-platform`

## 当前任务

用 FMPD 数据集上效果最好的权重（YOLOv8s, mAP50 73.9%, epoch 233）对全部 293 张图片跑批量预测，输出带标注框的检测结果图。

## 背景

v8s_baseline 训练是 2026-05-08 在云 GPU（RTX 5060 Ti, `xnvsn4npo7blo10hunt:30906`，已下线）上完成的。本地只下载了权重和 results.csv，**预测图没拉下来**。搜索了另两台云服务器（`s1yqog8xe25kfzdhunt:30804`、`bq5zvtg8v4tkwu3hunt:30572`）均无 FMPD 预测数据。

昨天用该权重在本机 RTX 4050 上跑了 80/20 验证，拿到真实指标：mAP50 72.2%、mAP50-95 47.3%。分类别：螺旋藻 99.5%、沃氏藻 95.2%、锥囊藻 61.7%、其他浮游植物 61.1%、非浮游植物 43.6%。

## 运行步骤

### 1. 批量预测脚本已写好

`pic/pic_0616/batch_predict.py` — 调用 YOLO predict，对 293 张图批量输出。

```bash
cd e:/code/codex/pic/pic_0616
KMP_DUPLICATE_LIB_OK=TRUE "A:/Anaconda_envs/envs/ican/python.exe" batch_predict.py
```

环境：conda ican，`KMP_DUPLICATE_LIB_OK=TRUE` 解决 OpenMP 冲突。

### 2. 关键路径

| 用途 | 路径 |
|------|------|
| 权重 | `code/algae_image_v2/weights/best_v8s.pt` |
| 输入图（I_enh 增强后） | `code/algae_guardian/data/fmpd_rdn_output/images/` (293 jpg) |
| 输出目录 | `pic/pic_0616/v8s_predictions/` |
| 训练指标 | `code/algae_guardian/data/yolo_results/training/results.csv` |
| 训练配置 | `code/algae_guardian/data/yolo_results/training/args.yaml` |

### 3. 预测完成后

- 输出图复制到 `pic/pic_0616/v8s_predictions/`，更新 `docs/2026-06-15_image_inventory.md` 补充该目录
- RDN 灰度版预测图在 `code/algae_guardian/data/rdn_output_v2_灰度版本/yolo_results/`（176张），可一并整理

## 已完成的关联工作

- 阿里云 ECS（`120.27.15.235`）已同步最新 V2 代码 + 前端 + 4138 条数据库记录
- LiveMonitor.vue 已移除"视频演示"文字
- `pic/pic_0616/eval_summary_v8s.png` 已生成（四合一中文评估图）
- `docs/2026-06-15_image_inventory.md` 已补全 RDN 灰度版、LifeWatch 训练、v8l val_predict 等条目
- LifeWatch 84.7% 训练完整产出（49MB）已下载到 `code/algae_guardian/data/lifewatch_yolo_results/lifewatch_v2_v8s_320/`

## 云服务器凭证（敏感）

| 用途 | Host | Port | 状态 |
|------|------|------|------|
| ~~FMPD 训练~~ | `xnvsn4npo7blo10hunt.funhpc.com` | 30906 | 已下线 |
| LifeWatch 84.7% | `s1yqog8xe25kfzdhunt.funhpc.com` | 30804 | 在线 |
| LifeWatch HSV | `bq5zvtg8v4tkwu3hunt.funhpc.com` | 30572 | 在线 |

## Suggested Skills

- `superpowers:verification-before-completion` — 预测完成后验证输出图片数量和质量
- `superpowers:finishing-a-development-branch` — 任务结束后整理 commit
