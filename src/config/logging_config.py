"""
Structured JSON logging configuration for multi-agent observability.
Outputs machine-readable JSON logs for each agent step and action.
"""
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from src.config.settings import settings


class AgentJsonFormatter(logging.Formatter):
    """
    Custom JSON formatter ensuring strict compliance with required schema:
    {"timestamp": "...", "task_id": "...", "agent_name": "...", "action_details": "..."}
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        if timestamp.endswith("+00:00"):
            timestamp = timestamp[:-6] + "Z"

        task_id = getattr(record, "task_id", "N/A")
        agent_name = getattr(record, "agent_name", record.name)
        action_details = getattr(record, "action_details", record.getMessage())

        log_data = {
            "timestamp": timestamp,
            "task_id": str(task_id),
            "agent_name": str(agent_name),
            "action_details": str(action_details),
        }
        return json.dumps(log_data)


def setup_logging():
    """Configure root logger and dedicated agent activity file handler."""
    log_file_path = Path(settings.LOG_FILE_PATH)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    agent_logger = logging.getLogger("agent_activity")
    agent_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not any(isinstance(h, logging.FileHandler) and Path(h.baseFilename) == log_file_path.resolve() for h in agent_logger.handlers):
        file_handler = logging.FileHandler(str(log_file_path), mode="a", encoding="utf-8")
        file_handler.setFormatter(AgentJsonFormatter())
        agent_logger.addHandler(file_handler)

    # Also log to console for container logs
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(AgentJsonFormatter())
    agent_logger.addHandler(console_handler)

    return agent_logger


# Global agent activity logger
agent_logger = setup_logging()


def log_agent_activity(task_id: str, agent_name: str, action_details: str):
    """
    Helper function to log structured agent actions.
    Appends a formatted JSON line directly to logs/agent_activity.log and to logger.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    if timestamp.endswith("+00:00"):
        timestamp = timestamp[:-6] + "Z"

    entry = {
        "timestamp": timestamp,
        "task_id": str(task_id),
        "agent_name": str(agent_name),
        "action_details": str(action_details)
    }

    # Ensure log directory exists
    log_path = Path(settings.LOG_FILE_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
        f.flush()

    # Also pass through agent_logger
    agent_logger.info(
        action_details,
        extra={
            "task_id": str(task_id),
            "agent_name": str(agent_name),
            "action_details": str(action_details)
        }
    )
