"""
Tests for Redis shared scratchpad workspace integration (task:<task_id>:workspace).
"""
import uuid
import pytest
from src.services.redis_service import redis_service
from src.agents.research_agent import research_node
from src.agents.writing_agent import draft_writing_node


def test_redis_scratchpad_key_pattern():
    task_id = str(uuid.uuid4())
    key = redis_service.get_scratchpad_key(task_id)
    assert key == f"task:{task_id}:workspace"


def test_research_agent_writes_and_writing_agent_reads_scratchpad(mock_redis):
    task_id = str(uuid.uuid4())
    prompt = "Research the key features of LangGraph and CrewAI."

    # 1. Execute ResearchAgent node
    initial_state = {
        "task_id": task_id,
        "prompt": prompt,
        "status": "RUNNING",
        "agent_logs": []
    }
    after_research = research_node(initial_state)

    # Verify key exists in Redis scratchpad
    scratchpad_key = f"task:{task_id}:workspace"
    raw_workspace = mock_redis.get(scratchpad_key)
    assert raw_workspace is not None

    # Verify data in Redis scratchpad contains research output
    workspace_data = redis_service.get_scratchpad(task_id)
    assert isinstance(workspace_data, dict)
    assert "content" in workspace_data
    assert "LangGraph" in workspace_data["content"]
    assert "CrewAI" in workspace_data["content"]

    # 2. Execute WritingAgent draft node
    after_writing = draft_writing_node(after_research)

    assert after_writing["draft_summary"] is not None
    assert "LangGraph" in after_writing["draft_summary"]
    assert "CrewAI" in after_writing["draft_summary"]
    assert after_writing["status"] == "AWAITING_APPROVAL"
