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


# The models below back the plain REST endpoints - the same services the agent's
# tools call, reachable over ordinary HTTP without going through the LLM.

class PropertyResponse(BaseModel):
    id: int
    title: str
    city: str
    district: Optional[str] = None
    property_type: str
    bedrooms: int
    price: int
    currency: str
    description: Optional[str] = None
    is_available: bool


class ViewingSlotsResponse(BaseModel):
    property_id: int
    slots: List[str] = Field(..., description="Slots not yet booked for this property.")


class BookingRequest(BaseModel):
    property_id: int = Field(..., ge=1)
    customer_name: str = Field(..., min_length=1, max_length=120)
    customer_phone: str = Field(..., min_length=5, max_length=40)
    slot: str = Field(..., description="One of the slots from GET /api/properties/{id}/slots.")


class BookingResponse(BaseModel):
    booking_id: int
    property_id: int
    property_title: str
    customer_name: str
    slot: str
    status: str
