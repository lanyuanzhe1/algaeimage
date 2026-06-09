"""Pydantic request/response models — re-exported from shared/schemas.py.

单一来源: shared/schemas.py 是 API 契约的唯一定义处。
此文件仅做 re-export，保证向后兼容。
"""
import os
import sys

# 确保项目根在 sys.path 中（兼容直接 import 本模块的场景）
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.schemas import (  # noqa: F401, E402
    BatchDetectResponse,
    BatchResult,
    BatchSummary,
    DetectionItem,
    HistoryItem,
    HistoryListResponse,
    SingleDetectResponse,
    StatsResponse,
    VizDetectResponse,
    VizStep,
)
