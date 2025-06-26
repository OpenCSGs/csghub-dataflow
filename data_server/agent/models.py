from pydantic import BaseModel
from typing import Literal
from autogen_core.models import (
    UserMessage,
)
from datetime import datetime, timezone

class TaskResult(BaseModel):
    """Result of running a task."""
    stop_reason: str | None = None
    """The reason the task stopped."""
    usage: str = "100 tokens"
    duration: float = 6000


class Message(BaseModel):
    type: Literal["system"] | Literal["message"] | Literal["input_request"]
    data: TaskResult | UserMessage = None
    status: Literal["complete"] | Literal["running"] | Literal["connected"] | Literal["cancelled"]
    timestamp: str = datetime.now(timezone.utc).isoformat()
