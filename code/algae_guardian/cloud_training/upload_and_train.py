"""Upload fmpd_rdn_output to cloud server & start YOLO training."""
import paramiko
import sys
from pathlib import Path

HOST = "r3cw5phvxmwqeiehunt.funhpc.com"
PORT = 30957
USER = "root"
PASSWORD = "ZWAL2OPnkyBOIVxw1AaXcfaFXCDD2sCv"
LOCAL_DATA = Path(r"E:\code\codex\code\algae_guardian\data\fmpd_rdn_output")
REMOTE_DATA = "/data/fmpd_rdn_output"
ICAN_PYTHON = "/data/miniconda/envs/ican/bin/python"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
sftp = client.open_sftp()

print("[1/4] 创建远程目录...")
client.exec_command(f"mkdir -p {REMOTE_DATA}/images")
client.exec_command(f"mkdir -p {REMOTE_DATA}/labels")

print("[2/4] 上传 images/ (293 张, 640x640 JPG)...")
for f in sorted((LOCAL_DATA / "images").iterdir()):
    sftp.put(str(f), f"{REMOTE_DATA}/images/{f.name}")

print("[3/4] 上传 labels/ (293 个 YOLO 标注)...")
for f in sorted((LOCAL_DATA / "labels").iterdir()):
    sftp.put(str(f), f"{REMOTE_DATA}/labels/{f.name}")

# Upload config files
for f in ["dataset.yaml", "quality_report.csv"]:
    p = LOCAL_DATA / f
    if p.exists():
        sftp.put(str(p), f"{REMOTE_DATA}/{f}")

sftp.close()

print("[4/4] 验证上传...")
stdin, stdout, stderr = client.exec_command(f"ls {REMOTE_DATA}/images/ | wc -l")
img_count = stdout.read().decode().strip()
stdin, stdout, stderr = client.exec_command(f"ls {REMOTE_DATA}/labels/ | wc -l")
lbl_count = stdout.read().decode().strip()
print(f"    images: {img_count}, labels: {lbl_count}")

# Show dataset.yaml
stdin, stdout, stderr = client.exec_command(f"cat {REMOTE_DATA}/dataset.yaml")
print(f"    dataset.yaml:\n{stdout.read().decode().strip()}")

client.close()
print("上传完成！")
