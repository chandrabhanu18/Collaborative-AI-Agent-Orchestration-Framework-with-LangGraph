"""
Database session management for asynchronous (FastAPI) and synchronous (Celery) contexts.
"""
import logging
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config.settings import settings
from src.db.models import Base

logger = logging.getLogger(__name__)

# Async Engine and Session for FastAPI
async_engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync Engine and Session for Celery worker
sync_engine = create_engine(
    settings.sync_database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Initializes the database schema automatically if tables do not exist."""
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.warning(f"Async DB init encountered an issue ({e}). Attempting sync fallback init.")
        try:
            Base.metadata.create_all(bind=sync_engine)
            logger.info("Sync fallback DB init succeeded.")
        except Exception as sync_e:
            logger.error(f"Failed to initialize database: {sync_e}")
            raise sync_e


def init_db_sync():
    """Synchronously initializes the database schema (used by workers/scripts)."""
    Base.metadata.create_all(bind=sync_engine)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """Provides a synchronous database session for Celery tasks."""
    return SyncSessionLocal()
