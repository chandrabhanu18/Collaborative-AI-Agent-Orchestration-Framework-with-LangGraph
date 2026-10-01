"""
Celery background tasks for orchestrating LangGraph multi-agent workflows.
"""
import logging
from typing import Optional
from src.worker.celery_app import celery_app
from src.db.session import get_sync_db
from src.services.task_service import task_service
from src.services.redis_service import redis_service
from src.agents.workflow import execute_phase1_workflow, execute_phase2_workflow
from src.config.logging_config import log_agent_activity

logger = logging.getLogger(__name__)


@celery_app.task(name="src.worker.tasks.run_agent_workflow", bind=True)
def run_agent_workflow(self, task_id: str, prompt: str):
    """
    Executes Phase 1:
    - Status: PENDING -> RUNNING
    - Executes ResearchAgent -> WritingAgent (draft)
    - Status: RUNNING -> AWAITING_APPROVAL
    """
    logger.info(f"Starting Celery workflow task for task_id={task_id}")
    db = get_sync_db()

    try:
        # Step 1: Update status to RUNNING and publish
        task_service.sync_update_task(db=db, task_id=task_id, status="RUNNING")
        redis_service.publish_status(task_id=task_id, status="RUNNING")
        log_agent_activity(
            task_id=task_id,
            agent_name="CeleryWorker",
            action_details=f"Task transitioned to RUNNING. Starting workflow for prompt: '{prompt}'"
        )

        # Step 2: Execute LangGraph Phase 1
        state = execute_phase1_workflow(task_id=task_id, prompt=prompt)

        # Step 3: Save draft in Redis workspace & update task status to AWAITING_APPROVAL
        draft_summary = state.get("draft_summary", "")
        agent_logs = state.get("agent_logs", [])

        # Store draft metadata in Redis scratchpad
        existing_workspace = redis_service.get_scratchpad(task_id) or {}
        if isinstance(existing_workspace, dict):
            existing_workspace["draft"] = draft_summary
            redis_service.set_scratchpad(task_id, existing_workspace)

        task_service.sync_update_task(
            db=db,
            task_id=task_id,
            status="AWAITING_APPROVAL",
            agent_logs=agent_logs
        )
        redis_service.publish_status(task_id=task_id, status="AWAITING_APPROVAL")

        log_agent_activity(
            task_id=task_id,
            agent_name="CeleryWorker",
            action_details="Phase 1 complete. Paused at AWAITING_APPROVAL for human input."
        )
        return {"task_id": task_id, "status": "AWAITING_APPROVAL"}

    except Exception as exc:
        logger.exception(f"Error executing agent workflow for task {task_id}: {exc}")
        log_agent_activity(
            task_id=task_id,
            agent_name="CeleryWorker",
            action_details=f"Workflow failed with error: {str(exc)}"
        )
        task_service.sync_update_task(db=db, task_id=task_id, status="FAILED", result=f"Error: {str(exc)}")
        redis_service.publish_status(task_id=task_id, status="FAILED")
        raise exc
    finally:
        db.close()


@celery_app.task(name="src.worker.tasks.resume_agent_workflow", bind=True)
def resume_agent_workflow(
    self,
    task_id: str,
    approved: bool = True,
    feedback: Optional[str] = None
):
    """
    Executes Phase 2 (Resumed):
    - Status: RESUMED
    - WritingAgent finalizes summary with feedback
    - Status: COMPLETED
    - Stores final result in PostgreSQL and publishes update
    """
    logger.info(f"Resuming Celery workflow for task_id={task_id}, approved={approved}")
    db = get_sync_db()

    try:
        # Step 1: Update status to RESUMED and broadcast
        task_service.sync_update_task(db=db, task_id=task_id, status="RESUMED")
        redis_service.publish_status(task_id=task_id, status="RESUMED")
        log_agent_activity(
            task_id=task_id,
            agent_name="CeleryWorker",
            action_details=f"Task resumed. Human approved: {approved}, Feedback: '{feedback or 'None'}'"
        )

        task_record = task_service.sync_get_task(db=db, task_id=task_id)
        if not task_record:
            raise ValueError(f"Task with id {task_id} not found in database.")

        prompt = task_record.prompt
        existing_logs = task_record.agent_logs or []

        # Fetch draft from Redis scratchpad or fallback
        workspace_data = redis_service.get_scratchpad(task_id) or {}
        draft = ""
        if isinstance(workspace_data, dict):
            draft = workspace_data.get("draft") or workspace_data.get("content", "")

        # Step 2: Execute LangGraph Phase 2
        final_state = execute_phase2_workflow(
            task_id=task_id,
            prompt=prompt,
            draft_summary=draft,
            existing_agent_logs=existing_logs,
            feedback=feedback,
        )

        final_summary = final_state.get("final_summary", "")
        final_logs = final_state.get("agent_logs", existing_logs)

        # Step 3: Persist final summary to PostgreSQL result field and set status to COMPLETED
        task_service.sync_update_task(
            db=db,
            task_id=task_id,
            status="COMPLETED",
            result=final_summary,
            agent_logs=final_logs
        )
        redis_service.publish_status(task_id=task_id, status="COMPLETED")

        log_agent_activity(
            task_id=task_id,
            agent_name="CeleryWorker",
            action_details="Workflow completed successfully. Final result persisted to database."
        )
        return {"task_id": task_id, "status": "COMPLETED"}

    except Exception as exc:
        logger.exception(f"Error resuming agent workflow for task {task_id}: {exc}")
        log_agent_activity(
            task_id=task_id,
            agent_name="CeleryWorker",
            action_details=f"Resumed workflow failed with error: {str(exc)}"
        )
        task_service.sync_update_task(db=db, task_id=task_id, status="FAILED", result=f"Error: {str(exc)}")
        redis_service.publish_status(task_id=task_id, status="FAILED")
        raise exc
    finally:
        db.close()
