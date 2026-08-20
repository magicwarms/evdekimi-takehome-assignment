"""Request and response shapes for the REST API.

Pydantic validates incoming bodies for us, so a bad request is rejected with a
422 before it ever reaches the agent - and never costs an LLM call.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000,
                         description="What the customer said.")
    conversation_id: Optional[str] = Field(
        None, description="Omit to start a new conversation.")
    user_id: Optional[str] = Field(
        None, description="Your own identifier for the customer, if you have one.")


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    tools_used: List[str] = Field(
        ..., description="Tools the model chose on this turn, in call order.")
    steps: int = Field(..., description="How many times the model was invoked.")


class ErrorResponse(BaseModel):
    error: str
    request_id: Optional[str] = None
