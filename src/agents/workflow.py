"""
LangGraph workflow definition and orchestration logic.
Implements multi-agent state graph with human-in-the-loop interruption and resumption.
"""
from typing import Literal, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from src.agents.state import AgentWorkflowState
from src.agents.research_agent import research_node
from src.agents.writing_agent import draft_writing_node, final_writing_node
from src.config.logging_config import log_agent_activity


def approval_router(state: AgentWorkflowState) -> Literal["final_writing", "end"]:
    """Conditional edge router checking if human approval has been granted."""
    if state.get("human_approved", False):
        return "final_writing"
    return "end"


def build_agent_graph():
    """Builds and compiles the collaborative multi-agent StateGraph."""
    graph_builder = StateGraph(AgentWorkflowState)

    # Add agent nodes
    graph_builder.add_node("research", research_node)
    graph_builder.add_node("draft_writing", draft_writing_node)
    graph_builder.add_node("final_writing", final_writing_node)

    # Set workflow transitions
    graph_builder.set_entry_point("research")
    graph_builder.add_edge("research", "draft_writing")

    # Conditional edge for human-in-the-loop gate
    graph_builder.add_conditional_edges(
        "draft_writing",
        approval_router,
        {
            "final_writing": "final_writing",
            "end": END,
        }
    )
    graph_builder.add_edge("final_writing", END)

    return graph_builder.compile()


# Global compiled workflow graph
agent_graph = build_agent_graph()


def execute_phase1_workflow(task_id: str, prompt: str) -> AgentWorkflowState:
    """
    Executes Phase 1 of the workflow:
    ResearchAgent -> WritingAgent (draft) -> pauses at AWAITING_APPROVAL.
    """
    log_agent_activity(
        task_id=task_id,
        agent_name="Orchestrator",
        action_details=f"Starting LangGraph Phase 1 execution for prompt: '{prompt}'"
    )

    initial_state: AgentWorkflowState = {
        "task_id": task_id,
        "prompt": prompt,
        "human_approved": False,
        "human_feedback": None,
        "status": "RUNNING",
        "errors": [],
        "agent_logs": [],
        "current_step": "started"
    }

    result_state = agent_graph.invoke(initial_state)

    log_agent_activity(
        task_id=task_id,
        agent_name="Orchestrator",
        action_details=f"Phase 1 execution paused at status: {result_state.get('status')}"
    )
    return result_state


def execute_phase2_workflow(
    task_id: str,
    prompt: str,
    draft_summary: str,
    existing_agent_logs: Optional[list] = None,
    feedback: Optional[str] = None,
) -> AgentWorkflowState:
    """
    Executes Phase 2 of the workflow upon receiving human approval:
    WritingAgent finalization -> COMPLETED.
    """
    log_agent_activity(
        task_id=task_id,
        agent_name="Orchestrator",
        action_details=f"Resuming LangGraph execution with human feedback: '{feedback or 'None'}'"
    )

    resumed_state: AgentWorkflowState = {
        "task_id": task_id,
        "prompt": prompt,
        "draft_summary": draft_summary,
        "human_approved": True,
        "human_feedback": feedback,
        "status": "RESUMED",
        "errors": [],
        "agent_logs": list(existing_agent_logs or []),
        "current_step": "resuming"
    }

    # Execute final writing phase
    final_state = final_writing_node(resumed_state)

    log_agent_activity(
        task_id=task_id,
        agent_name="Orchestrator",
        action_details=f"LangGraph execution completed with status: {final_state.get('status')}"
    )
    return final_state
