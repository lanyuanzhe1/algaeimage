"""
藻影知微 V2 — 轻量版 API Server
===============================
自包含单文件，不依赖 PyTorch / OpenCV / NumPy / ultralytics。
用于低配服务器（1.6GB 内存 / 无 GPU）的演示部署。

依赖: fastapi uvicorn aiosqlite aiofiles pillow python-multipart

启动: python server_light.py
默认端口 8000，可通过 PORT 环境变量修改。
"""
import json
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Optional

from fastapi import FastAPI, APIRouter, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import aiofiles
import aiosqlite
import logging
from PIL import Image
# 确保能找到 shared/ 模块（部署时与 server_light.py 同级）
_srv_dir = os.path.dirname(os.path.abspath(__file__))
if _srv_dir not in sys.path:
    sys.path.insert(0, _srv_dir)

from shared.schemas import (  # noqa: E402
    BatchDetectResponse,
    BatchResult,
    BatchSummary,
    DetectionItem,
    DeviceInfo,
    DeviceListResponse,
    HistoryItem,
    HistoryListResponse,
    LatestResult,
    LatestResultsResponse,
    ReviewItem,
    ReviewListResponse,
    ReviewSubmitRequest,
    SingleDetectResponse,
    StatsResponse,
    StreamStatusResponse,
    VizDetectResponse,
    VizStep,
)

# ── 配置 ───────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
RESULT_DIR = os.path.join(DATA_DIR, "results")
DB_PATH = os.path.join(DATA_DIR, "history.db")

# ── 模拟数据 ──────────────────────────────────────────────

FMPD_CLASSES = [
    {"class_id": 0, "class_name": "Woronichinia", "class_name_zh": "沃氏藻", "risk_level": "high"},
    {"class_id": 1, "class_name": "Spiroides", "class_name_zh": "螺旋藻", "risk_level": "high"},
    {"class_id": 2, "class_name": "Dinobryon", "class_name_zh": "锥囊藻", "risk_level": "medium"},
    {"class_id": 3, "class_name": "Other-phytoplankton", "class_name_zh": "其他浮游植物", "risk_level": "low"},
    {"class_id": 4, "class_name": "Non-phytoplankton", "class_name_zh": "非浮游植物", "risk_level": "low"},
]

MOCK_DETECTIONS = [
    {"class_id": 0, "class_name": "Woronichinia", "class_name_zh": "沃氏藻",
     "confidence": 0.923, "bbox": [45.2, 78.1, 112.5, 148.3], "risk_level": "high"},
    {"class_id": 0, "class_name": "Woronichinia", "class_name_zh": "沃氏藻",
     "confidence": 0.887, "bbox": [230.1, 56.4, 301.8, 132.7], "risk_level": "high"},
    {"class_id": 2, "class_name": "Dinobryon", "class_name_zh": "锥囊藻",
     "confidence": 0.761, "bbox": [120.5, 200.3, 185.2, 268.9], "risk_level": "medium"},
    {"class_id": 3, "class_name": "Other-phytoplankton", "class_name_zh": "其他浮游植物",
     "confidence": 0.654, "bbox": [310.3, 180.5, 375.8, 245.1], "risk_level": "low"},
    {"class_id": 1, "class_name": "Spiroides", "class_name_zh": "螺旋藻",
     "confidence": 0.912, "bbox": [88.7, 320.4, 198.3, 402.8], "risk_level": "high"},
]

# 单像素蓝色 PNG（作为模拟结果图），前端用它渲染空检测结果
_1PX_BLUE_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+P+/HgAFhQJOrG7aQAAAABJRU5ErkJggg=="
)

# ── 数据库 ────────────────────────────────────────────────

