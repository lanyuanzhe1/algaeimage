"""Database setup with SQLAlchemy async."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from pathlib import Path

from .config import DATABASE_URL
from .models import Base


# Async engine for production use
async_engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


# Sync engine for initialization
def get_sync_engine():
    sync_url = DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///")
    sync_engine = create_engine(sync_url, echo=False)

    @event.listens_for(sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return sync_engine


def init_db():
    """Initialize database and create all tables."""
    engine = get_sync_engine()
    Base.metadata.create_all(bind=engine)

    # Verify tables exist
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Database initialized. Tables: {tables}")
    return tables


async def get_async_session():
    """Dependency for FastAPI to get async DB session."""
    async with async_session_factory() as session:
        yield session
