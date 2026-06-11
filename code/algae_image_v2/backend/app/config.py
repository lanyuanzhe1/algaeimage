"""应用配置 — 部署环境与路径常量。

职责边界:
  · 此文件 = 部署/路径/目录结构（resource_path, HOST, PORT, 目录, DB）
  · core_engine/config.py = 算法/业务（类名, 风险矩阵, 模型元数据, I_enh 参数）

注意: 算法参数不在这里定义；路径常量不放在 core_engine。
"""
import os
import sys


def resource_path(relative_path: str) -> str:
    """Resolve path compatible with both PyInstaller frozen and dev environments.

    When packaged by PyInstaller, sys._MEIPASS is the temp directory containing
    bundled data files. In dev mode, falls back to the project root derived from
    this file's location.
    """
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative_path)


BASE_DIR = resource_path("")

WEIGHTS_DIR = resource_path("weights")
YOLO_WEIGHTS = resource_path("weights/best_v8l.pt")
YOLO_WEIGHTS_V8S = resource_path("weights/best_v8s.pt")

DATA_DIR = resource_path("backend/data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
RESULT_DIR = os.path.join(DATA_DIR, "results")
DB_PATH = os.path.join(DATA_DIR, "detection_history.db")

API_PREFIX = "/api/v1"
HOST = "0.0.0.0"
PORT = 8000
