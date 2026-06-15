"""纯数据 API 路由 — 仪表板统计 + 检测历史 CRUD + 设备管理 + 人工复核。

无 ML 依赖（不需要 torch / cv2 / numpy / ultralytics），
可在任何 Python 环境中独立 import 和测试。
"""
import json
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
import aiosqlite

from .config import RESULT_DIR
from .database import get_db
from .schemas import (
    DeviceInfo,
    DeviceListResponse,
    HistoryItem,
    HistoryListResponse,
    ReviewItem,
    ReviewListResponse,
    ReviewSubmitRequest,
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


# ═══════════════════════════════════════════════════════════════════════════════
# Device Management
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(db: aiosqlite.Connection = Depends(get_db)):
    """列出所有设备"""
    rows = await db.execute_fetchall(
        "SELECT id, name, location, model, status, today_frames, alerts, uptime FROM devices ORDER BY name"
    )
    devices = [
        DeviceInfo(
            id=r["id"], name=r["name"], location=r["location"], model=r["model"],
            status=r["status"], today_frames=r["today_frames"], alerts=r["alerts"], uptime=r["uptime"],
        )
        for r in rows
    ]
    return DeviceListResponse(devices=devices)


@router.post("/devices")
async def add_device(
    name: str = Query(...),
    location: str = Query(""),
    model: str = Query("MV-CA013-20GC"),
    db: aiosqlite.Connection = Depends(get_db),
):
    """添加新设备"""
    device_id = uuid.uuid4().hex[:12]
    await db.execute(
        """INSERT INTO devices (id, name, location, model, status, today_frames, alerts, uptime)
           VALUES (?, ?, ?, ?, 'online', 0, 0, '0h')""",
        (device_id, name, location, model),
    )
    await db.commit()
    return {"status": "created", "id": device_id, "name": name}


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """删除设备"""
    row = await db.execute_fetchall("SELECT id FROM devices WHERE id = ?", (device_id,))
    if not row:
        raise HTTPException(status_code=404, detail="设备不存在")
    await db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
    await db.commit()
    return {"status": "deleted", "id": device_id}


@router.put("/devices/{device_id}")
async def update_device(
    device_id: str,
    name: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    today_frames: Optional[int] = Query(None),
    alerts: Optional[int] = Query(None),
    uptime: Optional[str] = Query(None),
    db: aiosqlite.Connection = Depends(get_db),
):
    """更新设备信息"""
    row = await db.execute_fetchall("SELECT id FROM devices WHERE id = ?", (device_id,))
    if not row:
        raise HTTPException(status_code=404, detail="设备不存在")
    sets = []
    vals = []
    for k, v in [("name", name), ("location", location), ("status", status),
                  ("today_frames", today_frames), ("alerts", alerts), ("uptime", uptime)]:
        if v is not None:
            sets.append(f"{k} = ?")
            vals.append(v)
    if sets:
        vals.append(device_id)
        await db.execute(f"UPDATE devices SET {', '.join(sets)} WHERE id = ?", vals)
        await db.commit()
    return {"status": "updated", "id": device_id}


# ═══════════════════════════════════════════════════════════════════════════════
# Review
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/review/list", response_model=ReviewListResponse)
async def list_reviews(
    status: Optional[str] = Query(None, description="filter: pending | approved | rejected"),
    db: aiosqlite.Connection = Depends(get_db),
):
    """列出复核记录"""
    if status:
        rows = await db.execute_fetchall(
            "SELECT * FROM reviewed_records WHERE status = ? ORDER BY created_at DESC LIMIT 100",
            (status,),
        )
        all_rows = rows
    else:
        rows = await db.execute_fetchall(
            "SELECT * FROM reviewed_records ORDER BY created_at DESC LIMIT 100"
        )
        all_rows = rows
    # Counts
    pending = await db.execute_fetchall("SELECT COUNT(*) as c FROM reviewed_records WHERE status='pending'")
    approved = await db.execute_fetchall("SELECT COUNT(*) as c FROM reviewed_records WHERE status='approved'")

    items = [
        ReviewItem(
            id=r["id"], detection_id=r["detection_id"], filename=r["filename"],
            class_name=r["class_name"], class_name_zh=r.get("class_name_zh", ""),
            confidence=r["confidence"], risk_level=r.get("risk_level"),
            status=r["status"], created_at=str(r["created_at"]),
        )
        for r in rows
    ]
    return ReviewListResponse(
        items=items, total=len(items),
        approved_count=approved[0]["c"] if approved else 0,
        pending_count=pending[0]["c"] if pending else 0,
    )


@router.post("/review/submit")
async def submit_review(
    body: ReviewSubmitRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """提交复核结果"""
    # Get detection details
    det_row = await db.execute_fetchall(
        "SELECT filename, detections, risk_level FROM detection_history WHERE id = ?",
        (body.detection_id,),
    )
    if not det_row:
        raise HTTPException(status_code=404, detail="检测记录不存在")

    r = det_row[0]
    dets = json.loads(r["detections"])
    # Use first detection's class for simplicity
    cls_name = dets[0]["class_name"] if dets else "Unknown"
    cls_zh = dets[0].get("class_name_zh", cls_name) if dets else "Unknown"
    conf = dets[0]["confidence"] if dets else 0

    review_id = uuid.uuid4().hex[:12]
    await db.execute(
        """INSERT INTO reviewed_records
           (id, detection_id, filename, class_name, class_name_zh, confidence, risk_level, status, corrected_class)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (review_id, body.detection_id, r["filename"], cls_name, cls_zh, conf,
         r.get("risk_level"), body.status, body.corrected_class),
    )
    await db.commit()
    return {"status": "ok", "id": review_id}


@router.post("/review/submit-batch")
async def submit_review_batch(
    db: aiosqlite.Connection = Depends(get_db),
):
    """批量将低置信度检测加入复核池"""
    rows = await db.execute_fetchall(
        "SELECT id, filename, detections, risk_level FROM detection_history ORDER BY created_at DESC LIMIT 50"
    )
    added = 0
    for r in rows:
        dets = json.loads(r["detections"])
        for d in dets:
            if d.get("confidence", 1) < 0.6:
                existing = await db.execute_fetchall(
                    "SELECT id FROM reviewed_records WHERE detection_id = ?", (r["id"],)
                )
                if existing:
                    continue
                review_id = uuid.uuid4().hex[:12]
                await db.execute(
                    """INSERT INTO reviewed_records
                       (id, detection_id, filename, class_name, class_name_zh, confidence, risk_level, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                    (review_id, r["id"], r["filename"], d.get("class_name", "Unknown"),
                     d.get("class_name_zh", ""), d.get("confidence", 0), r.get("risk_level")),
                )
                added += 1
    await db.commit()
    return {"status": "ok", "added": added}
