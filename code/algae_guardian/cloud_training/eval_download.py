"""Run validation on best model and download results to local."""
import paramiko, time, json
from pathlib import Path

HOST = "r3cw5phvxmwqeiehunt.funhpc.com"; PORT = 30957
USER = "root"; PASSWORD = "ZWAL2OPnkyBOIVxw1AaXcfaFXCDD2sCv"
REMOTE_RESULTS = "/data/fmpd_rdn_output/yolo_results"
LOCAL_RESULTS = Path(r"E:\code\codex\code\algae_guardian\data\fmpd_rdn_output\yolo_results")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)

# Find best.pt
stdin, stdout, stderr = client.exec_command(
    "ls /data/fmpd_rdn_output/yolo_results/v8l_upgrade/weights/best.pt 2>/dev/null && echo FOUND || echo NOT_FOUND",
    timeout=10
)
has_best = "FOUND" in stdout.read().decode()
if not has_best:
    print("best.pt not found, checking available weights...")
    stdin, stdout, stderr = client.exec_command(
        "ls /data/fmpd_rdn_output/yolo_results/v8l_upgrade/weights/", timeout=10
    )
    print(stdout.read().decode())
    client.close()
    exit(1)
print("best.pt found.")

# Run validation on val set
val_cmd = (
    '/data/miniconda/envs/ican/bin/python -c "'
    'from ultralytics import YOLO; '
    'm = YOLO(\"/data/fmpd_rdn_output/yolo_results/v8l_upgrade/weights/best.pt\"); '
    'r = m.val(data=\"/data/fmpd_rdn_output/dataset_split.yaml\", batch=32, imgsz=640, verbose=True); '
    'print(\"DONE\");'
    '"'
)
stdin, stdout, stderr = client.exec_command(val_cmd, timeout=120)
val_out = stdout.read().decode("utf-8", errors="replace")
val_err = stderr.read().decode("utf-8", errors="replace")
print("Validation output:")
print(val_out[-1000:] if len(val_out) > 1000 else val_out)

# Get best epoch results
stdin, stdout, stderr = client.exec_command(
    "grep '^all ' /data/fmpd_rdn_output/train_v8l.log | sort -k7 -nr | head -5",
    timeout=10
)
best_epochs = stdout.read().decode().strip()
print("\nBest epochs by mAP50:")
print(best_epochs)

# Download results
sftp = client.open_sftp()
local_dir = LOCAL_RESULTS / "v8l_upgrade"
local_dir.mkdir(parents=True, exist_ok=True)

def download_dir(remote_path, local_path, prefix=""):
    """Recursively download a remote directory."""
    try:
        items = sftp.listdir_attr(remote_path)
    except FileNotFoundError:
        print(f"  {prefix}[SKIP] {remote_path} not found")
        return
    for item in items:
        rp = f"{remote_path}/{item.filename}"
        lp = local_path / item.filename
        if item.st_mode & 0o40000:  # directory
            lp.mkdir(parents=True, exist_ok=True)
            download_dir(rp, lp, prefix + "  ")
        else:
            # Skip large files like cache/ weights might be large
            if item.st_size > 500_000_000:  # >500MB skip
                print(f"  {prefix}[SKIP] {item.filename} ({item.st_size/1e6:.0f}MB)")
                continue
            sftp.get(rp, str(lp))
            print(f"  {prefix}{item.filename} ({item.st_size/1024:.0f}KB)")

print(f"\nDownloading to {local_dir}...")
download_dir(f"{REMOTE_RESULTS}/v8l_upgrade", local_dir)
sftp.close()
client.close()

print(f"\nDone! Results saved to {local_dir}")
print(f"  Weights: {local_dir / 'weights' / 'best.pt'}")
