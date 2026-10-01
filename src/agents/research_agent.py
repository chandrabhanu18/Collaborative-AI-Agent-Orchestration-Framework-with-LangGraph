"""
ResearchAgent node for information gathering and storing intermediate data in Redis scratchpad.
"""
from datetime import datetime, timezone
from typing import Dict, Any
from src.agents.state import AgentWorkflowState
from src.agents.tools import execute_search_with_retry
from src.services.redis_service import redis_service
from src.config.logging_config import log_agent_activity


def research_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """
    Executes the research phase:
    1. Runs search with retry logic.
    2. Writes findings to Redis scratchpad (task:<task_id>:workspace).
    3. Records agent audit log entry.
    4. Logs structured activity to logs/agent_activity.log.
    """
    task_id = state.get("task_id", "unknown_task")
    prompt = state.get("prompt", "")

    log_agent_activity(
        task_id=task_id,
        agent_name="ResearchAgent",
        action_details=f"Initiating research phase for task prompt: '{prompt}'"
    )

    # Execute search with resilient retry support
    search_query = prompt if prompt else "LangGraph vs CrewAI architecture"
    research_content = execute_search_with_retry(query=search_query, task_id=task_id)

    research_payload: Dict[str, Any] = {
        "task_id": task_id,
        "query": search_query,
        "content": research_content,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": "Simulated Research Engine"
    }

    # Write intermediate artifact to Redis shared scratchpad
    redis_service.set_scratchpad(task_id=task_id, data=research_payload)
    log_agent_activity(
        task_id=task_id,
        agent_name="ResearchAgent",
        action_details=f"Saved intermediate research findings to Redis key task:{task_id}:workspace"
    )

    # Append to agent audit logs
    now_iso = datetime.now(timezone.utc).isoformat()
    if now_iso.endswith("+00:00"):
        now_iso = now_iso[:-6] + "Z"

    agent_logs = list(state.get("agent_logs") or [])
    agent_logs.append({
        "agent": "ResearchAgent",
        "action": f"Searching for {prompt[:50]} features",
        "timestamp": now_iso
    })

    log_agent_activity(
        task_id=task_id,
        agent_name="ResearchAgent",
        action_details="Completed research phase and successfully updated state."
    )

    return {
        **state,
        "research_data": research_payload,
        "agent_logs": agent_logs,
        "current_step": "research_completed",
        "status": "RUNNING"
    }
