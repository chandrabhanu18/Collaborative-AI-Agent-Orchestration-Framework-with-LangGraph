"""
Agent workflow state definition for LangGraph.
"""
from typing import TypedDict, Optional, List, Dict, Any


class AgentWorkflowState(TypedDict, total=False):
    task_id: str
    prompt: str
    research_data: Optional[Dict[str, Any]]
    draft_summary: Optional[str]
    final_summary: Optional[str]
    human_approved: bool
    human_feedback: Optional[str]
    status: str
    errors: List[str]
    agent_logs: List[Dict[str, str]]
    current_step: Optional[str]
