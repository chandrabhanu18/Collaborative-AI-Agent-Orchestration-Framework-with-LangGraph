"""
Pytest configuration, fixtures, and in-memory mock services.
"""
import os
import json
import uuid
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_agent_db.db"
os.environ["ASYNC_DATABASE_URL"] = "sqlite+aiosqlite:///./test_agent_db.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["LOG_FILE_PATH"] = "logs/test_agent_activity.log"

from src.db.models import Base
from src.db.session import get_async_db
from src.main import app
from src.services.redis_service import RedisService
from src.worker.celery_app import celery_app

# Enable eager execution for unit/integration tests so celery tasks execute without external daemon
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True

# Test SQLite DB Engines
test_async_engine = create_async_engine(
    "sqlite+aiosqlite:///./test_agent_db.db",
    echo=False,
    future=True,
)
TestAsyncSessionLocal = async_sessionmaker(
    bind=test_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

test_sync_engine = create_engine(
    "sqlite:///./test_agent_db.db",
    echo=False,
    future=True,
)
TestSyncSessionLocal = sessionmaker(
    bind=test_sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class InMemoryMockRedis:
    """In-memory mock for Redis scratchpad and pubsub during local tests."""
    def __init__(self):
        self.store = {}
        self.channels = {}

    def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        if key in self.store:
            del self.store[key]
            return 1
        return 0

    def publish(self, channel, message):
        if channel not in self.channels:
            self.channels[channel] = []
        self.channels[channel].append(message)
        return 1


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_database():
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Clean up test DB file if exists
    try:
        if os.path.exists("./test_agent_db.db"):
            os.remove("./test_agent_db.db")
    except Exception:
        pass


@pytest_asyncio.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestAsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(async_db_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_async_db():
        yield async_db_session

    app.dependency_overrides[get_async_db] = override_get_async_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis(monkeypatch):
    from src.services.redis_service import redis_service
    in_mem_redis = InMemoryMockRedis()
    monkeypatch.setattr(redis_service, "_sync_client", in_mem_redis)
    return in_mem_redis
