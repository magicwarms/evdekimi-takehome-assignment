"""Business logic for the FAQ knowledge base."""

from typing import List

from app.database import query_all


def search(question: str, limit: int = 3) -> List[dict]:
    """Score each FAQ by how many of its keywords appear in the question.

    This is deliberately simple, and it is NOT the agent's routing logic - by the
    time we get here the model has already decided to ask about a policy question.
    Replacing this with embeddings or pgvector later changes only this function.
    """
    asked = question.lower()
    scored = []

    for faq in query_all("SELECT * FROM faqs"):
        keywords = [k.strip() for k in faq["keywords"].split(",") if k.strip()]
        score = sum(1 for keyword in keywords if keyword in asked)
        if score:
            scored.append((score, faq))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [faq for _, faq in scored[:limit]]


def list_all() -> List[dict]:
    return query_all("SELECT * FROM faqs ORDER BY id")
