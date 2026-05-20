"""Fix dataset.yaml and install ultralytics on cloud server."""
import paramiko

HOST = "r3cw5phvxmwqeiehunt.funhpc.com"
PORT = 30957
USER = "root"
PASSWORD = "ZWAL2OPnkyBOIVxw1AaXcfaFXCDD2sCv"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)

# Fix dataset.yaml
yaml_content = """path: /data/fmpd_rdn_output
train: images
val: images
nc: 5
names: ["Other-phytoplankton", "Non-phytoplankton", "Woronichinia", "Spiroides", "Dinobryon"]
"""
stdin, stdout, stderr = client.exec_command("cat > /data/fmpd_rdn_output/dataset.yaml")
stdin.write(yaml_content)
stdin.channel.shutdown_write()
print("dataset.yaml:", stdout.read().decode().strip()[:100])

# Class distribution
stdin, stdout, stderr = client.exec_command(
    "awk '{print $1}' /data/fmpd_rdn_output/labels/*.txt | sort | uniq -c | sort -rn"
)
print("Class distribution:")
print(stdout.read().decode().strip())

# Install ultralytics
print("\nInstalling ultralytics...")
stdin, stdout, stderr = client.exec_command(
    "/data/miniconda/envs/ican/bin/pip install ultralytics -q",
    timeout=120
)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
if err:
    print("Install:", err[-300:])
else:
    print("Install: OK")

# Verify
stdin, stdout, stderr = client.exec_command(
    "/data/miniconda/envs/ican/bin/python -c \"from ultralytics import YOLO; print('YOLO OK')\""
)
print("Verify:", stdout.read().decode().strip())

client.close()
