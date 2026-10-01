"""
Task service layer for CRUD operations and state tracking in PostgreSQL.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Task

logger = logging.getLogger(__name__)


class TaskService:
    # ------------------ ASYNC (FastAPI) ------------------
    @staticmethod
    async def async_create_task(
        db: AsyncSession,
        prompt: str,
        task_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> Task:
        if task_id is None:
            task_id = uuid.uuid4()
        elif isinstance(task_id, str):
            task_id = uuid.UUID(task_id)

        now = datetime.now(timezone.utc)
        task = Task(
            id=task_id,
            prompt=prompt,
            status="PENDING",
            result=None,
            agent_logs=[],
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    async def async_get_task(
        db: AsyncSession,
        task_id: Union[str, uuid.UUID],
    ) -> Optional[Task]:
        if isinstance(task_id, str):
            try:
                task_id = uuid.UUID(task_id)
            except ValueError:
                return None
        stmt = select(Task).where(Task.id == task_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def async_update_task_status(
        db: AsyncSession,
        task_id: Union[str, uuid.UUID],
        status: str,
        result: Optional[str] = None,
        agent_logs: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Task]:
        if isinstance(task_id, str):
            try:
                task_id = uuid.UUID(task_id)
            except ValueError:
                return None

        task = await TaskService.async_get_task(db, task_id)
        if not task:
            return None

        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        if result is not None:
            task.result = result
        if agent_logs is not None:
            task.agent_logs = agent_logs

        await db.flush()
        await db.refresh(task)
        return task

    # ------------------ SYNC (Celery Worker) ------------------
    @staticmethod
    def sync_get_task(
        db: Session,
        task_id: Union[str, uuid.UUID],
    ) -> Optional[Task]:
        if isinstance(task_id, str):
            try:
                task_id = uuid.UUID(task_id)
            except ValueError:
                return None
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def sync_update_task(
        db: Session,
        task_id: Union[str, uuid.UUID],
        status: Optional[str] = None,
        result: Optional[str] = None,
        agent_logs: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Task]:
        if isinstance(task_id, str):
            try:
                task_id = uuid.UUID(task_id)
            except ValueError:
                return None

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None

        if status is not None:
            task.status = status
        if result is not None:
            task.result = result
        if agent_logs is not None:
            task.agent_logs = agent_logs
        task.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def sync_append_agent_log(
        db: Session,
        task_id: Union[str, uuid.UUID],
        agent_name: str,
        action: str,
    ) -> Optional[Task]:
        if isinstance(task_id, str):
            try:
                task_id = uuid.UUID(task_id)
            except ValueError:
                return None

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None

        now = datetime.now(timezone.utc).isoformat()
        if now.endswith("+00:00"):
            now = now[:-6] + "Z"

        current_logs = list(task.agent_logs or [])
        current_logs.append({
            "agent": agent_name,
            "action": action,
            "timestamp": now,
        })
        task.agent_logs = current_logs
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(task)
        return task


task_service = TaskService()
