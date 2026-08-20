"""Business logic for handing a conversation to a human colleague."""

from datetime import datetime, timezone
from typing import List, Optional

from app.database import execute, query_all


def create(reason: str, summary: str = "",
           contact: Optional[str] = None,
           conversation_id: Optional[str] = None) -> dict:
    escalation_id = execute(
        "INSERT INTO escalations (conversation_id, reason, summary, contact, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (conversation_id, reason, summary, contact,
         datetime.now(timezone.utc).isoformat()),
    )
    return {
        "escalation_id": escalation_id,
        "status": "open",
        "message": "A human agent has been notified and will contact you shortly.",
    }


def list_all() -> List[dict]:
    return query_all("SELECT * FROM escalations ORDER BY id DESC")


def close(escalation_id: int) -> None:
    execute("UPDATE escalations SET status = 'closed' WHERE id = ?", (escalation_id,))