async def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(RESULT_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS detection_history (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                image_path TEXT NOT NULL,
                result_path TEXT NOT NULL,
                detections TEXT NOT NULL,
                q_score REAL,
                risk_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT 'MV-CA013-20GC',
                status TEXT NOT NULL DEFAULT 'offline',
                today_frames INTEGER NOT NULL DEFAULT 0,
                alerts INTEGER NOT NULL DEFAULT 0,
                uptime TEXT NOT NULL DEFAULT '0h',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                detection_id TEXT NOT NULL,
                filename TEXT NOT NULL DEFAULT '',
                class_name TEXT NOT NULL DEFAULT '',
                class_name_zh TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.0,
                risk_level TEXT DEFAULT 'low',
                status TEXT NOT NULL DEFAULT 'pending',
                corrected_class TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        # 首次初始化时插入默认设备
        db.row_factory = aiosqlite.Row
        row = await db.execute_fetchall("SELECT COUNT(*) as c FROM devices")
        if row[0]["c"] == 0:
            import uuid as _uuid
            await db.execute(
                "INSERT INTO devices (id, name, location, model, status, today_frames, alerts, uptime) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (_uuid.uuid4().hex, "海康 MV-CA013-20GC", "实验室 A区", "MV-CA013-20GC", "online", 0, 0, "0h"),
            )
            await db.commit()

async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

# ── 模拟管线 ──────────────────────────────────────────────

class MockPipeline:
    """返回模拟检测结果，不依赖任何 ML 库。"""

    def run(self, filepath: str) -> dict:
        t0 = time.perf_counter()
        # 随机选 2-5 个模拟检测
        import random
        n = random.randint(2, 5)
        dets = random.sample(MOCK_DETECTIONS, min(n, len(MOCK_DETECTIONS)))
        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "detections": dets,
            "result_image": None,  # 前端用 mock 图占位
            "q_score": round(random.uniform(0.65, 0.95), 4),
            "processing_time_ms": round(elapsed + random.uniform(80, 300), 1),
        }

    def run_with_visualization(self, filepath: str) -> dict:
        t0 = time.perf_counter()
        import random
        n = random.randint(2, 5)
        dets = random.sample(MOCK_DETECTIONS, min(n, len(MOCK_DETECTIONS)))
        elapsed = (time.perf_counter() - t0) * 1000

        steps = [
            {
                "title": "Step 1: RGB 原图",
                "image": f"data:image/png;base64,{_1PX_BLUE_PNG}",
                "description": "明场显微成像原始输入（模拟数据）",
            },
            {
                "title": "Step 2: HSV 偏振模拟",
                "image": f"data:image/png;base64,{_1PX_BLUE_PNG}",
                "description": "基于 HSV 色彩空间映射 I0 / I45 / I90 三通道偏振",
            },
            {
                "title": "Step 3: Stokes 参数",
                "image": f"data:image/png;base64,{_1PX_BLUE_PNG}",
                "description": "S0(强度) / DoLP(偏振度) / AoP(偏振角) 参数图",
            },
            {
                "title": "Step 4: I_enh v2 去散射增强",
                "image": f"data:image/png;base64,{_1PX_BLUE_PNG}",
                "description": "偏振增强: S0·(1+α-γ·DoLP+β·|sin(2·AoP)|·DoLP)",
            },
            {
                "title": "Step 5: YOLOv8 检测结果",
                "image": f"data:image/png;base64,{_1PX_BLUE_PNG}",
                "description": f"检测到 {len(dets)} 个藻类目标 (FMPD 5 类，模拟数据)",
            },
        ]

        return {
            "detections": dets,
            "steps": steps,
            "q_score": round(random.uniform(0.65, 0.95), 4),
            "processing_time_ms": round(elapsed + random.uniform(80, 300), 1),
        }


pipeline = MockPipeline()

# ── 路由 ──────────────────────────────────────────────────

router = APIRouter(prefix="/api/v1", tags=["api"])


def _minimal_png() -> bytes:
    """生成 1x1 蓝色 PNG 字节，作为模拟结果图。"""
    img = Image.new("RGB", (1, 1), color=(41, 128, 185))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}


def _safe_ext(filename: str) -> str:
    """返回安全的后缀名，不在白名单内的回退为 .png。"""
    ext = os.path.splitext(filename or "image.png")[1].lower()
    return ext if ext in _ALLOWED_EXTENSIONS else ".png"


