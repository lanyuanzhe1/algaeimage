# 选用 NVIDIA PyTorch 官方精简开发镜像，天然集成 CUDA 12.1 + Python 3.10/3.11 + PyTorch
FROM nvcr.io/nvidia/pytorch:23.10-py3

# 设置工作目录
WORKDIR /app

# 设置非交互和时区变量
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

# 安装系统运行依赖（如 FFmpeg, OpenCV 图像库所需的动态链接库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置清华 pip 国内镜像源，加快构建速度，同时升级 pip
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 只安装全链路必须的 Python 第三方依赖
# 包含 ultralytics(YOLOv8), opencv, pandas, scipy, scikit-image, paramiko(用于SSH)
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    ultralytics \
    opencv-python-headless \
    pandas \
    scipy \
    scikit-image \
    paramiko \
    matplotlib \
    tqdm

# 复制 Polar_sim_0522 整个项目代码进容器
COPY code/Polar_sim_0522/ /app/code/

# 设置 Python 根路径，确保不管在容器哪个目录下跑脚本，都可以无障碍 import "deploy" 或 "image_processing"
ENV PYTHONPATH=/app/code

# 声明外挂数据卷锚点
# /app/data: 宿主机放置 Flowcam_images_training.zip 或解压后的原始文件
# /app/results: 存储 RDN 训练好输出的权重及最终 YOLO 训练结果
RUN mkdir -p /app/data /app/results

# 默认启动命令：进入 code 目录并提供交互 shell 或作为主控端运行
CMD ["/bin/bash"]
