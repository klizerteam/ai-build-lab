"""
schemas.py - the shape of the /chat request and response (validated by Pydantic).
"""
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Earlier messages in the conversation, so the assistant has context.
    history: list[ChatMessage] = Field(default_factory=list, max_length=50)


class ToolCallTrace(BaseModel):
    """One tool the backend ran, shown in the UI so you can see what happened."""
    name: str
    arguments: dict[str, Any]
    result: Any


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
