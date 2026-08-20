"""Server-rendered admin pages.

Jinja2 templates rather than a JavaScript app: it keeps the whole project in
Python with no build step, which is the right trade for an internal MVP panel.
Auth is HTTP Basic - enough to keep the panel closed, and an obvious swap point
for real SSO before this ever holds customer data.
"""

import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from app.agent.prompts import get_system_prompt, set_system_prompt
from app.config import settings
from app.database import query_all
from app.services import booking_service, escalation_service, faq_service, property_service

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")
security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """compare_digest instead of == so the check is not timing-attackable."""
    user_ok = secrets.compare_digest(credentials.username, settings.admin_username)
    password_ok = secrets.compare_digest(credentials.password, settings.admin_password)

    if not (user_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@router.get("")
def dashboard(request: Request, _=Depends(require_admin)):
    stats = {
        "conversations": len(query_all("SELECT id FROM conversations")),
        "messages": len(query_all("SELECT id FROM messages")),
        "bookings": len(booking_service.list_all()),
        "escalations": len([e for e in escalation_service.list_all()
                            if e["status"] == "open"]),
        "properties": len(property_service.list_all()),
        "faqs": len(faq_service.list_all()),
    }
    return templates.TemplateResponse(
        request, "dashboard.html",
        {"stats": stats, "model": settings.openai_model},
    )


@router.get("/prompt")
def prompt_page(request: Request, _=Depends(require_admin)):
    return templates.TemplateResponse(
        request, "prompt.html", {"prompt": get_system_prompt(), "saved": False},
    )


@router.post("/prompt")
def prompt_save(request: Request, system_prompt: str = Form(...),
                _=Depends(require_admin)):
    set_system_prompt(system_prompt)
    return templates.TemplateResponse(
        request, "prompt.html", {"prompt": system_prompt, "saved": True},
    )


@router.get("/conversations")
def conversations(request: Request, _=Depends(require_admin)):
    rows = query_all(
        "SELECT c.id, c.user_id, c.created_at, COUNT(m.id) AS message_count "
        "FROM conversations c LEFT JOIN messages m ON m.conversation_id = c.id "
        "GROUP BY c.id ORDER BY c.created_at DESC"
    )
    return templates.TemplateResponse(
        request, "conversations.html", {"conversations": rows},
    )


@router.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id: str, request: Request,
                        _=Depends(require_admin)):
    """The full trace of one conversation: user turn, tool JSON, assistant reply.

    This is the screen that makes the agent's tool choice visible.
    """
    messages = query_all(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,),
    )
    return templates.TemplateResponse(
        request, "conversation_detail.html",
        {"conversation_id": conversation_id, "messages": messages},
    )


@router.get("/properties")
def properties(request: Request, _=Depends(require_admin)):
    return templates.TemplateResponse(
        request, "properties.html",
        {"properties": property_service.list_all(),
         "bookings": booking_service.list_all()},
    )


@router.get("/escalations")
def escalations(request: Request, _=Depends(require_admin)):
    return templates.TemplateResponse(
        request, "escalations.html",
        {"escalations": escalation_service.list_all()},
    )


@router.post("/escalations/{escalation_id}/close")
def close_escalation(escalation_id: int, _=Depends(require_admin)):
    escalation_service.close(escalation_id)
    return RedirectResponse("/admin/escalations", status_code=303)
