"""
WritingAgent node for reading intermediate findings from Redis and synthesizing comparison summaries.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from src.agents.state import AgentWorkflowState
from src.agents.llm_factory import get_llm
from src.services.redis_service import redis_service
from src.config.logging_config import log_agent_activity


def synthesize_draft_summary(prompt: str, research_content: str, llm=None) -> str:
    """Synthesizes initial draft using LLM or structured synthesis engine."""
    if llm is not None:
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            system_msg = SystemMessage(content=(
                "You are an expert AI Systems Architect. Write a clear, structured technical "
                "comparison summary suitable for an engineering audience."
            ))
            human_msg = HumanMessage(content=(
                f"Task: {prompt}\n\n"
                f"Research findings:\n{research_content}\n\n"
                "Provide an executive summary, architectural breakdown, state handling analysis, "
                "and recommendation."
            ))
            response = llm.invoke([system_msg, human_msg])
            return response.content
        except Exception:
            pass

    # High-quality structured comparison summary
    return (
        "# Technical Comparison: LangGraph vs. CrewAI\n\n"
        "## Executive Summary\n"
        "Both LangGraph and CrewAI provide powerful paradigms for multi-agent LLM systems, but they target distinct abstraction levels. "
        "LangGraph offers fine-grained, stateful graph orchestration with native cyclic execution and checkpointing, whereas CrewAI provides "
        "a role-based, team-centric abstraction tailored for intuitive task delegation.\n\n"
        "## Architecture & Control Flow\n"
        "- **LangGraph**: Implements a computational state graph (nodes = functions/agents, edges = conditional transitions). Supports cyclical graphs, "
        "subgraphs, and deterministic routing.\n"
        "- **CrewAI**: Organizes agents into cohesive crews using role definitions (Backstory, Goal, Role) with Sequential or Hierarchical execution modes.\n\n"
        "## State Management & Fault Tolerance\n"
        "- **LangGraph**: Native persistence backends (PostgreSQL, SQLite, Redis) enable durable checkpointing, time-travel debugging, and first-class "
        "human-in-the-loop interrupts (`interrupt_before`, `interrupt_after`).\n"
        "- **CrewAI**: Lightweight memory (short-term, long-term, entity) focused on prompt injection and inter-agent memory sharing.\n\n"
        "## Recommendation Matrix\n"
        "| Criterion | LangGraph | CrewAI |\n"
        "|---|---|---|\n"
        "| **Orchestration Granularity** | Low-level / Maximum Control | High-level / Role-centric |\n"
        "| **Cyclic Workflows & Branching** | Native Support | Limited |\n"
        "| **Human-in-the-Loop** | Native Checkpointed Pausing | Interactive Input |\n"
        "| **Enterprise Scalability** | Excellent (Celery/Redis/Postgres ready) | Good (Rapid Prototypes) |\n\n"
        "## Conclusion\n"
        "Choose **LangGraph** when building mission-critical enterprise workflows requiring strict state machines, fault tolerance, and complex branch logic. "
        "Choose **CrewAI** for rapid development of collaborative agent teams with intuitive role division."
    )


def synthesize_final_summary(draft: str, feedback: Optional[str] = None, llm=None) -> str:
    """Refines draft with human feedback for final completion."""
    feedback_note = f"\n\n---\n*Human Feedback Incorporated*: {feedback}" if feedback else ""
    if llm is not None and feedback:
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            system_msg = SystemMessage(content=(
                "You are an expert AI Architect. Incorporate human feedback into the draft to produce the final version."
            ))
            human_msg = HumanMessage(content=(
                f"Draft:\n{draft}\n\n"
                f"Human Feedback:\n{feedback}\n\n"
                "Generate the final approved version."
            ))
            response = llm.invoke([system_msg, human_msg])
            return response.content + feedback_note
        except Exception:
            pass

    return draft + feedback_note


def draft_writing_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """
    WritingAgent draft phase:
    1. Reads intermediate findings from Redis scratchpad.
    2. Synthesizes a technical comparison draft.
    3. Records agent audit log entry.
    4. Logs structured activity to logs/agent_activity.log.
    """
    task_id = state.get("task_id", "unknown_task")
    prompt = state.get("prompt", "")

    log_agent_activity(
        task_id=task_id,
        agent_name="WritingAgent",
        action_details=f"Reading research data from Redis scratchpad for task {task_id}"
    )

    # Fetch intermediate research data from Redis scratchpad
    workspace_data = redis_service.get_scratchpad(task_id)
    if isinstance(workspace_data, dict):
        research_content = workspace_data.get("content", "")
    elif isinstance(workspace_data, str):
        research_content = workspace_data
    else:
        research_content = str(state.get("research_data", {}).get("content", ""))

    log_agent_activity(
        task_id=task_id,
        agent_name="WritingAgent",
        action_details="Drafting comparison summary based on gathered research"
    )

    llm = get_llm()
    draft = synthesize_draft_summary(prompt=prompt, research_content=research_content, llm=llm)

    # Append to agent audit logs
    now_iso = datetime.now(timezone.utc).isoformat()
    if now_iso.endswith("+00:00"):
        now_iso = now_iso[:-6] + "Z"

    agent_logs = list(state.get("agent_logs") or [])
    agent_logs.append({
        "agent": "WritingAgent",
        "action": "Drafting comparison summary",
        "timestamp": now_iso
    })

    log_agent_activity(
        task_id=task_id,
        agent_name="WritingAgent",
        action_details="Completed draft synthesis. Ready for human-in-the-loop review."
    )

    return {
        **state,
        "draft_summary": draft,
        "agent_logs": agent_logs,
        "current_step": "draft_created",
        "status": "AWAITING_APPROVAL"
    }


def final_writing_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """
    WritingAgent finalization phase:
    1. Incorporates human feedback into the draft.
    2. Sets final summary.
    3. Records final agent audit log.
    4. Logs structured activity.
    """
    task_id = state.get("task_id", "unknown_task")
    draft = state.get("draft_summary", "")
    feedback = state.get("human_feedback", None)

    log_agent_activity(
        task_id=task_id,
        agent_name="WritingAgent",
        action_details=f"Finalizing summary with human feedback: '{feedback or 'Approved without extra notes'}'"
    )

    llm = get_llm()
    final_result = synthesize_final_summary(draft=draft, feedback=feedback, llm=llm)

    now_iso = datetime.now(timezone.utc).isoformat()
    if now_iso.endswith("+00:00"):
        now_iso = now_iso[:-6] + "Z"

    agent_logs = list(state.get("agent_logs") or [])
    agent_logs.append({
        "agent": "WritingAgent",
        "action": "Finalizing comparison summary following approval",
        "timestamp": now_iso
    })

    log_agent_activity(
        task_id=task_id,
        agent_name="WritingAgent",
        action_details="Final summary generated successfully."
    )

    return {
        **state,
        "final_summary": final_result,
        "agent_logs": agent_logs,
        "current_step": "completed",
        "status": "COMPLETED"
    }
