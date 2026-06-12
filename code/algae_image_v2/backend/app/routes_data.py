"""纯数据 API 路由 — 仪表板统计 + 检测历史 CRUD。

无 ML 依赖（不需要 torch / cv2 / numpy / ultralytics），
可在任何 Python 环境中独立 import 和测试。
"""
import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
import aiosqlite

from .config import RESULT_DIR
from .database import get_db
from .schemas import (
    HistoryItem,
    HistoryListResponse,
    StatsResponse,
)

router = APIRouter(prefix="/api/v1", tags=["data"])


def _overall_risk(detections: list[dict]) -> Optional[str]:
    """最高风险等级"""
    risks = [d.get("risk_level", "low") for d in detections]
    if "high" in risks:
        return "high"
    if "medium" in risks:
        return "medium"
    return "low" if risks else None


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/stats", response_model=StatsResponse)
async def get_stats(db: aiosqlite.Connection = Depends(get_db)):
    """返回检测汇总统计"""
    row = await db.execute_fetchall("SELECT COUNT(*) as c FROM detection_history")
    total = row[0]["c"] if row else 0

    row = await db.execute_fetchall(
        "SELECT COUNT(*) as c FROM detection_history WHERE date(created_at) = date('now')"
    )
    today = row[0]["c"] if row else 0

    rows = await db.execute_fetchall(
        "SELECT detections FROM detection_history ORDER BY created_at DESC LIMIT 500"
    )
    class_dist: dict[str, int] = {}
    risk_dist: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for r in rows:
        try:
            dets = json.loads(r["detections"])
            for d in dets:
                name = d.get("class_name", "Unknown")
                class_dist[name] = class_dist.get(name, 0) + 1
                risk = d.get("risk_level", "low")
                risk_dist[risk] = risk_dist.get(risk, 0) + 1
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    recent = await db.execute_fetchall(
        "SELECT id, filename, risk_level, q_score, created_at "
        "FROM detection_history ORDER BY created_at DESC LIMIT 10"
    )
    recent_list = [
        {
            "id": r["id"], "filename": r["filename"],
            "risk_level": r["risk_level"], "q_score": r["q_score"],
            "created_at": str(r["created_at"]),
        }
        for r in recent
    ]

    return StatsResponse(
        total_detections=total,
        today_count=today,
        class_distribution=class_dist,
        risk_distribution=risk_dist,
        recent_detections=recent_list,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# History
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/history", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: aiosqlite.Connection = Depends(get_db),
):
    """分页查询检测历史"""
    offset = (page - 1) * limit
    rows = await db.execute_fetchall(
        "SELECT id, filename, risk_level, q_score, created_at "
        "FROM detection_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    total_row = await db.execute_fetchall("SELECT COUNT(*) as c FROM detection_history")
    total = total_row[0]["c"] if total_row else 0

    items = [
        HistoryItem(
            id=r["id"], filename=r["filename"],
            risk_level=r["risk_level"], q_score=r["q_score"],
            created_at=str(r["created_at"]),
        )
        for r in rows
    ]
    return HistoryListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/history/{record_id}")
async def get_history_detail(record_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """查询单条历史记录详情"""
    row = await db.execute_fetchall(
        "SELECT * FROM detection_history WHERE id = ?", (record_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")

    r = row[0]
    return {
        "id": r["id"], "filename": r["filename"],
        "image_path": r["image_path"], "result_path": r["result_path"],
        "detections": json.loads(r["detections"]),
        "q_score": r["q_score"], "risk_level": r["risk_level"],
        "created_at": str(r["created_at"]),
    }


@router.delete("/history/{record_id}")
async def delete_history(record_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """删除历史记录及其关联文件"""
    row = await db.execute_fetchall(
        "SELECT image_path, result_path FROM detection_history WHERE id = ?", (record_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")

    image_path = row[0]["image_path"]
    result_path = row[0]["result_path"]
    if image_path and os.path.isfile(image_path):
        os.remove(image_path)
    if result_path:
        result_file = os.path.join(RESULT_DIR, os.path.basename(result_path))
        if os.path.isfile(result_file):
            os.remove(result_file)

    await db.execute("DELETE FROM detection_history WHERE id = ?", (record_id,))
    await db.commit()
    return {"status": "deleted", "id": record_id}
