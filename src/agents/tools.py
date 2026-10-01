"""
Tools for agents, including simulated research tool and flaky tool with retry logic.
"""
import time
import logging
from typing import Dict, Any
from src.config.logging_config import log_agent_activity

logger = logging.getLogger(__name__)

# State tracker for simulated flaky tool attempts
flaky_tool_attempts: Dict[str, int] = {}


def simulated_search_tool(query: str, task_id: str = "default") -> str:
    """
    Simulated search tool providing technical knowledge on AI orchestration frameworks,
    with built-in transient failure simulation for '__FLAKY_TEST__'.
    """
    clean_query = query.strip()

    # Flaky behavior requirement
    if "__FLAKY_TEST__" in clean_query:
        attempt_key = f"{task_id}:{clean_query}"
        attempts = flaky_tool_attempts.get(attempt_key, 0)
        if attempts == 0:
            flaky_tool_attempts[attempt_key] = 1
            raise Exception("Simulated transient network timeout.")
        return "Search results retrieved on second attempt."

    # Standard research knowledge base
    query_lower = clean_query.lower()
    if "langgraph" in query_lower or "crewai" in query_lower or "compare" in query_lower:
        return (
            "### Comprehensive Research Findings: LangGraph vs CrewAI\n\n"
            "**1. LangGraph (by LangChain):**\n"
            "- Architecture: Graph-based state machine allowing cyclical execution and multi-agent coordination.\n"
            "- State Management: Centralized typed state (TypedDict / Pydantic) with built-in persistence and time-travel.\n"
            "- Human-in-the-Loop: Native breakpoint and interrupt support (interrupt_before / interrupt_after).\n"
            "- Fine-Grained Control: Low-level flow control, conditional edges, custom branching, and subgraphs.\n"
            "- Use Case: Complex, deterministic, long-running agent workflows requiring strict orchestration and recovery.\n\n"
            "**2. CrewAI:**\n"
            "- Architecture: High-level role-based collaborative agent ensemble.\n"
            "- Agent Roles: Agents defined with specific Roles, Goals, and Backstories.\n"
            "- Execution Models: Sequential, Hierarchical, and Consensual delegation processes.\n"
            "- Tool Integration: Simple plug-and-play LangChain and custom tools.\n"
            "- Use Case: Rapid prototyping of role-playing agent crews for content generation, research, and ideation.\n\n"
            "**Key Comparison Dimensions:**\n"
            "- Control vs Abstraction: LangGraph offers lower-level control and state persistence; CrewAI offers intuitive higher-level abstractions.\n"
            "- State Persistence: LangGraph excels at checkpointing and fault tolerance for enterprise production systems.\n"
            "- Orchestration Style: LangGraph is graph/state-driven; CrewAI is role/task-driven."
        )

    return f"Simulated search results for query: '{clean_query}'. Key architectural patterns and operational best practices gathered."


def execute_search_with_retry(query: str, task_id: str, max_retries: int = 2) -> str:
    """
    Executes simulated_search_tool with automated retry logic and structured activity logging.
    """
    log_agent_activity(
        task_id=task_id,
        agent_name="ResearchAgent",
        action_details=f"Starting web search for '{query}'"
    )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                log_agent_activity(
                    task_id=task_id,
                    agent_name="ResearchAgent",
                    action_details=f"Retry attempt {attempt} for action: web search '{query}'"
                )
            result = simulated_search_tool(query=query, task_id=task_id)
            log_agent_activity(
                task_id=task_id,
                agent_name="ResearchAgent",
                action_details=f"Successfully completed web search for '{query}'"
            )
            return result
        except Exception as e:
            last_error = e
            log_agent_activity(
                task_id=task_id,
                agent_name="ResearchAgent",
                action_details=f"Tool failure encountered: {str(e)}. Initiating retry..."
            )
            time.sleep(0.1)

    raise last_error
