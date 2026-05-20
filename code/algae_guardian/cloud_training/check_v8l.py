"""Quick check of YOLOv8l training status."""
import paramiko

HOST = "r3cw5phvxmwqeiehunt.funhpc.com"; PORT = 30957
USER = "root"; PASSWORD = "ZWAL2OPnkyBOIVxw1AaXcfaFXCDD2sCv"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)

for cmd in [
    "ps aux | grep train_v8l | grep -v grep",
    "nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader 2>/dev/null",
    "wc -l /data/fmpd_rdn_output/train_v8l.log 2>/dev/null",
]:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=5)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    print(f"[{cmd[:40]}]: {out[:600]}")

# Log tail
stdin, stdout, stderr = client.exec_command(
    "tail -30 /data/fmpd_rdn_output/train_v8l.log 2>/dev/null || echo LOG_EMPTY",
    timeout=10,
)
log = stdout.read().decode("utf-8", errors="replace").strip()
if log and log != "LOG_EMPTY":
    lines = [
        l
        for l in log.split("\n")
        if any(k in l.lower() for k in ["epoch", "class", "all ", "speed", "results", "download", "model"])
    ]
    if lines:
        print("\n--- Training Log (filtered) ---")
        for l in lines:
            print(l[:200])
    else:
        print("\n--- Raw log (last 5 lines) ---")
        for l in log.split("\n")[-5:]:
            print(l[:200])
else:
    print(f"Log: {log}")

client.close()
