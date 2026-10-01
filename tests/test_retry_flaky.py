"""
Tests for flaky tool failure, automatic retry logic, and structured JSON activity logging.
"""
import json
import uuid
import os
import pytest
from pathlib import Path
from src.agents.tools import execute_search_with_retry, simulated_search_tool, flaky_tool_attempts
from src.agents.research_agent import research_node
from src.config.settings import settings


def test_flaky_tool_direct_failure_and_success():
    task_id = str(uuid.uuid4())
    query = "__FLAKY_TEST__"

    # Reset attempts for test
    attempt_key = f"{task_id}:{query}"
    flaky_tool_attempts.pop(attempt_key, None)

    # First attempt should raise Exception
    with pytest.raises(Exception) as exc_info:
        simulated_search_tool(query=query, task_id=task_id)
    assert "Simulated transient network timeout." in str(exc_info.value)

    # Second attempt should succeed
    result = simulated_search_tool(query=query, task_id=task_id)
    assert "Search results retrieved on second attempt." in result


def test_retry_wrapper_recovers_from_flaky_failure():
    task_id = str(uuid.uuid4())
    query = "__FLAKY_TEST__"

    # Reset attempt tracker
    attempt_key = f"{task_id}:{query}"
    flaky_tool_attempts.pop(attempt_key, None)

    # Calling with retry should not raise, but recover and succeed
    result = execute_search_with_retry(query=query, task_id=task_id, max_retries=2)
    assert "Search results retrieved on second attempt." in result


def test_flaky_tool_structured_logging_verification(mock_redis):
    task_id = f"test-flaky-{uuid.uuid4()}"
    prompt = "__FLAKY_TEST__"

    # Execute research node with flaky prompt
    state = {
        "task_id": task_id,
        "prompt": prompt,
        "status": "RUNNING",
        "agent_logs": []
    }

    result_state = research_node(state)
    assert result_state["status"] == "RUNNING"
    assert "Search results retrieved on second attempt." in result_state["research_data"]["content"]

    # Verify log entries in log file
    log_file_path = Path(settings.LOG_FILE_PATH)
    assert log_file_path.exists()

    with open(log_file_path, "r", encoding="utf-8") as f:
        log_lines = [json.loads(line) for line in f if line.strip()]

    task_logs = [log for log in log_lines if log.get("task_id") == task_id]
    assert len(task_logs) >= 3

    # Check for failure entry
    failure_entries = [
        l for l in task_logs if "Tool failure encountered" in l["action_details"]
    ]
    assert len(failure_entries) > 0, "Log must record the initial tool failure"

    # Check for retry entry
    retry_entries = [
        l for l in task_logs if "Retry attempt" in l["action_details"]
    ]
    assert len(retry_entries) > 0, "Log must record the retry attempt"

    # Verify structured fields
    for entry in task_logs:
        assert "timestamp" in entry
        assert "task_id" in entry
        assert "agent_name" in entry
        assert "action_details" in entry
