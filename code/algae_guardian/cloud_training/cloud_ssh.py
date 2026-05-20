"""SSH helper for cloud server operations using paramiko.

Usage:
    from cloud_ssh import CloudServer

    with CloudServer() as server:
        result = server.run("nvidia-smi")
        print(result.stdout)
        server.upload("local_file", "remote_path")
        server.download("remote_file", "local_path")
"""

import io
import os
import paramiko
import getpass
from pathlib import Path
from typing import Optional, Tuple

HOST = "xnvsn4npo7blo10hunt.funhpc.com"
PORT = 30906
USER = "root"
PASSWORD = "1NtsRxTIlXBCeRLOSX3nVvkLeXXE8SaI"


class SSHResult:
    def __init__(self, stdout: str, stderr: str, exit_code: int):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

    def ok(self) -> bool:
        return self.exit_code == 0


class CloudServer:
    """Context manager for cloud server SSH connection."""

    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp = None

    def __enter__(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=HOST,
            port=PORT,
            username=USER,
            password=PASSWORD,
            timeout=15,
        )
        # Enable compression for faster transfers
        self.client.get_transport().use_compression(True)
        self.sftp = self.client.open_sftp()
        print(f"[SSH] Connected to {USER}@{HOST}:{PORT}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()
        print("[SSH] Disconnected")

    def run(self, command: str, timeout: int = 120) -> SSHResult:
        """Run a shell command and return result."""
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return SSHResult(
            stdout=stdout.read().decode("utf-8", errors="replace").strip(),
            stderr=stderr.read().decode("utf-8", errors="replace").strip(),
            exit_code=exit_code,
        )

    def upload(self, local_path: str, remote_path: str):
        """Upload a file or directory to the cloud server."""
        local = Path(local_path)
        if local.is_file():
            # Ensure remote directory exists
            remote_dir = str(Path(remote_path).parent)
            self.run(f"mkdir -p '{remote_dir}'")
            self.sftp.put(str(local), remote_path)
            size_mb = local.stat().st_size / (1024 * 1024)
            print(f"[Upload] {local.name} -> {remote_path} ({size_mb:.1f} MB)")
        elif local.is_dir():
            # Create remote directory first
            self.run(f"mkdir -p '{remote_path}'")
            for f in local.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(local)
                    remote_file = str(Path(remote_path) / rel)
                    remote_file_dir = str(Path(remote_file).parent)
                    self.run(f"mkdir -p '{remote_file_dir}'")
                    self.sftp.put(str(f), remote_file)
            print(f"[Upload] Directory {local.name}/ -> {remote_path}/")

    def download(self, remote_path: str, local_path: str):
        """Download a file from the cloud server."""
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        self.sftp.get(remote_path, str(local))
        size_mb = local.stat().st_size / (1024 * 1024)
        print(f"[Download] {remote_path} -> {local.name} ({size_mb:.1f} MB)")

    def upload_text(self, content: str, remote_path: str):
        """Upload text content as a file."""
        f = io.BytesIO(content.encode("utf-8"))
        remote_dir = str(Path(remote_path).parent)
        self.run(f"mkdir -p '{remote_dir}'")
        self.sftp.putfo(f, remote_path)
        print(f"[Upload] text -> {remote_path}")

    def file_exists(self, remote_path: str) -> bool:
        """Check if a remote file exists."""
        result = self.run(f"test -f '{remote_path}' && echo 'EXISTS' || echo 'NOT_FOUND'")
        return "EXISTS" in result.stdout

    def dir_exists(self, remote_path: str) -> bool:
        """Check if a remote directory exists."""
        result = self.run(f"test -d '{remote_path}' && echo 'EXISTS' || echo 'NOT_FOUND'")
        return "EXISTS" in result.stdout


def check_server():
    """Quick health check of the cloud server."""
    with CloudServer() as s:
        # GPU info
        gpu = s.run("nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader")
        print(f"GPU: {gpu.stdout}")

        # Disk
        disk = s.run("df -h /data | tail -1")
        print(f"Disk: {disk.stdout}")

        # Python
        py = s.run("/data/miniconda/envs/ican/bin/python --version")
        print(f"Python: {py.stdout}")

        # Project dirs
        for d in ["/data/rdn_training", "/data/SPDRDN", "/data/algae_guardian"]:
            if s.dir_exists(d):
                size = s.run(f"du -sh {d} 2>/dev/null | cut -f1")
                print(f"  {d}: exists ({size.stdout})")
            else:
                print(f"  {d}: NOT_FOUND")

        # RDN model
        model = "/data/rdn_training/checkpoint/best.pth"
        if s.file_exists(model):
            print(f"  {model}: exists")
        else:
            # Check other locations
            for p in ["/data/rdn_training/output/*.pth", "/data/rdn_training/*.pth"]:
                result = s.run(f"ls -la {p} 2>/dev/null")
                if result.ok():
                    print(f"  Found: {result.stdout}")


if __name__ == "__main__":
    check_server()
