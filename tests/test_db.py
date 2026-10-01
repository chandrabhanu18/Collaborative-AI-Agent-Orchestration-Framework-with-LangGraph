"""
Tests for database schema, models, and task persistence.
"""
import uuid
import pytest
from datetime import datetime
from src.db.models import Task
from src.services.task_service import task_service
from sqlalchemy import inspect


@pytest.mark.asyncio
async def test_task_schema_columns(async_db_session):
    """Verifies that the tasks table schema contains all mandatory columns."""
    task_id = uuid.uuid4()
    task = Task(
        id=task_id,
        prompt="Schema verification test",
        status="PENDING",
        result=None,
        agent_logs=[{"agent": "TestAgent", "action": "test", "timestamp": "2026-09-29T10:00:00Z"}],
    )
    async_db_session.add(task)
    await async_db_session.commit()
    await async_db_session.refresh(task)

    assert task.id == task_id
    assert task.prompt == "Schema verification test"
    assert task.status == "PENDING"
    assert task.result is None
    assert len(task.agent_logs) == 1
    assert task.created_at is not None
    assert task.updated_at is not None


@pytest.mark.asyncio
async def test_task_service_crud(async_db_session):
    """Tests task creation, retrieval, and status updates."""
    # 1. Create task
    task = await task_service.async_create_task(
        db=async_db_session,
        prompt="CRUD test prompt",
    )
    assert task.id is not None
    assert task.status == "PENDING"

    # 2. Get task
    fetched = await task_service.async_get_task(db=async_db_session, task_id=task.id)
    assert fetched is not None
    assert fetched.prompt == "CRUD test prompt"

    # 3. Update status & result
    updated = await task_service.async_update_task_status(
        db=async_db_session,
        task_id=task.id,
        status="COMPLETED",
        result="Final test result output",
        agent_logs=[{"agent": "WritingAgent", "action": "Done", "timestamp": "2026-09-29T10:00:00Z"}]
    )
    assert updated.status == "COMPLETED"
    assert updated.result == "Final test result output"
    assert len(updated.agent_logs) == 1