@router.post("/preview")
async def preview_image(file: UploadFile = File(...)):
    """上传图片转换为 PNG 供浏览器预览（使用 Pillow，无需 OpenCV）。"""
    contents = await file.read()
    try:
        img = Image.open(BytesIO(contents))
        img = img.convert("RGB")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析图片")


@router.post("/detect", response_model=SingleDetectResponse)
async def detect_single(file: UploadFile = File(...)):
    """单张图片检测（返回模拟数据）。"""
    # 保存上传文件
    file_id = uuid.uuid4().hex
    ext = _safe_ext(file.filename or "image.png")
    safe_name = f"{file_id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(await file.read())

    # 运行管线
    result = pipeline.run(filepath)

    # 保存结果图
    result_filename = f"{file_id}.png"
    result_path = os.path.join(RESULT_DIR, result_filename)
    async with aiofiles.open(result_path, "wb") as f:
        await f.write(_minimal_png())
    result_url = f"/static/results/{result_filename}"

    dets = result["detections"]
    risk = _overall_risk(dets)
    det_items = _to_items(dets)

    # 写入数据库
    conn = await get_db()
    try:
        await conn.execute(
            """INSERT INTO detection_history
                   (id, filename, image_path, result_path, detections, q_score, risk_level)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (file_id, file.filename or "unknown", filepath, result_url,
             json.dumps([d.model_dump() for d in det_items]),
             round(result["q_score"], 4), risk),
        )
        await conn.commit()
    finally:
        await conn.close()

    return SingleDetectResponse(
        id=file_id,
        filename=file.filename or "unknown",
        detections=det_items,
        q_score=round(result["q_score"], 4),
        risk_level=risk,
        result_image_url=result_url,
        processing_time_ms=round(result["processing_time_ms"], 1),
    )


@router.post("/detect/batch", response_model=BatchDetectResponse)
async def detect_batch(files: list[UploadFile] = File(...)):
    """批量检测（最多 50 张，模拟数据）。"""
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="最多 50 张")
    import random

    batch_id = uuid.uuid4().hex
    results: list[BatchResult] = []
    total_dets = 0
    high_count = 0
    q_scores: list[float] = []

    for f in files:
        try:
            file_id = uuid.uuid4().hex
            ext = _safe_ext(f.filename or "img.png")
            filepath = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
            async with aiofiles.open(filepath, "wb") as fh:
                await fh.write(await f.read())

            result = pipeline.run(filepath)
            dets = result["detections"]
            total_dets += len(dets)
            if any(d.get("risk_level") == "high" for d in dets):
                high_count += 1
            q_scores.append(result["q_score"])

            results.append(BatchResult(
                filename=f.filename or "unknown",
                detections=_to_items(dets),
                status="ok",
            ))
        except Exception as e:
            logging.warning("批量检测处理失败: %s — %s", f.filename, e)
            results.append(BatchResult(
                filename=f.filename or "unknown",
                detections=[],
                status="error",
                error="处理失败",
            ))

    avg_q = sum(q_scores) / len(q_scores) if q_scores else 0.0
    return BatchDetectResponse(
        batch_id=batch_id,
        total=len(files),
        results=results,
        summary=BatchSummary(
            total_detections=total_dets,
            high_risk_count=high_count,
            avg_q_score=round(avg_q, 4),
        ),
    )


@router.post("/detect/visualize", response_model=VizDetectResponse)
async def detect_visualize(file: UploadFile = File(...)):
    """单张检测 + 5 步管线可视化（模拟数据）。"""
    file_id = uuid.uuid4().hex
    ext = _safe_ext(file.filename or "image.png")
    filepath = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(await file.read())

    result = pipeline.run_with_visualization(filepath)
    dets = result["detections"]
    risk = _overall_risk(dets)
    det_items = _to_items(dets)

    # 保存结果
    result_path = os.path.join(RESULT_DIR, f"{file_id}.png")
    async with aiofiles.open(result_path, "wb") as f:
        await f.write(_minimal_png())

    conn = await get_db()
    try:
        await conn.execute(
            """INSERT INTO detection_history
                   (id, filename, image_path, result_path, detections, q_score, risk_level)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (file_id, file.filename or "unknown", filepath,
             f"/static/results/{file_id}.png",
             json.dumps([d.model_dump() for d in det_items]),
             round(result["q_score"], 4), risk),
        )
        await conn.commit()
    finally:
        await conn.close()

    return VizDetectResponse(
        id=file_id,
        filename=file.filename or "unknown",
        steps=[VizStep(**s) for s in result["steps"]],
        detections=det_items,
        q_score=round(result["q_score"], 4),
        risk_level=risk,
        processing_time_ms=round(result["processing_time_ms"], 1),
    )


