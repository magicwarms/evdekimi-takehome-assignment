from fastapi import APIRouter

from app.agent.runner import run_agent
from app.logging_config import get_logger
from app.schemas import ChatRequest, ChatResponse, ErrorResponse

router = APIRouter(prefix="/api", tags=["chat"])
logger = get_logger(__name__)


@router.post("/chat", response_model=ChatResponse,
             responses={503: {"model": ErrorResponse}})
def chat(payload: ChatRequest):
    """Send one message to the assistant and get its reply.

    The endpoint is stateless: conversation state lives in the database, so any
    replica can serve any request. The response includes tools_used so callers
    can see which tool the model chose without reading the server logs.
    """
    logger.info("Chat request", extra={"extra_data": {
        "conversation_id": payload.conversation_id,
        "user_id": payload.user_id,
    }})

    result = run_agent(
        user_message=payload.message,
        conversation_id=payload.conversation_id,
        user_id=payload.user_id,
    )
    return ChatResponse(**result)
