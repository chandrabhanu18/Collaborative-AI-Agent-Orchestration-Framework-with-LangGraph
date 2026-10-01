"""
Unit tests for individual agent nodes and tool interactions.
"""
import uuid
import pytest
from src.agents.research_agent import research_node
from src.agents.writing_agent import draft_writing_node, final_writing_node, synthesize_draft_summary, synthesize_final_summary


def test_synthesize_draft_summary():
    prompt = "Compare LangGraph and CrewAI"
    research_content = "LangGraph uses graphs; CrewAI uses roles."
    summary = synthesize_draft_summary(prompt=prompt, research_content=research_content)
    assert "LangGraph" in summary
    assert "CrewAI" in summary
    assert "Comparison" in summary


def test_synthesize_final_summary_with_feedback():
    draft = "Base draft summary"
    feedback = "Add more details on Redis state."
    final_result = synthesize_final_summary(draft=draft, feedback=feedback)
    assert draft in final_result
    assert feedback in final_result


def test_research_agent_node_execution(mock_redis):
    task_id = str(uuid.uuid4())
    state = {
        "task_id": task_id,
        "prompt": "Evaluate agent frameworks",
        "status": "RUNNING",
        "agent_logs": []
    }
    updated_state = research_node(state)
    assert updated_state["status"] == "RUNNING"
    assert updated_state["research_data"] is not None
    assert len(updated_state["agent_logs"]) == 1
    assert updated_state["agent_logs"][0]["agent"] == "ResearchAgent"


def test_writing_agent_draft_and_final_nodes(mock_redis):
    task_id = str(uuid.uuid4())
    state = {
        "task_id": task_id,
        "prompt": "Compare LangGraph and CrewAI",
        "status": "RUNNING",
        "agent_logs": [{"agent": "ResearchAgent", "action": "Gathered data", "timestamp": "2026-09-29T10:00:00Z"}]
    }
    # 1. Draft phase
    draft_state = draft_writing_node(state)
    assert draft_state["status"] == "AWAITING_APPROVAL"
    assert draft_state["draft_summary"] is not None
    assert len(draft_state["agent_logs"]) == 2

    # 2. Final phase
    draft_state["human_feedback"] = "Approved with excellence."
    final_state = final_writing_node(draft_state)
    assert final_state["status"] == "COMPLETED"
    assert final_state["final_summary"] is not None
    assert len(final_state["agent_logs"]) == 3
    assert final_state["agent_logs"][2]["agent"] == "WritingAgent"