# ── Dashboard ─────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=StatsResponse)
async def get_stats():
    """从数据库获取统计（真实数据）。"""
    conn = await get_db()
    try:
        row = await conn.execute_fetchall("SELECT COUNT(*) as c FROM detection_history")
        total = row[0]["c"] if row else 0

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = await conn.execute_fetchall(
            "SELECT COUNT(*) as c FROM detection_history WHERE date(created_at) = ?",
            (today_str,),
        )
        today = row[0]["c"] if row else 0

        rows = await conn.execute_fetchall(
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

        recent = await conn.execute_fetchall(
            "SELECT id, filename, risk_level, q_score, created_at "
            "FROM detection_history ORDER BY created_at DESC LIMIT 10"
        )
        recent_list = [
            {"id": r["id"], "filename": r["filename"],
             "risk_level": r["risk_level"], "q_score": r["q_score"],
             "created_at": str(r["created_at"])}
            for r in recent
        ]
    finally:
        await conn.close()

    return StatsResponse(
        total_detections=total,
        today_count=today,
        class_distribution=class_dist,
        risk_distribution=risk_dist,
        recent_detections=recent_list,
    )


# ── History ───────────────────────────────────────────────

@router.get("/history", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    conn = await get_db()
    try:
        offset = (page - 1) * limit
        rows = await conn.execute_fetchall(
            "SELECT id, filename, risk_level, q_score, created_at "
            "FROM detection_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        total_row = await conn.execute_fetchall("SELECT COUNT(*) as c FROM detection_history")
        total = total_row[0]["c"] if total_row else 0
    finally:
        await conn.close()

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
async def get_history_detail(record_id: str):
    conn = await get_db()
    try:
        row = await conn.execute_fetchall(
            "SELECT * FROM detection_history WHERE id = ?", (record_id,)
        )
    finally:
        await conn.close()

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
async def delete_history(record_id: str):
    conn = await get_db()
    try:
        row = await conn.execute_fetchall(
            "SELECT image_path, result_path FROM detection_history WHERE id = ?",
            (record_id,),
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

        await conn.execute("DELETE FROM detection_history WHERE id = ?", (record_id,))
        await conn.commit()
    finally:
        await conn.close()
    return {"status": "deleted", "id": record_id}


# ── Stream / Latest ───────────────────────────────────────

_stream_state = {
    "active": False,
    "total_frames": 0,
    "started_at": None,
}


@router.get("/detect/latest", response_model=LatestResultsResponse)
async def get_latest(n: int = Query(10, ge=1, le=100)):
    """最近 N 条检测结果（轻量，无 base64，供前端轮询）"""
    conn = await get_db()
    try:
        rows = await conn.execute_fetchall(
            "SELECT id, filename, detections, q_score, risk_level, created_at "
            "FROM detection_history ORDER BY created_at DESC LIMIT ?",
            (n,),
        )
        results = []
        for r in rows:
            dets = json.loads(r["detections"])
            results.append(LatestResult(
                id=r["id"], filename=r["filename"],
                detections=[DetectionItem(**d) for d in dets],
                q_score=r["q_score"], risk_level=r["risk_level"],
                processing_time_ms=0.0,
                raw_image_url=None, result_image_url=f"/static/results/{r['id']}.png",
            ))
    finally:
        await conn.close()
    return LatestResultsResponse(results=results, count=len(results))


@router.get("/detect/stream-status", response_model=StreamStatusResponse)
async def stream_status():
    """采集状态（演示模式始终为 inactive）"""
    return StreamStatusResponse(
        active=_stream_state["active"],
        total_frames=_stream_state["total_frames"],
        buffer_size=0,
        elapsed_seconds=0.0,
        effective_fps=0.0,
    )


# ── Video (demo) ──────────────────────────────────────────

@router.get("/detect/video-list")
async def video_list():
    """扫描 video/ 目录返回可用 mp4（演示模式返回空）"""
    video_dir = os.path.join(BASE_DIR, "video")
    videos = []
    if os.path.isdir(video_dir):
        for f in sorted(os.listdir(video_dir)):
            if f.lower().endswith((".mp4", ".avi", ".mov")):
                videos.append({"name": f, "path": os.path.join(video_dir, f)})
    return {"videos": videos}


@router.get("/detect/video-status")
async def video_status():
    return {"active": False, "video_path": None, "fps": 0, "current_frame": 0, "total_frames": 0}


@router.post("/detect/stream/start")
async def stream_start(exposure_us: int = Query(5000)):
    """演示模式不支持相机启动"""
    raise HTTPException(status_code=400, detail="演示服务器不支持相机直连，请在本地运行")


@router.post("/detect/stream/stop")
async def stream_stop():
    _stream_state["active"] = False
    return {"status": "stopped"}


@router.post("/detect/stream/start-video")
async def stream_start_video(video_path: str = Query(...), fps: int = Query(10), loop: bool = Query(False)):
    raise HTTPException(status_code=400, detail="演示服务器不支持视频流，请在本地运行")


@router.post("/detect/stream/stop-video")
async def stream_stop_video():
    return {"status": "stopped"}


# ── Device Management ─────────────────────────────────────

@router.get("/devices", response_model=DeviceListResponse)
async def list_devices():
    conn = await get_db()
    try:
        rows = await conn.execute_fetchall("SELECT * FROM devices ORDER BY created_at DESC")
        devices = [
            DeviceInfo(id=r["id"], name=r["name"], location=r["location"], model=r["model"],
                       status=r["status"], today_frames=r["today_frames"], alerts=r["alerts"], uptime=r["uptime"])
            for r in rows
        ]
    finally:
        await conn.close()
    return DeviceListResponse(devices=devices)


@router.post("/devices")
async def add_device(name: str = Query(...), location: str = Query(""), model: str = Query("MV-CA013-20GC")):
    conn = await get_db()
    try:
        dev_id = uuid.uuid4().hex
        await conn.execute(
            "INSERT INTO devices (id, name, location, model, status, today_frames, alerts, uptime) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (dev_id, name, location, model, "offline", 0, 0, "0h"),
        )
        await conn.commit()
    finally:
        await conn.close()
    return {"id": dev_id, "name": name, "status": "created"}


@router.put("/devices/{device_id}")
async def update_device(device_id: str, name: str = Query(None), location: str = Query(None),
                        model: str = Query(None), status: str = Query(None)):
    conn = await get_db()
    try:
        sets = []
        vals = []
        for k, v in [("name", name), ("location", location), ("model", model), ("status", status)]:
            if v is not None:
                sets.append(f"{k} = ?")
                vals.append(v)
        if not sets:
            raise HTTPException(status_code=400, detail="无更新字段")
        vals.append(device_id)
        await conn.execute(f"UPDATE devices SET {', '.join(sets)} WHERE id = ?", vals)
        await conn.commit()
    finally:
        await conn.close()
    return {"id": device_id, "status": "updated"}


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str):
    conn = await get_db()
    try:
        row = await conn.execute_fetchall("SELECT id FROM devices WHERE id = ?", (device_id,))
        if not row:
            raise HTTPException(status_code=404, detail="设备不存在")
        await conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        await conn.commit()
    finally:
        await conn.close()
    return {"status": "deleted", "id": device_id}


# ── Review ────────────────────────────────────────────────

@router.get("/review/list", response_model=ReviewListResponse)
async def list_reviews(status: str = Query(None)):
    conn = await get_db()
    try:
        where = "WHERE status = ?" if status else ""
        params = (status,) if status else ()
        rows = await conn.execute_fetchall(
            f"SELECT * FROM reviews {where} ORDER BY created_at DESC LIMIT 200", params
        )
        items = [
            ReviewItem(id=r["id"], detection_id=r["detection_id"], filename=r["filename"],
                       class_name=r["class_name"], class_name_zh=r["class_name_zh"],
                       confidence=round(r["confidence"], 4), risk_level=r["risk_level"],
                       status=r["status"], created_at=str(r["created_at"]))
            for r in rows
        ]
        # 统计
        all_rows = await conn.execute_fetchall("SELECT status FROM reviews")
        approved = sum(1 for r in all_rows if r["status"] == "approved")
        pending = sum(1 for r in all_rows if r["status"] == "pending")
    finally:
        await conn.close()
    return ReviewListResponse(items=items, total=len(items), approved_count=approved, pending_count=pending)


@router.post("/review/submit")
async def submit_review(body: ReviewSubmitRequest):
    conn = await get_db()
    try:
        row = await conn.execute_fetchall("SELECT * FROM detection_history WHERE id = ?", (body.detection_id,))
        if not row:
            raise HTTPException(status_code=404, detail="检测记录不存在")
        r = row[0]
        dets = json.loads(r["detections"]) if r["detections"] else []
        # 取第一个检测结果的类名
        cls_name = dets[0].get("class_name", "") if dets else ""
        cls_zh = dets[0].get("class_name_zh", "") if dets else ""
        conf = dets[0].get("confidence", 0.0) if dets else 0.0
        risk = dets[0].get("risk_level", "low") if dets else "low"

        review_id = uuid.uuid4().hex
        await conn.execute(
            "INSERT INTO reviews (id, detection_id, filename, class_name, class_name_zh, confidence, risk_level, status, corrected_class) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (review_id, body.detection_id, r["filename"], cls_name, cls_zh, conf, risk, body.status, body.corrected_class),
        )
        await conn.commit()
    finally:
        await conn.close()
    return {"id": review_id, "status": body.status}


@router.post("/review/submit-batch")
async def submit_review_batch():
    """批量提交低置信度检测到复核池（演示模式返回空操作）"""
    return {"count": 0, "message": "演示模式：批量提交需要完整管线支持"}


# ── Helpers ───────────────────────────────────────────────

def _overall_risk(detections: list[dict]) -> Optional[str]:
    risks = [d.get("risk_level", "low") for d in detections]
    if "high" in risks:
        return "high"
    if "medium" in risks:
        return "medium"
    return "low" if risks else None


def _to_items(detections: list[dict]) -> list[DetectionItem]:
    return [
        DetectionItem(
            class_id=d["class_id"],
            class_name=d["class_name"],
            class_name_zh=d.get("class_name_zh", d["class_name"]),
            confidence=round(d["confidence"], 4),
            bbox=[round(v, 1) for v in d["bbox"]],
            risk_level=d.get("risk_level", "low"),
        )
        for d in detections
    ]


# ── App ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print(f"[Startup] SQLite 就绪 — {DB_PATH}")
    print(f"[Startup] 轻量模式 — 无 PyTorch / YOLO，返回模拟数据")
    print(f"[Startup] 端口: {PORT}")
    yield

app = FastAPI(
    title="藻影知微 V2 — Lightweight Demo",
    description="HSV 偏振管线 API（模拟数据，演示用）",
    version="2.0.0-light",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static/results", StaticFiles(directory=RESULT_DIR), name="results")
app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server_light:app", host=HOST, port=PORT, reload=False)
