"""Upload deduplicated split data to server and start YOLOv8l training."""
import paramiko, time
from pathlib import Path

HOST = "r3cw5phvxmwqeiehunt.funhpc.com"; PORT = 30957
USER = "root"; PASSWORD = "ZWAL2OPnkyBOIVxw1AaXcfaFXCDD2sCv"
LOCAL = Path(r"E:\code\codex\code\algae_guardian\data\fmpd_rdn_output")
REMOTE = "/data/fmpd_rdn_output"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
sftp = client.open_sftp()

print("[1/4] 上传 train-val split + 修复后的标签...")
for split in ["train", "val"]:
    for sub in ["images", "labels"]:
        local_dir = LOCAL / split / sub
        remote_dir = f"{REMOTE}/{split}/{sub}"
        client.exec_command(f"mkdir -p {remote_dir}")
        for f in sorted(local_dir.iterdir()):
            sftp.put(str(f), f"{remote_dir}/{f.name}")
    img_c = len(list((LOCAL / split / "images").iterdir()))
    lbl_c = len(list((LOCAL / split / "labels").iterdir()))
    print(f"    {split}: {img_c} images, {lbl_c} labels")

# Upload updated labels (deduplicated) + dataset config
print("[2/4] 上传更新后的根目录标签和配置...")
for f in ["dataset_split.yaml"]:
    p = LOCAL / f
    if p.exists():
        sftp.put(str(p), f"{REMOTE}/{f}")

# Upload training script
train_script = """from ultralytics import YOLO
model = YOLO("yolov8l.pt")

# Per-class weights (inverse frequency, sqrt-smoothed)
model.hyp['cls_pw'] = [0.7, 0.5, 1.2, 1.5, 1.0]

results = model.train(
    data="/data/fmpd_rdn_output/dataset_split.yaml",
    epochs=300,
    patience=50,
    batch=32,
    imgsz=640,
    device=0,
    workers=4,
    optimizer="AdamW",
    lr0=0.001,
    lrf=0.0001,
    warmup_epochs=5,
    augment=True,
    mosaic=1.0,
    mixup=0.1,
    degrees=10,
    translate=0.1,
    scale=0.5,
    fliplr=0.5,
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    close_mosaic=10,
    cache=True,
    project="/data/fmpd_rdn_output/yolo_results",
    name="v8l_upgrade",
    exist_ok=True,
    verbose=True,
)
"""
with sftp.open(f"{REMOTE}/train_v8l.py", "w") as f:
    f.write(train_script)
print(f"    train_v8l.py uploaded")

sftp.close()

# Start training
print("[3/4] 启动 YOLOv8l 训练...")
stdin, stdout, stderr = client.exec_command(
    'nohup /data/miniconda/envs/ican/bin/python /data/fmpd_rdn_output/train_v8l.py '
    '> /data/fmpd_rdn_output/train_v8l.log 2>&1 & echo PID=$!',
    timeout=10
)
pid = stdout.read().decode().strip()
print(f"    {pid}")

time.sleep(5)
stdin, stdout, stderr = client.exec_command('ps aux | grep train_v8l | grep -v grep', timeout=5)
p = stdout.read().decode().strip()
print(f"    Running: {'YES' if p else 'NO'}")

client.close()
print("[4/4] 完成！")
