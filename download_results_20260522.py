import os
import sys
from pathlib import Path

# 添加 cloud_ssh.py 所在的路径
sys.path.append(r"e:\code\codex\code\algae_guardian\cloud_training")
from cloud_ssh import CloudServer

def download_folder_contents(server, remote_dir, local_dir):
    print(f"Scanning remote directory: {remote_dir}")
    # 列出远程目录下所有文件
    cmd = f"find {remote_dir} -type f"
    result = server.run(cmd)
    if not result.ok():
        print(f"Failed to list remote directory: {remote_dir}")
        return

    remote_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
    print(f"Found {len(remote_files)} files to download.")

    for remote_path in remote_files:
        # 获取相对路径
        rel_path = os.path.relpath(remote_path, remote_dir)
        local_path = os.path.join(local_dir, rel_path)
        
        # 确保本地父目录存在
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        print(f"Downloading {rel_path}...")
        server.download(remote_path, local_path)

def main():
    remote_results_dir = "/data/lifewatch_yolo/yolo_results/lifewatch_v2_v8s_320"
    remote_train_logs_dir = "/data/lifewatch_yolo/train"
    
    # 制定带日期的本地目录
    local_base_dir = r"E:\code\codex\results\yolo_results_20260522"
    
    os.makedirs(local_base_dir, exist_ok=True)

    with CloudServer() as server:
        # 1. 下载全套 YOLO 训练工件和权重
        print("\n=== [1/2] 开始下载 YOLO 训练核心产物和最佳权重 ===")
        local_results_dir = os.path.join(local_base_dir, "yolo_artifacts")
        download_folder_contents(server, remote_results_dir, local_results_dir)
        
        # 2. 下载系统监控和训练的心跳/日志
        print("\n=== [2/2] 开始下载云端训练日志和监控面板运行日志 ===")
        local_logs_dir = os.path.join(local_base_dir, "logs")
        os.makedirs(local_logs_dir, exist_ok=True)
        
        target_logs = [
            "auto_train_yolo.log",
            "monitor.log",
            "monitor_setup.log",
            "training_status.json"
        ]
        
        for log_file in target_logs:
            remote_log_path = f"{remote_train_logs_dir}/{log_file}"
            local_log_path = os.path.join(local_logs_dir, log_file)
            if server.file_exists(remote_log_path):
                print(f"Downloading remote log: {log_file}...")
                server.download(remote_log_path, local_log_path)
            else:
                print(f"Remote log {log_file} not found, skipping.")

    print(f"\n🎉 恭喜！当前所有完整的训练历史产出、最佳模型权重(best.pt)、损失与评估图已经妥善下载！")
    print(f"文件保存到本地路径: {local_base_dir}")

if __name__ == '__main__':
    main()
