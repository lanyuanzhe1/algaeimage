import os
import sys

# 添加 cloud_ssh.py 所在的路径
sys.path.append(r"e:\code\algaeimage\code\algae_guardian\cloud_training")
from cloud_ssh import CloudServer

def main():
    remote_dir = "/data/lifewatch_yolo/yolo_results/lifewatch_v2_v8s_320/"
    local_dir = r"e:\code\algaeimage\pic\yolo_intermediate"
    
    # 我们想要下载的关键词
    target_keywords = ["results.png", "train_batch", "val_batch"]

    with CloudServer() as server:
        print(f"Listing .jpg and .png files in {remote_dir}...")
        
        # 查找图片文件
        cmd = f"find {remote_dir} -maxdepth 1 -type f -name '*.jpg' -o -name '*.png'"
        result = server.run(cmd)
        
        if not result.ok():
            print("Failed to list files or no files found.")
            print("Stderr:", result.stderr)
            return

        files = result.stdout.split('\n')
        print(f"Found {len(files)} image files on server.")
        
        # 筛选感兴趣的文件
        files_to_download = []
        for file in files:
            file = file.strip()
            if not file:
                continue
                
            fname = file.split('/')[-1]
            if any(k in fname for k in target_keywords):
                files_to_download.append(file)
        
        print(f"\nSelected {len(files_to_download)} files to download:")
        for f in files_to_download:
            print("  -", f)
            
        print(f"\nStarting download to {local_dir}...")
        os.makedirs(local_dir, exist_ok=True)
        
        # 执行下载
        for remote_path in files_to_download:
            fname = remote_path.split('/')[-1]
            local_path = os.path.join(local_dir, fname)
            print(f"Downloading {fname}...")
            server.download(remote_path, local_path)
            
        print("\nDownload complete! Local files are stored at:")
        for f in files_to_download:
            print(f"  - {os.path.join(local_dir, f.split('/')[-1])}")

if __name__ == '__main__':
    main()
