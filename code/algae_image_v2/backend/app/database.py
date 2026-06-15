"""SQLite database initialization and connection management."""
import os
import aiosqlite
from .config import DB_PATH, DATA_DIR, UPLOAD_DIR, RESULT_DIR


async def init_db():
    """Create tables and data directories on startup."""
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
                created_at TEXT DEFAULT (datetime('now','+8 hours'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS batch_tasks (
                id TEXT PRIMARY KEY,
                total INTEGER NOT NULL,
                completed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'processing',
                created_at TEXT DEFAULT (datetime('now','+8 hours'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT 'MV-CA013-20GC',
                status TEXT NOT NULL DEFAULT 'offline',
                today_frames INTEGER DEFAULT 0,
                alerts INTEGER DEFAULT 0,
                uptime TEXT DEFAULT '--',
                created_at TEXT DEFAULT (datetime('now','+8 hours'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviewed_records (
                id TEXT PRIMARY KEY,
                detection_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                class_name TEXT NOT NULL,
                class_name_zh TEXT DEFAULT '',
                confidence REAL DEFAULT 0,
                risk_level TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                corrected_class TEXT,
                created_at TEXT DEFAULT (datetime('now','+8 hours'))
            )
        """)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    """Return an async database connection with row_factory set for dict-like access."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db
