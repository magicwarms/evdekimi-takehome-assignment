from fastapi import APIRouter

from app.agent.tools import ALL_TOOLS
from app.config import settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    """Liveness check. Also lists the registered tools, which makes it easy to
    confirm a newly added tool was picked up without reading the code."""
    return {
        "status": "ok",
        "model": settings.openai_model,
        "tools": [t.name for t in ALL_TOOLS],
    }
