import json
from typing import Optional

from langchain_core.tools import tool

from app.services import escalation_service


@tool
def escalate_to_human(reason: str, summary: str,
                      contact: Optional[str] = None) -> str:
    """Hand the conversation over to a human colleague.

    Use this when the customer explicitly asks to speak to a person, when they
    are unhappy or frustrated, when they want to negotiate the price or discuss
    legal or mortgage details, or when you genuinely cannot help them with the
    other tools you have.

    Args:
        reason: Short category, for example "price negotiation" or
            "customer request".
        summary: One or two sentences a colleague can read to pick the
            conversation up where you left it.
        contact: The customer's phone number or email, if they have given one.
    """
    result = escalation_service.create(reason=reason, summary=summary, contact=contact)
    return json.dumps(result)
