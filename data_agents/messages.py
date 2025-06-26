from dataclasses import dataclass
from pydantic import BaseModel
from autogen_core.models import (
    UserMessage,
)

@dataclass
class Message:
    content: str


class GroupChatMessage(BaseModel):
    body: UserMessage


class RequestToSpeak(BaseModel):
    pass 

@dataclass
class TerminateMessage:
    content: str