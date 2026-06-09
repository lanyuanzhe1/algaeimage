import paramiko
import os

HOST = 'xkh2l3rq6jm4cpuhunt.funhpc.com'
PORT = 30769
USER = 'root'
PASSWORD = 'wEoOG5Y791pBAT5CmRvyre2yI8Sgr1hv'

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD)
    
    print("Preparing 500 images on server...")
    # Get 500 images from test.txt
    cmd = """
    mkdir -p /tmp/img500
    rm -rf /tmp/img500/*
    cat << 'EOF' > /tmp/select_500.py
import random, os, shutil
with open('/data/lifewatch_hsv/splits/test.txt') as f:
    lines = f.readlines()
selected = random.sample(lines, 500)
count = 0
for line in selected:
    path = line.strip().rsplit(' ', 1)[0]
    
    clean_path = path.replace('\\\\', '/')
    parts = clean_path.split('/')
    if len(parts) >= 2:
        class_name = parts[-2]
        file_name = parts[-1]
        
        src = os.path.join('/data/datasets/lifewatch/images_all', class_name, file_name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join('/tmp/img500', file_name))
            count += 1
print(f"Copied {count} files.")
EOF
    python3 /tmp/select_500.py
    cd /tmp && zip -r img500.zip img500 -q
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()  # wait for finish
    print(f"Zip command exited with {exit_status}")
    print(stderr.read().decode())
    
    print("Downloading zip...")
    local_dir = r"e:\code\codex\lifewatch_raw_samples"
    os.makedirs(local_dir, exist_ok=True)
    sftp = client.open_sftp()
    sftp.get("/tmp/img500.zip", os.path.join(local_dir, "img500.zip"))
    sftp.close()
    
    print("Download complete.")
    client.exec_command("rm /tmp/img500.zip")
    client.close()

if __name__ == "__main__":
    main()
