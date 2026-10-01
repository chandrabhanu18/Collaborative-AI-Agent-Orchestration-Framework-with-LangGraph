"""
Pydantic schemas for API requests, responses, and validation.
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class AgentLogEntry(BaseModel):
    agent: str = Field(..., description="Agent name e.g. ResearchAgent or WritingAgent")
    action: str = Field(..., description="Description of the action taken")
    timestamp: str = Field(..., description="ISO 8601 timestamp string")


class TaskCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Initial prompt for collaborative agent task")


class TaskCreateResponse(BaseModel):
    task_id: str = Field(..., description="UUID of the created task")
    status: str = Field(default="PENDING", description="Initial status of the task")


class TaskDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Union[UUID, str]
    prompt: str
    status: str
    result: Optional[str] = None
    agent_logs: Optional[Union[List[Dict[str, Any]], List[AgentLogEntry], Dict[str, Any]]] = None
    created_at: Union[datetime, str]
    updated_at: Union[datetime, str]


class TaskApprovalRequest(BaseModel):
    approved: bool = Field(default=True, description="Whether the draft is approved")
    feedback: Optional[str] = Field(default=None, description="Optional human feedback for the draft")


class TaskApprovalResponse(BaseModel):
    task_id: str = Field(..., description="UUID of the resumed task")
    status: str = Field(default="RESUMED", description="Resumed status of the task")


class WebSocketStatusMessage(BaseModel):
    task_id: str
    status: str
