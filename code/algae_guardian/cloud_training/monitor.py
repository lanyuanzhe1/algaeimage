import os
import sys
import time
import subprocess
import json
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("/data/lifewatch_yolo/train/monitor.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# 目标监控参数
TARGET_PID = 6301
LOG_FILE_PATH = "/data/lifewatch_yolo/train/auto_train_yolo.log"
STATUS_JSON_PATH = "/data/lifewatch_yolo/train/training_status.json"

def get_process_info(pid):
    """获取指定 PID 的 Python 训练进程 CPU, 内存与活动状态"""
    try:
        # 使用 ps 获取 CPU、MEM 占用
        out = subprocess.check_output(f"ps -p {pid} -o %cpu,%mem,stat,comm", shell=True)
        lines = out.decode('utf-8').strip().split('\n')
        if len(lines) > 1:
            stats = lines[1].split()
            return {
                "active": True,
                "cpu": stats[0],
                "mem": stats[1],
                "stat": stats[2],
                "comm": stats[3]
            }
    except Exception:
        pass
    return {"active": False}

def get_gpu_info(pid):
    """获取指定 PID 在 nvidia-smi 中的显存和 GPU 占用率"""
    try:
        out = subprocess.check_output("nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits", shell=True)
        for line in out.decode('utf-8').strip().split('\n'):
            if line:
                parts = line.split(',')
                if int(parts[0].strip()) == pid:
                    mem_used = parts[1].strip()
                    # 再次获取整体利用率
                    gpu_util_out = subprocess.check_output("nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits", shell=True)
                    gpu_util = gpu_util_out.decode('utf-8').strip()
                    return {"gpu_mem_mib": mem_used, "gpu_util_pct": gpu_util}
    except Exception:
        pass
    return {"gpu_mem_mib": "0", "gpu_util_pct": "0"}

def parse_last_progress(log_path):
    """解析日志以确定当前的 Epoch、Batch 迭代进度和 ETA"""
    if not os.path.exists(log_path):
        return None
    try:
        # 读取最后 50 行
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[-50:]
        
        # 寻找最近的进度行，例如: " 1/100      14.4G     0.0601     0.7606     ... 645/2367"
        epoch_str = "Unknown"
        progress_str = "Unknown"
        speed_str = "Unknown"
        
        for line in reversed(lines):
            # 去除颜色控制代码
            clean_line = line.replace('\x1b', '').replace('[K', '').strip()
            # 找到类似于 "1/100" 且含有 "/" 格式的行
            if "100" in clean_line and "/" in clean_line and "it/s" in clean_line:
                parts = clean_line.split()
                for p in parts:
                    if "/100" in p:
                        epoch_str = p
                    if "/2367" in p:
                        progress_str = p
                    if "it/s" in p or "s/it" in p:
                        speed_str = p
                break
        return {"epoch": epoch_str, "progress": progress_str, "speed": speed_str}
    except Exception as e:
        return {"error": str(e)}

def main():
    logging.info("=" * 50)
    logging.info("LifeWatch YOLOv8s Training Monitor Daemon Started")
    logging.info(f"Target PID: {TARGET_PID}")
    logging.info("=" * 50)

    consecutive_inactive = 0
    
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        proc_info = get_process_info(TARGET_PID)
        gpu_info = get_gpu_info(TARGET_PID)
        prog_info = parse_last_progress(LOG_FILE_PATH)
        
        status_data = {
            "timestamp": now,
            "pid": TARGET_PID,
            "process_stats": proc_info,
            "gpu_stats": gpu_info,
            "progress_stats": prog_info if prog_info else {}
        }
        
        # 写出最新的 JSON 状态，供前端或巡检脚本实时一键调用获取
        try:
            with open(STATUS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to write status JSON: {e}")
            
        if proc_info["active"]:
            consecutive_inactive = 0
            logging.info(
                f"Heartbeat - PID: {TARGET_PID} | CPU: {proc_info['cpu']}% | MEM: {proc_info['mem']}% | "
                f"GPU Mem: {gpu_info['gpu_mem_mib']}MiB | GPU Util: {gpu_info['gpu_util_pct']}% | "
                f"Epoch: {prog_info.get('epoch', 'N/A') if prog_info else 'N/A'} | "
                f"Progress: {prog_info.get('progress', 'N/A') if prog_info else 'N/A'} ({prog_info.get('speed', 'N/A') if prog_info else 'N/A'})"
            )
        else:
            consecutive_inactive += 1
            logging.warning(f"Process PID {TARGET_PID} not active! Warning count: {consecutive_inactive}/3")
            if consecutive_inactive >= 3:
                logging.critical("ALERT: Training process has terminated! Shutting down monitor daemon.")
                # 这里可以执行额外的挽救措施（例如发送报警、或落盘标记训练结束）
                break
                
        # 每隔 60 秒轮询一次
        time.sleep(60)

if __name__ == "__main__":
    main()
