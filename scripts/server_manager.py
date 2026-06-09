"""
阿里云 ECS 服务器管理工具
使用 SSH 密钥连接，替代之前硬编码密码的方式。

用法:
    python scripts/server_manager.py              # 交互菜单
    python scripts/server_manager.py status       # 快速状态
    python scripts/server_manager.py exec "ls /"  # 执行单条命令
    python scripts/server_manager.py upload local remote  # 上传文件
    python scripts/server_manager.py download remote local  # 下载文件
"""
import os
import sys
import paramiko
from pathlib import Path

# 服务器配置 — 使用 SSH config 别名，或直接指定
HOST = "aliyun-ecs"  # 对应 ~/.ssh/config 中的 Host
PORT = 22
USER = "root"
KEY_PATH = os.path.expanduser("~/.ssh/id_ed25519_aliyun")


def connect():
    """建立 SSH 连接（使用密钥）"""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        # 优先从 ~/.ssh/config 读取
        ssh_config = paramiko.SSHConfig()
        config_path = os.path.expanduser("~/.ssh/config")
        if os.path.exists(config_path):
            with open(config_path) as f:
                ssh_config.parse(f)
            host_conf = ssh_config.lookup(HOST)
            hostname = host_conf.get("hostname", HOST)
            user = host_conf.get("user", USER)
            key_path = host_conf.get("identityfile", [KEY_PATH])[0]
        else:
            hostname = HOST
            user = USER
            key_path = KEY_PATH

        client.connect(
            hostname=hostname,
            port=PORT,
            username=user,
            key_filename=os.path.expanduser(key_path),
            timeout=10,
        )
        return client
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        sys.exit(1)


def run_command(client, cmd: str, print_output: bool = True) -> tuple[str, str]:
    """执行远程命令，返回 (stdout, stderr)"""
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if print_output:
        if out:
            print(out.strip())
        if err:
            print(f"[stderr] {err.strip()}")
    return out, err


def show_status(client):
    """快速概览：系统信息 + 资源使用"""
    print("=" * 55)
    print("  服务器状态 —", HOST)
    print("=" * 55)

    # 系统信息
    run_command(client, "echo '  [主机名]' && hostname && echo '' && echo '  [系统]' && lsb_release -d 2>/dev/null | cut -f2 || cat /etc/os-release | head -1")

    # 运行时间
    run_command(client, "echo '  [运行时间]' && uptime -p")

    # CPU / 内存
    run_command(client, "echo '' && echo '  [CPU & 内存]' && top -bn1 | head -5")

    # 磁盘
    run_command(client, "echo '' && echo '  [磁盘]' && df -h / /data 2>/dev/null | grep -v '^Filesystem'")

    # GPU（如果有）
    run_command(client, "echo '' && echo '  [GPU]' && nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>/dev/null || echo '  无 GPU'")

    # Python / 训练进程
    run_command(client, "echo '' && echo '  [Python 进程]' && (ps aux | grep -E 'python|train|yolo' | grep -v grep | head -10 || echo '  无相关进程')")

    print("=" * 55)


def interactive_menu(client):
    """交互式菜单"""
    while True:
        print("""
  ╔══════════════════════════════════╗
  ║   阿里云 ECS 管理工具           ║
  ╠══════════════════════════════════╣
  ║  [1] 服务器状态概览            ║
  ║  [2] 执行自定义命令            ║
  ║  [3] 查看 /data 目录           ║
  ║  [4] 查看磁盘使用              ║
  ║  [5] 查看 Python 进程          ║
  ║  [0] 退出                      ║
  ╚══════════════════════════════════╝""")
        choice = input("  选择 > ").strip()

        if choice == "1":
            show_status(client)
        elif choice == "2":
            cmd = input("  输入命令 > ").strip()
            if cmd:
                run_command(client, cmd)
        elif choice == "3":
            run_command(client, "ls -lh /data/ 2>/dev/null || echo '/data 目录不存在'")
        elif choice == "4":
            run_command(client, "df -h")
        elif choice == "5":
            run_command(client, "ps aux | grep python | grep -v grep || echo '无 Python 进程'")
        elif choice == "0":
            print("  再见 👋")
            break
        else:
            print("  无效选项")


def sftp_transfer(client, local_path: str, remote_path: str, direction: str = "upload"):
    """上传或下载文件"""
    try:
        sftp = client.open_sftp()
        if direction == "upload":
            sftp.put(local_path, remote_path)
            print(f"✅ 上传完成: {local_path} → {remote_path}")
        else:
            sftp.get(remote_path, local_path)
            print(f"✅ 下载完成: {remote_path} → {local_path}")
        sftp.close()
    except Exception as e:
        print(f"❌ 传输失败: {e}")


def main():
    client = connect()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "status":
            show_status(client)
        elif cmd == "exec" and len(sys.argv) > 2:
            run_command(client, " ".join(sys.argv[2:]))
        elif cmd == "upload" and len(sys.argv) > 3:
            sftp_transfer(client, sys.argv[2], sys.argv[3], "upload")
        elif cmd == "download" and len(sys.argv) > 3:
            sftp_transfer(client, sys.argv[2], sys.argv[3], "download")
        else:
            print(__doc__)
    else:
        interactive_menu(client)

    client.close()


if __name__ == "__main__":
    main()
