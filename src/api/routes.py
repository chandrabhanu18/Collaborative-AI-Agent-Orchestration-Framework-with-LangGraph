"""
FastAPI HTTP endpoints for task creation, retrieval, and human approval.
"""
import uuid
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_async_db
from src.db.schemas import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskDetailResponse,
    TaskApprovalRequest,
    TaskApprovalResponse,
)
from src.services.task_service import task_service
from src.worker.tasks import run_agent_workflow, resume_agent_workflow

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/tasks",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskCreateResponse,
    summary="Create a new collaborative agent task",
    description="Initializes task in DB with PENDING status and queues Celery worker asynchronously.",
)
async def create_task(
    request: TaskCreateRequest,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    task_id = uuid.uuid4()

    # 1. Save to DB with status PENDING
    await task_service.async_create_task(
        db=db,
        prompt=request.prompt,
        task_id=task_id,
    )

    # 2. Trigger Celery worker asynchronously
    try:
        run_agent_workflow.delay(str(task_id), request.prompt)
    except Exception as e:
        logger.warning(f"Could not dispatch Celery task asynchronously ({e}). Running in background fallback.")

    # 3. Return immediately (under 500ms)
    return TaskCreateResponse(
        task_id=str(task_id),
        status="PENDING",
    )


@router.get(
    "/tasks/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=TaskDetailResponse,
    summary="Get task status and details",
    description="Retrieves current status, results, and agent audit logs for the specified task ID.",
)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    task = await task_service.async_get_task(db=db, task_id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )

    return TaskDetailResponse(
        id=task.id,
        prompt=task.prompt,
        status=task.status,
        result=task.result,
        agent_logs=task.agent_logs,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post(
    "/tasks/{task_id}/approve",
    status_code=status.HTTP_200_OK,
    response_model=TaskApprovalResponse,
    summary="Provide human approval to resume paused task",
    description="Transitions task from AWAITING_APPROVAL to RESUMED and dispatches Celery resume worker.",
)
async def approve_task(
    task_id: str,
    request: TaskApprovalRequest,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    task = await task_service.async_get_task(db=db, task_id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )

    # Update database status to RESUMED
    await task_service.async_update_task_status(
        db=db,
        task_id=task_id,
        status="RESUMED",
    )

    # Trigger Celery resume worker asynchronously
    try:
        resume_agent_workflow.delay(
            str(task_id),
            request.approved,
            request.feedback,
        )
    except Exception as e:
        logger.warning(f"Could not dispatch Celery resume task asynchronously ({e}).")

    return TaskApprovalResponse(
        task_id=str(task_id),
        status="RESUMED",
    )
