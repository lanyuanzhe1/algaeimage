"""Download YOLO results from server to local."""
import paramiko
import os
from pathlib import Path

HOST = "r3cw5phvxmwqeiehunt.funhpc.com"
PORT = 30957
USER = "root"
PASSWORD = "ZWAL2OPnkyBOIVxw1AaXcfaFXCDD2sCv"

LOCAL_DIR = Path(r"E:\code\algaeimage\code\algae_guardian\data\yolo_results")
REMOTE_RESULTS = "/data/fmpd_rdn_output/yolo_results/v8s_baseline"
REMOTE_PREDICT = "/data/fmpd_rdn_output/yolo_results/v8s_baseline_predict"
REMOTE_LOG = "/data/fmpd_rdn_output/train.log"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
sftp = client.open_sftp()

# 1. Download training results
print("[1/4] 下载 training results...")
local_train = LOCAL_DIR / "training"
local_train.mkdir(parents=True, exist_ok=True)

for item in ["results.csv", "results.png", "args.yaml", "weights/best.pt", "weights/last.pt"]:
    remote = f"{REMOTE_RESULTS}/{item}"
    local = local_train / item
    local.parent.mkdir(parents=True, exist_ok=True)
    try:
        sftp.stat(remote)
        sftp.get(remote, str(local))
        size = local.stat().st_size / (1024*1024)
        print(f"    {item} ({size:.1f} MB)" if size > 0.5 else f"    {item}")
    except FileNotFoundError:
        print(f"    {item}: NOT FOUND")

# 2. Download train.log
print("[2/4] 下载 train.log...")
local_log = LOCAL_DIR / "training" / "train.log"
try:
    sftp.get(REMOTE_LOG, str(local_log))
    print(f"    train.log ({local_log.stat().st_size/1024:.0f} KB)")
except:
    print("    train.log: NOT FOUND")

# 3. Download prediction images (with bounding boxes)
print("[3/4] 下载 293 张预测结果图 (63MB)...")
local_pred = LOCAL_DIR / "predictions"
local_pred.mkdir(parents=True, exist_ok=True)

for fname in sftp.listdir(REMOTE_PREDICT):
    if fname.endswith(".jpg") or fname.endswith(".png"):
        sftp.get(f"{REMOTE_PREDICT}/{fname}", str(local_pred / fname))

img_count = len(list(local_pred.glob("*")))
print(f"    {img_count} 张图已下载到 {local_pred}")

# 4. Download prediction labels
print("[4/4] 下载预测标签...")
local_labels = LOCAL_DIR / "predictions" / "labels"
local_labels.mkdir(parents=True, exist_ok=True)
try:
    for fname in sftp.listdir(f"{REMOTE_PREDICT}/labels"):
        if fname.endswith(".txt"):
            sftp.get(f"{REMOTE_PREDICT}/labels/{fname}", str(local_labels / fname))
    lbl_count = len(list(local_labels.glob("*")))
    print(f"    {lbl_count} 标签已下载")
except FileNotFoundError:
    print("    labels/: NOT FOUND")

sftp.close()
client.close()
print("\n下载完成！保存到:", LOCAL_DIR)
