"""
End-to-end multi-agent workflow tests validating LangGraph orchestration,
state transitions, human-in-the-loop pauses, and audit log tracking.
"""
import uuid
import json
import pytest
from pathlib import Path
from src.agents.workflow import execute_phase1_workflow, execute_phase2_workflow
from src.config.settings import settings


def test_full_two_phase_collaborative_workflow(mock_redis):
    task_id = str(uuid.uuid4())
    prompt = "Research the key features of LangGraph and CrewAI. Write a short comparison summary for a technical audience."

    # Phase 1: ResearchAgent + WritingAgent (draft) -> Pauses at AWAITING_APPROVAL
    phase1_state = execute_phase1_workflow(task_id=task_id, prompt=prompt)

    assert phase1_state["status"] == "AWAITING_APPROVAL"
    assert phase1_state["current_step"] == "draft_created"
    assert phase1_state["draft_summary"] is not None
    assert len(phase1_state["draft_summary"]) > 0
    assert "LangGraph" in phase1_state["draft_summary"]
    assert "CrewAI" in phase1_state["draft_summary"]

    # Verify agent_logs audit trail has ResearchAgent and WritingAgent entries
    agent_logs = phase1_state["agent_logs"]
    assert len(agent_logs) >= 2
    agents_acted = {entry["agent"] for entry in agent_logs}
    assert "ResearchAgent" in agents_acted
    assert "WritingAgent" in agents_acted

    for entry in agent_logs:
        assert "agent" in entry
        assert "action" in entry
        assert "timestamp" in entry

    # Phase 2: Human approval -> Resumes -> Finalizes summary -> COMPLETED
    human_feedback = "Please emphasize enterprise fault tolerance."
    phase2_state = execute_phase2_workflow(
        task_id=task_id,
        prompt=prompt,
        draft_summary=phase1_state["draft_summary"],
        existing_agent_logs=agent_logs,
        feedback=human_feedback,
    )

    assert phase2_state["status"] == "COMPLETED"
    assert phase2_state["current_step"] == "completed"
    assert phase2_state["final_summary"] is not None
    assert len(phase2_state["final_summary"]) > 0
    assert "Human Feedback Incorporated" in phase2_state["final_summary"] or human_feedback in phase2_state["final_summary"]

    # Verify log file has structured logs for this task
    log_file_path = Path(settings.LOG_FILE_PATH)
    assert log_file_path.exists()
    with open(log_file_path, "r", encoding="utf-8") as f:
        log_lines = [json.loads(line) for line in f if line.strip()]

    task_logs = [log for log in log_lines if log.get("task_id") == task_id]
    assert len(task_logs) >= 4
    agent_names_logged = {log["agent_name"] for log in task_logs}
    assert "ResearchAgent" in agent_names_logged
    assert "WritingAgent" in agent_names_logged
    assert "Orchestrator" in agent_names_logged
