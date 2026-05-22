# LifeWatch HSV 偏振全链路 Docker 封装方案

为了应对您在 RTX 4090 服务器上后续部署、训练和运行新算法（`Polar_sim_0522`）时环境配置多变、重新编译耗时、CUDA 依赖繁杂的问题，我们将此套系统的 Python 编译环境、基础加速库彻底通过 **Docker + Nvidia Container Runtime** 进行固化。

以下是封装方案的核心分析、配置模板以及存储规划。

---

## 一、 存储空间分布精算 (Disk Space Analysis)

根据对您当前项目与数据集工件的量化，如果把所有东西塞进 Docker 会导致镜像崩溃。我们使用 **“环境在内、数据在外”** 的「外挂挂载模式」。

| 分区类型 | 对应物理载体 | 存放内容 | 预估占用大小 | 备注 |
| :--- | :--- | :--- | :--- | :--- |
| **容器基础镜像** | 容器内部 | Ubuntu、CUDA Toolkit 12.1、CUDNN、PyTorch、各 Python 依赖包、项目纯代码（不含数据）。 | **约 15.0 GB** | 100% 固化，一次编译，到处运行。 |
| **外挂数据卷 (Volume)** | 宿主机 SSD 磁盘 | 1. 原始 LifeWatch 数据集（images、labels）<br>2. 由其模拟出的一套偏振模拟中间产物（`polarized`）、RDN 增强后图片 55GB。 | **约 11.0 GB（冷数据）**<br>若含模拟增强态则为 **56.0 GB** | **不在镜像内部占用。** 宿主机映射进入。 |
| **结果与输出挂载** | 宿主机 SSD 磁盘 | 1. 训练得到的 `best.pt`、`rdn_hsv_lifewatch.pth`<br>2. 训练指标图表 `results.png` 等。 | **约 50.0 MB** | **不在镜像内部。** 确保容器销毁后数据不丢失。 |

---

## 二、 核心 Docker 配置文件

我们在新环境 [code/Polar_sim_0522/Dockerfile](code/Polar_sim_0522/Dockerfile) 部署了环境配置：

1. **[Dockerfile](code/Polar_sim_0522/Dockerfile)**：采用 NVIDIA 官方高性能官方机器学习 PyTorch 构建，集成 CUDA 动态加速组件，精简打包 Python 包缓存。
2. **[docker-compose.yml](code/Polar_sim_0522/docker-compose.yml)**：极速配置显卡直通、共享内存（SHM_SIZE 防止 DataLoader 报错溢出）及存储映射。

---

## 三、 零碎无痛运行步骤

当代码上传并登录到 RTX 4090 云服务器后，您再也无需手动配置 `Conda` 环境，只需以下三步：

### 步骤 1：构建 Docker 镜像 (仅需一次)
```bash
cd /data/lifewatch_hsv/code/Polar_sim_0522
docker compose build
```

### 步骤 2：启动并进入容器后台
```bash
docker compose up -d
docker compose exec algae_trainer bash
```

### 步骤 3：在容器一键运行新训练流程
此时您完全处于纯净、100% 兼容的 CUDA 12 + PyTorch 系统内，只需运行：
```bash
python deploy/run_all.py
```
所有训练产物、模型权重将自动回写到您宿主机的成果指定硬盘上！
